"""Endpoint host normalization + trust-domain derivation.

A port is not an isolation boundary and neither is the spelling of a host:
case, a trailing dot, an explicit :port, and every loopback address must all
collapse deterministically. IPv6 must survive intact — '::1' is a real host,
never '' or 'unknown'. The verifier duplicates this rule (verifier/apl_verify.py
_normalize_host / _trust_domain); test_verifier_host_rule_matches_common below
pins the two implementations together on this same table.
"""
import pytest

from cli.commands import _common as c
from verifier import apl_verify

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


@pytest.mark.parametrize("raw,host,domain", HOST_TABLE)
def test_verifier_host_rule_matches_common(raw, host, domain):
    """The verifier duplicates the rule to stay standalone; the two copies
    must never drift. Pin them together on the shared host table."""
    assert apl_verify._normalize_host(raw) == c.normalize_host(raw) == host
    assert apl_verify._trust_domain(raw) == c.trust_domain(raw) == domain
