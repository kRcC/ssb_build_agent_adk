from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd

from src.ssb_client import get_ssb_befolkningsdata, get_ssb_behandlingsdata
from src.transform import jsonstat_to_dataframe

DEFAULT_START_YEAR = "2021"
DEFAULT_END_YEAR = "2025"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except Exception:
        return default


def _normalize(value: float, min_value: float, max_value: float) -> float:
    if max_value == min_value:
        return 50.0
    return ((value - min_value) / (max_value - min_value)) * 100


def get_population_dataframe() -> pd.DataFrame:
    return jsonstat_to_dataframe(get_ssb_befolkningsdata())


def get_building_case_dataframe() -> pd.DataFrame:
    return jsonstat_to_dataframe(get_ssb_behandlingsdata())


def get_population_growth(start_year: str = DEFAULT_START_YEAR, end_year: str = DEFAULT_END_YEAR) -> list[dict[str, Any]]:
    """Beregner befolkningsvekst per kommune mellom start_year og end_year."""
    df = get_population_dataframe()
    if df.empty:
        return []

    required = {"Tid", "Region_kode", "Region", "verdi"}
    if not required.issubset(df.columns):
        return []

    df["Tid"] = df["Tid"].astype(str)
    df["verdi"] = pd.to_numeric(df["verdi"], errors="coerce")

    if "ContentsCode_kode" in df.columns:
        person_rows = df[df["ContentsCode_kode"].astype(str).str.contains("Person", case=False, na=False)]
        if not person_rows.empty:
            df = person_rows

    pivot = df.pivot_table(
        index=["Region_kode", "Region"],
        columns="Tid",
        values="verdi",
        aggfunc="sum",
    ).reset_index()

    if start_year not in pivot.columns or end_year not in pivot.columns:
        return []

    pivot["befolkning_start"] = pd.to_numeric(pivot[start_year], errors="coerce")
    pivot["befolkning_end"] = pd.to_numeric(pivot[end_year], errors="coerce")
    pivot = pivot.dropna(subset=["befolkning_start", "befolkning_end"])
    pivot = pivot[pivot["befolkning_start"] > 0]

    pivot["befolkningsvekst"] = pivot["befolkning_end"] - pivot["befolkning_start"]
    pivot["vekst_prosent"] = (pivot["befolkningsvekst"] / pivot["befolkning_start"] * 100).round(2)
    pivot["kommune_kode"] = pivot["Region_kode"].astype(str)
    pivot["kommune"] = pivot["Region"].map(lambda n: str(n).strip())

    result = pivot[[
        "kommune_kode",
        "kommune",
        "befolkning_start",
        "befolkning_end",
        "befolkningsvekst",
        "vekst_prosent",
    ]].sort_values("befolkningsvekst", ascending=False)

    return result.to_dict(orient="records")


def get_case_processing_time(year: str = DEFAULT_END_YEAR) -> list[dict[str, Any]]:
    """Henter gjennomsnittlig saksbehandlingstid per kommune for valgt år."""
    df = get_building_case_dataframe()
    if df.empty:
        return []

    required = {"Tid", "ContentsCode_kode", "verdi"}
    if not required.issubset(df.columns):
        return []

    df["Tid"] = df["Tid"].astype(str)
    df["verdi"] = pd.to_numeric(df["verdi"], errors="coerce")

    df_case = df[df["ContentsCode_kode"].astype(str).str.contains("KOSgjennomsnitts", na=False)]
    df_case = df_case[df_case["Tid"] == str(year)]

    code_col = "KOKkommuneregion0000_kode"
    name_col = "KOKkommuneregion0000"
    if df_case.empty or code_col not in df_case.columns or name_col not in df_case.columns:
        return []

    result = df_case.rename(columns={
        code_col: "kommune_kode",
        name_col: "kommune",
        "verdi": "saksbehandlingstid",
    })

    result["kommune_kode"] = result["kommune_kode"].astype(str)
    result["kommune"] = result["kommune"].map(lambda n: str(n).strip())

    return result[["kommune_kode", "kommune", "Tid", "saksbehandlingstid"]].dropna(
        subset=["saksbehandlingstid"]
    ).to_dict(orient="records")


