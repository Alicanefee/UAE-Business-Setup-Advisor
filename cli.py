"""Command-line demo.

Examples:
    python cli.py "I want to set up a software company in Dubai; my clients are overseas"
    python cli.py "Renew my Dubai free zone software license" --renew --documents "Passport copy; Application form"
    python cli.py "Trading company in Dubai selling to local customers" --json
"""
from __future__ import annotations

import argparse
import json
import sys

from services.orchestrator import Orchestrator
from storage.sqlite import Repository


def main() -> int:
    parser = argparse.ArgumentParser(description="UAE Business Setup Advisor — CLI demo")
    parser.add_argument("message", help="Describe the business in plain English")
    parser.add_argument("--renew", action="store_true", help="Renewal mode")
    parser.add_argument("--documents", default="",
                        help="Renewal only: documents you hold, separated by ';'")
    parser.add_argument("--json", action="store_true", help="Print the raw terminal event")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    orchestrator = Orchestrator(Repository())
    documents = [d for d in args.documents.split(";") if d.strip()]
    events = list(orchestrator.stream("cli", args.message,
                                      "renew" if args.renew else "new", documents))
    final = events[-1]

    if args.json:
        print(json.dumps(final, indent=2, ensure_ascii=False))
        return 0

    states = " → ".join(e["state"] for e in events if e["type"] == "state")
    print(f"[flow] {states}\n")

    if final["type"] == "question":
        print(f"? {final['text']}\n  (source: {final['source']})")
    elif final["type"] == "abstain":
        print(f"! {final['text']}\n  (reason: {final['reason']})")
    else:
        answer = final["answer"]
        print(answer["title"])
        print("=" * len(answer["title"]))
        for row in answer["summary"]:
            print(f"{row['label']:<18} {row['value']}  [{row['source']}]")
        for section in answer["sections"]:
            print(f"\n{section['heading']}")
            for item in section["items"]:
                print(f"  - {item['text']}  [{item['source']}]")
        print(f"\n{answer['disclaimer']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
