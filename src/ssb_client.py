from __future__ import annotations

from typing import Any

import requests

API_URL = "https://data.ssb.no/api/pxwebapi/v2/tables/{table_id}/data"

SSB_BEHANDLINGSDATA = "13021"
SSB_BEFOLKNINGSDATA = "07459"
DEFAULT_TIMEOUT_SECONDS = 30


def _fetch_ssb(table_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Henter JSON-stat2-data fra SSB Statistikkbanken.

    Returnerer alltid dict. Ved feil returneres {"error": "..."} slik at appen ikke krasjer.
    """
    try:
        response = requests.get(
            API_URL.format(table_id=table_id),
            params=params,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP-feil fra SSB: {e}", "table_id": table_id}
    except requests.exceptions.Timeout:
        return {"error": "Tidsavbrudd: SSB svarte ikke raskt nok.", "table_id": table_id}
    except requests.exceptions.RequestException as e:
        return {"error": f"Feil ved API-kall: {e}", "table_id": table_id}
    except ValueError as e:
        return {"error": f"Kunne ikke lese JSON fra SSB: {e}", "table_id": table_id}


def get_ssb_behandlingsdata() -> dict[str, Any]:
    """Henter byggesaksdata fra SSB-tabell 13021."""
    params = {
        "lang": "no",
        "outputFormat": "json-stat2",
        "valuecodes[Tid]": "2021,2022,2023,2024,2025",
        "valuecodes[KOKckategori0000]": "aalle",
        "valuecodes[KOKkommuneregion0000]": "*",
        "codelist[KOKkommuneregion0000]": "agg_KOGkommuneregion000005402",
        "valuecodes[KOKctype0000]": "abygsokialt",
        "valuecodes[ContentsCode]": (
            "KOSmottattesokna0000,"
            "KOSbehandletsokn0000,"
            "KOSgjennomsnitts0000"
        ),
        "heading": "KOKckategori0000,KOKctype0000,Tid,ContentsCode",
        "stub": "KOKkommuneregion0000",
    }
    return _fetch_ssb(SSB_BEHANDLINGSDATA, params)


def get_ssb_befolkningsdata() -> dict[str, Any]:
    """Henter befolkningsdata fra SSB-tabell 07459."""
    params = {
        "lang": "no",
        "outputFormat": "json-stat2",
        "valuecodes[ContentsCode]": "*",
        "valuecodes[Tid]": "2021,2022,2023,2024,2025",
        "valuecodes[Region]": "*",
        "codelist[Region]": "agg_KommSummer",
        "heading": "ContentsCode,Tid",
        "stub": "Region",
    }
    return _fetch_ssb(SSB_BEFOLKNINGSDATA, params)

