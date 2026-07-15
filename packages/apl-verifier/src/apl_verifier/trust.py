# SPDX-License-Identifier: Apache-2.0
"""Trust-domain normalization — the single implementation.

A trust domain is the party that actually sees a payload. Ports are not
isolation boundaries (two ports on one host are one domain); every loopback
spelling collapses to one domain; known vendor API hosts collapse to the
vendor label. This module is the ONE place the rule lives: the runtime imports
`normalize_host`/`trust_domain` from here, and the verifier re-derives the same
values from signed receipts. There is no second copy to drift.
"""
from __future__ import annotations

from urllib.parse import urlsplit

# Known vendor API hosts -> trust-domain label. Anything else aggregates by its
# endpoint host with the port stripped.
VENDOR_TRUST_DOMAINS = {
    "api.anthropic.com": "anthropic",
    "api.openai.com": "openai",
}

# Every spelling of the local machine is one trust domain: a loopback address
# is not an isolation boundary, so 'localhost', '127.0.0.1' and '::1' must never
# look like three distinct parties.
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
_LOOPBACK_DOMAIN = "loopback"


def normalize_host(endpoint_host: str) -> str:
    """Canonical host label for an endpoint: lowercase, trailing dot stripped,
    port removed, IPv6-safe. Accepts a bare host ('api.openai.com', '::1'),
    a host:port ('api.openai.com:443', '[::1]:8080') or a full URL. Returns
    '' only when there is genuinely no host to name."""
    raw = (endpoint_host or "").strip()
    if not raw:
        return ""
    # urlsplit only extracts host/port when it sees an authority; give it one.
    # A bare 'api.openai.com:443' looks like a scheme, so we always prefix //.
    probe = raw if "://" in raw else "//" + raw
    try:
        parsed = urlsplit(probe)
        host = parsed.hostname  # already strips [] from IPv6 and the :port
    except ValueError:
        host = None
    if not host:
        # urlsplit could not find an authority (e.g. a lone '::1' with no
        # brackets parses as a scheme-relative path). Fall back to the raw
        # value with a trailing :port heuristic that leaves IPv6 intact.
        host = raw
        if host.count(":") == 1:  # host:port, never bare IPv6 (>=2 colons)
            host = host.rsplit(":", 1)[0]
    return host.rstrip(".").lower()


def trust_domain(endpoint_host: str) -> str:
    """Trust-domain label for an endpoint host. Host is normalized (lowercase,
    trailing dot and port stripped, IPv6-safe); every loopback spelling
    collapses to one domain; known vendors collapse to the vendor label."""
    host = normalize_host(endpoint_host)
    if host in _LOOPBACK_HOSTS:
        return _LOOPBACK_DOMAIN
    return VENDOR_TRUST_DOMAINS.get(host, host or "unknown")
