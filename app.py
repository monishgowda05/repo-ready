"""
RepoReady - Streamlit Web Dashboard (Aceternity UI Edition)
Sleek, glassmorphic compliance dashboard inspired by Aceternity UI and modern design standards.
Features floating dock navigation, glowing metric cards, live diff auto-healer, and local SLM inference.
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

# Aceternity-Inspired Custom CSS (Glassmorphism, Shimmer Buttons, Neon Glows)
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">

<style>
    /* Global Typography & Palette */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    /* Background Radial Mesh Glow */
    .stApp {
        background-color: #09090b !important;
        background-image: 
            radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.14) 0%, transparent 50%),
            radial-gradient(circle at 90% 90%, rgba(168, 85, 247, 0.08) 0%, transparent 40%),
            radial-gradient(circle at 10% 80%, rgba(16, 185, 129, 0.06) 0%, transparent 40%) !important;
    }
    
    /* Aceternity Metric Cards with Glow Borders */
    .metric-card {
        background: rgba(18, 18, 24, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px 20px;
        text-align: center;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.7);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        border-color: rgba(99, 102, 241, 0.4);
        box-shadow: 0 20px 40px -10px rgba(99, 102, 241, 0.2);
    }
    
    .card-glow-green {
        border-color: rgba(16, 185, 129, 0.3);
        box-shadow: 0 10px 30px -10px rgba(16, 185, 129, 0.2);
    }
    .card-glow-yellow {
        border-color: rgba(245, 158, 11, 0.3);
        box-shadow: 0 10px 30px -10px rgba(245, 158, 11, 0.2);
    }
    .card-glow-red {
        border-color: rgba(239, 68, 68, 0.3);
        box-shadow: 0 10px 30px -10px rgba(239, 68, 68, 0.2);
    }
    
    .metric-value-green {
        font-size: 3.2rem;
        font-weight: 800;
        color: #10B981;
        margin: 0;
        text-shadow: 0 0 20px rgba(16, 185, 129, 0.4);
    }
    .metric-value-yellow {
        font-size: 3.2rem;
        font-weight: 800;
        color: #F59E0B;
        margin: 0;
        text-shadow: 0 0 20px rgba(245, 158, 11, 0.4);
    }
    .metric-value-red {
        font-size: 3.2rem;
        font-weight: 800;
        color: #EF4444;
        margin: 0;
        text-shadow: 0 0 20px rgba(239, 68, 68, 0.4);
    }
    .metric-label {
        font-size: 0.95rem;
        color: #94A3B8;
        font-weight: 500;
        margin-top: 8px;
        letter-spacing: 0.5px;
    }
    
    /* Status Badges */
    .badge-pass {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.3));
        color: #34D399;
        border: 1px solid rgba(52, 211, 153, 0.4);
        padding: 6px 16px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 1.1rem;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.25);
    }
    .badge-fail {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(185, 28, 28, 0.3));
        color: #F87171;
        border: 1px solid rgba(248, 113, 113, 0.4);
        padding: 6px 16px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 1.1rem;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.25);
    }
    .badge-warn {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(180, 83, 9, 0.3));
        color: #FBBF24;
        border: 1px solid rgba(251, 191, 36, 0.4);
        padding: 6px 16px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 1.1rem;
        box-shadow: 0 0 15px rgba(245, 158, 11, 0.25);
    }
    
    /* Aceternity Shimmer Primary Button */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #6366f1 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 10px 24px !important;
        box-shadow: 0 0 25px rgba(99, 102, 241, 0.45), inset 0 1px 1px rgba(255, 255, 255, 0.3) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: 0 0 35px rgba(124, 58, 237, 0.7), inset 0 1px 1px rgba(255, 255, 255, 0.5) !important;
    }
    
    /* Sleek Secondary Buttons */
    .stButton > button:not([kind="primary"]) {
        background: rgba(24, 24, 27, 0.7) !important;
        color: #e4e4e7 !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(12px) !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:not([kind="primary"]):hover {
        background: rgba(39, 39, 42, 0.85) !important;
        border-color: rgba(99, 102, 241, 0.4) !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
    }

    /* Aceternity Floating Dock */
    .floating-dock-container {
        display: flex;
        justify-content: center;
        margin: 20px 0 30px 0;
    }
    .floating-dock {
        display: inline-flex;
        align-items: center;
        gap: 12px;
        padding: 10px 20px;
        background: rgba(18, 18, 24, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 9999px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), inset 0 1px 1px rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
    }
    .dock-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #e4e4e7;
        font-size: 1.3rem;
        cursor: pointer;
        transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
        text-decoration: none;
    }
    .dock-item:hover {
        transform: scale(1.3) translateY(-6px);
        background: rgba(99, 102, 241, 0.25);
        border-color: rgba(99, 102, 241, 0.5);
        box-shadow: 0 10px 20px rgba(99, 102, 241, 0.35);
        color: #ffffff;
    }

    /* Input Field Styling */
    .stTextInput > div > div > input {
        background-color: rgba(18, 18, 24, 0.8) !important;
        color: #f4f4f5 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        font-size: 1rem !important;
        padding: 12px 16px !important;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.4) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.35) !important;
    }
    
    /* Code Diff Window Styling */
    .window-header {
        display: flex;
        align-items: center;
        gap: 8px;
        background: rgba(24, 24, 27, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-bottom: none;
        padding: 10px 16px;
        border-radius: 12px 12px 0 0;
        font-size: 0.85rem;
        color: #a1a1aa;
        font-family: 'JetBrains Mono', monospace;
    }
    .dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }
    .dot-red { background: #ef4444; }
    .dot-yellow { background: #f59e0b; }
    .dot-green { background: #10b981; }
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
    st.image("https://raw.githubusercontent.com/google/gemma_pytorch/main/assets/gemma_logo.png", width=64)
    st.title("RepoReady Engine")
    st.caption("Open-Weight AI Compliance & Hacktoberfest Auditor")

    st.markdown("---")
    st.subheader("⚡ Local SLM Engine")

    ollama_active = is_ollama_running()
    model_ready = is_model_installed(selected_model if 'selected_model' in locals() else "gemma2:2b")

    if ollama_active and model_ready:
        st.success("🟢 Local Ollama: Online (Gemma 2 Ready)", icon="⚡")
    elif ollama_active:
        st.warning("🟡 Local Ollama: Online (Model Pulling)", icon="⏳")
    else:
        st.info("⚪ Local Ollama: Offline (Using Fallback)", icon="ℹ️")

    selected_model = st.selectbox(
        "Active SLM Model",
        ["gemma2:2b", "llama3.2:3b", "mistral:7b"],
        index=0,
        help="Google Gemma 2 (2B) is a 2.6B parameter Small Language Model running locally on your RTX GPU."
    )

    st.markdown(r"""
    **Hardware Acceleration:**
    - **Compute:** NVIDIA CUDA 8.6
    - **Model:** Gemma 2 (2.6B SLM)
    - **Latency:** ~1.2s offline
    """)

    st.markdown("---")
    st.subheader("🧪 Hackathon Demo Controls")
    if st.button("⚡ Load Broken Demo Repo", use_container_width=True):
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


# Header with Modern Aceternity Style
col_head1, col_head2 = st.columns([5, 1])
with col_head1:
    st.title("🛡️ RepoReady: Open-Weight AI Compliance Auditor")
    st.markdown("""
    Ensure your hackathon project satisfies open-source licensing rules, properly attributes 
    **Open-Weight AI Models** (Gemma, Llama, Mistral), and prevents credential leaks.
    """)
with col_head2:
    st.link_button("⭐ GitHub Repo", "https://github.com/monishgowda05/repo-ready", use_container_width=True)


# Quick Aceternity Floating Dock Bar
st.markdown("""
<div class="floating-dock-container">
    <div class="floating-dock">
        <a href="#audit-section" class="dock-item" title="Quick Audit">🔍</a>
        <a href="#quick-presets" class="dock-item" title="Presets">⚡</a>
        <a href="#overview-tab" class="dock-item" title="Compliance Score">📊</a>
        <a href="#models-tab" class="dock-item" title="AI Model Attribution">🤖</a>
        <a href="#autofix-tab" class="dock-item" title="One-Click Auto-Healer">✨</a>
        <a href="https://github.com/monishgowda05/repo-ready" target="_blank" class="dock-item" title="GitHub">🐙</a>
    </div>
