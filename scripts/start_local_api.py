"""Run the CyberAgent local FastAPI server as a standalone Windows helper."""

from __future__ import annotations

import signal
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_running = True


def _stop(*_args: object) -> None:
    global _running
    _running = False


def main() -> int:
    from app.api.server import start_server

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    print("starting CyberAgent local API on http://127.0.0.1:8765", flush=True)
    start_server(port=8765)
    print("CyberAgent local API started", flush=True)

    while _running:
        time.sleep(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