def rank_municipalities(
    start_year: str = DEFAULT_START_YEAR,
    end_year: str = DEFAULT_END_YEAR,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Rangerer kommuner etter forklarbar beslutningsmodell.

    Modell:
    - Høy prosentvis befolkningsvekst er positivt.
    - Kort saksbehandlingstid er positivt.
    - Total score = 65% attraktivitet + 35% gjennomføring.
    """
    growth = get_population_growth(start_year, end_year)
    cases = get_case_processing_time(end_year)

    case_by_code = {str(item["kommune_kode"]): item for item in cases}
    merged: list[dict[str, Any]] = []

    for pop in growth:
        raw_code = str(pop["kommune_kode"])
        # Befolkningsdata bruker "K-XXXX"-format; byggesaksdata bruker "XXXX" direkte.
        code = raw_code.lstrip("K-") if raw_code.startswith("K-") else raw_code
        case = case_by_code.get(code)
        if not case:
            continue

        merged.append({
            "kommune_kode": code,
            "kommune": pop["kommune"],
            "befolkning_start": round(_safe_float(pop["befolkning_start"]), 0),
            "befolkning_end": round(_safe_float(pop["befolkning_end"]), 0),
            "befolkningsvekst": round(_safe_float(pop["befolkningsvekst"]), 0),
            "vekst_prosent": round(_safe_float(pop["vekst_prosent"]), 2),
            "saksbehandlingstid": round(_safe_float(case["saksbehandlingstid"]), 2),
        })

    if not merged:
        return []

    min_growth_pct = min(item["vekst_prosent"] for item in merged)
    max_growth_pct = max(item["vekst_prosent"] for item in merged)
    min_case = min(item["saksbehandlingstid"] for item in merged)
    max_case = max(item["saksbehandlingstid"] for item in merged)

    for item in merged:
        attraktivitet_score = _normalize(item["vekst_prosent"], min_growth_pct, max_growth_pct)
        gjennomforing_score = 100 - _normalize(item["saksbehandlingstid"], min_case, max_case)
        total_score = attraktivitet_score * 0.65 + gjennomforing_score * 0.35

        item["attraktivitet_score"] = round(attraktivitet_score, 2)
        item["gjennomforing_score"] = round(gjennomforing_score, 2)
        item["total_score"] = round(total_score, 2)

        if total_score >= 75:
            item["anbefaling"] = "Sterk kandidat"
        elif total_score >= 55:
            item["anbefaling"] = "Bør vurderes"
        else:
            item["anbefaling"] = "Lavere prioritet"

    ranked = sorted(merged, key=lambda item: item["total_score"], reverse=True)
    return ranked[: max(1, int(limit))]


def get_best_building_candidate() -> dict[str, Any]:
    ranking = rank_municipalities(limit=1)
    if not ranking:
        return {"error": "Fant ingen kommuner med komplett datagrunnlag."}
    return ranking[0]


def extract_municipality_names(question: str, available_names: list[str]) -> list[str]:
    q = (question or "").lower()
    found = []
    for name in sorted(available_names, key=len, reverse=True):
        variants = [name.lower()]
        if " - " in name:
            variants.append(name.split(" - ", 1)[0].strip().lower())

        if any(re.search(rf"(?<!\w){re.escape(variant)}(?!\w)", q) for variant in variants):
            found.append(name)
    return found


def compare_municipalities(
    municipalities: list[str],
    start_year: str = DEFAULT_START_YEAR,
    end_year: str = DEFAULT_END_YEAR,
) -> list[dict[str, Any]]:
    ranking = rank_municipalities(start_year=start_year, end_year=end_year, limit=500)
    names = [name.lower().strip() for name in municipalities]
    return [item for item in ranking if item["kommune"].lower().strip() in names]


def summarize_municipality(municipality: str) -> dict[str, Any]:
    ranking = rank_municipalities(limit=500)
    target = municipality.lower().strip()
    for item in ranking:
        if item["kommune"].lower().strip() == target:
            return item
    return {"error": f"Fant ikke kommune: {municipality}"}


def get_llm_context(question: str, top_n: int = 10) -> dict[str, Any]:
    """Liten, ferdig analysert datapakke til LLM.

    Denne funksjonen er bevisst kompakt for å redusere tokenbruk og 429-risiko.
    """
    q = (question or "").lower()
    ranking = rank_municipalities(limit=500)

    if not ranking:
        return {
            "question": question,
            "intent": "unknown",
            "error": "Fant ingen komplett rangering. Sjekk SSB-data og transformering.",
        }

    available_names = [item["kommune"] for item in ranking]

    if "saksbehandlingstid" in q:
        return {
            "question": question,
            "intent": "get_case_processing_time",
            "municipalities": sorted(ranking, key=lambda x: x["saksbehandlingstid"])[: max(1, top_n)],
            "score_model": "Kort saksbehandlingstid er bedre",
        }

    if "sammenlign" in q or "compare" in q:
        requested = extract_municipality_names(question, available_names)
        if not requested:
            requested = ["Oslo", "Bærum", "Lillestrøm"]
        results = compare_municipalities(requested)
        return {
            "question": question,
            "intent": "compare_municipalities",
            "municipalities": results[: max(1, top_n)],
            "score_model": "65% prosentvis befolkningsvekst + 35% kort saksbehandlingstid",
        }
        
        
    requested = extract_municipality_names(question, available_names)
    if len(requested) == 1 or any(word in q for word in ["vurder", "forklar", "oppsummer"]):
        name = requested[0] if requested else ranking[0]["kommune"]
        return {
            "question": question,
            "intent": "summarize_municipality",
            "municipality": summarize_municipality(name),
            "score_model": "65% prosentvis befolkningsvekst + 35% kort saksbehandlingstid",
        }
        
        
    return {
        "question": question,
        "intent": "rank_municipalities",
        "top_candidates": ranking[: max(1, top_n)],
        "score_model": {
            "attraktivitet": "Normalisert prosentvis befolkningsvekst 2021–2025",
            "gjennomforing": "Kort saksbehandlingstid gir høyere score",
            "total_score": "65% attraktivitet + 35% gjennomføring",
        },
    }
