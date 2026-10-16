"""Step 1 - Settings that fail closed, and tokens that are checked by what they claim, not by how they look."""
from __future__ import annotations

import dataclasses
import json
import time

import jwt
import pytest
from lab_support import SECRET, T0, forge_token


def settings(ta, clock, **kw):
    kw.setdefault("secret", SECRET)
    kw.setdefault("db_path", "unused.db")
    return ta.Settings(clock=clock, **kw)


def claims(clock, **overrides):
    now = int(clock())
    base = {"iss": "ticketapi", "aud": "ticketapi-clients", "sub": "alice", "role": "reader", "iat": now, "exp": now + 900}
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}


def refused(ta, st, token):
    with pytest.raises(ta.AuthError) as info:
        ta.verify_token(st, token)
    return info.value.code


# ------------------------------------------------------------------------------------------------------------------------------------------- Settings
def test_settings_with_a_real_secret_are_accepted_and_have_safe_defaults(ta):
    st = ta.Settings(secret=SECRET, db_path="t.db")
    assert (st.issuer, st.audience, st.token_ttl, st.max_body, st.expose_schema) == ("ticketapi", "ticketapi-clients", 900, 16_384, False)
    assert st.clock is time.time


def test_the_secret_never_appears_in_the_text_of_the_settings(ta):
    st = ta.Settings(secret=SECRET, db_path="t.db")
    assert SECRET not in repr(st) and SECRET not in str(st)


def test_settings_are_frozen(ta):
    st = ta.Settings(secret=SECRET, db_path="t.db")
    with pytest.raises(dataclasses.FrozenInstanceError):
        st.secret = "another-secret-another-secret-12345678"          # type: ignore[misc]


@pytest.mark.parametrize("secret", ["", "short", "a" * 31, "abcdefgh" * 3 + "ijklmno", "ab" * 20, "a" * 40, "0123456789" * 4, None, 12345678901234567890123456789012, b"x" * 40])
def test_a_weak_or_mistyped_secret_is_refused(ta, secret):
    with pytest.raises(ta.SettingsError):
        ta.Settings(secret=secret, db_path="t.db")


def test_the_secret_length_and_variety_limits_are_exact(ta):
    thirty_two_twelve_distinct = "abcdefghijkl" + "a" * 20
    assert len(thirty_two_twelve_distinct) == 32 and len(set(thirty_two_twelve_distinct)) == 12
    ta.Settings(secret=thirty_two_twelve_distinct, db_path="t.db")
    with pytest.raises(ta.SettingsError):
        ta.Settings(secret="abcdefghijk" + "a" * 21, db_path="t.db")          # 32 characters, 11 different
    with pytest.raises(ta.SettingsError):
        ta.Settings(secret="abcdefghijkl" + "a" * 19, db_path="t.db")         # 12 different but 31 characters


def test_a_refusal_does_not_repeat_the_secret(ta):
    with pytest.raises(ta.SettingsError) as info:
        ta.Settings(secret=SECRET, db_path="t.db", token_ttl=0)
    assert SECRET not in str(info.value)
    with pytest.raises(ta.SettingsError) as info:
        ta.Settings(secret="weakweakweakweakweakweakweakweakweak", db_path="t.db")
    assert "weakweakweak" not in str(info.value)


def test_settings_error_is_a_value_error(ta):
    assert issubclass(ta.SettingsError, ValueError)


@pytest.mark.parametrize("ttl", [0, -1, 3601, 10**6, True, False, "900", 900.0, None])
def test_a_token_ttl_outside_one_to_3600_seconds_is_refused(ta, ttl):
    with pytest.raises(ta.SettingsError):
        ta.Settings(secret=SECRET, db_path="t.db", token_ttl=ttl)


@pytest.mark.parametrize("ttl", [1, 60, 3600])
def test_boundary_token_ttls_are_accepted(ta, ttl):
    assert ta.Settings(secret=SECRET, db_path="t.db", token_ttl=ttl).token_ttl == ttl


