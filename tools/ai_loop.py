from __future__ import annotations
import subprocess
import sys

def run(cmd: list[str]) -> None:
    print("RUN:", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, check=False)
    if p.returncode != 0:
        raise SystemExit(p.returncode)

def main():
    py = sys.executable
    run([py, "-m", "ruff", "format", "--check", "."])
    run([py, "-m", "ruff", "check", "."])
    run([py, "-m", "mypy", "common_core", "apps"])
    run([py, "-m", "pytest", "-q"])
    print("OK: all checks passed")

if __name__ == "__main__":
    main()
