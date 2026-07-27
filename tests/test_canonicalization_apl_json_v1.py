# SPDX-License-Identifier: FSL-1.1-ALv2
"""P1/P4 canonicalization boundary vectors for apl-json-v1.

RECEIPT_STANDARD.md section 2 pins the canonical serialization as a named
algorithm, apl-json-v1, that is NOT RFC 8785 / JCS. These tests exercise the
boundary cases the spec now documents explicitly and prove the two honest
divergences from JCS:

  P4  number/float serialization -- exponent notation IS emitted where CPython
      emits it (0.0, 1.0, whole-number floats, tiny in-range ratios).
  P1  object-key ordering -- keys sort by Unicode code point (Python string
      comparison), which diverges from JCS UTF-16 code-unit ordering for
      supplementary-plane (astral, U+10000+) characters.

They are pure-property vectors over canonical_bytes; no receipt files or hashes
change. They also assert the spec text matches the implementation so the P4
prose correction cannot silently drift back.
"""
from pathlib import Path

from apl_verifier import canonical_bytes, compute_receipt_hash

REPO = Path(__file__).resolve().parents[1]
STANDARD = REPO / "RECEIPT_STANDARD.md"

# Boundary key characters, written as ASCII escapes:
#   BMP_MAX    = U+FFFF   (last Basic Multilingual Plane code point)
#   ASTRAL_MIN = U+10000  (first supplementary-plane / astral code point)
BMP_MAX = "\uffff"
ASTRAL_MIN = "\U00010000"


def _canon(obj) -> str:
    return canonical_bytes(obj).decode("utf-8")


# ---- P4: number / float serialization (exponent allowed) -------------------

def test_zero_and_one_floats_roundtrip():
    # 0.0 and 1.0 are whole-valued floats; they serialize without exponent but
    # keep the decimal point, and must round-trip exactly.
    assert _canon({"a": 0.0}) == '{"a":0.0}'
    assert _canon({"a": 1.0}) == '{"a":1.0}'


def test_whole_number_large_float_uses_exponent():
    # A large whole-number float serializes in exponent form under CPython.
    assert _canon({"a": 1e16}) == '{"a":1e+16}'


def test_tiny_in_range_ratio_uses_exponent():
    # The exact case from the P4 finding: a rounded ratio in (0, 1e-4) emits
    # exponent notation. This is what the spec now documents (previously it
    # wrongly said "without exponent notation").
    value = round(1 / 1e6, 6)  # 1e-06
    assert _canon({"exposure_ratio": value}) == '{"exposure_ratio":1e-06}'


def test_integer_stays_integer():
    # Integers are not floats: 1 serializes as 1, distinct from the float 1.0.
    assert _canon({"a": 1}) == '{"a":1}'
    assert _canon({"a": 1}) != _canon({"a": 1.0})


# ---- P1: key ordering by code point (diverges from JCS for astral chars) ---

def test_key_ordering_is_code_point_not_utf16():
    # By Unicode code point, U+FFFF < U+10000, so apl-json-v1 orders the U+FFFF
    # key first. JCS, sorting by UTF-16 code units, would place the astral key
    # (surrogate lead 0xD800) BEFORE U+FFFF -- the opposite order. This is the
    # documented divergence, present even with zero floats in the body.
    obj = {ASTRAL_MIN: 1, BMP_MAX: 2}
    canon = _canon(obj)
    assert canon.index(f'"{BMP_MAX}"') < canon.index(f'"{ASTRAL_MIN}"')


def test_astral_key_ordering_is_deterministic_under_single_rule():
    # Zero floats present, yet the byte string (and thus the sha256) depends on
    # which ordering rule is used -- proving the "byte-identical for float-free
    # bodies" claim would be false, which is exactly why the spec does not make
    # it. Under our single rule the hash is stable regardless of input order.
    code_point_order = compute_receipt_hash({BMP_MAX: 1, ASTRAL_MIN: 2})
    assert compute_receipt_hash({ASTRAL_MIN: 2, BMP_MAX: 1}) == code_point_order


# ---- spec/impl agreement guard (P4 prose must match implementation) --------

def test_spec_documents_apl_json_v1_and_exponent_allowed():
    text = STANDARD.read_text(encoding="utf-8").lower()
    assert "apl-json-v1" in text
    # The corrected prose must state exponent is permitted, and must NOT keep
    # the old unqualified "without exponent notation" claim.
    assert "exponent notation is permitted" in text
    assert "numbers must be written without exponent notation" not in text
    # And it must be explicit that this is not RFC 8785 / JCS.
    assert "not rfc 8785" in text
