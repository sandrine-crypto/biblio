"""Application Streamlit de Recherche Bibliographique Scientifique Automatisee."""

import logging
import os
import sys

import streamlit as st

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

import config
from models import Article, articles_to_json
from agents.agent1_collector import run_collection
from agents.agent2_analyzer import run_analysis
from agents.agent3_editor import run_editing
from utils.bibtex_export import generate_bibtex
from utils.pdf_report import generate_html_report
from utils.pptx_report import generate_pptx
from llm_client import CLAUDE, MISTRAL, PERPLEXITY, PROVIDER_LABELS, is_provider_available
from i18n import t

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

# ---- Configuration page -------------------------------------------------------

st.set_page_config(
    page_title="Scientific Literature Search",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

LLM_OPTIONS = [CLAUDE, MISTRAL, PERPLEXITY]
LLM_DISPLAY = [PROVIDER_LABELS[p] for p in LLM_OPTIONS]


def _get_lang() -> str:
    return st.session_state.get("lang", "fr")


def main():
    lang = _get_lang()

    st.title(f"📚 {t('main_title', lang)}")
    st.markdown(t("main_subtitle", lang))

    # ---- Sidebar : parameters ------------------------------------------------
    with st.sidebar:
        # Language selector at top
        lang_choice = st.selectbox(
            "🌐 Langue / Language",
            options=["Francais", "English"],
            index=0 if lang == "fr" else 1,
            key="lang_select",
        )
        new_lang = "fr" if lang_choice == "Francais" else "en"
        if new_lang != lang:
            st.session_state["lang"] = new_lang
            st.rerun()
        lang = new_lang

        st.header(f"⚙️ {t('sidebar_header', lang)}")

        keywords = st.text_area(
            t("keywords_label", lang),
            placeholder=t("keywords_placeholder", lang),
            help=t("keywords_help", lang),
            height=80,
        )

        col1, col2 = st.columns(2)
        with col1:
            date_from = st.text_input(t("date_from", lang), value="2020/01/01", help="Format: YYYY/MM/DD")
        with col2:
            date_to = st.text_input(t("date_to", lang), value="2025/12/31", help="Format: YYYY/MM/DD")

        st.subheader(f"📡 {t('sources_header', lang)}")
        src_pubmed = st.checkbox("PubMed", value=True)
        src_semantic = st.checkbox("Semantic Scholar", value=True)
        src_europe = st.checkbox("Europe PMC", value=True)
        src_scholar = st.checkbox("Google Scholar", value=False, help=f"⚠️ {t('google_scholar_warning', lang)}")

        max_results = st.slider(t("max_results_label", lang), 10, 100, 50, step=10)

        # ---- LLM model selection ----
        st.subheader(f"🤖 {t('llm_config_header', lang)}")

        llm_report_idx = st.selectbox(
            t("llm_report_label", lang),
            options=range(len(LLM_OPTIONS)),
            format_func=lambda i: LLM_DISPLAY[i],
            index=0,  # Claude by default
            key="llm_report_select",
        )
        llm_report = LLM_OPTIONS[llm_report_idx]

        # Filter verification options to exclude the report LLM
        verif_options = [i for i in range(len(LLM_OPTIONS)) if LLM_OPTIONS[i] != llm_report]
        verif_display = [LLM_DISPLAY[i] for i in verif_options]

        llm_verif_choice = st.selectbox(
            t("llm_verif_label", lang),
            options=range(len(verif_options)),
            format_func=lambda i: verif_display[i],
            index=0,
            key="llm_verif_select",
        )
        llm_verif = LLM_OPTIONS[verif_options[llm_verif_choice]]

        st.caption(f"ℹ️ {t('llm_must_differ', lang)}")

        # ---- PPTX settings ----
        st.subheader(f"📊 {t('pptx_header', lang)}")
        num_slides = st.slider(t("pptx_slides_label", lang), 5, 40, 15, step=1)
        pptx_template_file = st.file_uploader(
            t("pptx_template_label", lang),
            type=["pptx"],
            help=t("pptx_template_help", lang),
            key="pptx_template",
        )

        # ---- API keys ----
        st.subheader(f"🔑 {t('api_config_header', lang)}")

        def _resolve_key(secret_name: str) -> str:
            try:
                if secret_name in st.secrets:
                    return str(st.secrets[secret_name])
            except Exception:
                pass
            return os.environ.get(secret_name, "")

        stored_anthropic = _resolve_key("ANTHROPIC_API_KEY")
        stored_perplexity = _resolve_key("PERPLEXITY_API_KEY")
        stored_mistral = _resolve_key("MISTRAL_API_KEY")
        stored_ncbi_key = _resolve_key("NCBI_API_KEY")

        # Anthropic key input
        if not stored_anthropic:
            anthropic_key_input = st.text_input(
                t("anthropic_key_label", lang),
                type="password", key="anthropic_key",
                help=t("anthropic_key_help", lang),
                placeholder="sk-ant-...",
            )
        else:
            anthropic_key_input = ""

        # Mistral key input
        if not stored_mistral:
            mistral_key_input = st.text_input(
                t("mistral_key_label", lang),
                type="password", key="mistral_key",
                help=t("mistral_key_help", lang),
                placeholder="...",
            )
        else:
            mistral_key_input = ""

        # Perplexity key input
        if not stored_perplexity:
            perplexity_key_input = st.text_input(
                t("perplexity_key_label", lang),
                type="password", key="perplexity_key",
                help=t("perplexity_key_help", lang),
                placeholder="pplx-...",
            )
        else:
            perplexity_key_input = ""

        # NCBI key input
        if not stored_ncbi_key:
            ncbi_key_input = st.text_input(
                t("ncbi_key_label", lang),
                type="password", key="ncbi_key",
                help=t("ncbi_key_help", lang),
            )
        else:
            ncbi_key_input = ""

        effective_anthropic_key = stored_anthropic or anthropic_key_input
        effective_perplexity_key = stored_perplexity or perplexity_key_input
        effective_mistral_key = stored_mistral or mistral_key_input
        effective_ncbi_key = stored_ncbi_key or ncbi_key_input

        # API status display
        api_status = []
        for provider, key in [
            ("Claude (Anthropic)", effective_anthropic_key),
            ("Mistral AI", effective_mistral_key),
            ("Perplexity", effective_perplexity_key),
        ]:
            api_status.append(f"✅ {provider}" if key else f"❌ {provider}")
        if effective_ncbi_key:
            api_status.append("✅ NCBI API Key")

        st.markdown(f"**{t('api_status_title', lang)}**\n" + "\n".join(f"- {s}" for s in api_status))

        st.divider()
        run_button = st.button(f"🚀 {t('run_button', lang)}", type="primary", use_container_width=True)

    # ---- Main area -----------------------------------------------------------

    if run_button:
        if not keywords.strip():
            st.error(t("error_no_keywords", lang))
            return

        # Apply keys to config
        config.ANTHROPIC_API_KEY = effective_anthropic_key
        config.PERPLEXITY_API_KEY = effective_perplexity_key
        config.MISTRAL_API_KEY = effective_mistral_key
        config.NCBI_API_KEY = effective_ncbi_key

        # Check API keys for selected LLMs
        if not is_provider_available(llm_report):
            st.error(t("llm_key_missing", lang, provider=PROVIDER_LABELS[llm_report]))
            return
        if not is_provider_available(llm_verif):
            st.error(t("llm_key_missing", lang, provider=PROVIDER_LABELS[llm_verif]))
            return

        sources_enabled = []
        if src_pubmed:
            sources_enabled.append("pubmed")
        if src_semantic:
            sources_enabled.append("semantic_scholar")
        if src_europe:
            sources_enabled.append("europe_pmc")
        if src_scholar:
            sources_enabled.append("google_scholar")

        if not sources_enabled:
            st.error(t("error_no_sources", lang))
            return

        # ---- Agent 1 : Collection --------------------------------------------
        with st.status(f"🔍 {t('agent1_status', lang)}", expanded=True) as status1:
            log_area_1 = st.empty()
            logs_1 = []

            def progress_1(msg):
                logs_1.append(msg)
                log_area_1.markdown("\n\n".join(logs_1))

            articles, collection_report = run_collection(
                keywords=keywords,
                date_from=date_from,
                date_to=date_to,
                sources_enabled=sources_enabled,
                max_results=max_results,
                progress_callback=progress_1,
            )

            status1.update(
                label=f"✅ {t('agent1_done', lang, count=collection_report.final_count)}",
                state="complete",
            )

        if not articles:
            st.warning(t("no_articles_found", lang))
            return

        st.session_state["articles"] = articles
        st.session_state["keywords"] = keywords
        st.session_state["date_from"] = date_from
        st.session_state["date_to"] = date_to

        # ---- Agent 2 : Analysis (selected LLM) ------------------------------
        with st.status(f"📝 {t('agent2_status', lang)} [{PROVIDER_LABELS[llm_report]}]", expanded=True) as status2:
            log_area_2 = st.empty()
            logs_2 = []

            def progress_2(msg):
                logs_2.append(msg)
                log_area_2.markdown("\n\n".join(logs_2))

            report_markdown, cited_metadata = run_analysis(
                articles=articles,
                progress_callback=progress_2,
                lang=lang,
                llm_provider=llm_report,
            )

            status2.update(label=f"✅ {t('agent2_done', lang)}", state="complete")

        st.session_state["report_markdown"] = report_markdown

        # ---- Agent 3 : Editing (selected LLM for verification) ---------------
        with st.status(f"🎨 {t('agent3_status', lang)} [{PROVIDER_LABELS[llm_verif]}]", expanded=True) as status3:
            log_area_3 = st.empty()
            logs_3 = []

            def progress_3(msg):
                logs_3.append(msg)
                log_area_3.markdown("\n\n".join(logs_3))

            editor_report, corrected_report = run_editing(
                articles=articles,
                report_markdown=report_markdown,
                progress_callback=progress_3,
                lang=lang,
                llm_provider=llm_verif,
            )

            report_markdown = corrected_report

            status3.update(label=f"✅ {t('agent3_done', lang)}", state="complete")

        st.session_state["editor_report"] = editor_report
        st.session_state["report_markdown"] = report_markdown

        # ---- Exports ---------------------------------------------------------
        with st.status(f"📦 {t('exports_status', lang)}", expanded=False) as status_export:
            bibtex_content = generate_bibtex(articles)

            html_report = generate_html_report(
                report_markdown=report_markdown,
                articles=articles,
                editor_report=editor_report,
                keywords=keywords,
                date_from=date_from,
                date_to=date_to,
                lang=lang,
            )

            # Save uploaded PPTX template if provided
            pptx_template_path = None
            if pptx_template_file is not None:
                pptx_template_path = os.path.join(config.OUTPUT_DIR, "_template.pptx")
                with open(pptx_template_path, "wb") as tf:
                    tf.write(pptx_template_file.getbuffer())

            pptx_path = generate_pptx(
                report_markdown=report_markdown,
                articles=articles,
                editor_report=editor_report,
                keywords=keywords,
                date_from=date_from,
                date_to=date_to,
                lang=lang,
                num_slides=num_slides,
                template_path=pptx_template_path,
            )

            # Read PPTX bytes for download
            pptx_bytes = b""
            if os.path.exists(pptx_path):
                with open(pptx_path, "rb") as f:
                    pptx_bytes = f.read()

            status_export.update(label=f"✅ {t('exports_done', lang)}", state="complete")

        st.session_state["bibtex_content"] = bibtex_content
        st.session_state["html_report"] = html_report
        st.session_state["pptx_bytes"] = pptx_bytes

        st.success(f"🎉 {t('pipeline_done', lang)}")

    # ---- Display results -----------------------------------------------------
    if "articles" in st.session_state:
        _display_results()


def _display_results():
    """Display results in tabs."""
    lang = _get_lang()
    articles = st.session_state["articles"]
    report_markdown = st.session_state.get("report_markdown", "")
    editor_report = st.session_state.get("editor_report")
    bibtex_content = st.session_state.get("bibtex_content", "")
    html_report = st.session_state.get("html_report", "")
    pptx_bytes = st.session_state.get("pptx_bytes", b"")

    st.divider()

    col_dl1, col_dl2, col_dl3, col_dl4 = st.columns(4)

    with col_dl1:
        st.download_button(
            f"📥 {t('download_json', lang)}",
            data=articles_to_json(articles),
            file_name="corpus.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_dl2:
        st.download_button(
            f"📥 {t('download_bibtex', lang)}",
            data=bibtex_content,
            file_name="references.bib",
            mime="text/plain",
            use_container_width=True,
        )

    with col_dl3:
        if html_report:
            st.download_button(
                f"📥 {t('download_html', lang)}",
                data=html_report,
                file_name="rapport_bibliographique.html",
                mime="text/html",
                use_container_width=True,
            )
        else:
            st.button(f"📥 {t('report_unavailable', lang)}", disabled=True, use_container_width=True)

    with col_dl4:
        if pptx_bytes:
            st.download_button(
                f"📥 {t('download_pptx', lang)}",
                data=pptx_bytes,
                file_name="rapport_bibliographique.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True,
            )
        else:
            st.button(f"📥 {t('download_pptx', lang)}", disabled=True, use_container_width=True)

    tab_report, tab_figures, tab_data, tab_verification = st.tabs([
        f"📝 {t('tab_report', lang)}",
        f"📊 {t('tab_figures', lang)}",
        f"📋 {t('tab_data', lang)}",
        f"🔍 {t('tab_verification', lang)}",
    ])

    with tab_report:
        st.markdown(report_markdown, unsafe_allow_html=True)

    with tab_figures:
        if editor_report and editor_report.figures_generated:
            for fig_path in editor_report.figures_generated:
                if os.path.exists(fig_path):
                    st.image(fig_path, use_container_width=True)
                    st.caption(os.path.basename(fig_path))
        else:
            st.info(t("no_figures", lang))

    with tab_data:
        st.subheader(f"📋 {t('articles_count', lang, count=len(articles))}")

        table_data = []
        for a in articles:
            table_data.append({
                t("col_title", lang): a.title[:80] + ("..." if len(a.title) > 80 else ""),
                t("col_authors", lang): ", ".join(a.authors[:3]) + ("..." if len(a.authors) > 3 else ""),
                t("col_journal", lang): a.journal or "—",
                t("col_year", lang): a.year or "—",
                t("col_citations", lang): a.citation_count,
                t("col_doi", lang): a.doi or "—",
                t("col_source", lang): a.source,
            })

        st.dataframe(table_data, use_container_width=True, hide_index=True)

    with tab_verification:
        if editor_report and editor_report.verifications:
            score = editor_report.confidence_score
            st.metric(t("confidence_metric", lang), f"{score:.0f}%")

            for v in editor_report.verifications:
                if v.correction:
                    icon = "🔧"
                    label = t("status_corrected", lang)
                elif v.verified:
                    icon = "✅"
                    label = t("status_verified", lang)
                else:
                    icon = "⚠️"
                    label = t("status_unverified", lang)
                with st.expander(f"{icon} {v.claim[:100]}..."):
                    st.write(f"**{t('label_status', lang)}** {label}")
                    st.write(f"**{t('label_confidence', lang)}** {v.confidence*100:.0f}%")
                    if v.correction:
                        st.success(f"**{t('label_correction', lang)}** {v.correction}")
                    if v.source:
                        st.info(f"**{t('label_source', lang)}** {v.source}")
        else:
            st.info(t("verification_unavailable", lang))


if __name__ == "__main__":
    main()
