"""Application Streamlit de Recherche Bibliographique Scientifique Automatisée."""

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
from utils.pdf_report import generate_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

# ─── Configuration page ─────────────────────────────────────────────────────

st.set_page_config(
    page_title="Recherche Bibliographique Scientifique",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    st.title("📚 Recherche Bibliographique Scientifique")
    st.markdown(
        "Pipeline multi-agents automatisé : **Collecte → Analyse → Édition**"
    )

    # ─── Sidebar : paramètres ────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Paramètres de recherche")

        keywords = st.text_input(
            "Mots-clés de recherche",
            placeholder="ex: CRISPR gene therapy cancer",
            help="Termes de recherche séparés par des espaces",
        )

        col1, col2 = st.columns(2)
        with col1:
            date_from = st.text_input("Date de début", value="2020/01/01", help="Format: YYYY/MM/DD")
        with col2:
            date_to = st.text_input("Date de fin", value="2025/12/31", help="Format: YYYY/MM/DD")

        st.subheader("📡 Sources")
        src_pubmed = st.checkbox("PubMed", value=True)
        src_semantic = st.checkbox("Semantic Scholar", value=True)
        src_europe = st.checkbox("Europe PMC", value=True)
        src_scholar = st.checkbox("Google Scholar", value=False, help="⚠️ Peut être bloqué")

        max_results = st.slider("Résultats max par source", 10, 100, 50, step=10)

        st.subheader("🔑 Configuration API")

        anthropic_key_input = st.text_input(
            "Clé API Anthropic",
            type="password",
            value="",
            help="Requis pour l'analyse LLM. Laisser vide si configurée dans Secrets.",
            placeholder="sk-ant-...",
        )

        perplexity_key_input = st.text_input(
            "Clé API Perplexity (optionnel)",
            type="password",
            value="",
            help="Pour la vérification factuelle. Laisser vide si non nécessaire.",
            placeholder="pplx-...",
        )

        ncbi_key_input = st.text_input(
            "Clé API NCBI (optionnel)",
            type="password",
            value="",
            help="Augmente le rate limit PubMed (10 req/s au lieu de 3).",
        )

        ncbi_email = st.text_input(
            "Email NCBI",
            value=config.NCBI_EMAIL,
            help="Requis pour PubMed",
        )

        # Effective keys: sidebar input > st.secrets > env var
        effective_anthropic_key = anthropic_key_input or config.ANTHROPIC_API_KEY
        effective_perplexity_key = perplexity_key_input or config.PERPLEXITY_API_KEY
        effective_ncbi_key = ncbi_key_input or config.NCBI_API_KEY

        api_status = []
        if effective_anthropic_key:
            api_status.append("✅ Anthropic (Claude)")
        else:
            api_status.append("❌ Anthropic (clé manquante)")

        if effective_perplexity_key:
            api_status.append("✅ Perplexity")
        else:
            api_status.append("⚠️ Perplexity (optionnel)")

        if effective_ncbi_key:
            api_status.append("✅ NCBI API Key")

        st.markdown("**Statut des APIs :**\n" + "\n".join(f"- {s}" for s in api_status))

        st.divider()
        run_button = st.button("🚀 Lancer la recherche", type="primary", use_container_width=True)

    # ─── Main area ───────────────────────────────────────────────────────

    if run_button:
        if not keywords.strip():
            st.error("Veuillez entrer des mots-clés de recherche.")
            return

        # Override config with effective keys (sidebar > secrets > env)
        config.ANTHROPIC_API_KEY = effective_anthropic_key
        config.PERPLEXITY_API_KEY = effective_perplexity_key
        config.NCBI_API_KEY = effective_ncbi_key
        config.NCBI_EMAIL = ncbi_email

        if not effective_anthropic_key:
            st.warning(
                "⚠️ Clé API Anthropic non configurée. L'analyse LLM sera en mode dégradé. "
                "Ajoutez la clé dans la sidebar ou dans Settings → Secrets (ANTHROPIC_API_KEY)."
            )

        # Build sources list
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
            st.error("Veuillez sélectionner au moins une source.")
            return

        # ─── Agent 1 : Collecte ──────────────────────────────────────────
        with st.status("🔍 Agent 1 — Documentaliste (Collecte & Déduplication)", expanded=True) as status1:
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
                label=f"✅ Agent 1 terminé — {collection_report.final_count} articles uniques",
                state="complete",
            )

        if not articles:
            st.warning("Aucun article trouvé. Essayez d'élargir vos critères de recherche.")
            return

        # Store articles in session state
        st.session_state["articles"] = articles
        st.session_state["keywords"] = keywords
        st.session_state["date_from"] = date_from
        st.session_state["date_to"] = date_to

        # ─── Agent 2 : Analyse ───────────────────────────────────────────
        with st.status("📝 Agent 2 — Chercheur scientifique (Analyse & Synthèse)", expanded=True) as status2:
            log_area_2 = st.empty()
            logs_2 = []

            def progress_2(msg):
                logs_2.append(msg)
                log_area_2.markdown("\n\n".join(logs_2))

            report_markdown, cited_metadata = run_analysis(
                articles=articles,
                progress_callback=progress_2,
            )

            status2.update(label="✅ Agent 2 terminé — Rapport généré", state="complete")

        st.session_state["report_markdown"] = report_markdown

        # ─── Agent 3 : Édition ───────────────────────────────────────────
        with st.status("🎨 Agent 3 — Éditeur & Visualisation", expanded=True) as status3:
            log_area_3 = st.empty()
            logs_3 = []

            def progress_3(msg):
                logs_3.append(msg)
                log_area_3.markdown("\n\n".join(logs_3))

            editor_report = run_editing(
                articles=articles,
                report_markdown=report_markdown,
                progress_callback=progress_3,
            )

            status3.update(label="✅ Agent 3 terminé", state="complete")

        st.session_state["editor_report"] = editor_report

        # ─── Exports ─────────────────────────────────────────────────────
        with st.status("📦 Génération des exports...", expanded=False) as status_export:
            # BibTeX
            bibtex_content = generate_bibtex(articles)

            # PDF
            pdf_path = generate_pdf(
                report_markdown=report_markdown,
                articles=articles,
                editor_report=editor_report,
                keywords=keywords,
                date_from=date_from,
                date_to=date_to,
            )

            status_export.update(label="✅ Exports générés", state="complete")

        st.session_state["bibtex_content"] = bibtex_content
        st.session_state["pdf_path"] = pdf_path

        st.success("🎉 Pipeline terminé avec succès !")

    # ─── Display results ─────────────────────────────────────────────────
    if "articles" in st.session_state:
        _display_results()


