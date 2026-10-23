"""
RepoReady - Static + AST-Lite Repository Scanner
Scans Git repositories for open-weight AI models, license presence,
dependencies, README documentation, and security leaks.
"""

import os
import re
import sys
import json
import shutil
import tempfile
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Supported file extensions for code and config scanning
CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".sh", ".yaml", ".yml",
    ".json", ".ipynb", ".toml", ".env", ".txt", ".md"
}

# Directories to ignore
IGNORE_DIRS = {
    ".git", "venv", ".venv", "env", "node_modules", "__pycache__",
    ".idea", ".vscode", "dist", "build", ".pytest_cache", ".temp_clones"
}

# Files that contain pattern definitions themselves (avoid self-detection)
SELF_SCAN_EXCLUDE = {"scanner.py"}

# AI Frameworks and Model Patterns
AI_FRAMEWORK_PATTERNS = {
    "ollama": re.compile(r"\b(import\s+ollama|from\s+ollama|ollama\.chat|ollama\.generate|ollama\s+run|ollama\s+pull)\b", re.IGNORECASE),
    "transformers": re.compile(r"\b(import\s+transformers|from\s+transformers|AutoModel|AutoTokenizer|pipeline\s*\(|AutoModelForCausalLM)\b", re.IGNORECASE),
    "vllm": re.compile(r"\b(import\s+vllm|from\s+vllm|LLM\s*\(|SamplingParams)\b", re.IGNORECASE),
    "gguf": re.compile(r"\b(\.gguf|llama_cpp|LlamaCpp|ctransformers)\b", re.IGNORECASE),
    "huggingface": re.compile(r"\b(huggingface_hub|from_pretrained|hf_hub_download)\b", re.IGNORECASE),
    "torch": re.compile(r"\b(import\s+torch|from\s+torch)\b", re.IGNORECASE),
}

# Known Open-Weight and Proprietary Models Detection
MODEL_SIGNATURES = [
    {
        "pattern": re.compile(r"(google/gemma-2-[0-9]+b|gemma-2-[0-9]+b[-a-z]*|gemma2:[0-9]+b|gemma:[0-9]+b|google/gemma)", re.IGNORECASE),
        "name": "Google Gemma 2",
        "family": "Gemma",
        "category": "Open-Weight SLM",
        "params": "2B / 9B / 27B",
        "terms_url": "https://ai.google.dev/gemma/terms",
        "hf_url": "https://huggingface.co/google/gemma-2-2b-it",
    },
    {
        "pattern": re.compile(r"(meta-llama/Llama-3\.[0-9]-[0-9]+b|llama-3\.[0-9]-[0-9]+b|llama3\.[0-9]:[0-9]+b|meta-llama/Llama-2|llama-2-[0-9]+b)", re.IGNORECASE),
        "name": "Meta Llama 3",
        "family": "Llama",
        "category": "Open-Weight LLM",
        "params": "1B / 3B / 8B / 70B",
        "terms_url": "https://llama.meta.com/llama3/license/",
        "hf_url": "https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct",
    },
    {
        "pattern": re.compile(r"(mistralai/Mistral-7B|mistral-7b|mistral:[0-9]+b|mixtral-[0-9]+x[0-9]+b|mistralai/Mixtral)", re.IGNORECASE),
        "name": "Mistral / Mixtral",
        "family": "Mistral",
        "category": "Open-Weight LLM",
        "params": "7B / 8x7B",
        "terms_url": "https://mistral.ai/terms/",
        "hf_url": "https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3",
    },
    {
        "pattern": re.compile(r"(Qwen/Qwen2\.[0-9]-[0-9]+b|qwen2\.[0-9]:[0-9]+b|qwen2:[0-9]+b|qwen-[0-9]+b)", re.IGNORECASE),
        "name": "Qwen 2.5",
        "family": "Qwen",
        "category": "Open-Weight LLM",
        "params": "0.5B / 1.5B / 7B / 14B / 72B",
        "terms_url": "https://github.com/QwenLM/Qwen2.5/blob/main/LICENSE",
        "hf_url": "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct",
    },
    {
        "pattern": re.compile(r"(deepseek-ai/DeepSeek-R1|deepseek-r1|deepseek-coder|deepseek-v2)", re.IGNORECASE),
        "name": "DeepSeek R1 / V2",
        "family": "DeepSeek",
        "category": "Open-Weight LLM",
        "params": "1.5B - 671B",
        "terms_url": "https://github.com/deepseek-ai/DeepSeek-V2/blob/main/LICENSE-MODEL",
        "hf_url": "https://huggingface.co/deepseek-ai/DeepSeek-R1",
    },
    {
        "pattern": re.compile(r"(microsoft/phi-3|phi-3|phi-3\.5|phi-4|phi-2)", re.IGNORECASE),
        "name": "Microsoft Phi-3/4",
        "family": "Phi",
        "category": "Open-Weight SLM",
        "params": "3.8B / 14B",
        "terms_url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct/blob/main/LICENSE",
        "hf_url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct",
    },
    {
        "pattern": re.compile(r"(gpt-4o|gpt-4-turbo|gpt-3\.5-turbo|claude-3|claude-3\.5)", re.IGNORECASE),
        "name": "Proprietary Commercial API",
        "family": "Commercial",
        "category": "Proprietary",
        "params": "Unknown (Cloud API)",
        "terms_url": "https://openai.com/policies/terms-of-use",
        "hf_url": "",
    }
]

