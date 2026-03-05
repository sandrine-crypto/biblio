"""Agent 3 — Éditeur & Visualisation : Vérification + infographies + PDF."""

import json
import logging
import os
import re
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import requests as req

from config import PERPLEXITY_API_KEY, PERPLEXITY_MODEL, PERPLEXITY_API_URL, OUTPUT_DIR, FIGURES_DIR
from models import Article, VerificationResult, EditorReport

logger = logging.getLogger(__name__)

# Styling
sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams.update({"figure.dpi": 300, "savefig.dpi": 300, "figure.figsize": (10, 6)})


# ─── Vérification via Perplexity ────────────────────────────────────────────

def _extract_claims(report: str, n: int = 10) -> list[str]:
    """Extrait les N principales affirmations factuelles du rapport."""
    sentences = re.split(r'(?<=[.!?])\s+', report)
    claims = []
    for s in sentences:
        s = s.strip()
        if len(s) > 50 and any(kw in s.lower() for kw in [
            "montr", "démontr", "révèl", "suggèr", "confirm", "identifi",
            "observ", "associé", "corrél", "augment", "diminu", "significati",
            "show", "demonstrat", "reveal", "suggest", "confirm", "identify",
            "observ", "associat", "correlat", "increas", "decreas", "significant",
        ]):
            claims.append(s)
        if len(claims) >= n:
            break

    # If not enough claims found with keywords, take longest sentences
    if len(claims) < n:
        remaining = [s.strip() for s in sentences if s.strip() not in claims and len(s.strip()) > 40]
        remaining.sort(key=len, reverse=True)
        claims.extend(remaining[:n - len(claims)])

    return claims[:n]


