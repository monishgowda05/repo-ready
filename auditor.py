"""
RepoReady - Open-Weight AI Compliance & Audit Engine
Leverages local Google Gemma 2 (2B) SLM via Ollama to evaluate open-source
licensing, open-weight attribution, and code safety with structured JSON output.
Includes a deterministic fallback engine so the audit NEVER crashes offline.
"""

import os
import sys
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "gemma2:2b")


class DetectedModelCompliance(BaseModel):
    model_name: str
    classification: str = Field(description="Open-Weight SLM, Open-Weight LLM, Proprietary, or Unknown")
    terms_linked_in_readme: bool
    required_license_url: str


class AuditReport(BaseModel):
    readiness_score: int = Field(ge=0, le=100, description="Compliance score from 0 to 100")
    license_status: str = Field(description="PASS, WARN, or FAIL with short explanation")
    detected_ai_models: List[DetectedModelCompliance] = Field(default_factory=list)
    critical_issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    readme_patch_markdown: str = Field(description="Markdown section to inject into README.md")
    engine_used: str = Field(default="gemma2:2b (Local SLM)")


def generate_patch_markdown(scan_data: Dict[str, Any]) -> str:
    """Generates the compliant README markdown block for open-weight attribution and quickstart."""
    models = scan_data.get("detected_ai_models", [])
    deps = scan_data.get("dependencies", {})
    license_type = scan_data.get("license", {}).get("license_type", "MIT")
    if license_type in ("MISSING", "UNKNOWN"):
        license_type = "MIT"

    lines = [
        "",
        "---",
        "",
        "## 🧠 Open-Weight AI Model & Licensing Attribution",
        "",
        f"> **Notice on Open-Weight vs. Open-Source Terms:**  ",
        f"> The source code in this repository is licensed under the **{license_type} License** (see `LICENSE`).  ",
        "> In accordance with Hacktoberfest and Responsible AI open standards, the open-weight machine learning models ",
        "> utilized herein are subject to their respective creators' model licenses and acceptable use policies.",
        "",
        "| Model Name | Category | Provider / Terms | Official License URL |",
        "| :--- | :--- | :--- | :--- |",
    ]

    if models:
        for m in models:
            terms_url = m.get("terms_url", "https://huggingface.co")
            cat = m.get("category", "Open-Weight")
            name = m.get("model_name", "AI Model")
            lines.append(f"| **{name}** | {cat} | Provider Terms | [Terms of Use]({terms_url}) |")
    else:
        lines.append("| **Google Gemma 2 (2B)** | Open-Weight SLM | Google Gemma Terms | [ai.google.dev/gemma/terms](https://ai.google.dev/gemma/terms) |")

    # Quickstart Guide tailored to dependencies
    lines.extend([
        "",
        "## ⚡ Quickstart & Reproducibility (Judge Guide)",
        "",
        "### 1. Prerequisites",
        "- Python 3.10+ installed",
    ])

    has_ollama = "ollama" in scan_data.get("ai_frameworks_detected", {})
    if has_ollama:
        lines.append("- [Ollama](https://ollama.com) installed and running locally")

    lines.extend([
        "",
        "### 2. Environment Setup",
        "```bash",
        "# Clone the repository",
        "git clone <repository-url>",
        "cd <repository-directory>",
        "",
        "# Create and activate virtual environment",
        "python -m venv venv",
        "# Windows:",
        "venv\\Scripts\\activate",
        "# Linux / macOS:",
        "source venv/bin/activate",
        "",
        "# Install dependencies",
    ])

    if deps.get("requirements_txt"):
        lines.append("pip install -r requirements.txt")
    else:
        lines.append("pip install -r requirements.txt")

    if has_ollama:
        lines.extend([
            "",
            "# Pull the required open-weight model",
            "ollama pull gemma2:2b",
        ])

    lines.extend([
        "```",
        "",
        "### 3. Running the Application",
        "```bash",
        "python main.py",
        "```",
        "",
    ])

    return "\n".join(lines)


