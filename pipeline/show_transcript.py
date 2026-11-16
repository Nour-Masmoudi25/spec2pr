"""Print a compact, readable view of one role transcript from pipeline.run_team.

    python -m pipeline.show_transcript runs/week2/team/T05/02-implementer-T05-1.jsonl [--width 300]
"""
import argparse
import json
import sys
from pathlib import Path


def clip(text, width):
    text = " ".join(str(text).split())
    return text if len(text) <= width else text[:width] + " ..."


def blocks(message):
    content = message.get("content", "")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return [b for b in content if isinstance(b, dict)]


def show(path, width):
    step = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            print("[init] model=%s" % event.get("model"))
        elif kind == "assistant":
            for b in blocks(event.get("message", {})):
                if b.get("type") == "text":
                    print("[assistant] " + clip(b.get("text", ""), width))
                elif b.get("type") == "tool_use":
                    step += 1
                    print("[tool %d] %s %s" % (step, b.get("name"),
                          clip(json.dumps(b.get("input", {}), ensure_ascii=False), width)))
        elif kind == "user":
            for b in blocks(event.get("message", {})):
                if b.get("type") == "tool_result":
                    out = b.get("content", "")
                    if isinstance(out, list):
                        out = " ".join(x.get("text", "") for x in out if isinstance(x, dict))
                    print("   -> " + ("ERROR " if b.get("is_error") else "") + clip(out, width))
        elif kind == "result":
            print("[result] turns=%s cost=%s" % (event.get("num_turns"), event.get("total_cost_usd")))
        elif kind in ("system", "attachment"):
            text = json.dumps(event, ensure_ascii=False)
            if "block" in text.lower() or "denied" in text.lower():
                print("[hook/permission] " + clip(text, width))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--width", type=int, default=300)
    args = parser.parse_args(argv)
    show(args.transcript, args.width)
    return 0


if __name__ == "__main__":
    sys.exit(main())