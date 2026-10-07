"""Human-review packet for the committee/industry mappings.   python -m poltracker.committee_industry_review

Reads the mapping file and, read-only, the current securities, trades and committee seats, and writes a Markdown packet grouped by
committee/subcommittee: every row with its SIC range, the SIC titles it covers, level, rationale, the official wording relied on, source,
whether the jurisdiction was read or inferred from a name, how many current securities and trades it matches, and why it deserves scrutiny.

It never edits a mapping, never marks anything reviewed, flags no trade, and prints no politician names (counts and tickers only). Every number
is computed from the data, so the packet cannot drift from the mappings.
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .committee_industry import EXPLICIT_BASES, Assignment, CommitteeIndustryMatcher, Mapping, load_assignments, load_rows, parse_sic
from .db import make_session_factory
from .models import Politician, Security, Trade

DATA = Path(__file__).resolve().parents[2] / "data"
# Scrutiny thresholds (documented in the packet, so a reviewer can see why a row was flagged).
BROAD_WIDTH = 100  # a SIC range spanning this many codes or more
BROAD_TITLES = 10  # or covering this many official SIC titles
MANY_TRADES = 25  # a row that matches this many current trades

# Flags that point at a substantive concern about what the range captures. The rest (inferred name, related level, overlap) apply to most rows.
SUBSTANTIVE = ("broad_range", "mixed_industries", "many_matches", "false_positive_history")

FLAG_TEXT = {
    "broad_range": f"broad SIC range (spans {BROAD_WIDTH}+ codes or covers {BROAD_TITLES}+ official titles)",
    "mixed_industries": "captures more than one SIC industry group among current securities (see the descriptions)",
    "inferred_from_name": "jurisdiction inferred from a subcommittee or committee name, not read from official wording",
    "related_level": "'related' level (adjacent or partial relevance)",
    "many_matches": f"matches {MANY_TRADES}+ current trades",
    "overlaps_other_committee": "overlaps a mapping of another committee",
    "false_positive_history": "adjusted after a false positive found in an earlier manual review",
}


def row_key(m: Mapping) -> str:
    where = m.committee_code + (f"/{m.subcommittee_code}" if m.subcommittee_code else "")
    return f"{where}:{m.sic_range or 'none'}:{m.relevance_level}"


@dataclass
class RowReport:
    mapping: Mapping
    key: str
    official_titles: list[tuple[str, str]] = field(default_factory=list)
    data_descriptions: list[tuple[str, str, int]] = field(default_factory=list)  # (sic, description, securities)
    securities_matched: int = 0
    trades_matched: int = 0
    trades_primary: int = 0
    politicians_matched: int = 0
    example_tickers: list[str] = field(default_factory=list)
    overlaps: list[str] = field(default_factory=list)
    mixed_groups: dict[str, list[str]] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)


@dataclass
class Review:
    version: str
    rows: list[RowReport]
    trades_total: int = 0
    securities_total: int = 0
    trades_direct: int = 0  # trades with at least one direct match
    trades_related_only: int = 0
    trades_with_match: int = 0


def to_mappings(rows: list[dict]) -> list[Mapping]:
    out = []
    for i, r in enumerate(rows, start=1):
        out.append(Mapping(
            i, r["chamber"], r["committee_code"], r.get("subcommittee_code") or None, r["committee_name"], r.get("subcommittee_name"),
            parse_sic(r.get("sic_start")), parse_sic(r.get("sic_end")), r.get("industry_pattern"), r["relevance_level"], r["rationale"],
            r.get("jurisdiction_text"), r.get("source_citation"), r["source_url"], None, r["mapping_version"], r["review_status"],
            r.get("reviewed_by"), r.get("review_note"), r["jurisdiction_basis"],
        ))
    return out


def build_review(session_factory: sessionmaker[Session], rows: list[dict], sic_titles: dict[str, str]) -> Review:
    mappings = to_mappings(rows)
    matcher = CommitteeIndustryMatcher(mappings)
    reports = {m.id: RowReport(m, row_key(m)) for m in mappings}
    review = Review(matcher.version or "", list(reports.values()))
    with session_factory() as session:
        securities = session.execute(
            select(Security.id, Security.ticker, Security.sic_code, Security.industry).where(Security.id.in_(select(Trade.security_id).where(Trade.security_id.is_not(None))))
        ).all()
        review.securities_total = len(securities)
        by_sic: dict[str, Counter] = {}
        for rep in reports.values():
            m = rep.mapping
            if m.sic_start is None:
                continue
            rep.official_titles = [(c, t.title()) for c, t in sorted(sic_titles.items()) if m.sic_start <= int(c) <= m.sic_end]
            hits = Counter()
            tickers = []
            for _sid, ticker, sic, industry in securities:
                n = parse_sic(sic)
                if n is None or not m.sic_start <= n <= m.sic_end:
                    continue
                if m.industry_pattern and not (industry and __import__("re").search(m.industry_pattern, industry, __import__("re").I)):
                    continue
                hits[(sic, industry or "")] += 1
                tickers.append(ticker)
            rep.securities_matched = sum(hits.values())
            rep.data_descriptions = [(sic, desc, n) for (sic, desc), n in sorted(hits.items())]
            rep.example_tickers = sorted(tickers)[:8]
        assignments: dict[int, list[Assignment]] = {}
        cache: dict[tuple, list[Mapping]] = {}
        politicians: dict[int, set] = defaultdict(set)
        for pid, sic, industry in session.execute(select(Trade.politician_id, Security.sic_code, Security.industry).join(Security, Security.id == Trade.security_id)):
            review.trades_total += 1
            if pid not in assignments:
                assignments[pid] = load_assignments(session, pid)
            key = (pid, sic, industry)
            if key not in cache:
                cache[key] = matcher.applicable_rows(assignments[pid], sic, industry)
            found = cache[key]
            if not found:
                continue
            review.trades_with_match += 1
            if any(m.relevance_level == "direct" for m in found):
                review.trades_direct += 1
            else:
                review.trades_related_only += 1
            reports[found[0].id].trades_primary += 1
            for m in found:
                reports[m.id].trades_matched += 1
                politicians[m.id].add(pid)
        for mid, pids in politicians.items():
            reports[mid].politicians_matched = len(pids)
    _flag(review, reports)
    return review


def _flag(review: Review, reports: dict[int, RowReport]) -> None:
    live = [r for r in reports.values() if r.mapping.relevance_level != "none" and r.mapping.sic_start is not None]
    for rep in live:
        m = rep.mapping
        for other in live:
            o = other.mapping
            if o.committee_code != m.committee_code and o.sic_start <= m.sic_end and m.sic_start <= o.sic_end:
                label = f"{o.committee_code}{'/' + o.subcommittee_code if o.subcommittee_code else ''} {o.sic_range} ({o.relevance_level})"
                if label not in rep.overlaps:
                    rep.overlaps.append(label)
        groups: dict[str, list[str]] = defaultdict(list)
        for sic, desc, n in rep.data_descriptions:
            groups[sic[:3]].append(f"{sic} {desc} ({n})")
        rep.mixed_groups = dict(groups) if len(groups) >= 2 else {}
    for rep in reports.values():
        m = rep.mapping
        f = rep.flags
        if m.relevance_level != "none" and m.sic_start is not None:
            if m.sic_end - m.sic_start >= BROAD_WIDTH or len(rep.official_titles) >= BROAD_TITLES:
                f.append("broad_range")
            if rep.mixed_groups:
                f.append("mixed_industries")
        if not m.explicitly_verified:
            f.append("inferred_from_name")
        if m.relevance_level == "related":
            f.append("related_level")
        if rep.trades_matched >= MANY_TRADES:
            f.append("many_matches")
        if rep.overlaps:
            f.append("overlaps_other_committee")
        if (m.review_note or "").startswith("Review history"):
            f.append("false_positive_history")


# --- rendering ------------------------------------------------------------------------------------------------

def _summary(review: Review) -> dict:
    rows = review.rows
    live = [r for r in rows if r.mapping.relevance_level != "none"]
    return {
        "mapping_version": review.version,
        "mappings": len(rows),
        "direct": sum(r.mapping.relevance_level == "direct" for r in rows),
        "related": sum(r.mapping.relevance_level == "related" for r in rows),
        "none": sum(r.mapping.relevance_level == "none" for r in rows),
        "committee_level": sum(r.mapping.subcommittee_code is None for r in rows),
        "subcommittee_level": sum(r.mapping.subcommittee_code is not None for r in rows),
        "explicit_jurisdiction": sum(r.mapping.explicitly_verified for r in rows),
        "inferred_subcommittee_name": sum(r.mapping.jurisdiction_basis == "subcommittee_name" for r in rows),
        "inferred_committee_name": sum(r.mapping.jurisdiction_basis == "committee_name" for r in rows),
        "explicit_jurisdiction_non_none": sum(r.mapping.explicitly_verified for r in live),
        "needs_review": sum(r.mapping.review_status == "needs_review" for r in rows),
        "reviewed": sum(r.mapping.review_status == "reviewed" for r in rows),
        "trades_total": review.trades_total,
        "trades_with_any_match": review.trades_with_match,
        "trades_with_a_direct_match": review.trades_direct,
        "trades_with_related_only_matches": review.trades_related_only,
        "rows_flagged_for_scrutiny": sum(1 for r in rows if r.flags),
        "rows_with_a_priority_concern": sum(1 for r in rows if any(f in SUBSTANTIVE for f in r.flags)),
        "rows_matching_no_current_security": sum(1 for r in live if r.securities_matched == 0),
        "rows_matching_no_current_trade": sum(1 for r in live if r.trades_matched == 0),
    }


def _label(r: RowReport) -> str:
    m = r.mapping
    return f"{m.committee_name}" + (f" / {m.subcommittee_name}" if m.subcommittee_name else "")


def render_markdown(review: Review) -> str:
    s = _summary(review)
    out: list[str] = []
    w = out.append
    w(f"# Committee / industry mappings: review packet (version {review.version})\n")
    w("Generated from the mapping file and the current POLTRACKER securities, trades and committee seats. Nothing here is a finding about any "
      "politician or company. A mapping only says an industry is within an area plausibly relevant to a committee's jurisdiction.\n")
    w("**No row has been reviewed.** Every row is `needs_review` with an empty `reviewed_at`. To approve a row, edit "
      "`data/committee_industry_mappings.json`: set `review_status` to `reviewed`, `reviewed_at` to the approval time and `reviewed_by` to your name "
      "(all three together; the loader rejects anything else), then run `--sync`.\n")
    w("## Summary\n")
    w("| Measure | Count |\n|---|---|")
    for label, key in [("Mappings", "mappings"), ("direct", "direct"), ("related", "related"), ("none (reviewed as not industry-specific)", "none"),
                       ("committee-level / subcommittee-level", None), ("Explicit-jurisdiction mappings (official wording read)", "explicit_jurisdiction"),
                       ("Inferred from a subcommittee name", "inferred_subcommittee_name"), ("Inferred from a committee name only", "inferred_committee_name"),
                       ("Rows needing review / already reviewed", None), ("Trades in the data that have a security", "trades_total"),
                       ("Trades with at least one match", "trades_with_any_match"), ("Trades affected by a direct mapping", "trades_with_a_direct_match"),
                       ("Trades affected by related-only mappings", "trades_with_related_only_matches"), ("Rows flagged for any scrutiny reason", "rows_flagged_for_scrutiny"),
                       ("Rows with a priority concern (broad, mixed, many matches, earlier false positive)", "rows_with_a_priority_concern"),
                       ("Industry rows matching no current security", "rows_matching_no_current_security"),
                       ("Industry rows matching no current trade", "rows_matching_no_current_trade")]:
        if key:
            w(f"| {label} | {s[key]} |")
        elif label.startswith("committee-level"):
            w(f"| {label} | {s['committee_level']} / {s['subcommittee_level']} |")
        else:
            w(f"| {label} | {s['needs_review']} / {s['reviewed']} |")
    w("\n**Phase 3 policy:** only mappings that are both `reviewed` and `direct` may contribute to a contextual-review flag. `reviewed` + `related` is supporting context only. `needs_review` mappings never affect a flag. A trade has one committee-relevance signal with possibly several evidence records (see the docs).\n")

    live = [r for r in review.rows if r.mapping.relevance_level != "none"]
    w("## Top 20 mappings by number of affected trades\n")
    w("| # | Mapping | Level | Trades matched | Primary for | Securities | Politicians |\n|---|---|---|---|---|---|---|")
    for i, r in enumerate(sorted(live, key=lambda r: (-r.trades_matched, r.key))[:20], start=1):
        w(f"| {i} | {r.key}  ({_label(r)}) | {r.mapping.relevance_level} | {r.trades_matched} | {r.trades_primary} | {r.securities_matched} | {r.politicians_matched} |")

    w("\n## Rows that deserve extra scrutiny\n")
    w("Why a row is flagged:\n")
    for k, v in FLAG_TEXT.items():
        w(f"- `{k}`: {v}")
    priority = [r for r in review.rows if any(f in SUBSTANTIVE for f in r.flags)]
    w(f"\n### Priority: rows with a substantive concern ({len(priority)})\n")
    w("Broad ranges, ranges mixing industry groups, rows matching many trades, and rows adjusted after an earlier false positive.\n")
    w("| Row | Level | Reasons | Trades matched | Securities |\n|---|---|---|---|---|")
    for r in sorted(priority, key=lambda r: (-sum(f in SUBSTANTIVE for f in r.flags), -r.trades_matched, r.key)):
        w(f"| {r.key} ({_label(r)}) | {r.mapping.relevance_level} | {', '.join(r.flags)} | {r.trades_matched} | {r.securities_matched} |")
    routine = [r for r in review.rows if r.flags and r not in priority]
    w(f"\n### Routine: flagged only for name inference, related level or overlap ({len(routine)})\n")
    w("These are flagged in their entries below. The first group applies to nearly every subcommittee row, so it is not repeated here.\n")

    w("## SIC ranges that capture more than one industry group among current securities\n")
    w("Grouped by the first three digits of the SIC code (a SIC industry group). Whether the groups are *materially* different is for the reviewer to judge.\n")
    mixed = [r for r in live if r.mixed_groups]
    if not mixed:
        w("None.\n")
    for r in sorted(mixed, key=lambda r: (-len(r.mixed_groups), r.key)):
        w(f"- **{r.key}** ({_label(r)}): " + "; ".join(f"[{g}] " + ", ".join(d) for g, d in sorted(r.mixed_groups.items())))

    w("\n## Review entries, by committee and subcommittee\n")
    by_committee: dict[str, list[RowReport]] = defaultdict(list)
    for r in review.rows:
        by_committee[r.mapping.committee_code].append(r)
    for code in sorted(by_committee):
        rows = sorted(by_committee[code], key=lambda r: (r.mapping.subcommittee_code is not None, r.mapping.subcommittee_name or "", r.mapping.sic_start or 0))
        w(f"\n### {code}: {rows[0].mapping.committee_name}\n")
        for r in rows:
            m = r.mapping
            scope = f"subcommittee {m.subcommittee_code} ({m.subcommittee_name})" if m.subcommittee_code else "committee level"
            basis = "explicitly verified (official wording read)" if m.explicitly_verified else "inferred from the " + ("subcommittee" if m.jurisdiction_basis == "subcommittee_name" else "committee") + " name, not verified"
            w(f"#### `{r.key}`  {m.relevance_level}  |  {m.review_status}\n")
            w(f"- **Scope:** {scope}")
            w(f"- **SIC range:** {m.sic_range or 'none (reviewed as having no industry-specific jurisdiction)'}")
            if r.official_titles:
                shown = "; ".join(f"{c} {t}" for c, t in r.official_titles[:12]) + (f"; +{len(r.official_titles) - 12} more" if len(r.official_titles) > 12 else "")
                w(f"- **Official SIC titles covered:** {shown}")
            elif m.sic_start is not None:
                w("- **Official SIC titles covered:** none in the SEC table (the SEC lists only codes assigned to registrants)")
            w(f"- **Rationale:** {m.rationale}")
            w(f"- **Official jurisdiction wording used:** {m.jurisdiction_text or 'none recorded'}")
            w(f"- **Citation / source:** {m.source_citation or 'none'}  <{m.source_url}>")
            w(f"- **Jurisdiction basis:** `{m.jurisdiction_basis}`: {basis}")
            if m.sic_start is not None:
                descs = ", ".join(f"{sic} {d or '(no description)'} x{n}" for sic, d, n in r.data_descriptions) or "no current security in this range"
                w(f"- **In POLTRACKER data:** {r.securities_matched} securities ({descs})")
                tick = (" Examples: " + ", ".join(r.example_tickers) + ".") if r.example_tickers else ""
                w(f"- **Trades matched:** {r.trades_matched} by {r.politicians_matched} politician{'' if r.politicians_matched == 1 else 's'} (primary match for {r.trades_primary}).{tick}")
            if r.overlaps:
                w(f"- **Overlaps other committees:** {'; '.join(r.overlaps)}")
            if r.flags:
                w(f"- **Scrutiny:** " + "; ".join(f"`{f}`" for f in r.flags))
            if m.review_note:
                w(f"- **Review note:** {m.review_note}")
            w(f"- **Decision:** [ ] approve   [ ] change   [ ] remove\n")
    return "\n".join(out) + "\n"


# --- the priority-row review table ------------------------------------------------------------------------------

ACTIONS = ("APPROVE DIRECT", "DOWNGRADE TO RELATED", "SPLIT RANGE", "REMOVE", "NEEDS MORE SOURCE REVIEW", "KEEP RELATED")
DIRECT_ONLY = ("APPROVE DIRECT", "DOWNGRADE TO RELATED", "SPLIT RANGE")  # these only make sense for a row that is currently direct
LEVEL_ORDER = {"direct": 0, "related": 1, "none": 2}


class RecommendationError(ValueError):
    pass


def priority_rows(review: Review) -> list[RowReport]:
    """The rows with a substantive concern, ordered: direct before related, most trades first, broad/mixed first, then key."""
    rows = [r for r in review.rows if any(f in SUBSTANTIVE for f in r.flags)]
    return sorted(rows, key=lambda r: (LEVEL_ORDER[r.mapping.relevance_level], -r.trades_matched, -(("broad_range" in r.flags) + ("mixed_industries" in r.flags)), r.key))


def load_recommendations(path: Path) -> dict[str, dict]:
    try:
        items = json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise RecommendationError(f"cannot read {path}: {exc}") from exc
    if not isinstance(items, list):
        raise RecommendationError("recommendations must be a JSON list")
    out: dict[str, dict] = {}
    for i, it in enumerate(items, start=1):
        if not isinstance(it, dict) or not it.get("key") or not str(it.get("reason") or "").strip():
            raise RecommendationError(f"recommendation {i}: needs key and reason")
        if it.get("action") not in ACTIONS:
            raise RecommendationError(f"recommendation {i}: action must be one of {ACTIONS}")
        if it["key"] in out:
            raise RecommendationError(f"recommendation {i}: duplicate key {it['key']}")
        out[it["key"]] = it
    return out


def validate_recommendations(review: Review, recs: dict[str, dict]) -> None:
    """Exactly one recommendation per priority row, and an action that fits the row's current level. Mappings are never touched."""
    rows = {r.key: r for r in priority_rows(review)}
    if missing := sorted(set(rows) - set(recs)):
        raise RecommendationError(f"no recommendation for: {', '.join(missing)}")
    if extra := sorted(set(recs) - set(rows)):
        raise RecommendationError(f"recommendation for a row that is not a priority row: {', '.join(extra)}")
    for key, rec in recs.items():
        level = rows[key].mapping.relevance_level
        if rec["action"] in DIRECT_ONLY and level != "direct":
            raise RecommendationError(f"{key}: {rec['action']} only applies to a direct row")
        if rec["action"] == "KEEP RELATED" and level != "related":
            raise RecommendationError(f"{key}: KEEP RELATED only applies to a related row")