def deterministic_audit(scan_data: Dict[str, Any]) -> AuditReport:
    """
    Deterministic fallback compliance analyzer.
    Follows Hacktoberfest evaluation rules strictly when Ollama is unavailable.
    """
    score = 100
    critical_issues = []
    recommendations = []
    models_compliance = []

    # 1. License Check
    license_info = scan_data.get("license", {})
    has_license = license_info.get("has_license", False)
    license_type = license_info.get("license_type", "MISSING")

    if not has_license:
        score -= 28
        license_status = "FAIL: No LICENSE file detected in repository root."
        critical_issues.append("Missing LICENSE file. An open-source repository must have a recognized OSI license.")
        recommendations.append("Generate a standard MIT or Apache-2.0 LICENSE file.")
    elif license_type in ("UNKNOWN", "MISSING"):
        score -= 15
        license_status = f"WARN: Non-standard or unrecognized license text in {license_info.get('filename')}."
        critical_issues.append("Unrecognized license format. Confirm standard OSI terms.")
    else:
        license_status = f"PASS: Valid {license_type} license found in {license_info.get('filename')}."

    # 2. README Check
    readme_info = scan_data.get("readme", {})
    has_readme = readme_info.get("has_readme", False)
    char_count = readme_info.get("char_count", 0)

    if not has_readme:
        score -= 20
        critical_issues.append("Missing README.md file. Judges cannot verify project purpose or quickstart.")
        recommendations.append("Create a comprehensive README.md with project description and setup instructions.")
    elif char_count < 120:
        score -= 12
        critical_issues.append("README.md is severely lacking documentation (<120 characters).")
        recommendations.append("Expand README.md to include reproduction steps and attribution.")

    # 3. Open-Weight Model Attribution
    detected_models = scan_data.get("detected_ai_models", [])
    unattributed_penalty = 0
    for m in detected_models:
        name = m.get("model_name", "Unknown")
        cat = m.get("category", "Open-Weight")
        attributed = m.get("terms_linked_in_readme", False)
        terms_url = m.get("terms_url", "")

        models_compliance.append(DetectedModelCompliance(
            model_name=name,
            classification=cat,
            terms_linked_in_readme=attributed,
            required_license_url=terms_url
        ))

        if not attributed and cat in ("Open-Weight SLM", "Open-Weight LLM"):
            unattributed_penalty += 12
            critical_issues.append(
                f"Open-Weight model '{name}' detected in code without provider license attribution in README.md. "
                f"Model weights are not governed by code license (MIT) and require linking {terms_url}."
            )
            recommendations.append(f"Add Open-Weight attribution block linking to {terms_url} in README.md.")

    score -= min(24, unattributed_penalty)

    # 4. Security Leaks
    sec = scan_data.get("security", {})
    if sec.get("secret_files"):
        score -= 16
        critical_issues.append(f"Accidentally committed secret/env files: {sec.get('secret_files')}")
        recommendations.append("Remove sensitive environment files from Git history and add them to .gitignore.")

    if sec.get("secret_leaks"):
        score -= 12
        critical_issues.append(f"Possible hardcoded credentials detected in {len(sec.get('secret_leaks'))} code lines.")
        recommendations.append("Move hardcoded API tokens or private keys to environment variables.")

    # Clamp score
    score = max(0, min(100, score))

    patch = generate_patch_markdown(scan_data)

    return AuditReport(
        readiness_score=score,
        license_status=license_status,
        detected_ai_models=models_compliance,
        critical_issues=critical_issues,
        recommendations=recommendations,
        readme_patch_markdown=patch,
        engine_used="Deterministic Heuristic Analyzer (Local Fallback)"
    )


