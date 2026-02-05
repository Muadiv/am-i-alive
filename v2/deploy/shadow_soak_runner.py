#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib import error, request


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_json(url: str, timeout: int = 10) -> tuple[bool, object]:
    try:
        with request.urlopen(url, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
        return True, json.loads(payload)
    except (error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        return False, {"error": str(exc)}


def evaluate_snapshot(v1_base: str, v2_base: str) -> dict[str, object]:
    checks = {
        "v1_health": fetch_json(f"{v1_base}/health"),
        "v1_state": fetch_json(f"{v1_base}/api/state"),
        "v2_health": fetch_json(f"{v2_base}/health"),
        "v2_state": fetch_json(f"{v2_base}/api/public/state"),
        "v2_vote_round": fetch_json(f"{v2_base}/api/public/vote-round"),
        "v2_funding": fetch_json(f"{v2_base}/api/public/funding"),
    }
    failures: list[str] = []

    for key, (ok, payload) in checks.items():
        if not ok:
            failures.append(f"{key}: request failed")
            continue
        if key.endswith("health") and not isinstance(payload, dict):
            failures.append(f"{key}: invalid payload")

    v2_state_ok, v2_state = checks["v2_state"]
    if v2_state_ok and isinstance(v2_state, dict):
        data = v2_state.get("data", {})
        if not isinstance(data, dict) or "is_alive" not in data or "life_number" not in data:
            failures.append("v2_state: missing required fields")

    return {
        "timestamp": utc_now_iso(),
        "ok": len(failures) == 0,
        "failures": failures,
        "checks": {k: payload for k, (_ok, payload) in checks.items()},
    }


def run_shadow_soak(
    v1_base: str,
    v2_base: str,
    iterations: int,
    interval_seconds: int,
    output_file: Path,
) -> dict[str, object]:
    snapshots: list[dict[str, object]] = []
    for idx in range(iterations):
        snapshot = evaluate_snapshot(v1_base=v1_base, v2_base=v2_base)
        snapshots.append(snapshot)
        if idx < iterations - 1:
            time.sleep(interval_seconds)

    pass_count = sum(1 for row in snapshots if bool(row.get("ok")))
    report = {
        "started_at": snapshots[0]["timestamp"] if snapshots else utc_now_iso(),
        "finished_at": utc_now_iso(),
        "iterations": iterations,
        "interval_seconds": interval_seconds,
        "pass_count": pass_count,
        "fail_count": iterations - pass_count,
        "success_rate": (pass_count / iterations) if iterations > 0 else 0.0,
        "snapshots": snapshots,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run shadow soak checks for v1/v2.")
    parser.add_argument("--v1", default="http://127.0.0.1", help="v1 base URL")
    parser.add_argument("--v2", default="http://127.0.0.1:8080", help="v2 base URL")
    parser.add_argument("--iterations", type=int, default=12, help="number of snapshots")
    parser.add_argument("--interval", type=int, default=300, help="seconds between snapshots")
    parser.add_argument(
        "--output",
        default="/var/lib/am-i-alive-v2/soak/latest-shadow-soak.json",
        help="output report path",
    )
    args = parser.parse_args()

    report = run_shadow_soak(
        v1_base=args.v1,
        v2_base=args.v2,
        iterations=args.iterations,
        interval_seconds=args.interval,
        output_file=Path(args.output),
    )

    print(json.dumps({
        "iterations": report["iterations"],
        "pass_count": report["pass_count"],
        "fail_count": report["fail_count"],
        "success_rate": report["success_rate"],
        "output": args.output,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