@pytest.mark.parametrize("size", [0, -5, 1_000_001, True, "16384", 1.5, None])
def test_a_body_limit_outside_one_to_a_million_bytes_is_refused(ta, size):
    with pytest.raises(ta.SettingsError):
        ta.Settings(secret=SECRET, db_path="t.db", max_body=size)


@pytest.mark.parametrize("size", [1, 16_384, 1_000_000])
def test_boundary_body_limits_are_accepted(ta, size):
    assert ta.Settings(secret=SECRET, db_path="t.db", max_body=size).max_body == size


def test_an_empty_database_path_is_refused(ta):
    with pytest.raises(ta.SettingsError):
        ta.Settings(secret=SECRET, db_path="")


def test_from_env_reads_the_given_mapping_and_not_the_process_environment(ta, monkeypatch):
    monkeypatch.setenv("TICKETAPI_SECRET", "x")
    st = ta.Settings.from_env({"TICKETAPI_SECRET": SECRET, "TICKETAPI_DB": "/data/t.db"})
    assert st.secret == SECRET and st.db_path == "/data/t.db" and st.token_ttl == 900


def test_from_env_reads_the_token_ttl(ta):
    assert ta.Settings.from_env({"TICKETAPI_SECRET": SECRET, "TICKETAPI_DB": "t.db", "TICKETAPI_TOKEN_TTL": "60"}).token_ttl == 60


@pytest.mark.parametrize(
    "env, fragment",
    [
        ({"TICKETAPI_DB": "t.db"}, "TICKETAPI_SECRET"),
        ({"TICKETAPI_SECRET": "", "TICKETAPI_DB": "t.db"}, "TICKETAPI_SECRET"),
        ({"TICKETAPI_SECRET": SECRET}, "TICKETAPI_DB"),
        ({"TICKETAPI_SECRET": SECRET, "TICKETAPI_DB": ""}, "TICKETAPI_DB"),
        ({"TICKETAPI_SECRET": SECRET, "TICKETAPI_DB": "t.db", "TICKETAPI_TOKEN_TTL": "soon"}, "TICKETAPI_TOKEN_TTL"),
    ],
)
def test_from_env_refuses_to_start_without_what_it_needs_and_names_the_variable(ta, env, fragment):
    with pytest.raises(ta.SettingsError) as info:
        ta.Settings.from_env(env)
    assert fragment in str(info.value)


def test_from_env_applies_the_same_rules_as_the_constructor(ta):
    with pytest.raises(ta.SettingsError):
        ta.Settings.from_env({"TICKETAPI_SECRET": "changeme", "TICKETAPI_DB": "t.db"})
    with pytest.raises(ta.SettingsError):
        ta.Settings.from_env({"TICKETAPI_SECRET": SECRET, "TICKETAPI_DB": "t.db", "TICKETAPI_TOKEN_TTL": "0"})


# ------------------------------------------------------------------------------------------------------------------------------------------- issue_token
def test_issue_token_signs_the_documented_claims_with_hs256(ta, clock):
    st = settings(ta, clock)
    token = ta.issue_token(st, "alice", "reader")
    assert jwt.get_unverified_header(token)["alg"] == "HS256"
    payload = jwt.decode(token, SECRET, algorithms=["HS256"], audience=st.audience, issuer=st.issuer, options={"verify_exp": False, "verify_iat": False})
    assert payload["sub"] == "alice" and payload["role"] == "reader"
    assert payload["iss"] == "ticketapi" and payload["aud"] == "ticketapi-clients"
    assert payload["iat"] == T0 and payload["exp"] == T0 + 900
    assert isinstance(payload["jti"], str) and len(payload["jti"]) == 16 and int(payload["jti"], 16) >= 0


def test_issue_token_uses_the_clock_and_the_ttl_of_the_settings(ta, clock):
    st = settings(ta, clock, token_ttl=60, issuer="idp", audience="tickets")
    clock.advance(1000.7)
    payload = jwt.decode(ta.issue_token(st, "bob", "agent"), SECRET, algorithms=["HS256"], audience="tickets", issuer="idp", options={"verify_exp": False, "verify_iat": False})
    assert payload["iat"] == T0 + 1000 and payload["exp"] == T0 + 1060