_CLAUSE = re.compile(r"Rule X,? (?:clause )?1\([a-z]\)((?:\(\d+\)(?:,\s*)?)+)")


def clause_wording(m: Mapping, limit: int = 300) -> str:
    """The specific official clauses the rationale cites, quoted from the recorded jurisdiction text."""
    text = m.jurisdiction_text or ""
    items = {n: t.strip() for n, t in re.findall(r"\((\d+)\)\s*(.*?)(?=\s*\(\d+\)\s|$)", text, flags=re.S)}
    numbers = [n for group in _CLAUSE.findall(f"{m.rationale or ''} {m.source_citation or ''}") for n in re.findall(r"\((\d+)\)", group)]
    picked = [f"({n}) {items[n]}" for n in dict.fromkeys(numbers) if n in items]
    wording = " ".join(picked) if picked else (text[:limit] or "none recorded")
    if m.jurisdiction_basis == "subcommittee_name":
        wording += " [committee wording; the subcommittee's scope is inferred from its name]"
    elif m.jurisdiction_basis == "committee_published_text":
        wording += " [subcommittee text published by the committee]"
    return wording if len(wording) <= limit + 70 else wording[:limit].rstrip() + "..."


def _cell(text: str, limit: int | None = None) -> str:
    text = " ".join(str(text).split()).replace("|", "/")
    return text if limit is None or len(text) <= limit else text[: limit - 3].rstrip() + "..."


