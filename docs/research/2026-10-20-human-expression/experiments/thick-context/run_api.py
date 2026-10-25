#!/usr/bin/env python3
"""Generate the thick/thin conditions through the lab relay.

Preregistration: preregistration.md (written before the first call).
Every call is logged: requested model, returned model, usage, latency, retries.
"""
from __future__ import annotations

import json
import os
import sys
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


def call(prompt: str, max_tokens: int = 2600) -> dict:
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(BASE_URL + "/chat/completions", data=body, headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def one(item: dict, cond: str) -> dict:
    out = RAW / cond / f"{item['id']}.txt"
    if out.exists() and out.stat().st_size > 200:
        return {"id": item["id"], "cond": cond, "status": "skip"}
    prompt = item["thick_prompt" if cond == "thick" else "thin_prompt"]
    last = None
    for attempt in range(4):
        t0 = time.time()
        try:
            d = call(prompt)
            text = d["choices"][0]["message"]["content"]
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            rec = {
                "id": item["id"], "cond": cond, "status": "ok",
                "model_requested": MODEL, "model_returned": d.get("model"),
                "usage": d.get("usage"), "latency_s": round(time.time() - t0, 1),
                "attempts": attempt + 1, "chars": len(text),
                "finish_reason": d["choices"][0].get("finish_reason"),
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            with META.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return rec
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:200]!r}"
        except Exception as e:  # noqa: BLE001
            last = repr(e)
        time.sleep(3 * (attempt + 1))
    rec = {"id": item["id"], "cond": cond, "status": "fail", "error": last}
    with META.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def main() -> int:
    items = json.loads(HERE.joinpath("items.json").read_text())
    only = sys.argv[1:] or None
    jobs = [(it, c) for it in items for c in ("thin", "thick") if not only or it["id"] in only]
    print(f"{len(jobs)} 次生成，模型 {MODEL}", flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=int(os.environ.get("CONC", "5"))) as ex:
        for rec in ex.map(lambda a: one(*a), jobs):
            done += 1
            print(f"[{done}/{len(jobs)}] {rec['id']} {rec['cond']} {rec['status']}"
                  + (f" {rec.get('chars')}字 {rec.get('latency_s')}s" if rec["status"] == "ok" else ""),
                  flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
