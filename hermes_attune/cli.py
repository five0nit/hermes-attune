import argparse
import json
import sqlite3
from zoneinfo import ZoneInfoNotFoundError
from pathlib import Path
import sys
from . import command
from .core import Attune
from .paths import default_root


def main():
    parser = argparse.ArgumentParser(description="Attune owner controls; Hermes uses the native plugin tools")
    parser.add_argument("--state", type=Path, help="Explicit state root for an isolated demo or tests")
    parser.add_argument("action", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    import shlex
    try:
        result = command(Attune(args.state or default_root()), shlex.join(args.action))
    except (ValueError, TypeError, OSError, ZoneInfoNotFoundError, sqlite3.Error) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
