"""Endpoint host normalization + trust-domain derivation.

A port is not an isolation boundary and neither is the spelling of a host:
case, a trailing dot, an explicit :port, and every loopback address must all
collapse deterministically. IPv6 must survive intact — '::1' is a real host,
never '' or 'unknown'. The rule has ONE implementation, in apl_verifier.trust;
the runtime imports it, so test_verifier_host_rule_is_single_source below pins
that the runtime uses that very implementation (no second copy to drift).
"""
import pytest

import apl_verifier
from cli.commands import _common as c

# (raw endpoint host, expected normalized host, expected trust domain)
HOST_TABLE = [
    ("API.OpenAI.com.", "api.openai.com", "openai"),
    ("api.openai.com:443", "api.openai.com", "openai"),
    ("[::1]:8080", "::1", "loopback"),
    ("::1", "::1", "loopback"),
    ("localhost", "localhost", "loopback"),
    ("127.0.0.1", "127.0.0.1", "loopback"),
    ("127.0.0.1:9999", "127.0.0.1", "loopback"),
    ("api.anthropic.com", "api.anthropic.com", "anthropic"),
    ("Example.Internal", "example.internal", "example.internal"),
    ("", "", "unknown"),
]


@pytest.mark.parametrize("raw,host,domain", HOST_TABLE)
def test_normalize_host_and_trust_domain(raw, host, domain):
    assert c.normalize_host(raw) == host
    assert c.trust_domain(raw) == domain


def test_ipv6_loopback_never_empty_or_unknown():
    for raw in ("::1", "[::1]:8080"):
        assert c.normalize_host(raw) not in ("", "unknown")
        assert c.trust_domain(raw) == "loopback"


def test_port_is_not_an_isolation_boundary():
    assert c.trust_domain("api.openai.com:443") == c.trust_domain("api.openai.com")
    assert c.trust_domain("127.0.0.1:1") == c.trust_domain("127.0.0.1:2")


def test_verifier_host_rule_is_single_source():
    """One implementation, no drift: the runtime's normalize_host/trust_domain
    ARE the apl_verifier functions (same object), so they cannot diverge."""
    assert c.normalize_host is apl_verifier.normalize_host
    assert c.trust_domain is apl_verifier.trust_domain


@pytest.mark.parametrize("raw,host,domain", HOST_TABLE)
def test_verifier_host_rule_matches_table(raw, host, domain):
    """The single implementation must satisfy the shared host table."""
    assert apl_verifier.normalize_host(raw) == c.normalize_host(raw) == host
    assert apl_verifier.trust_domain(raw) == c.trust_domain(raw) == domain
