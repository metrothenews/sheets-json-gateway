# sheets-json-gateway

**Shared production tracking for people and automation: a small, secured JSON API over the spreadsheets a team already runs its work in.**

Several of my automation projects use Google Sheets as their control plane, because producers and content teams already live in spreadsheets. Instead of each service carrying its own Google credentials and Sheets client, they all call this gateway over HTTP. It's deployed on Cloud Run, so it's the one place that holds Sheets access, enforces an allowlist, and redacts sensitive values.

Used by [sf-production-app](https://github.com/metrothenews/sf-production-app) (render job queue) and [scheduler-orchestrator](https://github.com/metrothenews/scheduler-orchestrator) (social post scheduling).

**Highlights**

- **One narrow surface.** Endpoints for batch read, key/value read and batch write. Callers never touch the Sheets API or service-account keys.
- **Defense in depth.** An optional shared API key (`GATEWAY_API_KEY`, compared in constant time), a per-sheet allowlist (`SHEETS_ALLOWLIST`), and redaction of sensitive config values on read. Use Cloud Run IAM in front of it as well.
- **Keyless auth to Google.** Uses Application Default Credentials (the Cloud Run service identity), so no JSON key file is deployed.

**Stack:** Python 3.12 · FastAPI · google-api-python-client · uv · Google Cloud Run

## Applications at scale

- **Spreadsheets as shared state for people and AI agents.** Most business processes already live in a spreadsheet. A narrow JSON API over it is exactly what LLM function calling needs: `read`, `read_kv` and `write` map directly onto tool definitions, so an agent can work in the same sheet as the team, with every change visible and reversible by a person.
- **Least privilege for agents.** The agent never holds Google credentials. The gateway decides which sheets exist for it (allowlist), what it may see (redaction) and whether it may call at all (API key or IAM). That's the guardrail pattern for giving models access to real business data.
- **A zero-migration backend.** Teams can automate a workflow without moving off the tool they already use, which is how internal automation actually gets adopted.

**What it demonstrates:** API and security design, secrets-free cloud auth, service decomposition, small well-tested surface area.

## Security

| Setting | Effect |
|---|---|
| `GATEWAY_API_KEY` | If set, every `/v1/*` request must send a matching `X-API-Key` header. Otherwise it gets `401`. `/healthz` stays open. |
| `SHEETS_ALLOWLIST` | Comma-separated sheet IDs the gateway will touch. Others get `403`. |
| Cloud Run IAM | Recommended: deploy without `--allow-unauthenticated` and call with an identity token. |

Set at least one of `GATEWAY_API_KEY` or Cloud Run IAM on any deployment. Without either, anyone with the URL can read and write the allowlisted sheets.

## Tests

```bash
uv sync && PYTHONPATH=src uv run --with pytest pytest -q tests
```

## Endpoints

### GET /healthz
Response:
{"ok": true}

### POST /v1/read
Reads one or more A1 ranges.

Request:
{
  "sheet_id": "<GOOGLE_SHEET_ID>",
  "ranges": ["'Tab Name'!A1:B5", "OtherTab!C2:C10"]
}

Response:
{
  "ok": true,
  "sheet_id": "<GOOGLE_SHEET_ID>",
  "valueRanges": [
    { "range": "...", "values": [["..."], ["..."]] }
  ]
}

### POST /v1/read_kv
Reads a two-column key/value tab into a JSON object.

Request:
{
  "sheet_id": "<GOOGLE_SHEET_ID>",
  "tab_name": "Publer Config"
}

Response:
{
  "ok": true,
  "sheet_id": "<GOOGLE_SHEET_ID>",
  "data": { "key": "value" }
}

NOTE: sensitive config keys are redacted in responses.

### POST /v1/write
Batch-writes values to one or more ranges.

Request:
{
  "sheet_id": "<GOOGLE_SHEET_ID>",
  "updates": [
    {
      "range": "'Publer Config'!B31",
      "values": [["2026-02-08T04:11:35Z"]]
    }
  ]
}

Response:
{
  "ok": true,
  "sheet_id": "<GOOGLE_SHEET_ID>",
  "updatedRanges": ["'Publer Config'!B31"]
}

## Environment variables

- SHEETS_ALLOWLIST: comma-separated Sheet IDs allowed (recommended)
- GOOGLE_APPLICATION_CREDENTIALS: local/dev only, if using a JSON file

## Local run

uv sync
GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/application_default_credentials.json" \
SHEETS_ALLOWLIST="<SHEET_ID>" \
uv run uvicorn sheets_json_gateway.app:app --host 0.0.0.0 --port 8080

## Deploy (Cloud Run)

TODO: add Dockerfile or buildpacks deploy instructions.
