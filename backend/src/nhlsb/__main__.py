"""`python -m nhlsb` -> launch the server.

PyInstaller-safe: uses absolute import (relative imports break when frozen).
"""
from __future__ import annotations
import argparse
import sys
import uvicorn

from nhlsb.main import app


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--reload", action="store_true",
                    help="Dev autoreload (ignored when frozen).")
    args = ap.parse_args()

    if args.reload and not getattr(sys, "frozen", False):
        uvicorn.run("nhlsb.main:app", host=args.host, port=args.port, reload=True)
    else:
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
