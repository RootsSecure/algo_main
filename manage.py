from __future__ import annotations

import argparse
import subprocess
import sys


def run_command(command: list[str]) -> int:
    return subprocess.call(command)


def main() -> int:
    parser = argparse.ArgumentParser(description="Project task runner for NRI Plot Sentinel.")
    parser.add_argument("command", choices=["run", "test", "migrate"], help="Task to execute")
    args = parser.parse_args()

    if args.command == "run":
        return run_command([sys.executable, "-m", "uvicorn", "app.main:app", "--reload"])
    if args.command == "test":
        return run_command([sys.executable, "-B", "-m", "pytest", "tests", "-p", "no:cacheprovider"])
    if args.command == "migrate":
        return run_command([sys.executable, "-m", "alembic", "upgrade", "head"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
