#!/usr/bin/env python3
"""Backward-compatible entry point: python smartpca_viz.py

This file is kept for compatibility. The preferred invocation is:
    python -m smartpca_viz
"""

from smartpca_viz.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
