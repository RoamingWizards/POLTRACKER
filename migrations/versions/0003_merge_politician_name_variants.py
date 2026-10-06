"""merge politician name variants and recompute trade fingerprints

Data migration. Upstream formats some member names inconsistently ("Scott Scott Franklin",
"John J McGuire" vs "John McGuire"). The politician key feeds the trade fingerprint, so
fixing the key means politicians are merged AND every trade fingerprint is recomputed;
otherwise the next ingest would re-insert the affected trades.

The helpers below are a frozen copy of the normalisation rules at the time of writing, so
this migration keeps behaving the same even if poltracker.normalize changes later.
It cannot be reversed (merged politicians are not restored).

Revision ID: 0003
Revises: 0002
"""
import hashlib
import re
from collections import Counter, defaultdict

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_HONORIFICS = {"mr", "mrs", "ms", "dr", "hon", "honorable", "sen", "rep", "senator"}


def _norm_name(raw):
    tokens = [t for t in raw.replace(",", " ").split() if t.lower().rstrip(".") not in _HONORIFICS]
    if len(tokens) >= 3 and tokens[0].lower().rstrip(".") == tokens[1].lower().rstrip("."):
        tokens = tokens[1:]
    return " ".join(tokens)


def _is_initial(token):
    bare = token.rstrip(".")
    return len(bare) == 1 and bare.isalpha()


def _key(name, chamber):
    tokens = name.split()
    kept = [t for i, t in enumerate(tokens) if not (0 < i < len(tokens) - 1 and _is_initial(t))]
    return f"{chamber}:{re.sub(r'[^a-z0-9]+', '', ' '.join(kept).lower())}"


def _old_key(name, chamber):
    return f"{chamber}:{re.sub(r'[^a-z0-9]+', '', name.lower())}"


def fingerprint_parts(row, key):
    asset = row["asset_name"].lower() if row["asset_name"] and not row["ticker"] else ""
    return [
        key,
        row["ticker"] or "",
        asset,
        row["transaction_type"],
        str(row["transaction_date"]),
        str(row["disclosure_date"]) if row["disclosure_date"] else "",
        str(row["amount_min"]),
        str(row["amount_max"]),
    ]


def compute_fingerprints(trades, key_of):
    """trades: rows ordered by id. Returns {trade_id: fingerprint}; identical lines get 0,1,2..."""
    seen = Counter()
    out = {}
    for row in trades:
        parts = fingerprint_parts(row, key_of(row))
        base = "|".join(parts)
        out[row["id"]] = hashlib.sha256(f"{base}|{seen[base]}".encode()).hexdigest()
        seen[base] += 1
    return out


def upgrade() -> None:
    conn = op.get_bind()
    politicians = [dict(r._mapping) for r in conn.execute(sa.text("select id, name, chamber from politicians"))]
    counts = dict(conn.execute(sa.text("select politician_id, count(*) from trades group by politician_id")).all())

    groups = defaultdict(list)
    for p in politicians:
        p["new_name"] = _norm_name(p["name"])
        groups[_key(p["new_name"], p["chamber"])].append(p)

    remap = {}  # politician id -> surviving id
    for key, members in groups.items():
        # survivor: most trades, then lowest id, so the choice is deterministic
        members.sort(key=lambda p: (-counts.get(p["id"], 0), p["id"]))
        survivor = members[0]
        for m in members[1:]:
            remap[m["id"]] = survivor["id"]
            conn.execute(sa.text("update trades set politician_id=:s where politician_id=:m"), {"s": survivor["id"], "m": m["id"]})
            conn.execute(sa.text("delete from politicians where id=:m"), {"m": m["id"]})
        conn.execute(
            sa.text("update politicians set name=:n, canonical_key=:k where id=:i"),
            {"n": survivor["new_name"], "k": key, "i": survivor["id"]},
        )
        conn.execute(
            sa.text("update trades set politician_name=:n where politician_id=:i"),
            {"n": survivor["new_name"], "i": survivor["id"]},
        )

    trades = [
        dict(r._mapping)
        for r in conn.execute(
            sa.text(
                "select id, politician_name, chamber, ticker, asset_name, transaction_type, transaction_date, "
                "disclosure_date, amount_min, amount_max from trades order by id"
            )
        )
    ]
    new_fps = compute_fingerprints(trades, lambda r: _key(r["politician_name"], r["chamber"]))

    # Two-step update so no row ever collides with another row's old value on the unique index.
    if not new_fps:  # fresh database: nothing to recompute
        return
    conn.execute(sa.text("update trades set fingerprint='tmp-' || id"))
    conn.execute(
        sa.text("update trades set fingerprint=:fp where id=:id"),
        [{"fp": fp, "id": tid} for tid, fp in new_fps.items()],
    )


def downgrade() -> None:
    raise NotImplementedError("0003 merges rows and cannot be reversed; restore from a backup instead")
