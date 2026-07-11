"""
RegOps demo UI — this is what you screen-record for the demo video.

Run with:
    streamlit run app.py

Shows the pipeline live:
  1. Upload/select a circular PDF -> ingestion + chunking
  2. Run extraction -> structured obligations table
  3. Compare against a baseline -> diff view (new / amended / unchanged)
"""

import json
import time
import pandas as pd
import streamlit as st
from ingest import extract_text, chunk_by_clause
from extract import extract_from_chunks_batch
from diff import classify_obligations_batch

st.set_page_config(page_title="RegOps — Agentic Compliance Copilot", layout="wide")
st.title("RegOps — Agentic Compliance Copilot")
st.caption("SEBI circular in → structured, traceable, audit-ready obligations out")

def render_custom_table(df: pd.DataFrame):
    """Renders a pandas DataFrame as an HTML table styled to perfectly mimic 
    Streamlit's native dataframe components. Bypasses PyArrow to guarantee 
    absolute stability against segmentation faults under python 3.14."""
    if df.empty:
        st.info("No records found.")
        return
    
    # Prettify column headers
    df_styled = df.copy()
    df_styled.columns = [col.replace("_", " ").title() for col in df_styled.columns]
    
    # Convert to HTML and remove newlines to prevent markdown paragraph-wrapping bugs
    html = df_styled.to_html(index=False, classes="dataframe-styled")
    html = html.replace("\n", " ")
    
    # Custom CSS to mimic Streamlit's native tables perfectly
    custom_css = """
    <style>
    .dataframe-styled {
        width: 100%;
        border-collapse: collapse;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 14px;
        color: #31333F;
        margin: 15px 0;
    }
    .dataframe-styled th {
        background-color: #f0f2f6;
        color: #31333F;
        font-weight: 600;
        text-align: left;
        padding: 10px 16px;
        border: 1px solid #e2e8f0;
    }
    .dataframe-styled td {
        padding: 10px 16px;
        border: 1px solid #e2e8f0;
        background-color: #ffffff;
        vertical-align: top;
        line-height: 1.4;
    }
    .dataframe-styled tr:nth-child(even) td {
        background-color: #f8fafc;
    }
    .dataframe-styled tr:hover td {
        background-color: #f1f5f9;
    }
    </style>
    """
    st.markdown(custom_css + html, unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["1. Ingest & Extract", "2. Baseline Register", "3. Diff / Change Detection"])

if "obligations" not in st.session_state:
    st.session_state.obligations = []
if "baseline" not in st.session_state:
    st.session_state.baseline = []
if "diff_results" not in st.session_state:
    st.session_state.diff_results = []

with tab1:
    st.subheader("Ingest a circular")
    uploaded = st.file_uploader("Upload a SEBI circular (PDF)", type="pdf")

    if uploaded:
        with open("temp_circular.pdf", "wb") as f:
            f.write(uploaded.read())

        full_text = extract_text("temp_circular.pdf")
        chunks = chunk_by_clause(full_text)
        st.success(f"Parsed circular into {len(chunks)} clause-level chunks.")

        with st.expander("View chunks"):
            st.json(chunks[:5])

        max_chunks = st.slider(
            "Chunks to process (keep small for a quick live demo)",
            1, min(len(chunks), 30), min(5, len(chunks)),
        )

        if st.button("Run Extraction Agent", type="primary"):
            progress = st.progress(0.0)
            all_obligations = []
            
            batch_size = 10
            chunks_to_process = chunks[:max_chunks]
            num_chunks = len(chunks_to_process)
            
            for i in range(0, num_chunks, batch_size):
                batch = chunks_to_process[i : i + batch_size]
                obligations = extract_from_chunks_batch(batch)
                all_obligations.extend(obligations)
                progress.progress(min(1.0, (i + len(batch)) / num_chunks))
        
            st.session_state.obligations = all_obligations
            st.success(f"Extracted {len(all_obligations)} obligations.")

        if st.session_state.obligations:
            render_custom_table(pd.DataFrame(st.session_state.obligations))
            
            json_str = json.dumps(st.session_state.obligations, indent=2)
            st.download_button(
                label="💾 Download Extracted Obligations (JSON)",
                data=json_str,
                file_name="extracted_obligations.json",
                mime="application/json"
            )

with tab2:
    st.subheader("Baseline obligation register")
    st.write(
        "This represents your already-tracked obligations (e.g. from the "
        "master circular). Load a saved obligations.json, or reuse the "
        "extraction you just ran as the baseline."
    )

    baseline_file = st.file_uploader("Load baseline obligations JSON", type="json", key="baseline_upload")
    if baseline_file:
        st.session_state.baseline = json.load(baseline_file)
        st.success(f"Loaded {len(st.session_state.baseline)} baseline obligations.")

    if st.button("Use current extraction as baseline"):
        st.session_state.baseline = st.session_state.obligations
        st.success("Baseline set from current extraction.")

    if st.session_state.baseline:
        render_custom_table(pd.DataFrame(st.session_state.baseline))
        
        json_str = json.dumps(st.session_state.baseline, indent=2)
        st.download_button(
            label="💾 Download Baseline Register (JSON)",
            data=json_str,
            file_name="baseline_obligations.json",
            mime="application/json"
        )

with tab3:
    st.subheader("Diff against baseline")
    st.write(
        "Upload obligations extracted from a NEWER circular to see what's "
        "new, amended, or unchanged vs. the baseline register."
    )

    new_file = st.file_uploader("Load new circular's obligations JSON", type="json", key="new_upload")

    if new_file and st.session_state.baseline:
        new_obligations = json.load(new_file)
        if st.button("Run Diff Agent", type="primary"):
            results = []
            progress = st.progress(0.0)
            
            batch_size = 10
            num_obs = len(new_obligations)
            
            for i in range(0, num_obs, batch_size):
                batch = new_obligations[i : i + batch_size]
                batch_results = classify_obligations_batch(batch, st.session_state.baseline)
                results.extend(batch_results)
                progress.progress(min(1.0, (i + len(batch)) / num_obs))

            st.session_state.diff_results = results
            st.success("Diff comparison completed successfully.")

        if st.session_state.diff_results:
            for tag, color in [("new", "green"), ("amended", "orange"), ("unchanged", "gray")]:
                subset = [r for r in st.session_state.diff_results if r["classification"] == tag]
                if subset:
                    st.markdown(f"### :{color}[{tag.upper()}] ({len(subset)})")
                    
                    df_sub = pd.DataFrame(subset)
                    cols_to_show = ["clause_reference", "obligation_text", "matched_baseline_obligation", "reasoning"]
                    df_sub_show = df_sub[[c for c in cols_to_show if c in df_sub.columns]]
                    render_custom_table(df_sub_show)
            
            json_str = json.dumps(st.session_state.diff_results, indent=2)
            st.download_button(
                label="💾 Download Rule Changes Diff (JSON)",
                data=json_str,
                file_name="compliance_diff.json",
                mime="application/json"
            )
    elif not st.session_state.baseline:
        st.info("Set a baseline in tab 2 first.")