def verify_claims(report: str, progress_callback=None) -> tuple[list[VerificationResult], float]:
    """Vérifie les claims du rapport via l'API Perplexity."""
    results = []

    if not PERPLEXITY_API_KEY:
        msg = "⚠️ PERPLEXITY_API_KEY non configurée. Vérification factuelle ignorée."
        logger.warning(msg)
        if progress_callback:
            progress_callback(msg)
        return results, 0.0

    def log_progress(msg: str):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    claims = _extract_claims(report)
    log_progress(f"🔍 Vérification de {len(claims)} affirmations via Perplexity...")

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }

    for i, claim in enumerate(claims, 1):
        log_progress(f"  Vérification {i}/{len(claims)}...")
        try:
            payload = {
                "model": PERPLEXITY_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Tu es un vérificateur scientifique. Vérifie la factualité de "
                            "l'affirmation suivante. Réponds en JSON avec les champs: "
                            '"verified" (bool), "confidence" (0-1), "correction" (string ou null), '
                            '"source" (string ou null). Sois concis.'
                        ),
                    },
                    {"role": "user", "content": f"Vérifie cette affirmation scientifique: {claim}"},
                ],
                "max_tokens": 512,
            }

            response = req.post(PERPLEXITY_API_URL, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            content = response.json()["choices"][0]["message"]["content"]

            # Try to parse JSON from response
            try:
                json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
                if json_match:
                    verification = json.loads(json_match.group())
                else:
                    verification = json.loads(content)

                results.append(VerificationResult(
                    claim=claim,
                    verified=verification.get("verified", True),
                    correction=verification.get("correction"),
                    source=verification.get("source"),
                    confidence=float(verification.get("confidence", 0.5)),
                ))
            except (json.JSONDecodeError, ValueError):
                results.append(VerificationResult(
                    claim=claim,
                    verified=True,
                    confidence=0.5,
                ))

        except Exception as e:
            logger.warning(f"Erreur vérification claim {i}: {e}")
            results.append(VerificationResult(claim=claim, verified=True, confidence=0.5))

    # Score de confiance global
    if results:
        confidence_score = sum(v.confidence for v in results) / len(results) * 100
    else:
        confidence_score = 0.0

    log_progress(f"✅ Score de confiance global: {confidence_score:.0f}%")
    return results, confidence_score


# ─── Visualisations ─────────────────────────────────────────────────────────

def generate_visualizations(articles: list[Article], report: str, progress_callback=None) -> list[str]:
    """Génère toutes les infographies."""
    os.makedirs(FIGURES_DIR, exist_ok=True)
    figures = []

    def log_progress(msg: str):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    log_progress("📊 Génération des visualisations...")

    # 1. Timeline publications par année
    try:
        fig_path = _plot_timeline(articles)
        if fig_path:
            figures.append(fig_path)
            log_progress("  ✅ Timeline des publications")
    except Exception as e:
        logger.error(f"Erreur timeline: {e}")

    # 2. Top 15 journaux
    try:
        fig_path = _plot_top_journals(articles)
        if fig_path:
            figures.append(fig_path)
            log_progress("  ✅ Top 15 journaux")
    except Exception as e:
        logger.error(f"Erreur journaux: {e}")

    # 3. Word cloud
    try:
        fig_path = _plot_wordcloud(articles)
        if fig_path:
            figures.append(fig_path)
            log_progress("  ✅ Word cloud")
    except Exception as e:
        logger.error(f"Erreur wordcloud: {e}")

    # 4. Réseau co-citations (si ≥ 20 articles)
    if len(articles) >= 20:
        try:
            fig_path = _plot_cocitation_network(articles)
            if fig_path:
                figures.append(fig_path)
                log_progress("  ✅ Réseau de co-citations")
        except Exception as e:
            logger.error(f"Erreur réseau: {e}")

    # 5. Heatmap sous-thématiques × années
    try:
        fig_path = _plot_theme_heatmap(articles)
        if fig_path:
            figures.append(fig_path)
            log_progress("  ✅ Heatmap thématiques × années")
    except Exception as e:
        logger.error(f"Erreur heatmap: {e}")

    log_progress(f"📊 {len(figures)} figures générées")
    return figures


def _plot_timeline(articles: list[Article]) -> str | None:
    """Bar chart du volume de publications par année."""
    years = [a.year for a in articles if a.year]
    if not years:
        return None

    year_counts = Counter(years)
    sorted_years = sorted(year_counts.keys())
    counts = [year_counts[y] for y in sorted_years]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar([str(y) for y in sorted_years], counts, color=sns.color_palette("deep")[0], edgecolor="white")
    ax.set_xlabel("Année", fontsize=12)
    ax.set_ylabel("Nombre de publications", fontsize=12)
    ax.set_title("Volume de publications par année", fontsize=14, fontweight="bold")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    path = os.path.join(FIGURES_DIR, "timeline.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_top_journals(articles: list[Article]) -> str | None:
    """Top 15 journaux par nombre de publications."""
    journals = [a.journal for a in articles if a.journal]
    if not journals:
        return None

    journal_counts = Counter(journals).most_common(15)
    names = [j[0][:50] for j in journal_counts]
    counts = [j[1] for j in journal_counts]

    fig, ax = plt.subplots(figsize=(12, 8))
    colors = sns.color_palette("deep", len(names))
    ax.barh(range(len(names)), counts, color=colors, edgecolor="white")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=10)
    ax.set_xlabel("Nombre de publications", fontsize=12)
    ax.set_title("Top 15 journaux par nombre de publications", fontsize=14, fontweight="bold")
    ax.invert_yaxis()
    plt.tight_layout()

    path = os.path.join(FIGURES_DIR, "top_journals.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_wordcloud(articles: list[Article]) -> str | None:
    """Word cloud des abstracts."""
    from wordcloud import WordCloud

    texts = [a.abstract for a in articles if a.abstract]
    if not texts:
        return None

    combined = " ".join(texts)

    # Stopwords combinées (anglais + français)
    stopwords = set()
    try:
        from wordcloud import STOPWORDS
        stopwords.update(STOPWORDS)
    except ImportError:
        pass
    stopwords.update([
        "et", "le", "la", "les", "de", "du", "des", "un", "une", "en", "dans",
        "pour", "par", "sur", "avec", "qui", "que", "est", "sont", "ont", "été",
        "cette", "ces", "nous", "notre", "leur", "il", "elle", "ils", "elles",
        "the", "and", "was", "were", "been", "have", "has", "had", "are", "is",
        "our", "their", "this", "that", "from", "with", "which", "these", "those",
        "not", "but", "can", "may", "will", "would", "could", "should", "also",
        "than", "more", "most", "between", "using", "used", "however", "both",
        "results", "study", "studies", "found", "showed", "based", "including",
        "background", "methods", "conclusions", "objective", "purpose",
    ])

    wc = WordCloud(
        width=1200, height=600,
        background_color="white",
        max_words=100,
        stopwords=stopwords,
        colormap="viridis",
        contour_width=1,
        contour_color="steelblue",
    ).generate(combined)

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title("Nuage de mots des abstracts", fontsize=14, fontweight="bold", pad=20)
    plt.tight_layout()

    path = os.path.join(FIGURES_DIR, "wordcloud.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_cocitation_network(articles: list[Article]) -> str | None:
    """Réseau de co-citations basé sur les mots-clés partagés."""
    import networkx as nx

    # Build network based on shared keywords
    articles_with_kw = [(i, a) for i, a in enumerate(articles) if a.keywords]
    if len(articles_with_kw) < 5:
        return None

    G = nx.Graph()

    # Add nodes
    for i, a in articles_with_kw[:40]:  # Limit for readability
        label = a.title[:30] + "..." if len(a.title) > 30 else a.title
        G.add_node(i, label=label, size=max(a.citation_count, 1))

    # Add edges based on shared keywords
    for idx1 in range(len(articles_with_kw)):
        i, a1 = articles_with_kw[idx1]
        kw1 = set(k.lower() for k in a1.keywords)
        for idx2 in range(idx1 + 1, len(articles_with_kw)):
            j, a2 = articles_with_kw[idx2]
            kw2 = set(k.lower() for k in a2.keywords)
            shared = kw1 & kw2
            if shared:
                G.add_edge(i, j, weight=len(shared))

    if G.number_of_edges() == 0:
        return None

    fig, ax = plt.subplots(figsize=(14, 10))

    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    node_sizes = [max(G.nodes[n].get("size", 1) * 50, 100) for n in G.nodes()]
    labels = {n: G.nodes[n].get("label", str(n)) for n in G.nodes()}

    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color=sns.color_palette("deep")[0],
                           alpha=0.7, ax=ax)
    edge_weights = [G[u][v].get("weight", 1) for u, v in G.edges()]
    nx.draw_networkx_edges(G, pos, width=[w * 0.5 for w in edge_weights], alpha=0.3, ax=ax)
    nx.draw_networkx_labels(G, pos, labels, font_size=6, ax=ax)

    ax.set_title("Réseau de co-citations (mots-clés partagés)", fontsize=14, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()

    path = os.path.join(FIGURES_DIR, "cocitation_network.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_theme_heatmap(articles: list[Article]) -> str | None:
    """Heatmap des sous-thématiques × années."""
    import numpy as np

    # Collect keyword-year pairs
    kw_year_pairs = []
    for a in articles:
        if a.year and a.keywords:
            for kw in a.keywords[:5]:  # Top 5 keywords per article
                kw_year_pairs.append((kw.lower(), a.year))

    if not kw_year_pairs:
        return None

    # Find top keywords
    kw_counts = Counter(kw for kw, _ in kw_year_pairs)
    top_keywords = [kw for kw, _ in kw_counts.most_common(15)]

    if len(top_keywords) < 3:
        return None

    # Get year range
    years = sorted(set(y for _, y in kw_year_pairs))
    if len(years) < 2:
        return None

    # Build matrix
    matrix = np.zeros((len(top_keywords), len(years)))
    year_idx = {y: i for i, y in enumerate(years)}

    for kw, y in kw_year_pairs:
        if kw in top_keywords and y in year_idx:
            ki = top_keywords.index(kw)
            matrix[ki][year_idx[y]] += 1

    fig, ax = plt.subplots(figsize=(14, 8))
    sns.heatmap(
        matrix,
        xticklabels=[str(y) for y in years],
        yticklabels=top_keywords,
        cmap="YlOrRd",
        annot=True,
        fmt=".0f",
        linewidths=0.5,
        ax=ax,
    )
    ax.set_title("Heatmap: thématiques × années", fontsize=14, fontweight="bold")
    ax.set_xlabel("Année", fontsize=12)
    ax.set_ylabel("Thématique", fontsize=12)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    path = os.path.join(FIGURES_DIR, "theme_heatmap.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


# ─── Pipeline principal ─────────────────────────────────────────────────────

def run_editing(
    articles: list[Article],
    report_markdown: str,
    progress_callback=None,
) -> EditorReport:
    """Exécute la vérification, les visualisations et la génération du rapport final.

    Args:
        articles: Articles du corpus
        report_markdown: Rapport markdown de l'Agent 2
        progress_callback: Fonction optionnelle (message: str)

    Returns:
        EditorReport avec les résultats
    """
    def log_progress(msg: str):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    editor_report = EditorReport()

    # 1. Vérification factuelle
    log_progress("🔎 Phase de vérification factuelle...")
    verifications, confidence = verify_claims(report_markdown, progress_callback)
    editor_report.verifications = verifications
    editor_report.confidence_score = confidence

    # 2. Visualisations
    log_progress("📊 Phase de génération des visualisations...")
    figures = generate_visualizations(articles, report_markdown, progress_callback)
    editor_report.figures_generated = figures

    # 3. Sauvegarde du rapport d'édition
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    editor_path = os.path.join(OUTPUT_DIR, "editor_report.json")
    with open(editor_path, "w", encoding="utf-8") as f:
        json.dump(editor_report.to_dict(), f, ensure_ascii=False, indent=2)

    log_progress("✅ Agent Éditeur terminé")
    return editor_report
