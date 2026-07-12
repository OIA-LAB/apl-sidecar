"""APL Sidecar CLI - local, offline, no API keys.

Usage:
    apl --help
    apl demo       [--output apl-out] [--scenario example_dir]
    apl preview    <example_dir>
    apl mask       <example_dir>
    apl run        <example_dir> [--output apl-out]
    apl run-mock   <example_dir>
    apl run-live   <example_dir> [--seat FRAGMENT_ID=KIND ...]
                   [--output apl-live-out] [--chain prev_receipt.json] [--yes]
                   KIND is anthropic or openai. With exactly two fragments and
                   no --seat, defaults to anthropic,openai. Three or more
                   fragments require every seat to be named explicitly; the
                   supported fragment range is 2-5.
    apl rehydrate  <example_dir>
    apl inspect    <receipt.json>
    apl verify     <receipt.json> [more...] [--pubkey key.pem]
    apl break-receipt <receipt.json>
    apl playground [--port 8791]
    apl proxy      [--port 8793]
"""
from __future__ import annotations

import sys
from pathlib import Path

_CLI = Path(__file__).resolve().parent
sys.path.insert(0, str(_CLI.parent))
sys.path.insert(0, str(_CLI))

from commands import break_receipt as cmd_break_receipt  # noqa: E402
from commands import demo as cmd_demo  # noqa: E402
from commands import inspect as cmd_inspect  # noqa: E402
from commands import mask as cmd_mask  # noqa: E402
from commands import preview as cmd_preview  # noqa: E402
from commands import rehydrate as cmd_rehydrate  # noqa: E402
from commands import run_live as cmd_run_live  # noqa: E402
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
        the page (learned the hard way). A local demo never needs caching.
        Root redirects to the playground — a trust product must not greet
        its users with a raw directory listing."""

        def end_headers(self):
            self.send_header("Cache-Control", "no-store, must-revalidate")
            super().end_headers()

        def do_GET(self):  # noqa: N802
            if self.path in ("", "/"):
                self.send_response(302)
                self.send_header("Location", "/app/local_playground/")
                self.end_headers()
                return
            super().do_GET()

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
    if argv == ["--help"] or argv == ["-h"]:
        print(__doc__)
        return 0
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "demo":
        output, scenario = "apl-out", None
        while rest:
            flag = rest.pop(0)
            if flag not in ("--output", "--scenario") or not rest:
                print("demo accepts --output <dir> and --scenario <example_dir>", file=sys.stderr)
                return 2
            value = rest.pop(0)
            if flag == "--output":
                output = value
            else:
                scenario = value
        return cmd_demo.run(output, scenario)
    if cmd == "run" and rest:
        scenario = rest.pop(0)
        output = "apl-out"
        if rest:
            if len(rest) != 2 or rest[0] != "--output":
                print("run accepts <example_dir> [--output <dir>]", file=sys.stderr)
                return 2
            output = rest[1]
        return cmd_demo.run(output, scenario)
    if cmd == "preview" and len(rest) == 1:
        return cmd_preview.run(rest[0])
    if cmd == "mask" and len(rest) == 1:
        return cmd_mask.run(rest[0])
    if cmd == "run-mock" and len(rest) == 1:
        return cmd_run_mock.run(rest[0])
    if cmd == "run-live" and rest:
        scenario = rest.pop(0)
        seats: list[str] = []
        opts = {"--output": "apl-live-out", "--chain": None}
        yes = False
        while rest:
            flag = rest.pop(0)
            if flag == "--yes":
                yes = True
                continue
            if flag == "--seat":
                if not rest:
                    print("--seat expects <fragment_id>=<anthropic|openai>",
                          file=sys.stderr)
                    return 2
                seats.append(rest.pop(0))
                continue
            if flag not in opts or not rest:
                print("run-live accepts <example_dir> [--seat ID=KIND ...]"
                      " [--output DIR] [--chain RECEIPT] [--yes]", file=sys.stderr)
                return 2
            opts[flag] = rest.pop(0)
        return cmd_run_live.run(scenario, seat_specs=seats or None,
                                output=opts["--output"], yes=yes,
                                chain=opts["--chain"])
    if cmd == "rehydrate" and len(rest) == 1:
        return cmd_rehydrate.run(rest[0])
    if cmd == "inspect" and len(rest) == 1:
        return cmd_inspect.run(rest[0])
    if cmd == "break-receipt" and len(rest) == 1:
        return cmd_break_receipt.run(rest[0])
    if cmd == "verify" and rest:
        pubkey = None
        if "--pubkey" in rest:
            i = rest.index("--pubkey")
            pubkey = rest[i + 1]
            del rest[i:i + 2]
        return cmd_verify.run(rest, pubkey)
    if cmd == "playground":
        return _playground(rest)
    if cmd == "proxy":
        from relay.openai_proxy import serve

        port = 8793
        if rest:
            if len(rest) != 2 or rest[0] != "--port":
                print("proxy accepts only --port <integer>", file=sys.stderr)
                return 2
            try:
                port = int(rest[1])
            except ValueError:
                print("proxy --port requires an integer", file=sys.stderr)
                return 2
        return serve(port)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