def test_every_token_has_its_own_id(ta, clock):
    st = settings(ta, clock)
    ids = {jwt.decode(ta.issue_token(st, "alice", "reader"), options={"verify_signature": False})["jti"] for _ in range(20)}
    assert len(ids) == 20


@pytest.mark.parametrize("role", ["", "root", "Reader", "ADMIN", "reader ", None, 1, "agent,admin"])
def test_issue_token_refuses_an_unknown_role(ta, clock, role):
    with pytest.raises(ValueError):
        ta.issue_token(settings(ta, clock), "alice", role)


@pytest.mark.parametrize("subject", ["", "a b", "x" * 65, "a/b", "a;b", "a'b", "a\nb", "é", "a\x00", None, 5, "bob smith", "../x"])
def test_issue_token_refuses_a_subject_outside_the_pattern(ta, clock, subject):
    with pytest.raises(ValueError):
        ta.issue_token(settings(ta, clock), subject, "reader")


@pytest.mark.parametrize("subject", ["a", "x" * 64, "alice@example.org", "svc_ticket-bot.1", "0", "A.B_C-D@E"])
def test_issue_token_accepts_a_subject_inside_the_pattern(ta, clock, subject):
    st = settings(ta, clock)
    assert ta.verify_token(st, ta.issue_token(st, subject, "reader")).subject == subject


# ------------------------------------------------------------------------------------------------------------------------------------------- verify_token
@pytest.mark.parametrize("role, staff", [("reader", False), ("agent", True), ("admin", True)])
def test_a_valid_token_gives_the_principal_it_was_issued_for(ta, clock, role, staff):
    st = settings(ta, clock)
    principal = ta.verify_token(st, ta.issue_token(st, "alice", role))
    assert (principal.subject, principal.role, principal.is_staff) == ("alice", role, staff)


def test_a_principal_is_a_frozen_value(ta, clock):
    st = settings(ta, clock)
    principal = ta.verify_token(st, ta.issue_token(st, "alice", "reader"))
    assert principal == ta.Principal("alice", "reader")
    with pytest.raises(dataclasses.FrozenInstanceError):
        principal.role = "admin"                              # type: ignore[misc]


@pytest.mark.parametrize("token", ["", "abc", "a.b.c", "a.b", "....", " ", "Bearer x.y.z", "x" * 5000, None, 5, b"abc.def.ghi", ["a.b.c"]])
def test_something_that_is_not_a_token_is_malformed(ta, clock, token):
    assert refused(ta, settings(ta, clock), token) == "malformed"


def token_of_at_least(clock, length):
    """The shortest forged token (with a padding claim) that has at least `length` characters."""
    for pad in range(0, 8000):
        token = forge_token(claims(clock, pad="x" * pad))
        if len(token) >= length:
            return token
    raise AssertionError("no token of that length")


def test_a_token_of_exactly_4096_characters_is_still_read_and_a_longer_one_is_not(ta, clock):
    st = settings(ta, clock)
    exact = token_of_at_least(clock, 4096)
    assert len(exact) == 4096
    assert ta.verify_token(st, exact).subject == "alice"
    longer = token_of_at_least(clock, 4097)
    assert len(longer) > 4096 and refused(ta, st, longer) == "malformed"


def test_an_unsigned_token_with_alg_none_is_refused(ta, clock):
    assert refused(ta, settings(ta, clock), forge_token(claims(clock), alg="none")) == "bad_algorithm"


@pytest.mark.parametrize("alg", ["HS384", "HS512"])
def test_another_hmac_algorithm_is_refused_even_with_the_right_secret(ta, clock, alg):
    assert refused(ta, settings(ta, clock), forge_token(claims(clock), alg=alg)) == "bad_algorithm"


