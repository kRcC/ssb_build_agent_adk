from __future__ import annotations

import itertools
from typing import Any

import pandas as pd


def _ordered_codes(category: dict[str, Any]) -> list[str]:
    """Returnerer koder i JSON-stat2-rekkefølge."""
    index = category.get("index", {})

    if isinstance(index, dict):
        return [code for code, _ in sorted(index.items(), key=lambda item: item[1])]

    if isinstance(index, list):
        return [str(code) for code in index]

    return []


def jsonstat_to_dataframe(data: dict[str, Any]) -> pd.DataFrame:
    """Transformerer JSON-stat2 fra SSB til Pandas DataFrame.

    SSB returnerer dimensjoner + flat verdiliste. Denne funksjonen lager én rad per
    dimensjonskombinasjon og kobler riktig verdi til riktig rad.
    """
    if not data or data.get("error"):
        return pd.DataFrame()

    dimensions = data.get("id", [])
    values = data.get("value", [])
    dimension_container = data.get("dimension", {})

    if not dimensions or not isinstance(values, list):
        return pd.DataFrame()

    dimension_values: list[list[dict[str, Any]]] = []

    for dimension_name in dimensions:
        dimension = dimension_container.get(dimension_name, {})
        category = dimension.get("category", {})
        labels = category.get("label", {})
        ordered_codes = _ordered_codes(category)

        rows_for_dimension = []
        for code in ordered_codes:
            rows_for_dimension.append({
                f"{dimension_name}_kode": code,
                dimension_name: labels.get(code, code),
            })

        if not rows_for_dimension:
            return pd.DataFrame()

        dimension_values.append(rows_for_dimension)

    combinations = itertools.product(*dimension_values)
    rows = []

    for i, combination in enumerate(combinations):
        row: dict[str, Any] = {}
        for dimension_data in combination:
            row.update(dimension_data)
        row["verdi"] = values[i] if i < len(values) else None
        rows.append(row)

    return pd.DataFrame(rows)
