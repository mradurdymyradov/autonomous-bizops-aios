"""Small CLI for Zark Lab's streaming creative API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


API_URL = "https://api.zarklab.ai/v1/complete"
ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip("'\""))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Call the Zark image/video API")
    p.add_argument("query", help="Creative request to send to Zark")
    p.add_argument("--tool", choices=("auto", "image", "video"), default="auto")
    p.add_argument("--dry-run", action="store_true", help="Plan/check without generating media")
    p.add_argument("--file-id", action="append", default=[], help="Reference file ID; repeat as needed")
    p.add_argument("--session", default="vaios-zark", help="Conversation-continuity session ID")
    p.add_argument("--model", default="auto")
    p.add_argument("--aspect-ratio")
    p.add_argument("--quality")
    p.add_argument("--duration", type=int)
    p.add_argument("--num-images", type=int)
    p.add_argument("--sound", choices=("on", "off"))
    return p


def main() -> int:
    args = parser().parse_args()
    load_env(ROOT / ".env")
    api_key = os.environ.get("ZARK_API_KEY")
    if not api_key:
        print("ZARK_API_KEY is missing from the environment or project .env", file=sys.stderr)
        return 2

    tool_params = {"model": args.model}
    for key in ("aspect_ratio", "quality", "duration", "num_images", "sound"):
        value = getattr(args, key)
        if value is not None:
            tool_params[key] = value

    payload = {
        "chat_session_id": args.session,
        "query": args.query,
        "file_ids": args.file_id,
        "tool": args.tool,
        "mode": "dry_run" if args.dry_run else "autonomous",
        "tool_params": tool_params,
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        method="POST",
    )

    assistant_chunks: list[str] = []
    generated: list[dict[str, str]] = []
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                try:
                    event = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                event_type = event.get("type")
                if event_type == "ai_chunk":
                    assistant_chunks.append(event.get("content", ""))
                elif event_type == "generation_complete":
                    generated.append(
                        {
                            "media_type": event.get("media_type", ""),
                            "file_id": event.get("file_id", ""),
                            "filename": event.get("filename", ""),
                        }
                    )
                elif event_type == "error":
                    print(json.dumps(event, ensure_ascii=False), file=sys.stderr)
                    return 1
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Zark API HTTP {exc.code}: {body}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Zark API connection failed: {exc.reason}", file=sys.stderr)
        return 1

    result = {
        "mode": payload["mode"],
        "response": "".join(assistant_chunks).strip(),
        "generated_files": generated,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