# Sensitive/Secret File Signatures
SECRET_FILE_PATTERNS = [
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r".*\.(pem|key|pkcs12|pfx|id_rsa)$", re.IGNORECASE),
    re.compile(r"^(credentials|service_account|secret).*\.json$", re.IGNORECASE),
]

# Suspicious Secret Line Signatures
SECRET_CONTENT_PATTERNS = [
    re.compile(r"(API_KEY|SECRET_KEY|AUTH_TOKEN|PRIVATE_KEY|AWS_SECRET_ACCESS_KEY)\s*=\s*['\"][A-Za-z0-9_\-\.]{8,}['\"]", re.IGNORECASE),
    re.compile(r"-----BEGIN (RSA|EC|OPENSSH|DSA|PRIVATE) KEY-----"),
    re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"),
]


def is_git_url(path: str) -> bool:
    """Checks whether the given string is a remote Git URL."""
    return path.startswith("http://") or path.startswith("https://") or path.startswith("git@")


def clone_remote_repo(url: str) -> str:
    """Clones a remote git repo into a temporary folder."""
    temp_dir = tempfile.mkdtemp(prefix="repo_ready_clone_")
    try:
        import git
        git.Repo.clone_from(url, temp_dir, depth=1)
        return temp_dir
    except Exception as e:
        # Fallback to subprocess if gitpython encounters an issue
        import subprocess
        res = subprocess.run(["git", "clone", "--depth", "1", url, temp_dir], capture_output=True, text=True)
        if res.returncode != 0:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"Failed to clone git repository {url}: {res.stderr}")
        return temp_dir


def detect_license(root_path: Path) -> Dict[str, Any]:
    """Inspects the repo for LICENSE file and identifies its license type."""
    license_files = ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md", "LICENCE"]
    found_file = None
    content = ""
    
    for filename in license_files:
        candidate = root_path / filename
        if candidate.is_file():
            found_file = filename
            try:
                content = candidate.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                content = ""
            break

    if not found_file:
        return {
            "has_license": False,
            "filename": None,
            "license_type": "MISSING",
            "snippet": ""
        }

    # License type heuristic
    content_upper = content.upper()
    license_type = "UNKNOWN"
    if "MIT LICENSE" in content_upper or "PERMISSION IS HEREBY GRANTED, FREE OF CHARGE" in content_upper:
        license_type = "MIT"
    elif "APACHE LICENSE" in content_upper and "VERSION 2.0" in content_upper:
        license_type = "Apache-2.0"
    elif "GNU GENERAL PUBLIC LICENSE" in content_upper:
        if "VERSION 3" in content_upper:
            license_type = "GPL-3.0"
        elif "VERSION 2" in content_upper:
            license_type = "GPL-2.0"
        else:
            license_type = "GPL"
    elif "BSD" in content_upper and "REDISTRIBUTION AND USE" in content_upper:
        license_type = "BSD"
    elif "MOZILLA PUBLIC LICENSE" in content_upper:
        license_type = "MPL-2.0"
    elif "CREATIVE COMMONS" in content_upper:
        license_type = "CC"

    return {
        "has_license": True,
        "filename": found_file,
        "license_type": license_type,
        "snippet": content[:300].strip()
    }


