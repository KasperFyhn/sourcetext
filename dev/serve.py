"""Serve a mock-data scenario for manual UI testing.

    python dev/serve.py <scenario> [--port 8001] [--dev]

Scenarios are the modules in dev/scenarios/, each exposing `make_source_text()`.
With --dev the built UI is not mounted (API only); pair it with `npm run dev` in ui/
for hot-reloading UI work, or just use scripts/dev.sh.
"""

import argparse
import importlib
from pathlib import Path

import sourcetext.server.app as server_app

SCENARIO_DIR = Path(__file__).parent / "scenarios"


def available_scenarios() -> list[str]:
    return sorted(p.stem for p in SCENARIO_DIR.glob("*.py") if not p.stem.startswith("_"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scenario", choices=available_scenarios())
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--dev", action="store_true", help="API only: do not mount the built UI")
    args = parser.parse_args()

    server_app._dev = args.dev
    module = importlib.import_module(f"scenarios.{args.scenario}")
    module.make_source_text().start_server(port=args.port, block=True)


if __name__ == "__main__":
    main()
