"""
Streamlit Web Interface for the AI Document Comparison Assistant.
Fulfills Functional Requirements FR-01 through FR-12 and Section 8 UI specifications.
"""

import os
import streamlit as st
from dotenv import load_dotenv

from document_reader import validate_and_extract_pdf
from comparison import compare_documents, LLMComparisonError, DEFAULT_MODEL
from report_generator import generate_docx_report

load_dotenv()

st.set_page_config(
    page_title="AI Document Comparison Assistant",
    page_icon="📄",
    layout="wide",
)


def init_session_state() -> None:
    """Initializes Streamlit session state keys for comparison results and reset handling."""
    if "comparison_result" not in st.session_state:
        st.session_state["comparison_result"] = None
    if "doc_a_extracted" not in st.session_state:
        st.session_state["doc_a_extracted"] = None
    if "doc_b_extracted" not in st.session_state:
        st.session_state["doc_b_extracted"] = None
    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = 0


def reset_comparison() -> None:
    """FR-12: Reset and compare again — clears current comparison and file uploaders."""
    st.session_state["comparison_result"] = None
    st.session_state["doc_a_extracted"] = None
    st.session_state["doc_b_extracted"] = None
    st.session_state["uploader_key"] += 1


def main() -> None:
    init_session_state()

    # Sidebar: Configuration & Sample Documents option
    with st.sidebar:
        st.header("⚙️ Configuration")
        env_key_present = bool(
            os.getenv("GEMINI_API_KEY")
            and os.getenv("GEMINI_API_KEY") != "your_gemini_api_key_here"
        )
        api_key_input = st.text_input(
            "Gemini API Key (optional if set in .env)",
            type="password",
            help="Enter your Google Gemini API key or configure GEMINI_API_KEY in a .env file.",
        )
        if env_key_present and not api_key_input:
            st.caption("✅ Using `GEMINI_API_KEY` loaded from `.env`")

        model_name = st.selectbox(
            "LLM Model",
            options=["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
            index=0,
        )

        st.divider()
        st.subheader("🔄 Actions")
        if st.button("Reset & Compare New Documents", use_container_width=True):
            reset_comparison()
            st.rerun()

        st.divider()
        st.caption(
            "**Scope Note:** This is an informational comparison tool. "
            "It is not a legal decision-maker and does not claim that a document is "
            "legally safe, compliant, or equivalent."
        )

    # Section 8: Expected User Interface — Title and short instruction
    st.title("📄 AI Document Comparison Assistant")
    st.markdown(
        "Upload two text-based PDF documents (such as course syllabi, company policies, "
        "project specifications, agreements, or instruction manuals) to extract their text, "
        "generate separate summaries, compare similarities and differences, highlight key details "
        "(dates, amounts, deadlines, eligibility criteria), and download a structured report."
    )

    # FR-01: Two upload areas labelled Document A and Document B
    uploader_suffix = st.session_state["uploader_key"]
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("📘 Document A (Original / Version 1)")
        file_a = st.file_uploader(
            "Upload Document A (PDF)",
            type=["pdf"],
            key=f"file_a_{uploader_suffix}",
            help="Select the first PDF document for comparison.",
        )

    with col_b:
        st.subheader("📙 Document B (Updated / Version 2)")
        file_b = st.file_uploader(
            "Upload Document B (PDF)",
            type=["pdf"],
            key=f"file_b_{uploader_suffix}",
            help="Select the second PDF document for comparison.",
        )

    # Option to load bundled sample documents for quick testing/demo
    use_samples = st.checkbox(
        "Or test with bundled sample documents (`sample_documents/document_a.pdf` & `document_b.pdf`)",
        value=False,
    )

    doc_a_info = None
    doc_b_info = None

    # Validate and preview uploaded files immediately (FR-01, FR-02, FR-03, FR-04)
    if use_samples:
        sample_a_path = os.path.join(os.path.dirname(__file__), "sample_documents", "document_a.pdf")
        sample_b_path = os.path.join(os.path.dirname(__file__), "sample_documents", "document_b.pdf")
        if os.path.exists(sample_a_path) and os.path.exists(sample_b_path):
            doc_a_info = validate_and_extract_pdf(sample_a_path, filename="document_a.pdf")
            doc_b_info = validate_and_extract_pdf(sample_b_path, filename="document_b.pdf")
        else:
            st.error("Bundled sample documents were not found in `sample_documents/`.")
    else:
        if file_a is not None:
            doc_a_info = validate_and_extract_pdf(file_a, filename=file_a.name)
        if file_b is not None:
            doc_b_info = validate_and_extract_pdf(file_b, filename=file_b.name)

    # Display extraction status & previews (FR-02 & FR-04)
    if doc_a_info or doc_b_info:
        prev_col_a, prev_col_b = st.columns(2)
        with prev_col_a:
            if doc_a_info:
                if not doc_a_info["is_valid"]:
                    st.error(f"**Document A Error:** {doc_a_info['error_message']}")
                else:
                    st.success(
                        f"**{doc_a_info['filename']}** — "
                        f"{doc_a_info['readable_pages']}/{doc_a_info['page_count']} readable page(s) | "
                        f"{doc_a_info['char_count']:,} characters ({doc_a_info['word_count']:,} words)"
                    )
                    if doc_a_info.get("limitations_note"):
                        st.warning(doc_a_info["limitations_note"])
                    with st.expander(f"Preview Extracted Content ({doc_a_info['filename']})"):
                        st.text(doc_a_info["preview_text"])

        with prev_col_b:
            if doc_b_info:
                if not doc_b_info["is_valid"]:
                    st.error(f"**Document B Error:** {doc_b_info['error_message']}")
                else:
                    st.success(
                        f"**{doc_b_info['filename']}** — "
                        f"{doc_b_info['readable_pages']}/{doc_b_info['page_count']} readable page(s) | "
                        f"{doc_b_info['char_count']:,} characters ({doc_b_info['word_count']:,} words)"
                    )
                    if doc_b_info.get("limitations_note"):
                        st.warning(doc_b_info["limitations_note"])
                    with st.expander(f"Preview Extracted Content ({doc_b_info['filename']})"):
                        st.text(doc_b_info["preview_text"])

    st.markdown("---")

    # Section 8: Button labelled "Compare Documents"
    btn_col1, btn_col2 = st.columns([3, 1])
    with btn_col1:
        compare_clicked = st.button(
            "🔍 Compare Documents",
            type="primary",
            use_container_width=True,
        )
    with btn_col2:
        if st.button("🗑️ Reset / Clear", use_container_width=True):
            reset_comparison()
            st.rerun()

    if compare_clicked:
        # Test case: One file missing
        if not doc_a_info or not doc_b_info:
            st.warning("⚠️ Please upload both **Document A** and **Document B** in PDF format before comparing.")
        elif not doc_a_info["is_valid"] or not doc_b_info["is_valid"]:
            st.error("❌ Cannot proceed with comparison because one or both uploaded files failed validation. Please fix the highlighted file errors above.")
        else:
            # Loading indicator while documents are being processed
            with st.spinner("Analyzing and comparing documents with AI... Please wait."):
                try:
                    comparison_output = compare_documents(
                        doc_a_data=doc_a_info,
                        doc_b_data=doc_b_info,
                        api_key=api_key_input,
                        model_name=model_name,
                    )
                    st.session_state["comparison_result"] = comparison_output
                    st.session_state["doc_a_extracted"] = doc_a_info
                    st.session_state["doc_b_extracted"] = doc_b_info
                except LLMComparisonError as exc:
                    st.error(f"**Comparison Error:** {str(exc)}")
                    st.info("💡 Tip: Check your API key and network connection, then click **Compare Documents** to retry.")
                except Exception as exc:
                    st.error(f"**Unexpected Error:** {str(exc)}")

    # FR-09 & Section 8/9: Display results in labelled tabs and provide Download Comparison Report button
    result = st.session_state.get("comparison_result")
    if result:
        st.subheader("📊 Comparison Results")

        tab_summaries, tab_similarities, tab_differences, tab_details, tab_conclusion = st.tabs([
            "📑 Summaries (Doc A & Doc B)",
            "🤝 Similarities",
            "⚖️ Differences",
            "📌 Key Details Comparison",
            "🏁 Overall Conclusion & Limitations",
        ])

        with tab_summaries:
            s_col_a, s_col_b = st.columns(2)
            with s_col_a:
                st.markdown(f"### 📘 Summary A: `{result.get('document_a_name', 'Document A')}`")
                st.write(result.get("document_a_summary", "Not available."))
            with s_col_b:
                st.markdown(f"### 📙 Summary B: `{result.get('document_b_name', 'Document B')}`")
                st.write(result.get("document_b_summary", "Not available."))

        with tab_similarities:
            st.markdown("### 🤝 Similarities Supported by Both Documents")
            sims = result.get("similarities", [])
            if sims:
                for item in sims:
                    st.markdown(f"- {item}")
            else:
                st.info("No common points were identified.")

        with tab_differences:
            st.markdown("### ⚖️ Meaningful Differences (Additions, Removals, Changes, Contradictions)")
            diffs = result.get("differences", [])
            if diffs:
                st.dataframe(diffs, use_container_width=True, hide_index=True)
            else:
                st.info("No meaningful differences were found between the two documents.")

        with tab_details:
            st.markdown("### 📌 Key Details Comparison (Dates, Amounts, Names, Deadlines, Requirements)")
            details = result.get("key_details_comparison", [])
            if details:
                st.dataframe(details, use_container_width=True, hide_index=True)
            else:
                st.info("No specific structured details were found for side-by-side comparison.")

        with tab_conclusion:
            st.markdown("### 🏁 Overall Conclusion")
            st.write(result.get("overall_conclusion", "Not available."))
            st.markdown("### ⚠️ Limitations & Scope Notes")
            st.info(result.get("limitations", "No extraction limitations noted."))

        st.divider()

        # FR-10 & Section 8: Download Comparison Report button
        try:
            docx_bytes = generate_docx_report(result)
            st.download_button(
                label="📥 Download Comparison Report (.docx)",
                data=docx_bytes,
                file_name="AI_Document_Comparison_Report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
            )
        except Exception as exc:
            st.error(f"Could not generate downloadable report: {str(exc)}")


if __name__ == "__main__":
    main()
