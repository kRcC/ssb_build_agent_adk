from __future__ import annotations

from typing import Any

from src.ssb_client import get_ssb_befolkningsdata, get_ssb_behandlingsdata
from src.analysis import (
    get_population_growth,
    get_case_processing_time,
    rank_municipalities,
    get_best_building_candidate,
    compare_municipalities,
    summarize_municipality,
    get_llm_context,
)


def get_population_data() -> dict[str, Any]:
    """Returnerer rå befolkningsdata fra SSB-tabell 07459."""
    return get_ssb_befolkningsdata() or {}


def get_building_case_data() -> dict[str, Any]:
    """Returnerer rå byggesaksdata fra SSB-tabell 13021."""
    return get_ssb_behandlingsdata() or {}


def get_data_summary() -> dict[str, Any]:
    """Returnerer kort metadata om SSB-datasettene."""
    population = get_population_data()
    building = get_building_case_data()

    return {
        "population": {
            "table_id": "07459",
            "description": "Befolkning etter region og år",
            "updated": population.get("updated", "ukjent"),
            "dimensions": population.get("id", []),
            "size": population.get("size", []),
            "value_count": len(population.get("value", [])),
            "error": population.get("error"),
        },
        "building_cases": {
            "table_id": "13021",
            "description": "Byggesøknader og saksbehandlingstid",
            "updated": building.get("updated", "ukjent"),
            "dimensions": building.get("id", []),
            "size": building.get("size", []),
            "value_count": len(building.get("value", [])),
            "error": building.get("error"),
        },
    }


__all__ = [
    "get_population_data",
    "get_building_case_data",
    "get_data_summary",
    "get_population_growth",
    "get_case_processing_time",
    "rank_municipalities",
    "get_best_building_candidate",
    "compare_municipalities",
    "summarize_municipality",
    "get_llm_context",
]