def read_readme(root_path: Path) -> Dict[str, Any]:
    """Locates and reads README.md or variant."""
    readme_files = ["README.md", "README.rst", "README.txt", "readme.md", "Readme.md"]
    found_file = None
    content = ""

    for filename in readme_files:
        candidate = root_path / filename
        if candidate.is_file():
            found_file = filename
            try:
                content = candidate.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                content = ""
            break

    return {
        "has_readme": bool(found_file),
        "filename": found_file,
        "content": content,
        "char_count": len(content),
    }


def find_dependencies(root_path: Path) -> Dict[str, List[str]]:
    """Extracts package dependency listings."""
    deps: Dict[str, List[str]] = {
        "requirements_txt": [],
        "pyproject_toml": [],
        "package_json": [],
    }

    req_file = root_path / "requirements.txt"
    if req_file.is_file():
        try:
            lines = [line.strip() for line in req_file.read_text(encoding="utf-8", errors="ignore").splitlines()]
            deps["requirements_txt"] = [l for l in lines if l and not l.startswith("#")]
        except Exception:
            pass

    pyproject_file = root_path / "pyproject.toml"
    if pyproject_file.is_file():
        try:
            content = pyproject_file.read_text(encoding="utf-8", errors="ignore")
            deps["pyproject_toml"] = re.findall(r'["\']([a-zA-Z0-9_\-\.\>=\<\~]+)["\']', content)[:30]
        except Exception:
            pass

    pkg_file = root_path / "package.json"
    if pkg_file.is_file():
        try:
            data = json.loads(pkg_file.read_text(encoding="utf-8", errors="ignore"))
            pkg_deps = list(data.get("dependencies", {}).keys()) + list(data.get("devDependencies", {}).keys())
            deps["package_json"] = pkg_deps
        except Exception:
            pass

    return deps


