# Sheets JSON Interface (Cloud Run)

A minimal HTTP service that reads/writes Google Sheets via JSON requests.
Intended to be a stable “database adapter” other systems can call via webhook.

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

NOTE: sensitive keys (e.g. Tom Scott's Headache) are redacted by default.

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
uv run uvicorn publer_worker.app:app --host 0.0.0.0 --port 8080

## Deploy (Cloud Run)

TODO: add Dockerfile or buildpacks deploy instructions.
