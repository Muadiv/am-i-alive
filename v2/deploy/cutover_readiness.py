#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib import error, request


def fetch_json(url: str, timeout: int = 10) -> tuple[bool, object]:
    try:
        with request.urlopen(url, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
        return True, json.loads(payload)
    except (error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        return False, {"error": str(exc)}


def load_soak_report(path: Path) -> tuple[bool, dict[str, object]]:
    if not path.exists():
        return False, {"error": f"report not found: {path}"}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, {"error": f"invalid report json: {exc}"}
    if not isinstance(parsed, dict):
        return False, {"error": "invalid report payload"}
    return True, parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate v2 cutover readiness gates.")
    parser.add_argument("--v1", default="http://127.0.0.1", help="v1 base URL")
    parser.add_argument("--v2", default="http://127.0.0.1:8080", help="v2 base URL")
    parser.add_argument(
        "--soak-report",
        default="/var/lib/am-i-alive-v2/soak/latest-shadow-soak.json",
        help="path to soak report json",
    )
    parser.add_argument("--min-iterations", type=int, default=3)
    parser.add_argument("--min-success-rate", type=float, default=0.99)
    args = parser.parse_args()

    checks: dict[str, dict[str, object]] = {}
    failures: list[str] = []

    for key, url in {
        "v1_health": f"{args.v1}/health",
        "v2_health": f"{args.v2}/health",
        "v2_state": f"{args.v2}/api/public/state",
        "v2_vote_round": f"{args.v2}/api/public/vote-round",
    }.items():
        ok, payload = fetch_json(url)
        checks[key] = {"ok": ok, "payload": payload}
        if not ok:
            failures.append(f"{key} check failed")

    soak_ok, soak_payload = load_soak_report(Path(args.soak_report))
    checks["shadow_soak"] = {"ok": soak_ok, "payload": soak_payload}
    if not soak_ok:
        failures.append("shadow soak report missing or invalid")
    else:
        iterations = int(soak_payload.get("iterations", 0))
        success_rate = float(soak_payload.get("success_rate", 0.0))
        if iterations < args.min_iterations:
            failures.append(f"shadow soak iterations too low: {iterations}")
        if success_rate < args.min_success_rate:
            failures.append(f"shadow soak success rate too low: {success_rate}")

    result = {
        "ready": len(failures) == 0,
        "failures": failures,
        "checks": checks,
    }
    print(json.dumps(result, indent=2))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
