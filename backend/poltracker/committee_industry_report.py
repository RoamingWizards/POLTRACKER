"""Measure committee/industry relevance over existing trades, read-only.   python -m poltracker.committee_industry_report

`--sync` loads the mapping file into committee_industry_mappings (the only write). `--report` evaluates every trade against its politician's
committee seats and its security's SIC code and prints counts and examples. It stores nothing per trade and flags nothing: the result is a
context measurement for review, not a finding about anyone.
"""

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from .committee_industry import (
    CommitteeIndustryMatcher, MappingError, load_assignments, load_mappings, sync_mappings,
)
from .db import make_session_factory
from .models import CommitteeAssignment, Politician, Security, Trade

DEFAULT_FILE = Path(__file__).resolve().parents[2] / "data" / "committee_industry_mappings.json"

# Industry groups used only to organise examples in the report (not used by the matcher).
GROUPS = {
    "defense": [(3480, 3489), (3720, 3769), (3795, 3795), (3812, 3812)],
    "finance": [(6000, 6499)],
    "healthcare": [(2833, 2836), (3841, 3845), (8000, 8099)],
    "energy": [(1200, 1399), (2911, 2911), (4911, 4939)],
    "transportation": [(4011, 4599), (3743, 3743)],
}


def group_of(sic: int | None) -> str | None:
    for name, ranges in GROUPS.items():
        if sic is not None and any(a <= sic <= b for a, b in ranges):
            return name
    return None


@dataclass
class RelevanceReport:
    version: str | None = None
    securities_with_sic: int = 0
    securities_total: int = 0
    politicians_total: int = 0
    politicians_with_assignments: int = 0
    trades_total: int = 0
    trades_no_security: int = 0
    evaluable: int = 0  # relevant or not_relevant: a deterministic answer exists
    relevant: int = 0
    relevant_direct: int = 0  # the best match is direct
    relevant_related_only: int = 0
    not_relevant: int = 0
    unknown_no_sic: int = 0
    unknown_no_assignments: int = 0
    unknown_unmapped: int = 0
    unmapped_committees: Counter = field(default_factory=Counter)  # committee name -> trades left unknown by it
    by_committee: Counter = field(default_factory=Counter)  # committee (or subcommittee) -> trades it matched as primary
    examples: dict[str, list[dict]] = field(default_factory=lambda: defaultdict(list))

    def to_text(self) -> str:
        n = lambda v: f"{v:,}"  # noqa: E731
        lines = [
            f"Mapping version: {self.version}",
            f"Securities with usable SIC data: {n(self.securities_with_sic)} of {n(self.securities_total)}",
            f"Politicians with committee assignments: {n(self.politicians_with_assignments)} of {n(self.politicians_total)}",
            f"Trades: {n(self.trades_total)} (no security: {n(self.trades_no_security)})",
            f"  evaluable (deterministic answer): {n(self.evaluable)}",
            f"    relevant (at least one match): {n(self.relevant)}   of which best match direct: {n(self.relevant_direct)}, related only: {n(self.relevant_related_only)}",
            f"    not relevant: {n(self.not_relevant)}",
            f"  unknown, no SIC data: {n(self.unknown_no_sic)}",
            f"  unknown, politician has no committee assignments: {n(self.unknown_no_assignments)}",
            f"  unknown, a committee is unmapped: {n(self.unknown_unmapped)}",
        ]
        return "\n".join(lines)


def evaluate_trades(session_factory: sessionmaker[Session], version: str | None = None, examples_per_group: int = 6) -> RelevanceReport:
    report = RelevanceReport()
    with session_factory() as session:
        matcher = CommitteeIndustryMatcher(load_mappings(session, version), version)
        report.version = matcher.version
        report.securities_total = session.scalar(select(func.count(Security.id)).where(Security.id.in_(select(Trade.security_id).where(Trade.security_id.is_not(None))))) or 0
        report.securities_with_sic = session.scalar(select(func.count(Security.id)).where(Security.sic_code.is_not(None), Security.id.in_(select(Trade.security_id).where(Trade.security_id.is_not(None))))) or 0
        report.politicians_total = session.scalar(select(func.count(Politician.id))) or 0
        report.politicians_with_assignments = session.scalar(select(func.count(func.distinct(CommitteeAssignment.politician_id)))) or 0
        assignments: dict[int, list] = {}
        cache: dict[tuple, object] = {}
        stmt = (select(Trade.id, Trade.politician_id, Trade.politician_name, Trade.ticker, Trade.transaction_type, Trade.transaction_date, Security.sic_code, Security.industry)
                .join(Security, Security.id == Trade.security_id, isouter=True).order_by(Trade.id))
        for tid, pid, pname, ticker, ttype, tdate, sic, industry in session.execute(stmt):
            report.trades_total += 1
            if pid not in assignments:
                assignments[pid] = load_assignments(session, pid)
            key = (pid, sic, industry)
            if key not in cache:
                cache[key] = matcher.evaluate(assignments[pid], sic, industry)
            rel = cache[key]
            if rel.status == "relevant":
                report.evaluable += 1
                report.relevant += 1
                report.relevant_direct += rel.level == "direct"
                report.relevant_related_only += rel.level == "related"
                p = rel.primary
                report.by_committee[f"{p.committee_code} {p.subcommittee_name or p.committee_name} [{p.scope}]"] += 1
                group = group_of(int(sic)) if sic else None
                if group and len(report.examples[group]) < examples_per_group * 10:
                    report.examples[group].append({"trade_id": tid, "politician": pname, "ticker": ticker, "sic": sic, "industry": industry, "type": ttype,
                                                   "date": str(tdate), "level": p.level, "committee": p.subcommittee_name or p.committee_name,
                                                   "scope": p.scope, "sic_range": p.sic_range, "rationale": p.rationale[:160]})
            elif rel.status == "not_relevant":
                report.evaluable += 1
                report.not_relevant += 1
            elif rel.reason == "no_sic":
                report.unknown_no_sic += 1
            elif rel.reason == "no_committee_assignments":
                report.unknown_no_assignments += 1
            else:
                report.unknown_unmapped += 1
                for name in rel.unmapped_committees:
                    report.unmapped_committees[name] += 1
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Committee/industry mappings: load them, or measure relevance over existing trades (read-only)")
    parser.add_argument("--sync", nargs="?", const=str(DEFAULT_FILE), metavar="FILE", help="load the mapping file (default data/committee_industry_mappings.json)")
    parser.add_argument("--report", action="store_true", help="evaluate every trade and print counts (writes nothing)")
    parser.add_argument("--version", help="mapping version to evaluate (default: the most recently loaded)")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)
    factory = make_session_factory()
    if args.sync:
        with factory() as session:
            try:
                version, count = sync_mappings(session, Path(args.sync))
                session.commit()
            except MappingError as exc:
                session.rollback()
                print(f"Mappings rejected, nothing was loaded: {exc}")
                return 1
        print(f"Loaded {count} mappings, version {version}.")
    if args.report:
        report = evaluate_trades(factory, args.version)
        if args.json:
            print(json.dumps({"summary": report.__dict__ | {"unmapped_committees": dict(report.unmapped_committees), "by_committee": dict(report.by_committee)}}, default=str, indent=1))
        else:
            print(report.to_text())
            print("\nTop committees by trades matched:")
            for name, k in report.by_committee.most_common(15):
                print(f"  {k:>5}  {name}")
            if report.unmapped_committees:
                print("\nCommittees with no mapping that left trades unknown:")
                for name, k in report.unmapped_committees.most_common(10):
                    print(f"  {k:>5}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
