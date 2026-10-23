"""
RepoReady - Terminal CLI Interface
Rich-powered terminal UI for static repo scanning, local SLM compliance auditing,
and automated repository remediation for Hacktoberfest.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from scanner import scan_repository
from auditor import run_audit
from fixer import heal_repository

console = Console(force_terminal=True, legacy_windows=False)


def get_score_color(score: int) -> str:
    if score >= 80:
        return "bold green"
    elif score >= 50:
        return "bold yellow"
    return "bold red"


def render_report(target_path: str, scan_data: dict, audit_report, fix_applied: Optional[dict] = None):
    # Header Banner
    console.print()
    banner = Text("🛡️  RepoReady: Open-Weight AI & Hacktoberfest Compliance Auditor", style="bold cyan")
    console.print(Panel(banner, subtitle="Powered by Google Gemma 2 (2B) Local SLM", border_style="cyan"))
    console.print()

    # Score Panel
    score = audit_report.readiness_score
    score_color = get_score_color(score)
    score_text = Text()
    score_text.append(f"  READINESS SCORE: {score}/100\n", style=score_color)
    score_text.append(f"  Target: {target_path}\n", style="dim")
    score_text.append(f"  License Status: {audit_report.license_status}\n", style="white")
    score_text.append(f"  Audit Engine: {audit_report.engine_used}\n", style="italic magenta")

    score_panel = Panel(score_text, title="📊 Compliance Evaluation", border_style=score_color.split()[-1])
    console.print(score_panel)
    console.print()

    # Detected AI Models Table
    models_table = Table(title="🤖 Detected AI Models & Licensing Attribution", header_style="bold magenta", expand=True)
    models_table.add_column("Model Name", style="bold white", width=22)
    models_table.add_column("Category", style="cyan", width=18)
    models_table.add_column("README Attributed?", style="bold", width=20)
    models_table.add_column("Required Terms of Use URL", style="blue")

    if audit_report.detected_ai_models:
        for m in audit_report.detected_ai_models:
            attr_style = "bold green" if m.terms_linked_in_readme else "bold red"
            attr_text = "✅ Linked" if m.terms_linked_in_readme else "❌ MISSING"
            models_table.add_row(m.model_name, m.classification, Text(attr_text, style=attr_style), m.required_license_url)
    else:
        models_table.add_row("None Detected", "N/A", "N/A", "N/A")

    console.print(models_table)
    console.print()

    # Critical Issues & Security Leaks
    issues_table = Table(title="⚠️  Critical Issues & Compliance Blockers", header_style="bold red", expand=True)
    issues_table.add_column("#", style="dim", width=4)
    issues_table.add_column("Description", style="white")

    all_issues = list(audit_report.critical_issues)
    sec = scan_data.get("security", {})
    if sec.get("secret_files"):
        all_issues.append(f"Secret / env files committed to repo: {', '.join(sec.get('secret_files'))}")

    if all_issues:
        for i, issue in enumerate(all_issues, 1):
            issues_table.add_row(str(i), issue)
    else:
        issues_table.add_row("✓", "No critical compliance blockers found! Fully Hacktoberfest ready.")

    console.print(issues_table)
    console.print()

    # Recommendations
    if audit_report.recommendations:
        recs_table = Table(title="💡 Actionable Recommendations", header_style="bold yellow", expand=True)
        recs_table.add_column("#", style="dim", width=4)
        recs_table.add_column("Action Item", style="white")
        for i, rec in enumerate(audit_report.recommendations, 1):
            recs_table.add_row(str(i), rec)
        console.print(recs_table)
        console.print()

    # Generated Patch Preview
    if audit_report.readme_patch_markdown:
        syntax = Syntax(audit_report.readme_patch_markdown[:600] + "\n...", "markdown", theme="monokai", line_numbers=False)
        patch_panel = Panel(syntax, title="📝 Generated README Patch (Open-Weight Attribution + Quickstart)", border_style="green")
        console.print(patch_panel)
        console.print()

    # Fix results if requested
    if fix_applied:
        fix_text = Text()
        fix_text.append(f"✓ {fix_applied.get('license_action')}\n", style="bold green")
        fix_text.append(f"✓ {fix_applied.get('readme_action')}\n", style="bold green")
        console.print(Panel(fix_text, title="✨ Auto-Healer Execution Results", border_style="bold green"))
        console.print()


def main():
    parser = argparse.ArgumentParser(description="RepoReady - Open-Weight AI & Hacktoberfest Compliance Auditor")
    parser.add_argument("path", nargs="?", default=".", help="Path to local repository or remote Git URL")
    parser.add_argument("--fix", "-f", action="store_true", help="Automatically generate missing LICENSE and patch README.md")
    parser.add_argument("--json", "-j", action="store_true", help="Output audit report as JSON")
    parser.add_argument("--license-type", default="MIT", choices=["MIT", "Apache-2.0"], help="Preferred license for auto-fix")
    parser.add_argument("--model", default="gemma2:2b", help="Ollama model to use for inference")
    args = parser.parse_args()

    target_path = args.path

    if args.json:
        scan_data = scan_repository(target_path)
        audit_report = run_audit(scan_data, prefer_ollama=True, model_name=args.model)
        output = {
            "target": target_path,
            "readiness_score": audit_report.readiness_score,
            "license_status": audit_report.license_status,
            "engine_used": audit_report.engine_used,
            "detected_ai_models": [m.model_dump() for m in audit_report.detected_ai_models],
            "critical_issues": audit_report.critical_issues,
            "recommendations": audit_report.recommendations,
            "readme_patch_markdown": audit_report.readme_patch_markdown,
            "security": scan_data.get("security", {})
        }
        print(json.dumps(output, indent=2))
        return

    with console.status("[bold cyan]Scanning repository and analyzing dependencies...", spinner="dots"):
        scan_data = scan_repository(target_path)

    with console.status(f"[bold magenta]Running local SLM compliance audit ({args.model})...", spinner="dots"):
        audit_report = run_audit(scan_data, prefer_ollama=True, model_name=args.model)

    fix_applied = None
    if args.fix:
        with console.status("[bold green]Auto-healing repository...", spinner="dots"):
            fix_applied = heal_repository(target_path, audit_report.model_dump(), preferred_license=args.license_type)

    render_report(target_path, scan_data, audit_report, fix_applied)


if __name__ == "__main__":
    main()
