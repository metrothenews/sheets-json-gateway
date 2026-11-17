from __future__ import annotations

import hmac
import os
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from sheets_json_gateway.sheets import read_ranges, read_key_value_tab, write_cells

app = FastAPI(title="Sheets JSON Interface", version="1.0")


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Require a shared key on /v1 routes when GATEWAY_API_KEY is set.

    Opt-in so existing deployments keep working; set GATEWAY_API_KEY (ideally from
    Secret Manager) on any deployment that is reachable without Cloud Run IAM.
    """
    expected = os.environ.get("GATEWAY_API_KEY", "").strip()
    if not expected:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="missing or invalid X-API-Key")


def _allowlisted(sheet_id: str) -> bool:
    allow = os.environ.get("SHEETS_ALLOWLIST", "").strip()
    if not allow:
        return True
    allowed = {s.strip() for s in allow.split(",") if s.strip()}
    return sheet_id in allowed

SENSITIVE_KEY = "Tom Scott\x27s Headache"

def _mask(v: Any) -> Any:
    s = str(v)
    if len(s) <= 8:
        return "********"
    return s[:4] + "..." + s[-2:]

def _redact_kv(data: Dict[str, Any]) -> Dict[str, Any]:
    if SENSITIVE_KEY in data:
        data = dict(data)
        data[SENSITIVE_KEY] = _mask(data[SENSITIVE_KEY])
    return data

def _redact_value_ranges(vrs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for vr in vrs:
        vr2 = dict(vr)
        vals = vr.get("values")
        if isinstance(vals, list) and vals and isinstance(vals[0], list):
            header = [str(x).strip().lower() for x in vals[0]]
            if len(header) >= 2 and header[0] == "key" and header[1] == "value":
                new_vals = [vals[0]]
                for row in vals[1:]:
                    if isinstance(row, list) and len(row) >= 2 and str(row[0]) == SENSITIVE_KEY:
                        row2 = list(row)
                        row2[1] = _mask(row2[1])
                        new_vals.append(row2)
                    else:
                        new_vals.append(row)
                vr2["values"] = new_vals
        out.append(vr2)
    return out



class ReadRequest(BaseModel):
    sheet_id: str
    ranges: List[str] = Field(min_length=1)


class ReadKVRequest(BaseModel):
    sheet_id: str
    tab_name: str


class WriteUpdate(BaseModel):
    range: str
    values: List[List[Any]]


class WriteRequest(BaseModel):
    sheet_id: str
    updates: List[WriteUpdate] = Field(min_length=1)


@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    return {"ok": True}


@app.post("/v1/read", dependencies=[Depends(require_api_key)])
def v1_read(req: ReadRequest) -> Dict[str, Any]:
    if not _allowlisted(req.sheet_id):
        raise HTTPException(status_code=403, detail="sheet_id not allowlisted")
    try:
        out = read_ranges(sheet_id=req.sheet_id, ranges=req.ranges)
        out = _redact_value_ranges(out)
        return {"ok": True, "sheet_id": req.sheet_id, "valueRanges": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/read_kv", dependencies=[Depends(require_api_key)])
def v1_read_kv(req: ReadKVRequest) -> Dict[str, Any]:
    if not _allowlisted(req.sheet_id):
        raise HTTPException(status_code=403, detail="sheet_id not allowlisted")
    try:
        data = read_key_value_tab(sheet_id=req.sheet_id, tab_name=req.tab_name)
        data = _redact_kv(data)
        return {"ok": True, "sheet_id": req.sheet_id, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/write", dependencies=[Depends(require_api_key)])
def v1_write(req: WriteRequest) -> Dict[str, Any]:
    if not _allowlisted(req.sheet_id):
        raise HTTPException(status_code=403, detail="sheet_id not allowlisted")
    try:
        updates = [{"range": u.range, "values": u.values} for u in req.updates]
        resp = write_cells(sheet_id=req.sheet_id, updates=updates)
        updated = []
        for r in resp.get("responses", []):
            rng = r.get("updatedRange")
            if rng:
                updated.append(rng)
        return {"ok": True, "sheet_id": req.sheet_id, "updatedRanges": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
