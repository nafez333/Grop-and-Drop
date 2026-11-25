"""ACK Server — Flask-based HTTP endpoint for phone acknowledgments.

Endpoints:
  POST /ack       — receive an ACK from the phone
  GET  /status    — return the last ACK received
  GET  /health    — health check

Logs all ACKs to data/logs/. CORS enabled so a phone can reach it.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# In-memory store for the last ACK (thread-safe)
_lock = threading.Lock()
_last_ack: Optional[Dict[str, Any]] = None
_ack_history: list = []

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "logs")
LOG_FILE = os.path.join(LOG_DIR, "acks.jsonl")


def _ensure_log_dir() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)


def _log_ack(ack_data: Dict[str, Any]) -> None:
    """Append an ACK record to the JSONL log file."""
    _ensure_log_dir()
    record = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "ack": ack_data,
    }
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.error("Failed to write ACK log: %s", exc)


@app.route("/ack", methods=["POST"])
def receive_ack() -> Any:
    """Receive an ACK from the phone.

    Body:
        {
            "message_id": str,
            "status": "received" | "error",
            "timestamp": str,
            "decoded_message": str
        }

    Returns:
        {"ack": true}
    """
    global _last_ack
    try:
        body = request.get_json(force=True) or {}
    except Exception as exc:  # noqa: BLE001
        logger.error("Invalid JSON in /ack: %s", exc)
        return jsonify({"error": "invalid JSON"}), 400

    message_id = body.get("message_id")
    status = body.get("status")
    timestamp = body.get("timestamp")
    decoded_message = body.get("decoded_message")

    if not message_id or status not in ("received", "error"):
        return jsonify({"error": "message_id and status (received|error) required"}), 400

    ack_record = {
        "message_id": message_id,
        "status": status,
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "decoded_message": decoded_message or "",
    }

    with _lock:
        _last_ack = ack_record
        _ack_history.append(ack_record)
        # Keep history bounded
        if len(_ack_history) > 10000:
            _ack_history[:] = _ack_history[-10000:]

    _log_ack(ack_record)
    logger.info("ACK received: message_id=%s status=%s", message_id, status)

    return jsonify({"ack": True})


@app.route("/status", methods=["GET"])
def get_status() -> Any:
    """Return the last ACK received."""
    with _lock:
        if _last_ack is None:
            return jsonify({"ack": None, "message": "no ACK received yet"}), 200
        return jsonify({"ack": _last_ack})


@app.route("/health", methods=["GET"])
def health() -> Any:
    """Health check endpoint."""
    return jsonify({"status": "ok"})


def run_server(host: str = "0.0.0.0", port: int = 8888, debug: bool = False) -> None:
    """Run the ACK server (blocking)."""
    logger.info("Starting ACK server on %s:%d", host, port)
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run_server()
