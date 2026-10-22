"""Entry point for ``python -m culture_chat``."""

from __future__ import annotations

import sys

from culture_chat.cli import main

if __name__ == "__main__":
    sys.exit(main())