def is_ollama_running(host: str = "127.0.0.1", port: int = 11434, timeout: float = 0.8) -> bool:
    """Instantly checks if local Ollama daemon is reachable on its default port."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def is_model_installed(model_name: str = DEFAULT_MODEL) -> bool:
    """Checks if the requested model is actually downloaded and ready in Ollama."""
    if not is_ollama_running():
        return False
    try:
        import ollama
        models = ollama.list()
        # Handle both dict and object response formats from ollama python library
        model_list = models.get("models", []) if isinstance(models, dict) else getattr(models, "models", [])
        for m in model_list:
            name = m.get("name", "") if isinstance(m, dict) else getattr(m, "model", "")
            if model_name in name:
                return True
        return False
    except Exception:
        return False


def audit_with_ollama(scan_data: Dict[str, Any], model_name: str = DEFAULT_MODEL) -> AuditReport:
    """
    Performs audit using local Ollama model (e.g. gemma2:2b).
    Falls back gracefully to deterministic audit if Ollama or model is unavailable.
    """
    if not is_ollama_running() or not is_model_installed(model_name):
        return deterministic_audit(scan_data)

    try:
        import ollama

        # Prepare succinct prompt payload
        models_summary = [
            f"{m.get('model_name')} ({m.get('category')}) - Attributed: {m.get('terms_linked_in_readme')}"
            for m in scan_data.get("detected_ai_models", [])
        ]
        
        prompt = f"""
You are RepoReady, an expert open-source compliance auditor for Hacktoberfest and AI hackathons.
Audit the following repository scan for Open-Source License compliance, Open-Weight AI attribution, and Secret leaks.

REPOSITORY SCAN DATA:
- Target: {scan_data.get('target')}
- License File: {scan_data.get('license', {}).get('filename')} (Type: {scan_data.get('license', {}).get('license_type')})
- README Present: {scan_data.get('readme', {}).get('has_readme')} (Chars: {scan_data.get('readme', {}).get('char_count')})
- README Snippet: {scan_data.get('readme', {}).get('content_preview')}
- Detected AI Models in Code: {json.dumps(models_summary)}
- Frameworks: {list(scan_data.get('ai_frameworks_detected', {}).keys())}
- Leaked Secrets/Env: {scan_data.get('security', {}).get('secret_files')}

AUDIT CRITERIA:
1. Open-source code license: A missing LICENSE drops 35 points.
2. Open-Weight vs Open-Source confusion: Using Llama, Gemma, or Mistral weights without explicitly linking their provider terms of use drops 25 points.
3. Secret files committed: Drops 20 points.
4. Calculate a realistic readiness_score between 0 and 100.
5. Provide a complete, ready-to-append `readme_patch_markdown` with an attribution table and reproducibility quickstart.

Output strictly valid JSON matching this schema:
{{
  "readiness_score": <int 0-100>,
  "license_status": "<PASS|WARN|FAIL>: <explanation>",
  "detected_ai_models": [
    {{
      "model_name": "<name>",
      "classification": "<Open-Weight SLM|Open-Weight LLM|Proprietary|Unknown>",
      "terms_linked_in_readme": <bool>,
      "required_license_url": "<url>"
    }}
  ],
  "critical_issues": ["<issue 1>", "<issue 2>"],
  "recommendations": ["<rec 1>", "<rec 2>"],
  "readme_patch_markdown": "<markdown string>"
}}
"""
        response = ollama.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": 0.1}
        )

        content = response["message"]["content"]
        data = json.loads(content)

        # Enforce patch markdown existence
        if not data.get("readme_patch_markdown") or len(data.get("readme_patch_markdown", "")) < 50:
            data["readme_patch_markdown"] = generate_patch_markdown(scan_data)

        report = AuditReport(**data, engine_used=f"{model_name} (Local Ollama SLM)")
        return report

    except Exception:
        # Fall back cleanly so the demo never fails
        return deterministic_audit(scan_data)


def run_audit(scan_data: Dict[str, Any], prefer_ollama: bool = True, model_name: str = DEFAULT_MODEL) -> AuditReport:
    """Entry point for running the audit with fallback handling."""
    if prefer_ollama:
        return audit_with_ollama(scan_data, model_name=model_name)
    return deterministic_audit(scan_data)
