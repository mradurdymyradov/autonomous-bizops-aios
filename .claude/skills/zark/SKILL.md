---
name: zark
description: Use Zark Lab's API for image or video generation and editing only when Operator explicitly asks to use Zark or invokes /zark. Do not select it merely because a task involves media.
---

# Zark Lab API

Use Zark only on an explicit current-conversation instruction. Calls can consume credits and create files in The Zark workspace.

Run the local client from the repository root:

```powershell
python automations/zark.py "<request>" --tool image
python automations/zark.py "<request>" --tool video --aspect-ratio 9:16 --duration 6 --sound on
python automations/zark.py "<request>" --dry-run
```

The client reads `ZARK_API_KEY` from the process environment or the gitignored root `.env`. Never print, copy, log, or place the key in a command. Do not store it in a generated artifact.

Run it on The Windows machine. If the agent sandbox denies the outbound socket, rerun the same command with the required network approval; that error does not mean the key is invalid.

## Choose the call

- `--tool image` for image generation or editing.
- `--tool video` for video generation, animation, or editing.
- `--tool auto` only when the requested media path is ambiguous.
- Add `--file-id <id>` for each Zark-hosted reference file intentionally selected by Operator.
- Use `--dry-run` for connectivity checks or when Operator asks for a plan without generation. It still invokes a model and may use a small amount of metered usage.

Pass only controls the user supplied or that are necessary for the requested deliverable. Supported client controls are `--model`, `--aspect-ratio`, `--quality`, `--duration`, `--num-images`, and `--sound`. Keep `--model auto` unless Operator names a model supported by his account.

One invocation is authorization for one bounded generation request, not a batch or retry loop. If the API fails, retry once only for a transient connection error. Never perform additional paid variants without explicit approval.

Report Zark's response and every returned `file_id`. Generated assets live in the Zark workspace; do not claim a local file exists unless it was separately retrieved and verified.

For request fields, event shapes, and tested limits, read [references/zark-api.md](../../../references/zark-api.md).