@pytest.mark.parametrize("alg", ["RS256", "ES256", "hs256", "None", "NONE", ""])
def test_an_algorithm_that_is_not_exactly_hs256_is_refused(ta, clock, alg):
    assert refused(ta, settings(ta, clock), forge_token(claims(clock), alg=alg)) == "bad_algorithm"


@pytest.mark.parametrize("name, value", [("jku", "https://evil.example/keys.json"), ("jwk", {"kty": "oct", "k": "AAAA"}), ("x5u", "https://evil.example/cert.pem"), ("x5c", ["AAAA"])])
def test_a_header_that_points_to_or_carries_a_key_is_refused(ta, clock, name, value):
    assert refused(ta, settings(ta, clock), forge_token(claims(clock), header={name: value})) == "unsafe_header"


def test_a_critical_extension_nobody_understands_is_refused(ta, clock):
    with pytest.raises(ta.AuthError):
        ta.verify_token(settings(ta, clock), forge_token(claims(clock), header={"crit": ["exp"]}))


def test_a_harmless_extra_header_is_ignored(ta, clock):
    st = settings(ta, clock)
    assert ta.verify_token(st, forge_token(claims(clock), header={"kid": "2026-10"})).subject == "alice"


def test_the_wrong_secret_gives_bad_signature(ta, clock):
    assert refused(ta, settings(ta, clock), forge_token(claims(clock), secret="another-secret-another-secret-0123456789")) == "bad_signature"


def test_a_payload_changed_after_signing_gives_bad_signature(ta, clock):
    st = settings(ta, clock)
    head, payload, signature = ta.issue_token(st, "alice", "reader").split(".")
    evil = forge_token(claims(clock, role="admin")).split(".")[1]
    assert refused(ta, st, f"{head}.{evil}.{signature}") == "bad_signature"


def test_a_cut_signature_gives_bad_signature(ta, clock):
    st = settings(ta, clock)
    token = ta.issue_token(st, "alice", "reader")
    assert refused(ta, st, token[:-2]) in {"bad_signature", "malformed"}
    assert refused(ta, st, token.rsplit(".", 1)[0] + ".") in {"bad_signature", "malformed"}


def test_the_issuer_must_match(ta, clock):
    assert refused(ta, settings(ta, clock), forge_token(claims(clock, iss="someone-else"))) == "wrong_issuer"


def test_the_audience_must_match(ta, clock):
    assert refused(ta, settings(ta, clock), forge_token(claims(clock, aud="another-service"))) == "wrong_audience"


def test_the_configured_issuer_and_audience_are_used(ta, clock):
    st = settings(ta, clock, issuer="idp.example", audience="tickets-api")
    assert ta.verify_token(st, forge_token(claims(clock, iss="idp.example", aud="tickets-api"))).subject == "alice"
    assert refused(ta, st, forge_token(claims(clock))) in {"wrong_issuer", "wrong_audience"}


@pytest.mark.parametrize("missing", ["exp", "iat", "sub", "iss", "aud"])
def test_a_missing_required_claim_gives_bad_claims(ta, clock, missing):
    assert refused(ta, settings(ta, clock), forge_token(claims(clock, **{missing: None}))) == "bad_claims"


@pytest.mark.parametrize("role", [None, "root", "Reader", "", 1, ["reader"], True])
def test_a_missing_or_unknown_role_gives_bad_claims(ta, clock, role):
    assert refused(ta, settings(ta, clock), forge_token(claims(clock, role=role))) == "bad_claims"


@pytest.mark.parametrize("sub", ["", "a b", "x" * 65, "a/b", "ünï", 123, ["alice"], True])
def test_a_subject_outside_the_pattern_or_of_the_wrong_type_gives_bad_claims(ta, clock, sub):
    assert refused(ta, settings(ta, clock), forge_token(claims(clock, sub=sub))) == "bad_claims"


