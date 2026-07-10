"""APL Sidecar CLI — local, offline, no API keys.

Usage:
    python cli/apl.py preview    <example_dir>
    python cli/apl.py mask       <example_dir>
    python cli/apl.py run-mock   <example_dir>
    python cli/apl.py rehydrate  <example_dir>
    python cli/apl.py inspect    <receipt.json>
    python cli/apl.py verify     <receipt.json> [more...] [--pubkey key.pem]
    python cli/apl.py playground [--port 8791]
"""
from __future__ import annotations

import sys
from pathlib import Path

_CLI = Path(__file__).resolve().parent
sys.path.insert(0, str(_CLI.parent))
sys.path.insert(0, str(_CLI))

from commands import inspect as cmd_inspect  # noqa: E402
from commands import mask as cmd_mask  # noqa: E402
from commands import preview as cmd_preview  # noqa: E402
from commands import rehydrate as cmd_rehydrate  # noqa: E402
from commands import run_mock as cmd_run_mock  # noqa: E402
from commands import verify as cmd_verify  # noqa: E402


def _playground(argv: list[str]) -> int:
    """Serve the local playground on loopback. Zero external network."""
    import http.server
    import functools
    port = 8791
    if "--port" in argv:
        port = int(argv[argv.index("--port") + 1])
    root = _CLI.parent

    class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
        """no-store: a stale cached app.js against fresh HTML silently breaks
        the page (learned the hard way). A local demo never needs caching."""

        def end_headers(self):
            self.send_header("Cache-Control", "no-store, must-revalidate")
            super().end_headers()

    handler = functools.partial(NoCacheHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}/app/local_playground/"
    print(f"APL Sidecar playground: {url}")
    print("Loopback only. No network calls. Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "preview" and len(rest) == 1:
        return cmd_preview.run(rest[0])
    if cmd == "mask" and len(rest) == 1:
        return cmd_mask.run(rest[0])
    if cmd == "run-mock" and len(rest) == 1:
        return cmd_run_mock.run(rest[0])
    if cmd == "rehydrate" and len(rest) == 1:
        return cmd_rehydrate.run(rest[0])
    if cmd == "inspect" and len(rest) == 1:
        return cmd_inspect.run(rest[0])
    if cmd == "verify" and rest:
        pubkey = None
        if "--pubkey" in rest:
            i = rest.index("--pubkey")
            pubkey = rest[i + 1]
            del rest[i:i + 2]
        return cmd_verify.run(rest, pubkey)
    if cmd == "playground":
        return _playground(rest)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
