from __future__ import annotations

import csv
import json
import threading
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file

import rank_tracker


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

_job_lock = threading.Lock()
_job_state: dict[str, Any] = {
    "running": False,
    "progress": ["Ready to check one keyword."],
    "result": None,
    "error": None,
}


def _set_state(**changes: Any) -> None:
    with _job_lock:
        _job_state.update(changes)


def _snapshot_state() -> dict[str, Any]:
    with _job_lock:
        return {
            "running": _job_state["running"],
            "progress": list(_job_state["progress"]),
            "result": _job_state["result"],
            "error": _job_state["error"],
        }


def _add_progress(message: str) -> None:
    with _job_lock:
        _job_state["progress"].append(message)
        _job_state["progress"] = _job_state["progress"][-30:]


def _run_job(keyword: str, target_url: str) -> None:
    driver = None
    try:
        _add_progress("Starting Chrome")
        driver = rank_tracker.create_driver()
        result = rank_tracker.check_keyword(
            driver,
            keyword,
            target_url,
            test_mode=True,
            pause_after_found=False,
            progress_callback=_add_progress,
        )
        rank_tracker.append_result(result)
        _set_state(result=result, progress=_job_state["progress"] + ["Check complete"])
    except Exception:
        _set_state(error="The rank check could not be completed. Check that Chrome and the local profile are available.")
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        _set_state(running=False)


def _start_job(keyword: str, target_url: str) -> None:
    worker = threading.Thread(target=_run_job, args=(keyword, target_url), daemon=True)
    worker.start()


def _recent_results(limit: int = 10) -> list[dict[str, str]]:
    if not rank_tracker.RESULTS_FILE.exists():
        return []
    try:
        with rank_tracker.RESULTS_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        return rows[-limit:][::-1]
    except (OSError, csv.Error):
        return []


def _check_vpn_location() -> dict[str, Any]:
    try:
        req = urllib.request.Request(
            "http://ip-api.com/json/?fields=status,country,countryCode,city,query",
            headers={"User-Agent": "TekglideRankChecker/1.0"},
        )
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "success":
                is_usa = data.get("countryCode") == "US"
                return {
                    "is_usa": is_usa,
                    "country": data.get("country", "Unknown"),
                    "city": data.get("city", "Unknown"),
                    "ip": data.get("query", ""),
                }
    except Exception:
        pass
    return {"is_usa": False, "country": "Unknown", "city": "Unknown", "ip": ""}


@app.get("/")
def index():
    return render_template("index.html", targets=rank_tracker.load_targets())


@app.get("/api/vpn-status")
def vpn_status():
    return jsonify(_check_vpn_location())


@app.post("/api/check")
def start_check():
    payload = request.get_json(silent=True) or {}
    keyword = str(payload.get("keyword", "")).strip()
    checklist = payload.get("checklist", {}) or {}
    required_checks = ("vpn", "location", "captcha")
    if not all(checklist.get(name) is True for name in required_checks):
        return jsonify({"error": "Confirm all three checklist items before starting a check."}), 400
    
    vpn_info = _check_vpn_location()
    if not vpn_info.get("is_usa"):
        loc = f"{vpn_info.get('city', '')}, {vpn_info.get('country', '')}".strip(", ")
        return jsonify({
            "error": f"USA VPN Required! Detected location: {loc or 'Outside USA'} (IP: {vpn_info.get('ip', 'Unknown')}). Please connect ExpressVPN to USA."
        }), 400

    if not keyword:
        return jsonify({"error": "Select a keyword before starting a check."}), 400
    try:
        target = rank_tracker.load_test_target(keyword)
    except SystemExit:
        return jsonify({"error": "That keyword is not available in targets.csv."}), 400
    with _job_lock:
        if _job_state["running"]:
            return jsonify({"error": "A rank check is already running. Wait for it to finish."}), 409
        _job_state.update(
            running=True,
            progress=[f"Starting check for {target['keyword']}"],
            result=None,
            error=None,
        )
    _start_job(target["keyword"], target["target_url"])
    return jsonify({"started": True, "keyword": target["keyword"], "target_url": target["target_url"]}), 202


@app.get("/api/status")
def status():
    return jsonify(_snapshot_state())


@app.get("/api/results")
def results():
    return jsonify({"results": _recent_results()})


@app.get("/api/download")
def download():
    if rank_tracker.RESULTS_FILE.exists():
        return send_file(
            str(rank_tracker.RESULTS_FILE),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"tekglide_rank_results_{datetime.now().strftime('%Y%m%d')}.csv",
        )
    return jsonify({"error": "No rank results yet."}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
