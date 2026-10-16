"""Submit the ScamBench-MY triage sweep through Token Factory's Batch API
(higher limits, lower cost than a tight loop) and pull the results back.

  python eval/run_eval.py --batch-prepare
  python scripts/batch_submit.py submit         # prints batch id
  python scripts/batch_submit.py status <id>
  python scripts/batch_submit.py fetch <id>     # writes eval/results/batch_triage_output.jsonl
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from openai import OpenAI  # noqa: E402

from jaga import config  # noqa: E402

OUT = config.ROOT / "eval" / "results"
client = OpenAI(api_key=config.NEBIUS_API_KEY, base_url=config.NEBIUS_BASE_URL)


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "submit"
    if cmd == "submit":
        f = client.files.create(file=open(OUT / "batch_triage_input.jsonl", "rb"), purpose="batch")
        b = client.batches.create(input_file_id=f.id, endpoint="/v1/chat/completions", completion_window="24h")
        print("batch id:", b.id, "status:", b.status)
    elif cmd == "status":
        b = client.batches.retrieve(sys.argv[2])
        print(b.status, getattr(b, "request_counts", ""))
    elif cmd == "fetch":
        b = client.batches.retrieve(sys.argv[2])
        if not b.output_file_id:
            raise SystemExit(f"not finished: {b.status}")
        content = client.files.content(b.output_file_id).read()
        (OUT / "batch_triage_output.jsonl").write_bytes(content)
        print("wrote", OUT / "batch_triage_output.jsonl")


if __name__ == "__main__":
    main()
