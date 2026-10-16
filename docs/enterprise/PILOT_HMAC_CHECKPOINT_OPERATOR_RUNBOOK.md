# Offline pilot evidence — independently held HMAC checkpoint (v1)

**State:** Engineering control for *internal synthetic training pilots only*. Not an enterprise LMS, hosted identity provider, external trusted timestamp, legal chain-of-custody certificate, student credential, or `TRAINING_CONTENT_GO` approval.

## Why this is needed

A SQLite owner can alter both materialized grades and the original unkeyed event history, then recompute that history's SHA-256 chain. The reconciliation implementation detects a forged grade only when the source event log is unchanged. This control produces a **keyed authentication code** over an independently captured snapshot of the tenant's validated audit state. When the operator protects the 32-byte secret and that receipt outside the database trust boundary, later alteration or rollback of an otherwise internally consistent database becomes detectable at verification time.

This is a keyed *HMAC*, **not a digital signature**: anyone possessing the key can issue valid receipts. The receipt timestamp is supplied by the issuing machine; it is not a trusted or independent time attestation. A local receipt on the same compromised machine is **not** independently anchored. No remote archive, WORM service, HSM, signing authority, key-rotation protocol, tenant SSO, encryption-at-rest, or automatic checkpoint scheduler is implemented. Use only synthetic or authorized nonpersonal training IDs.

## Operator procedure (POSIX-only; isolated nonproduction environment)

The operator is responsible for independent custody and safe retention. The following commands are an **illustrative local runbook**, not a request to put a secret in GitHub or to generate a production key on a shared computer.

1. Start from an existing, valid pilot SQLite database; `issue` refuses to initialize a database accidentally. Record the current checkout/commit and the pilot's approved synthetic scope. The training database itself stays in a private, non-repository directory.
2. Generate 32 cryptographically random bytes in a **restricted external secret store or offline operator directory**. Never paste the key into the shell command, Git, chat, a CI log or a student worksheet. On POSIX the key file must be a regular nonsymlink file with permissions `0600` or tighter. Its parent directories also need independently controlled access. The script does not create or persist a secret automatically.
3. Issue the receipt once per intended checkpoint. The path **must not exist**; earlier checkpoint files are never overwritten.
4. Move or copy the receipt through a trusted process to separately administered **append-only/offline protected custody**, and separately protect the HMAC key. Retain the oldest and newest receipts under the operator's evidence-retention policy. **No such custody is established by running the command alone.**
5. To validate, bring back the independently held receipt and key through approved offline channels, open the exact database, and verify. A mismatched receipt, key, tenant, role, or audit state returns nonzero. A new legitimate event after the receipt makes exact-snapshot verification fail until a **new** receipt is issued and safely retained; this is intentional. Never discard older receipts just to make verification green.

With the Python repo root on the module path:

```text
PYTHONPATH=scripts python -m enterprise.audit_checkpoint issue \
  --db /approved-private/pilot.db --tenant synthetic_tenant \
  --actor synthetic_admin --key-file /offline-operator/pilot-32byte.key \
  --key-id rotation_001 --receipt /independent-evidence/tenant-v1.receipt.json

PYTHONPATH=scripts python -m enterprise.audit_checkpoint verify \
  --db /approved-private/pilot.db --tenant synthetic_tenant \
  --actor synthetic_admin --key-file /offline-operator/pilot-32byte.key \
  --key-id rotation_001 --receipt /independent-evidence/tenant-v1.receipt.json
```

The placeholder paths above **are not real services or provisioned directories**. Specify existing private directories in an approved offline environment. Keys may be managed by an independent verifier, with database copy and receipt received through protected channels. Avoid co-hosting the production key and an attacker-writable ledger.

## Evidence and rejection contract

The v1 JSON receipt binds the exact `tenant`, event count, last global sequence ID, final chain SHA-256, recorded timestamp, explicit version and key identifier. Its HMAC-SHA256 is domain-separated from other operator data. The validator fails closed on unexpected fields, malformed types, duplicate JSON keys, invalid MAC, wrong tenant or key, wrong caller role, materialized-table divergence, full audit-history rewrites and old-database rollback relative to a **trusted later receipt**. The receipt contains no learner names, raw artifacts or grades. Its tenant and administrative IDs remain metadata and should be treated as sensitive in a genuine enterprise environment.

**Exit results:** 0 means an exact local snapshot was checked, or the receipt was successfully issued; it does **not** mean a course passed Gate A. 3 means blocking evidence or an operational error. A check cannot establish that the timestamp is independently valid, the issuer identity was externally authenticated, the student's evidence was legitimately collected, a reviewer was qualified, or a higher-priority receipt has not been withheld. In particular, comparison with an untrusted old receipt cannot prevent an adversary from substituting both the database and the receipt.

## Reproduce the defensive tests

```text
python -m pytest -q tests/test_enterprise_audit_checkpoint.py \
    tests/test_enterprise_pilot_ledger.py \
    tests/test_enterprise_release_preflight.py
```

This control is separate from instructor hidden test packs and the public training materials. Those packs must remain in approved private storage, not in this public repository. The existing public source-PDF privacy incident, copyright ownership and licence decisions, independent human reviews, and complete flagship-course approval remain unresolved and cannot be fixed by issuing a checkpoint.

## Migration and rollback discipline

This checkpoint format assumes the audit schema introduced by the audit/materialized state reconciliation implementation. Earlier pilot databases cannot be trusted through automatic in-place replay and **must not** be silently migrated, truncated or overwritten to pass this check. Preserve the original, arrange an authorized independent forensic review and only then develop a versioned migration with negative controls. The tool has no automatic migration. Old checkpoints must remain available throughout any later explicitly approved upgrade.
