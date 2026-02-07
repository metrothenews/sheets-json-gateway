from __future__ import annotations

from typing import Dict, List, Any

import google.auth
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _svc():
    creds, _ = google.auth.default(scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def read_key_value_tab(*, sheet_id: str, tab_name: str) -> Dict[str, str]:
    """
    Expects headers in row 1: key | value
    Reads all rows from A:B, returns dict.
    """
    service = _svc()
    rng = f"'{tab_name}'!A:B"
    resp = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=rng
    ).execute()
    values = resp.get("values", [])

    out: Dict[str, str] = {}
    for i, row in enumerate(values):
        if i == 0:
            continue
        if len(row) < 2:
            continue
        k = str(row[0]).strip()
        v = str(row[1]).strip()
        if k:
            out[k] = v
    return out


def write_cells(*, sheet_id: str, updates: List[Dict[str, Any]]) -> None:
    service = _svc()
    body = {"valueInputOption": "RAW", "data": updates}
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body=body
    ).execute()


def read_ranges(*, sheet_id: str, ranges: List[str]) -> List[Dict[str, Any]]:
    """
    Read multiple ranges in a single API call.

    Example:
      read_ranges(sheet_id=..., ranges=["Publer Config!A1:B10", "Content Schedule!A2:R2"])

    Returns:
      [{"range": "<range>", "values": [[...], ...]}, ...]  (order matches input)
    """
    service = _svc()
    resp = service.spreadsheets().values().batchGet(
        spreadsheetId=sheet_id,
        ranges=ranges,
        majorDimension="ROWS",
    ).execute()

    out: List[Dict[str, Any]] = []
    for vr in resp.get("valueRanges", []):
        out.append(
            {
                "range": vr.get("range", ""),
                "values": vr.get("values", []),
            }
        )
    return out


def read_publer_config(*, sheet_id: str) -> Dict[str, str]:
    """
    Convenience wrapper: loads the Publer Config tab into a dict.
    """
    return read_key_value_tab(sheet_id=sheet_id, tab_name="Publer Config")
