from __future__ import annotations

from src.analysis import (
    rank_municipalities,
    get_best_building_candidate,
    compare_municipalities,
    summarize_municipality,
    extract_municipality_names,
)


def _format_candidate(item: dict) -> str:
    return (
        f"**{item.get('kommune', 'Ukjent')}**  \n"
        f"- Total score: {item.get('total_score', 'ukjent')}  \n"
        f"- Befolkningsvekst: {item.get('befolkningsvekst', 'ukjent')} "
        f"({item.get('vekst_prosent', 'ukjent')} %)  \n"
        f"- Saksbehandlingstid: {item.get('saksbehandlingstid', 'ukjent')}  \n"
        f"- Vurdering: {item.get('anbefaling', 'ukjent')}"
    )


def answer_question_rule_based(question: str) -> str:
    """Tokenfri agent. Bruker ingen LLM og gir derfor ingen token-/rate-limit-kostnad."""
    q = (question or "").lower()
    ranking = rank_municipalities(limit=500)
    available_names = [item["kommune"] for item in ranking]

    if "sammenlign" in q:
        requested = extract_municipality_names(question, available_names)
        if not requested:
            return (
                "## Sammenligning\n\n"
                "Jeg fant ingen kommunenavn i spørsmålet. Prøv for eksempel: "
                "'Sammenlign Oslo, Bærum og Lillestrøm.'"
            )

        result = compare_municipalities(requested)
        body = "\n\n".join(_format_candidate(item) for item in result) or "Fant ingen match."
        return f"## Sammenligning\n\n{body}"

    if "beste" in q or "best" in q:
        result = get_best_building_candidate()
        if "error" in result:
            return f"## Beste kandidat\n\n{result['error']}"
        return f"## Beste kandidat\n\n{_format_candidate(result)}"

    requested = extract_municipality_names(question, available_names)
    if requested or any(word in q for word in ["vurder", "forklar", "oppsummer", "analyser"]):
        if not requested:
            return (
                "## Kommunevurdering\n\n"
                "Jeg fant ingen kommunenavn i spørsmålet. Prøv for eksempel: "
                "'Vurder Trondheim' eller 'Forklar Oslo'."
            )

        result = summarize_municipality(requested[0])
        if "error" in result:
            return f"## Kommunevurdering\n\n{result['error']}"
        return f"## Kommunevurdering\n\n{_format_candidate(result)}"

    return (
        "Prøv f.eks:\n"
        "- 'Vurder Lillestrøm'\n"
        "- 'Sammenlign Oslo og Bærum'\n"
        "- 'Hvilken kommune er best?'"
    )   
