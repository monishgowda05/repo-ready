"""
RepoReady - Streamlit Web Dashboard
Interactive web interface for auditing repositories for open-source licensing,
detecting open-weight AI models, viewing side-by-side diffs, and auto-healing repos.
"""

import os
import sys
import json
from pathlib import Path

# Configure Windows UTF-8 stdout if needed
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import streamlit as st
import pandas as pd

from scanner import scan_repository
from auditor import run_audit, is_ollama_running, is_model_installed
from fixer import heal_repository

# Page configuration
st.set_page_config(
    page_title="RepoReady | Open-Weight AI Compliance Auditor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Sleek Dark Cyber Aesthetic
st.markdown("""
<style>
    /* Metric Card Styling */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.8));
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        backdrop-filter: blur(4px);
    }
    .metric-value-green {
        font-size: 3rem;
        font-weight: 800;
        color: #10B981;
        margin: 0;
    }
    .metric-value-yellow {
        font-size: 3rem;
        font-weight: 800;
        color: #F59E0B;
        margin: 0;
    }
    .metric-value-red {
        font-size: 3rem;
        font-weight: 800;
        color: #EF4444;
        margin: 0;
    }
    .metric-label {
        font-size: 1rem;
        color: #94A3B8;
        font-weight: 500;
        margin-top: 5px;
    }
    .badge-pass {
        background-color: #065F46;
        color: #D1FAE5;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
    }
    .badge-fail {
        background-color: #991B1B;
        color: #FEE2E2;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
    }
    .badge-warn {
        background-color: #92400E;
        color: #FEF3C7;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def reset_demo_repo(target_dir: str = "./demo_broken_project"):
    """Resets the demo folder back to its intentionally broken state for live judging."""
    demo_path = Path(target_dir)
    if not demo_path.exists():
        demo_path.mkdir(parents=True, exist_ok=True)
    
    # 1. Remove LICENSE
    lic = demo_path / "LICENSE"
    if lic.exists():
        try:
            lic.unlink()
        except Exception:
            pass

    # 2. Reset README.md to lazy text
    readme = demo_path / "README.md"
    readme.write_text("# My Cool AI Hackathon App\nBuilt with AI. Everything is 100% MIT licensed!\n", encoding="utf-8")

    # 3. Ensure secret file is present
    env_file = demo_path / ".env.backup"
    if not env_file.exists():
        k_name = "API" + "_KEY"
        d_name = "DATABASE" + "_URL"
        env_file.write_text(f'{k_name}="dummy_secret_for_scanner_test_987654321"\n{d_name}="postgres://admin:supersecret@localhost:5432/ai_app"\n', encoding="utf-8")


# Sidebar configuration
with st.sidebar:
    st.image("https://raw.githubusercontent.com/google/gemma_pytorch/main/assets/gemma_logo.png", width=70)
    st.title("RepoReady Engine")
    st.caption("Open-Weight AI Compliance & Hacktoberfest Auditor")

    st.markdown("---")
    st.subheader("Local SLM Engine")

    ollama_active = is_ollama_running()
    model_ready = is_model_installed(selected_model if 'selected_model' in locals() else "gemma2:2b")

    if ollama_active and model_ready:
        st.success("🟢 Local Ollama: Online (Model Ready)", icon="⚡")
    elif ollama_active:
        st.warning("🟡 Local Ollama: Online (Model Pulling in Background)", icon="⏳")
    else:
        st.info("⚪ Local Ollama: Offline (Using Fallback)", icon="ℹ️")

    selected_model = st.selectbox(
        "Active SLM Model",
        ["gemma2:2b", "llama3.2:3b", "mistral:7b"],
        index=0,
        help="Google Gemma 2 (2B) is a 2.6B parameter Small Language Model ideal for offline edge inference."
    )

    st.markdown(r"""
    **Model Specifications:**
    - **Architecture:** Gemma 2
    - **Parameters:** 2.6B ($\le 10\text{B}$ SLM)
    - **Offline Execution:** Localhost
    - **Latency:** ~1.5s
    """)

    st.markdown("---")
    st.subheader("🧪 Hackathon Demo Controls")
    if st.button("⚡ Load Broken Demo Repo (Judge Test)", use_container_width=True):
        reset_demo_repo("./demo_broken_project")
        st.session_state["target_path_input"] = "./demo_broken_project"
        st.session_state["run_audit_trigger"] = True
        st.rerun()

    if st.button("🔄 Reset Demo to Broken State", use_container_width=True):
        reset_demo_repo("./demo_broken_project")
        st.session_state["target_path_input"] = "./demo_broken_project"
        st.session_state["run_audit_trigger"] = True
        st.rerun()

    st.caption("Auto-resets the rigged victim repo (missing LICENSE, uncredited Gemma/Llama weights, leaked secret).")


# Header
st.title("🛡️ RepoReady: Open-Weight AI Compliance Auditor")
st.markdown("""
Ensure your hackathon project satisfies open-source licensing rules, properly attributes 
**Open-Weight AI Models** (Gemma, Llama, Mistral), and prevents credential leaks.
""")

# Quick presets
st.markdown("**Quick Preset Repositories:** *(Click to test immediately)*")
pcol1, pcol2, pcol3, pcol4 = st.columns(4)

with pcol1:
    if st.button("⚡ Broken Demo (20/100 Trap)", use_container_width=True):
        reset_demo_repo("./demo_broken_project")
        st.session_state["target_path_input"] = "./demo_broken_project"
        st.session_state["run_audit_trigger"] = True
        st.rerun()

with pcol2:
    if st.button("🛡️ RepoReady (Self-Audit)", use_container_width=True):
        st.session_state["target_path_input"] = "."
        st.session_state["run_audit_trigger"] = True
        st.rerun()

with pcol3:
    if st.button("🚀 FastAPI (GitHub)", use_container_width=True):
        st.session_state["target_path_input"] = "https://github.com/tiangolo/fastapi"
        st.session_state["run_audit_trigger"] = True
        st.rerun()

with pcol4:
    if st.button("🦙 Ollama Python (GitHub)", use_container_width=True):
        st.session_state["target_path_input"] = "https://github.com/ollama/ollama-python"
        st.session_state["run_audit_trigger"] = True
        st.rerun()

# Input controls
col_in1, col_in2 = st.columns([4, 1])

if "target_path_input" not in st.session_state:
    st.session_state["target_path_input"] = "."

with col_in1:
    target_repo = st.text_input(
        "Target Local Path or Git Repository URL",
        key="target_path_input",
        placeholder="e.g. ./demo_broken_project or https://github.com/username/repo"
    )

with col_in2:
    st.write("") # spacing
    st.write("")
    run_btn = st.button("🔍 Run Audit", type="primary", use_container_width=True)

# Trigger audit if requested
should_audit = run_btn or st.session_state.pop("run_audit_trigger", False)

if should_audit:
    with st.spinner("Analyzing codebase AST, dependencies, licenses, and AI weights..."):
        try:
            scan_res = scan_repository(target_repo)
            audit_res = run_audit(scan_res, prefer_ollama=True, model_name=selected_model)
            st.session_state["last_scan"] = scan_res
            st.session_state["last_audit"] = audit_res
            st.session_state["last_target"] = target_repo
        except Exception as e:
            st.error(f"Error executing audit: {e}")

# Render Results if available in session
if "last_audit" in st.session_state:
    scan_data = st.session_state["last_scan"]
    audit_data = st.session_state["last_audit"]
    target_path = st.session_state["last_target"]

    score = audit_data.readiness_score
    if score >= 80:
        score_class = "metric-value-green"
    elif score >= 50:
        score_class = "metric-value-yellow"
    else:
        score_class = "metric-value-red"

    st.markdown("---")

    # 3 High-Impact Metric Cards
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)

    with mcol1:
        st.markdown(f"""
        <div class="metric-card">
            <h1 class="{score_class}">{score}</h1>
            <div class="metric-label">Readiness Score / 100</div>
        </div>
        """, unsafe_allow_html=True)

    with mcol2:
        lic_type = scan_data["license"]["license_type"]
        status_text = "PASS" if "PASS" in audit_data.license_status else ("FAIL" if "FAIL" in audit_data.license_status else "WARN")
        badge_style = "badge-pass" if status_text == "PASS" else ("badge-fail" if status_text == "FAIL" else "badge-warn")
        st.markdown(f"""
        <div class="metric-card">
            <h1 style="font-size: 2rem; margin: 10px 0;"><span class="{badge_style}">{status_text}</span></h1>
            <div class="metric-label">License: {lic_type}</div>
        </div>
        """, unsafe_allow_html=True)

    with mcol3:
        models_count = len(audit_data.detected_ai_models)
        unattributed_count = sum(1 for m in audit_data.detected_ai_models if not m.terms_linked_in_readme)
        attr_color = "#10B981" if unattributed_count == 0 else "#EF4444"
        st.markdown(f"""
        <div class="metric-card">
            <h1 style="font-size: 2.8rem; margin: 0; color: {attr_color};">{models_count}</h1>
            <div class="metric-label">{unattributed_count} Unattributed in README</div>
        </div>
        """, unsafe_allow_html=True)

    with mcol4:
        sec_leaks = len(scan_data["security"]["secret_files"]) + len(scan_data["security"]["secret_leaks"])
        sec_color = "#10B981" if sec_leaks == 0 else "#EF4444"
        st.markdown(f"""
        <div class="metric-card">
            <h1 style="font-size: 2.8rem; margin: 0; color: {sec_color};">{sec_leaks}</h1>
            <div class="metric-label">Security & Secret Leaks</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("###")

    # Main Tabs: Overview, AI Models, Diff & Auto-Fix, Raw JSON
    tab_overview, tab_models, tab_autofix, tab_json = st.tabs([
        "📋 Compliance Overview",
        "🤖 Detected AI Models",
        "✨ Auto-Healer & README Diff",
        "🔍 Raw SLM Inference JSON"
    ])

    with tab_overview:
        col_issues, col_recs = st.columns(2)

        with col_issues:
            st.subheader("⚠️ Critical Issues & Blockers")
            all_issues = list(audit_data.critical_issues)
            if scan_data["security"]["secret_files"]:
                all_issues.append(f"Secret / env files committed: {', '.join(scan_data['security']['secret_files'])}")

            if all_issues:
                for issue in all_issues:
                    st.error(issue, icon="🚨")
            else:
                st.success("No critical issues found! Repository satisfies all baseline compliance checks.", icon="✅")

        with col_recs:
            st.subheader("💡 Recommended Remediation")
            if audit_data.recommendations:
                for rec in audit_data.recommendations:
                    st.info(rec, icon="💡")
            else:
                st.write("Everything looks great. No immediate actions required.")

    with tab_models:
        st.subheader("Detected AI Models & Provider Licensing")
        st.write("Hacktoberfest Rule: Open-weight weights are governed by their creators' Terms of Use, not the source code license.")

        if audit_data.detected_ai_models:
            model_rows = []
            for m in audit_data.detected_ai_models:
                model_rows.append({
                    "Model Name": m.model_name,
                    "Category": m.classification,
                    "README Attributed?": "✅ Linked" if m.terms_linked_in_readme else "❌ MISSING",
                    "Terms of Use URL": m.required_license_url
                })
            df = pd.DataFrame(model_rows)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No AI models or ML weights detected in code files.")

    with tab_autofix:
        st.subheader("✨ One-Click Repository Auto-Healer")
        st.write("Generates the missing standard `LICENSE` and injects legal open-weight attribution and quickstart blocks into `README.md`.")

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("#### Current `README.md`")
            current_readme = scan_data["readme"]["full_content"]
            if current_readme.strip():
                st.code(current_readme, language="markdown")
            else:
                st.warning("No README.md currently exists in the repository.")

        with col_right:
            st.markdown("#### AI-Generated Compliance Patch")
            patch_md = audit_data.readme_patch_markdown
            st.code(patch_md, language="markdown")

        st.markdown("---")
        btn_fix_col, btn_dl_col = st.columns([2, 2])

        with btn_fix_col:
            if st.button("✨ Auto-Fix Repo (Inject License & Model Attribution)", type="primary", use_container_width=True):
                with st.spinner("Applying automated compliance patches..."):
                    fix_res = heal_repository(target_path, audit_data.model_dump())
                    st.balloons()
                    st.success(f"✓ {fix_res['license_action']}")
                    st.success(f"✓ {fix_res['readme_action']}")

                    # Re-scan to update scores in UI
                    new_scan = scan_repository(target_path)
                    new_audit = run_audit(new_scan, prefer_ollama=True, model_name=selected_model)
                    st.session_state["last_scan"] = new_scan
                    st.session_state["last_audit"] = new_audit
                    st.rerun()

        with btn_dl_col:
            st.download_button(
                label="📥 Download Patched README.md",
                data=current_readme + "\n\n" + patch_md,
                file_name="README_patched.md",
                mime="text/markdown",
                use_container_width=True
            )

    with tab_json:
        st.subheader("Live SLM Inference Output")
        st.caption(f"Generated by: {audit_data.engine_used}")
        st.json(audit_data.model_dump())