def _display_results():
    """Affiche les résultats dans des onglets."""
    articles = st.session_state["articles"]
    report_markdown = st.session_state.get("report_markdown", "")
    editor_report = st.session_state.get("editor_report")
    bibtex_content = st.session_state.get("bibtex_content", "")
    pdf_path = st.session_state.get("pdf_path")

    st.divider()

    # Download buttons
    col_dl1, col_dl2, col_dl3 = st.columns(3)

    with col_dl1:
        st.download_button(
            "📥 Télécharger JSON",
            data=articles_to_json(articles),
            file_name="corpus.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_dl2:
        st.download_button(
            "📥 Télécharger BibTeX",
            data=bibtex_content,
            file_name="references.bib",
            mime="text/plain",
            use_container_width=True,
        )

    with col_dl3:
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "📥 Télécharger PDF",
                    data=f.read(),
                    file_name="rapport_bibliographique.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        else:
            st.button("📥 PDF non disponible", disabled=True, use_container_width=True)

    # Tabs
    tab_report, tab_figures, tab_data, tab_verification = st.tabs([
        "📝 Rapport", "📊 Figures", "📋 Données", "🔍 Vérification"
    ])

    with tab_report:
        st.markdown(report_markdown)

    with tab_figures:
        if editor_report and editor_report.figures_generated:
            for fig_path in editor_report.figures_generated:
                if os.path.exists(fig_path):
                    st.image(fig_path, use_container_width=True)
                    st.caption(os.path.basename(fig_path))
        else:
            st.info("Aucune figure générée.")

    with tab_data:
        st.subheader(f"📋 {len(articles)} articles")

        # Build table data
        table_data = []
        for a in articles:
            table_data.append({
                "Titre": a.title[:80] + ("..." if len(a.title) > 80 else ""),
                "Auteurs": ", ".join(a.authors[:3]) + ("..." if len(a.authors) > 3 else ""),
                "Journal": a.journal or "—",
                "Année": a.year or "—",
                "Citations": a.citation_count,
                "DOI": a.doi or "—",
                "Source": a.source,
            })

        st.dataframe(table_data, use_container_width=True, hide_index=True)

    with tab_verification:
        if editor_report and editor_report.verifications:
            score = editor_report.confidence_score
            st.metric("Score de confiance global", f"{score:.0f}%")

            for v in editor_report.verifications:
                icon = "✅" if v.verified else "⚠️"
                with st.expander(f"{icon} {v.claim[:100]}..."):
                    st.write(f"**Vérifié:** {'Oui' if v.verified else 'Non'}")
                    st.write(f"**Confiance:** {v.confidence*100:.0f}%")
                    if v.correction:
                        st.warning(f"**Correction:** {v.correction}")
                    if v.source:
                        st.info(f"**Source:** {v.source}")
        else:
            st.info(
                "Vérification factuelle non disponible. "
                "Configurez PERPLEXITY_API_KEY pour activer cette fonctionnalité."
            )


if __name__ == "__main__":
    main()