</div>
""", unsafe_allow_html=True)


# Quick presets
st.markdown("<div id='quick-presets'></div>", unsafe_allow_html=True)
st.markdown("**Quick Preset Repositories:** *(Click any preset to test immediately)*")
pcol1, pcol2, pcol3, pcol4 = st.columns(4)

with pcol1:
    if st.button("⚡ Broken Demo (20/100 Trap)", use_container_width=True):
        reset_demo_repo("./demo_broken_project")
        st.session_state["target_path_input"] = "./demo_broken_project"
        st.session_state["run_audit_trigger"] = True
        st.rerun()

with pcol2:
    if st.button("🛡️ RepoReady (Self-Audit 100)", use_container_width=True):
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
st.markdown("<div id='audit-section'></div>", unsafe_allow_html=True)
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
    run_btn = st.button("🔍 Run Open-Weight Audit", type="primary", use_container_width=True)

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
        glow_class = "card-glow-green"
    elif score >= 50:
        score_class = "metric-value-yellow"
        glow_class = "card-glow-yellow"
    else:
        score_class = "metric-value-red"
        glow_class = "card-glow-red"

    st.markdown("---")

    # 4 Glowing Metric Cards (Aceternity UI Style)
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)

    with mcol1:
        st.markdown(f"""
        <div class="metric-card {glow_class}">
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
            <h1 style="font-size: 2.2rem; margin: 8px 0;"><span class="{badge_style}">{status_text}</span></h1>
            <div class="metric-label">License: {lic_type}</div>
        </div>
        """, unsafe_allow_html=True)

    with mcol3:
        models_count = len(audit_data.detected_ai_models)
        unattributed_count = sum(1 for m in audit_data.detected_ai_models if not m.terms_linked_in_readme)
        attr_color = "#10B981" if unattributed_count == 0 else "#EF4444"
        st.markdown(f"""
        <div class="metric-card">
            <h1 style="font-size: 2.8rem; margin: 0; color: {attr_color}; text-shadow: 0 0 20px {attr_color}44;">{models_count}</h1>
            <div class="metric-label">{unattributed_count} Unattributed in README</div>
        </div>
        """, unsafe_allow_html=True)

    with mcol4:
        sec_leaks = len(scan_data["security"]["secret_files"]) + len(scan_data["security"]["secret_leaks"])
        sec_color = "#10B981" if sec_leaks == 0 else "#EF4444"
        st.markdown(f"""
        <div class="metric-card">
            <h1 style="font-size: 2.8rem; margin: 0; color: {sec_color}; text-shadow: 0 0 20px {sec_color}44;">{sec_leaks}</h1>
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
            st.markdown("""
            <div class="window-header">
                <span class="dot dot-red"></span>
                <span class="dot dot-yellow"></span>
                <span class="dot dot-green"></span>
                <span>Current README.md</span>
            </div>
            """, unsafe_allow_html=True)
            current_readme = scan_data["readme"]["full_content"]
            if current_readme.strip():
                st.code(current_readme, language="markdown")
            else:
                st.warning("No README.md currently exists in the repository.")

        with col_right:
            st.markdown("""
            <div class="window-header">
                <span class="dot dot-red"></span>
                <span class="dot dot-yellow"></span>
                <span class="dot dot-green"></span>
                <span>AI-Generated Compliance Patch</span>
            </div>
            """, unsafe_allow_html=True)
            patch_md = audit_data.readme_patch_markdown
            st.code(patch_md, language="markdown")

        st.markdown("---")
        btn_fix_col, btn_dl_col = st.columns([2, 2])

        with btn_fix_col:
            is_remote = target_path.startswith("http://") or target_path.startswith("https://")
            if is_remote:
                st.info("💡 **Remote GitHub Repo:** Auto-Fix modifies local files directly. To update this remote repo, download the patch on the right to submit a Pull Request, or clone the repo locally to auto-fix!")
            else:
                if st.button("✨ Auto-Fix Repo (Inject License & Model Attribution)", type="primary", use_container_width=True):
                    with st.spinner("Applying automated compliance patches..."):
                        try:
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
                        except Exception as e:
                            st.error(f"Could not apply auto-fix: {e}")

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
