"""Entry point for `python -m ai_navigator`."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