def render_priority_table(review: Review, recs: dict[str, dict]) -> str:
    validate_recommendations(review, recs)
    rows = priority_rows(review)
    counts = {a: sum(1 for r in rows if recs[r.key]["action"] == a) for a in ACTIONS}
    out = [
        f"# Priority rows: review table (mapping version {review.version})\n",
        f"{len(rows)} rows with a substantive concern, ordered direct before related, then most trades matched, then broad/mixed ranges first. "
        "**Nothing here changes a mapping.** Each recommendation is a proposal for a person to accept or reject; every row stays `needs_review`.\n",
        "Phase 3 policy these recommendations are written against: only `reviewed` + `direct` mappings may contribute to a contextual-review flag, so a direct "
        "row must be squarely within the committee's jurisdiction and narrow enough that an industry match means something. `KEEP RELATED` is an addition to the "
        "requested actions, needed because a related row has nothing to 'approve direct'.\n",
        "| Action | Rows |",
        "|---|---|",
        *[f"| {a} | {n} |" for a, n in counts.items() if n],
        "",
        "| # | Committee / subcommittee | SIC range | SIC titles covered (current securities) | Level | Basis | Official wording | Trades | Example tickers | Overlaps | Recommended action | Why |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, start=1):
        m = r.mapping
        titles = "; ".join(f"{sic} {d} ({n})" for sic, d, n in r.data_descriptions[:6]) + (f"; +{len(r.data_descriptions) - 6} more" if len(r.data_descriptions) > 6 else "")
        where = m.committee_name + (f" / {m.subcommittee_name}" if m.subcommittee_name else "")
        flag = " (broad)" if "broad_range" in r.flags else ""
        out.append("| " + " | ".join([
            str(i), _cell(f"{m.committee_code}{'/' + m.subcommittee_code if m.subcommittee_code else ''} {where}", 90), f"{m.sic_range}{flag}", _cell(titles or "none", 200),
            m.relevance_level, m.jurisdiction_basis or "", _cell(clause_wording(m), 330), f"{r.trades_matched} ({r.politicians_matched} pol.)",
            ", ".join(r.example_tickers[:6]), _cell("; ".join(r.overlaps) or "none", 160), f"**{recs[r.key]['action']}**", _cell(recs[r.key]["reason"], 420)]) + " |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the human-review packet for the committee/industry mappings (read-only)")
    parser.add_argument("--file", type=Path, default=DATA / "committee_industry_mappings.json")
    parser.add_argument("--sic", type=Path, default=DATA / "sic_codes.json")
    parser.add_argument("--out", type=Path, help="write the Markdown packet here (default: stdout)")
    parser.add_argument("--json", type=Path, help="also write the per-row numbers as JSON")
    parser.add_argument("--priority-table", type=Path, help="write the compact priority-row review table here (needs --recommendations)")
    parser.add_argument("--recommendations", type=Path, help="JSON list of {key, action, reason} for exactly the priority rows")
    args = parser.parse_args(argv)
    rows = load_rows(args.file)
    sic = json.loads(args.sic.read_text())["codes"]
    review = build_review(make_session_factory(), rows, sic)
    if args.priority_table:
        if not args.recommendations:
            parser.error("--priority-table needs --recommendations")
        try:
            table = render_priority_table(review, load_recommendations(args.recommendations))
        except RecommendationError as exc:
            print(f"Recommendations rejected: {exc}")
            return 1
        args.priority_table.parent.mkdir(parents=True, exist_ok=True)
        args.priority_table.write_text(table)
        print(f"Wrote {args.priority_table}")
    text = render_markdown(review)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"Wrote {args.out} ({len(review.rows)} rows)")
    else:
        print(text)
    if args.json:
        payload = {"summary": _summary(review), "rows": [
            {"key": r.key, "committee": r.mapping.committee_code, "subcommittee": r.mapping.subcommittee_code, "level": r.mapping.relevance_level,
             "basis": r.mapping.jurisdiction_basis, "review_status": r.mapping.review_status, "securities_matched": r.securities_matched,
             "trades_matched": r.trades_matched, "trades_primary": r.trades_primary, "politicians_matched": r.politicians_matched, "flags": r.flags,
             "overlaps": r.overlaps} for r in review.rows]}
        args.json.write_text(json.dumps(payload, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
