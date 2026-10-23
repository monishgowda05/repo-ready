"""
RepoReady - One-Click Auto-Healer
Automatically generates missing standard LICENSE files and safely injects
Open-Weight AI Model Attribution + Judge Quickstart sections into README.md.
"""

import os
from pathlib import Path
from typing import Dict, Any, Tuple

MIT_LICENSE_TEMPLATE = """MIT License

Copyright (c) 2026 RepoReady Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

APACHE_LICENSE_TEMPLATE = """                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   Copyright 2026 RepoReady Contributors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""


def apply_license_fix(target_path: Path, license_type: str = "MIT", overwrite: bool = False) -> Tuple[bool, str]:
    """Generates standard LICENSE if missing."""
    target_path = Path(target_path)
    license_file = target_path / "LICENSE"

    if license_file.exists() and not overwrite:
        return False, f"Existing LICENSE file found at {license_file}. Skipped overwrite for safety."

    template = APACHE_LICENSE_TEMPLATE if license_type.upper() == "APACHE-2.0" else MIT_LICENSE_TEMPLATE
    try:
        license_file.write_text(template, encoding="utf-8")
        return True, f"Successfully created standard {license_type} LICENSE file at {license_file}."
    except Exception as e:
        return False, f"Failed to create LICENSE file: {e}"


def apply_readme_fix(target_path: Path, patch_markdown: str) -> Tuple[bool, str]:
    """Safely appends or prepends attribution and quickstart blocks into README.md."""
    target_path = Path(target_path)
    readme_candidates = ["README.md", "readme.md", "README.rst", "README.txt"]
    target_readme = None

    for candidate in readme_candidates:
        candidate_path = target_path / candidate
        if candidate_path.exists():
            target_readme = candidate_path
            break

    if not target_readme:
        target_readme = target_path / "README.md"
        content = "# Project Documentation\n\nGenerated with RepoReady Compliance Auto-Healer.\n"
    else:
        try:
            content = target_readme.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            content = ""

    # Avoid duplicate attribution sections if already present
    if "## 🧠 Open-Weight AI Model & Licensing Attribution" in content:
        return False, "Attribution section already present in README.md. Skipped to prevent duplicates."

    new_content = content.rstrip() + "\n" + patch_markdown.lstrip() + "\n"

    try:
        target_readme.write_text(new_content, encoding="utf-8")
        return True, f"Successfully patched {target_readme.name} with Open-Weight Attribution & Quickstart."
    except Exception as e:
        return False, f"Failed to patch README: {e}"


def heal_repository(target_path: str, audit_report_data: Dict[str, Any], preferred_license: str = "MIT") -> Dict[str, Any]:
    """
    Executes the full automated healing process on a target repository:
    1. Injects missing LICENSE file.
    2. Injects Open-Weight attribution & reproducibility quickstart in README.md.
    """
    path_obj = Path(target_path).resolve()
    if not path_obj.exists():
        raise FileNotFoundError(f"Target repository path not found: {target_path}")

    results = {
        "license_action": None,
        "readme_action": None,
        "success": False
    }

    # 1. License healing
    license_created, license_msg = apply_license_fix(path_obj, license_type=preferred_license)
    results["license_action"] = license_msg

    # 2. README healing
    patch_md = audit_report_data.get("readme_patch_markdown", "")
    if patch_md:
        readme_patched, readme_msg = apply_readme_fix(path_obj, patch_md)
        results["readme_action"] = readme_msg
    else:
        results["readme_action"] = "No patch markdown provided in audit report."

    results["success"] = True
    return results
