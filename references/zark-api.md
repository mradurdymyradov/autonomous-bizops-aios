# Zark API

Official docs: https://docs.zarklab.ai/api-reference/overview

## Connection

- Base URL: `https://api.zarklab.ai`
- Creative endpoint: `POST /v1/complete`
- Auth: `X-API-Key: <key>`
- Local credential: root `.env`, variable `ZARK_API_KEY`
- Local client: `automations/zark.py`
- Response: Server-Sent Events (`text/event-stream`)

The key was tested successfully on 2026-08-21 with `mode: dry_run`: HTTP 200, no generated file IDs, and no modifications. The run still invoked the configured model, so do not assume dry-run is unmetered.

## Request shape

`POST /v1/complete` uses snake_case fields:

```json
{
  "chat_session_id": "vaios-zark",
  "query": "Create a vertical product video",
  "file_ids": [],
  "tool": "video",
  "mode": "autonomous",
  "tool_params": {
    "model": "auto",
    "aspect_ratio": "9:16",
    "duration": 6,
    "sound": "on"
  }
}
```

Documented tools: `auto`, `image`, `video`. Documented modes: `autonomous`, `dry_run`. Common controls include `model`, `aspect_ratio`, `quality`, `duration`, `num_images`, and `sound`.

## Results

Capture these SSE events:

- `ai_chunk`: incremental assistant text.
- `generation_complete`: generated `media_type`, `file_id`, and `filename`.
- `agent_run_complete`: terminal status and complete list of generated file IDs.
- `ai_complete`: final response.

Generated output can be referenced in a later request through `file_ids`. The docs describe `GET /v1/media/files/{file_id}` for retrieval, but this local client intentionally handles generation only until a download workflow is requested and verified.

## Boundaries

- Calls can consume credits. One explicit request permits one bounded call, not unattended retries or variants.
- Never expose the key in a command, output, log, artifact, or committed file.
- Use only Zark file IDs that Operator selected for the request.
- Do not invent account model IDs; default to `auto`.
