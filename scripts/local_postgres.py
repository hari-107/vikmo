"""Manage the project's isolated PostgreSQL server without a Windows service.

Run with .venv/Scripts/python.exe scripts/local_postgres.py start|status|stop.
The database must already be initialized in local_data/postgres.
"""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
CLUSTER = ROOT / "local_data" / "postgres"
BIN = Path(os.environ.get("POSTGRES_BIN", r"C:\Program Files\PostgreSQL\18\bin"))


def status():
    return subprocess.run(
        [str(BIN / "pg_ctl.exe"), "-D", str(CLUSTER), "status"],
        capture_output=True, text=True, check=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "status", "stop"])
    args = parser.parse_args()
    if not (CLUSTER / "PG_VERSION").exists():
        parser.error("The project-local database has not been initialized.")
    result = status()
    if args.action == "status":
        print(result.stdout or result.stderr, end="")
        return result.returncode
    if args.action == "stop":
        if result.returncode != 0:
            print("The project-local PostgreSQL server is already stopped.")
            return 0
        return subprocess.run(
            [str(BIN / "pg_ctl.exe"), "-D", str(CLUSTER), "stop", "-m", "fast", "-w", "-t", "20"],
            check=False,
        ).returncode
    if result.returncode == 0:
        print("Project-local PostgreSQL is already running on 127.0.0.1:5433.")
        return 0
    # pg_ctl's restricted-token launcher is incompatible with the managed
    # Windows sandbox. Launch the existing binary without a visible console.
    with (ROOT / "local_data" / "postgres.log").open("a", encoding="utf-8") as log:
        process = subprocess.Popen(
            [str(BIN / "postgres.exe"), "-D", str(CLUSTER)],
            stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    for _ in range(20):
        time.sleep(0.5)
        if process.poll() is not None:
            print("PostgreSQL exited. See local_data/postgres.log.")
            return 1
        with socket.socket() as connection:
            connection.settimeout(0.5)
            if connection.connect_ex(("127.0.0.1", 5433)) == 0:
                print("Project-local PostgreSQL is running on 127.0.0.1:5433.")
                return 0
    print("PostgreSQL is still starting. Check local_data/postgres.log.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