def scan_repository(target: str) -> Dict[str, Any]:
    """
    Performs the full static and AST-lite scan of a repo.
    Accepts local path or remote Git URL.
    """
    is_remote = is_git_url(target)
    temp_dir: Optional[str] = None

    if is_remote:
        scan_path = Path(clone_remote_repo(target))
        temp_dir = str(scan_path)
    else:
        scan_path = Path(target).resolve()
        if not scan_path.exists():
            raise FileNotFoundError(f"Target path does not exist: {target}")

    try:
        file_tree: List[str] = []
        code_files: List[Path] = []
        secret_files_found: List[str] = []
        secret_leaks_in_code: List[Dict[str, Any]] = []

        # Walk filesystem
        for root, dirs, files in os.walk(scan_path):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".git")]

            rel_root = os.path.relpath(root, scan_path)
            prefix = "" if rel_root == "." else rel_root

            for f in files:
                rel_file_path = os.path.join(prefix, f).replace("\\", "/")
                file_tree.append(rel_file_path)

                # Check secret file names (ignore test fixture directories if scanning repo root)
                is_fixture = "demo_broken_project" in rel_file_path or "fixtures" in rel_file_path
                if not (scan_path.name != "demo_broken_project" and is_fixture):
                    for pat in SECRET_FILE_PATTERNS:
                        if pat.match(f):
                            secret_files_found.append(rel_file_path)
                            break

                p = Path(root) / f
                if p.suffix.lower() in CODE_EXTENSIONS and f not in SELF_SCAN_EXCLUDE:
                    code_files.append(p)

        # License & README
        license_info = detect_license(scan_path)
        readme_info = read_readme(scan_path)
        deps = find_dependencies(scan_path)

        # Scrape models & frameworks
        detected_models: Dict[str, Dict[str, Any]] = {}
        detected_frameworks: Dict[str, List[str]] = {k: [] for k in AI_FRAMEWORK_PATTERNS}

        for file_path in code_files:
            rel_path = os.path.relpath(file_path, scan_path).replace("\\", "/")
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Check framework imports
            for fw, pat in AI_FRAMEWORK_PATTERNS.items():
                if pat.search(text):
                    if rel_path not in detected_frameworks[fw]:
                        detected_frameworks[fw].append(rel_path)

            # Check models
            lines = text.splitlines()
            for line_no, line in enumerate(lines, 1):
                # Check for sensitive leaked credentials in code
                for sec_pat in SECRET_CONTENT_PATTERNS:
                    if sec_pat.search(line):
                        secret_leaks_in_code.append({
                            "file": rel_path,
                            "line": line_no,
                            "snippet": line[:80].strip()
                        })

                # Check model signatures
                for mod in MODEL_SIGNATURES:
                    m = mod["pattern"].search(line)
                    if m:
                        matched_str = m.group(0)
                        model_name = mod["name"]
                        if model_name not in detected_models:
                            detected_models[model_name] = {
                                "model_name": model_name,
                                "matched_token": matched_str,
                                "family": mod["family"],
                                "category": mod["category"],
                                "params": mod["params"],
                                "terms_url": mod["terms_url"],
                                "hf_url": mod["hf_url"],
                                "occurrences": []
                            }
                        detected_models[model_name]["occurrences"].append({
                            "file": rel_path,
                            "line": line_no,
                            "text": line[:100].strip()
                        })

        # Check README attribution
        readme_text = readme_info.get("content", "").lower()
        for mod_name, mod_data in detected_models.items():
            terms_url = mod_data["terms_url"].lower()
            family_name = mod_data["family"].lower()
            
            # Checks if either terms URL, HF URL or explicit terms are linked in README
            is_attributed = False
            if terms_url and terms_url in readme_text:
                is_attributed = True
            elif family_name in readme_text and ("terms" in readme_text or "license" in readme_text):
                is_attributed = True

            mod_data["terms_linked_in_readme"] = is_attributed

        result = {
            "target": str(scan_path),
            "is_remote": is_remote,
            "total_files": len(file_tree),
            "file_tree": file_tree[:100],  # cap for summary
            "license": license_info,
            "readme": {
                "has_readme": readme_info["has_readme"],
                "filename": readme_info["filename"],
                "char_count": readme_info["char_count"],
                "content_preview": readme_info["content"][:800],
                "full_content": readme_info["content"],
            },
            "dependencies": deps,
            "ai_frameworks_detected": {k: v for k, v in detected_frameworks.items() if v},
            "detected_ai_models": list(detected_models.values()),
            "security": {
                "secret_files": secret_files_found,
                "secret_leaks": secret_leaks_in_code[:10],
            }
        }

        return result

    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="RepoReady Static + AST-Lite Repository Scanner")
    parser.add_argument("--path", "-p", default=".", help="Local path or remote Git URL to scan")
    parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON results")
    args = parser.parse_args()

    try:
        report = scan_repository(args.path)
        if args.json:
            # Drop full content from standard CLI JSON to avoid massive output
            report_clean = dict(report)
            report_clean["readme"] = {k: v for k, v in report["readme"].items() if k != "full_content"}
            print(json.dumps(report_clean, indent=2))
        else:
            print(f"=== RepoReady Scan: {report['target']} ===")
            print(f"Total Files: {report['total_files']}")
            print(f"License: {report['license']['license_type']} (File: {report['license']['filename']})")
            print(f"README Present: {report['readme']['has_readme']} ({report['readme']['char_count']} chars)")
            print(f"AI Models Detected: {len(report['detected_ai_models'])}")
            for m in report['detected_ai_models']:
                print(f" - {m['model_name']} ({m['category']}) -> Attributed in README: {m['terms_linked_in_readme']}")
            if report['security']['secret_files']:
                print(f"WARNING: Sensitive files detected: {report['security']['secret_files']}")
    except Exception as e:
        print(f"Error scanning repository: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