@pytest.mark.parametrize("name, value", [("exp", 1.5e9), ("exp", "1800000000"), ("exp", True), ("iat", "now"), ("iat", 1.5e9), ("iat", False), ("nbf", "soon"), ("nbf", 1.5), ("nbf", True), ("nbf", False), ("exp", None)])
def test_a_time_claim_that_is_not_a_whole_number_gives_bad_claims(ta, clock, name, value):
    c = claims(clock)
    if value is None:
        c.pop(name)
    else:
        c[name] = value
    assert refused(ta, settings(ta, clock), forge_token(c)) == "bad_claims"


def test_a_token_that_expires_before_it_was_issued_gives_bad_claims(ta, clock):
    now = int(clock())
    assert refused(ta, settings(ta, clock), forge_token(claims(clock, iat=now, exp=now))) == "bad_claims"
    assert refused(ta, settings(ta, clock), forge_token(claims(clock, iat=now, exp=now - 5))) == "bad_claims"


def test_a_lifetime_longer_than_an_hour_gives_bad_claims_and_exactly_an_hour_is_accepted(ta, clock):
    st = settings(ta, clock)
    now = int(clock())
    assert refused(ta, st, forge_token(claims(clock, exp=now + 3601))) == "bad_claims"
    assert ta.verify_token(st, forge_token(claims(clock, exp=now + 3600))).subject == "alice"
    assert refused(ta, st, forge_token(claims(clock, exp=now + 10**9))) == "bad_claims"


def test_a_token_is_expired_at_its_exp_second_and_valid_one_second_before(ta, clock):
    st = settings(ta, clock)
    token = ta.issue_token(st, "alice", "reader")
    clock.advance(899)
    assert ta.verify_token(st, token).subject == "alice"
    clock.advance(1)
    assert refused(ta, st, token) == "expired"
    clock.advance(10_000)
    assert refused(ta, st, token) == "expired"


def test_an_issue_time_up_to_30_seconds_ahead_is_tolerated_and_31_is_not(ta, clock):
    st = settings(ta, clock)
    now = int(clock())
    assert ta.verify_token(st, forge_token(claims(clock, iat=now + 30, exp=now + 900))).subject == "alice"
    assert refused(ta, st, forge_token(claims(clock, iat=now + 31, exp=now + 900))) == "not_yet_valid"
    assert refused(ta, st, forge_token(claims(clock, iat=now + 3000, exp=now + 3900))) == "not_yet_valid"


def test_a_not_before_claim_in_the_future_is_honoured(ta, clock):
    st = settings(ta, clock)
    now = int(clock())
    assert refused(ta, st, forge_token(claims(clock, nbf=now + 60))) == "not_yet_valid"
    assert ta.verify_token(st, forge_token(claims(clock, nbf=now))).subject == "alice"
    assert ta.verify_token(st, forge_token(claims(clock, nbf=now - 60))).subject == "alice"


def test_time_comes_from_the_clock_of_the_settings_not_from_the_machine(ta):
    far = lambda: 2_000_000_000.0                                           # noqa: E731  - the year 2033
    st = ta.Settings(secret=SECRET, db_path="t.db", clock=far)
    token = ta.issue_token(st, "alice", "reader")
    assert ta.verify_token(st, token).subject == "alice"                    # real time (2026) is before this token's iat, but 'now' is the settings' clock
    machine = ta.Settings(secret=SECRET, db_path="t.db", clock=lambda: float(T0))
    assert refused(ta, machine, token) == "not_yet_valid"


def test_the_algorithm_of_the_header_is_checked_before_the_signature(ta, clock):
    token = forge_token(claims(clock), alg="HS512", secret="another-secret-another-secret-0123456789")
    assert refused(ta, settings(ta, clock), token) == "bad_algorithm"


def test_auth_error_carries_its_code(ta):
    err = ta.AuthError("expired")
    assert err.code == "expired" and isinstance(err, Exception) and "expired" in str(err)


def test_the_token_text_never_appears_in_an_error(ta, clock):
    st = settings(ta, clock)
    token = forge_token(claims(clock), secret="another-secret-another-secret-0123456789")
    with pytest.raises(ta.AuthError) as info:
        ta.verify_token(st, token)
    assert token not in str(info.value) and SECRET not in str(info.value)
