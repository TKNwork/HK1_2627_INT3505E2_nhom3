"""Run all 4 SmartSchedule services together."""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SERVICES = [
    ("core", 8000),
    ("ai", 8001),
    ("scheduling", 8002),
    ("notification", 8003),
]


def main() -> None:
    print("==================================================")
    print("  SmartSchedule - Khoi chay toan bo 4 services   ")
    print("==================================================")

    processes: list[subprocess.Popen] = []

    def stop_all(*_):
        print("\nDang dung toan bo services...")
        for p in processes:
            try:
                p.terminate()
            except Exception:
                pass
        time.sleep(0.5)
        for p in processes:
            try:
                p.kill()
            except Exception:
                pass
        print("Da tat toan bo services thanh cong!")
        sys.exit(0)

    signal.signal(signal.SIGINT, stop_all)
    signal.signal(signal.SIGTERM, stop_all)

    py_executable = sys.executable

    print("\nDang khoi dong cac dich vu:")
    for name, port in SERVICES:
        print(f" -> [{name.upper()}] tai http://127.0.0.1:{port}/docs")
        proc = subprocess.Popen(
            [
                py_executable,
                "-m",
                "uvicorn",
                f"services.{name}.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=ROOT,
        )
        processes.append(proc)

    print("\nBam Ctrl + C de dung tat ca services cung mot luc.\n")

    try:
        while True:
            time.sleep(1)
            for p in processes:
                if p.poll() is not None:
                    pass
    except KeyboardInterrupt:
        stop_all()


if __name__ == "__main__":
    main()

