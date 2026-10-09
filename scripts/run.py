"""One-command local setup and server. Python 3.12 and Node 20.19+ are required."""

import argparse
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    subprocess.run([str(a) for a in args], cwd=ROOT, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-install", action="store_true", help="Use existing dependencies and frontend build"
    )
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()
    if sys.version_info < (3, 12):
        raise SystemExit("PumpWatch requires Python 3.12 or newer.")
    # Local env files remain local; never print values or embed keys in the frontend.
    envfile = ROOT / ".env"
    if envfile.exists():
        for line in envfile.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                if key.strip() in {
                    "SERPAPI_KEY",
                    "PUMPWATCH_MODE",
                    "PUMPWATCH_STATE_DIR",
                    "PUMPWATCH_MONTHLY_BUDGET",
                    "PUMPWATCH_HOURLY_BUDGET",
                }:
                    os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
    env_dir = ROOT / ".venv"
    python = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        venv.create(env_dir, with_pip=True)
    if not args.skip_install:
        run([python, "-m", "pip", "install", "-r", ROOT / "backend/requirements.lock"])
        manager = shutil.which("pnpm") or shutil.which("npm")
        if not manager:
            raise SystemExit("Install Node 20.19+ with npm or pnpm, then run this command again.")
        if Path(manager).name.startswith("pnpm"):
            prefix = [manager, "--dir", ROOT / "frontend"]
            run([*prefix, "install", "--frozen-lockfile"])
            run([*prefix, "build"])
        else:
            run([manager, "--prefix", ROOT / "frontend", "install"])
            run([manager, "--prefix", ROOT / "frontend", "run", "build"])
    elif not (ROOT / "frontend/dist/index.html").exists():
        raise SystemExit("No frontend build. Run without --skip-install first.")
    os.environ["PYTHONPATH"] = str(ROOT / "backend")
    os.environ.setdefault("PUMPWATCH_MODE", "replay")
    print(
        f"\nPumpWatch → http://127.0.0.1:{args.port}  |  mode: {os.environ['PUMPWATCH_MODE']}\n", flush=True
    )
    try:
        run(
            [
                python,
                "-m",
                "uvicorn",
                "app.main:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                args.port,
            ]
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
