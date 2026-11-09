#!/usr/bin/env python3
"""PlaneByte Lead Engine: B2B prospect discovery and company intelligence."""
import sys

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app.cli.commands import main

if __name__ == "__main__":
    main()
