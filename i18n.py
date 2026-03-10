"""Internationalization — English / French translations."""

TRANSLATIONS = {
    "fr": {
        # Page config
        "page_title": "Recherche Bibliographique Scientifique",
        # Main
        "main_title": "Recherche Bibliographique Scientifique",
        "main_subtitle": "Pipeline multi-agents automatise : **Collecte -> Analyse -> Edition**",
        # Sidebar
        "sidebar_header": "Parametres de recherche",
        "keywords_label": "Mots-cles de recherche",
        "keywords_placeholder": 'ex: "gene therapy" CRISPR cancer "immune checkpoint"',
        "keywords_help": (
            "Entrez autant de mots-cles que necessaire. "
            "Utilisez des guillemets pour les expressions exactes : \"gene therapy\". "
            "Separez les mots-cles par des espaces ou des retours a la ligne."
        ),
        "date_from": "Date de debut",
        "date_to": "Date de fin",
        "sources_header": "Sources",
        "google_scholar_warning": "Peut etre bloque",
        "max_results_label": "Resultats max par source",
        "api_config_header": "Configuration API",
        "anthropic_key_label": "Cle API Anthropic",
        "anthropic_key_help": "Pour Claude.",
        "perplexity_key_label": "Cle API Perplexity",
        "perplexity_key_help": "Pour Perplexity.",
        "mistral_key_label": "Cle API Mistral",
        "mistral_key_help": "Pour Mistral AI.",
        "ncbi_key_label": "Cle API NCBI (optionnel)",
        "ncbi_key_help": "Augmente le rate limit PubMed (10 req/s au lieu de 3).",
        "api_status_title": "Statut des APIs :",
        "run_button": "Lancer la recherche",
        "language_label": "Langue / Language",
        # LLM selection
        "llm_config_header": "Modeles LLM",
        "llm_report_label": "LLM pour le rapport (Agent 2)",
        "llm_verif_label": "LLM pour la verification (Agent 3)",
        "llm_must_differ": "Les 2 modeles doivent etre differents.",
        "llm_key_missing": "Cle API manquante pour {provider}.",
        # PPTX
        "pptx_header": "Presentation PPTX",
        "pptx_slides_label": "Nombre de slides",
        "pptx_template_label": "Modele PPTX (optionnel)",
        "pptx_template_help": "Uploadez un fichier PPTX vide pour utiliser ses slide masters, polices et couleurs comme base.",
        "download_pptx": "Telecharger PPTX",
        # Errors / warnings
        "error_no_keywords": "Veuillez entrer des mots-cles de recherche.",
        "warning_no_llm_key": (
            "Cle API non configuree pour le LLM selectionne. "
            "Ajoutez la cle dans la sidebar ou dans Settings -> Secrets."
        ),
        "error_no_sources": "Veuillez selectionner au moins une source.",
        "no_articles_found": "Aucun article trouve. Essayez d'elargir vos criteres de recherche.",
        # Pipeline status
        "agent1_status": "Agent 1 — Documentaliste (Collecte & Deduplication)",
        "agent1_done": "Agent 1 termine — {count} articles uniques",
        "agent2_status": "Agent 2 — Chercheur scientifique (Analyse & Synthese)",
        "agent2_done": "Agent 2 termine — Rapport genere",
        "agent3_status": "Agent 3 — Editeur & Visualisation",
        "agent3_done": "Agent 3 termine",
        "exports_status": "Generation des exports...",
        "exports_done": "Exports generes",
        "pipeline_done": "Pipeline termine avec succes !",
        # Results
        "download_json": "Telecharger JSON",
        "download_bibtex": "Telecharger BibTeX",
        "download_html": "Telecharger Rapport HTML",
        "report_unavailable": "Rapport non disponible",
        "tab_report": "Rapport",
        "tab_figures": "Figures",
        "tab_data": "Donnees",
        "tab_verification": "Verification",
        "no_figures": "Aucune figure generee.",
        "articles_count": "{count} articles",
        "col_title": "Titre",
        "col_authors": "Auteurs",
        "col_journal": "Journal",
        "col_year": "Annee",
        "col_citations": "Citations",
        "col_doi": "DOI",
        "col_source": "Source",
        "confidence_metric": "Score de confiance global",
        "status_corrected": "Corrige",
        "status_verified": "Verifie",
        "status_unverified": "Non verifie",
        "label_status": "Statut:",
        "label_confidence": "Confiance:",
        "label_correction": "Correction appliquee :",
        "label_source": "Source:",
        "verification_unavailable": (
            "Verification factuelle non disponible. "
            "Configurez la cle API du LLM de verification pour activer cette fonctionnalite."
        ),
        # HTML report
        "html_title": "Rapport de Recherche Bibliographique Scientifique",
        "html_articles_analyzed": "Articles analyses",
        "html_factual_confidence": "Confiance factuelle",
        "html_period_covered": "Periode couverte",
        "html_synthesis_report": "Rapport de synthese",
        "html_infographics": "Infographies",
        "html_article_corpus": "Corpus d'articles",
        "html_factual_verification": "Verification factuelle",
        "html_footer": "Rapport genere automatiquement — Recherche Bibliographique Scientifique",
        # Figure captions
        "fig_timeline": "Volume de publications par annee",
        "fig_top_journals": "Top 15 journaux par nombre de publications",
        "fig_wordcloud": "Nuage de mots des abstracts",
        "fig_cocitation": "Reseau de co-citations (mots-cles partages)",
        "fig_heatmap": "Heatmap des sous-thematiques par annee",
    },
    "en": {
        # Page config
        "page_title": "Scientific Literature Search",
        # Main
        "main_title": "Scientific Literature Search",
        "main_subtitle": "Multi-agent automated pipeline: **Collection -> Analysis -> Editing**",
        # Sidebar
        "sidebar_header": "Search parameters",
        "keywords_label": "Search keywords",
        "keywords_placeholder": 'e.g.: "gene therapy" CRISPR cancer "immune checkpoint"',
        "keywords_help": (
            "Enter as many keywords as needed. "
            "Use quotes for exact phrases: \"gene therapy\". "
            "Separate keywords with spaces or line breaks."
        ),
        "date_from": "Start date",
        "date_to": "End date",
        "sources_header": "Sources",
        "google_scholar_warning": "May be blocked",
        "max_results_label": "Max results per source",
        "api_config_header": "API Configuration",
        "anthropic_key_label": "Anthropic API Key",
        "anthropic_key_help": "For Claude.",
        "perplexity_key_label": "Perplexity API Key",
        "perplexity_key_help": "For Perplexity.",
        "mistral_key_label": "Mistral API Key",
        "mistral_key_help": "For Mistral AI.",
        "ncbi_key_label": "NCBI API Key (optional)",
        "ncbi_key_help": "Increases PubMed rate limit (10 req/s instead of 3).",
        "api_status_title": "API Status:",
        "run_button": "Start search",
        "language_label": "Langue / Language",
        # LLM selection
        "llm_config_header": "LLM Models",
        "llm_report_label": "LLM for report (Agent 2)",
        "llm_verif_label": "LLM for verification (Agent 3)",
        "llm_must_differ": "The 2 models must be different.",
        "llm_key_missing": "API key missing for {provider}.",
        # PPTX
        "pptx_header": "PPTX Presentation",
        "pptx_slides_label": "Number of slides",
        "pptx_template_label": "PPTX template (optional)",
        "pptx_template_help": "Upload a blank PPTX file to use its slide masters, fonts and colors as a base.",
        "download_pptx": "Download PPTX",
        # Errors / warnings
        "error_no_keywords": "Please enter search keywords.",
        "warning_no_llm_key": (
            "API key not configured for the selected LLM. "
            "Add the key in the sidebar or in Settings -> Secrets."
        ),
        "error_no_sources": "Please select at least one source.",
        "no_articles_found": "No articles found. Try broadening your search criteria.",
        # Pipeline status
        "agent1_status": "Agent 1 — Librarian (Collection & Deduplication)",
        "agent1_done": "Agent 1 complete — {count} unique articles",
        "agent2_status": "Agent 2 — Scientific Researcher (Analysis & Synthesis)",
        "agent2_done": "Agent 2 complete — Report generated",
        "agent3_status": "Agent 3 — Editor & Visualization",
        "agent3_done": "Agent 3 complete",
        "exports_status": "Generating exports...",
        "exports_done": "Exports generated",
        "pipeline_done": "Pipeline completed successfully!",
        # Results
        "download_json": "Download JSON",
        "download_bibtex": "Download BibTeX",
        "download_html": "Download HTML Report",
        "report_unavailable": "Report unavailable",
        "tab_report": "Report",
        "tab_figures": "Figures",
        "tab_data": "Data",
        "tab_verification": "Verification",
        "no_figures": "No figures generated.",
        "articles_count": "{count} articles",
        "col_title": "Title",
        "col_authors": "Authors",
        "col_journal": "Journal",
        "col_year": "Year",
        "col_citations": "Citations",
        "col_doi": "DOI",
        "col_source": "Source",
        "confidence_metric": "Overall confidence score",
        "status_corrected": "Corrected",
        "status_verified": "Verified",
        "status_unverified": "Unverified",
        "label_status": "Status:",
        "label_confidence": "Confidence:",
        "label_correction": "Correction applied:",
        "label_source": "Source:",
        "verification_unavailable": (
            "Fact-checking unavailable. "
            "Configure the verification LLM API key to enable this feature."
        ),
        # HTML report
        "html_title": "Scientific Literature Review Report",
        "html_articles_analyzed": "Articles analyzed",
        "html_factual_confidence": "Factual confidence",
        "html_period_covered": "Period covered",
        "html_synthesis_report": "Synthesis report",
        "html_infographics": "Infographics",
        "html_article_corpus": "Article corpus",
        "html_factual_verification": "Fact-checking",
        "html_footer": "Automatically generated report — Scientific Literature Search",
        # Figure captions
        "fig_timeline": "Publication volume by year",
        "fig_top_journals": "Top 15 journals by publication count",
        "fig_wordcloud": "Abstract word cloud",
        "fig_cocitation": "Co-citation network (shared keywords)",
        "fig_heatmap": "Topic heatmap by year",
    },
}


def t(key: str, lang: str = "fr", **kwargs) -> str:
    """Get translated string. Falls back to French if key missing."""
    text = TRANSLATIONS.get(lang, TRANSLATIONS["fr"]).get(key, TRANSLATIONS["fr"].get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return text
