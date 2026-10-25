#!/usr/bin/env python3
"""Generate the 2x2 form-layer cells (120 calls) through the lab relay.

Same transport as the thick-context run: logged model, usage, retries.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE_URL = os.environ.get("RELAY_BASE", "https://api.donglilab.com/v1")
MODEL = os.environ.get("RELAY_MODEL", "gpt-6.1-sol")
KEY = os.environ.get("OPENAI_DONGLIAPI_API_KEY", "")
HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
META = HERE / "metadata.jsonl"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def call(prompt: str) -> dict:
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 2600}).encode()
    req = urllib.request.Request(BASE_URL + "/chat/completions", data=body, headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
        "User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def one(row: dict) -> dict:
    out = RAW / row["cell"] / f"{row['item']}.txt"
    if out.exists() and out.stat().st_size > 200:
        return {"id": row["id"], "cell": row["cell"], "status": "skip"}
    last = None
    for attempt in range(4):
        t0 = time.time()
        try:
            d = call(row["prompt"])
            text = d["choices"][0]["message"]["content"]
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            rec = {"id": row["id"], "cell": row["cell"], "status": "ok",
                   "model_requested": MODEL, "model_returned": d.get("model"),
                   "usage": d.get("usage"), "latency_s": round(time.time() - t0, 1),
                   "attempts": attempt + 1, "chars": len(text),
                   "finish_reason": d["choices"][0].get("finish_reason"),
                   "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
            with META.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return rec
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:160]!r}"
        except Exception as e:  # noqa: BLE001
            last = repr(e)
        time.sleep(3 * (attempt + 1))
    rec = {"id": row["id"], "cell": row["cell"], "status": "fail", "error": last}
    with META.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def main() -> int:
    rows = json.loads(HERE.joinpath("items.json").read_text())
    print(f"{len(rows)} 次生成，模型 {MODEL}", flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=int(os.environ.get("CONC", "6"))) as ex:
        for rec in ex.map(one, rows):
            done += 1
            print(f"[{done}/{len(rows)}] {rec['id']} {rec['status']}"
                  + (f" {rec.get('chars')}字" if rec["status"] == "ok" else ""), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
