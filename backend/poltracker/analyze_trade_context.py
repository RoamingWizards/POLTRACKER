"""Compute deterministic trade context signals and store them.   python -m poltracker.analyze_trade_context

Reads trades, politicians' committee seats, securities' SIC codes, the committee/industry mappings and the locally cached price bars.
Makes no network request and uses no language model. Safe to rerun: a trade whose result is unchanged is left alone, a changed one is updated
in place, and results of another context version or mapping version are never touched. Writes only trade_context and trade_context_evidence.
"""

import argparse
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from bisect import insort

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .committee_industry import CommitteeIndustryMatcher, load_assignments, load_mappings
from .config import get_settings
from .db import make_session_factory
from .models import Politician, Security, Trade, TradeContext, TradeContextEvidence
from .performance import PriceSeries, load_benchmark, load_series, transaction_date_problem
from .trade_context import ContextConfig, ContextResult, TradeInput, analyze_trade, trade_size_value


class AnalysisError(Exception):
    pass


def _tri(counter: Counter) -> str:
    return f"true {counter[True]:,} / false {counter[False]:,} / unknown {counter[None]:,}"


@dataclass
class AnalysisSummary:
    context_version: str
    mapping_version: str | None
    dry_run: bool
    evaluated: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    committee: Counter = field(default_factory=Counter)
    size: Counter = field(default_factory=Counter)
    delay: Counter = field(default_factory=Counter)
    excess: Counter = field(default_factory=Counter)
    flagged: int = 0
    flagged_politicians: set = field(default_factory=set)
    flagged_tickers: set = field(default_factory=set)
    committee_unknown_reasons: Counter = field(default_factory=Counter)
    needs_review_matches_ignored: int = 0  # trades with a needs_review mapping that was deliberately not used
    results: list[ContextResult] = field(default_factory=list, repr=False)

    def to_text(self) -> str:
        n = lambda v: f"{v:,}"  # noqa: E731
        lines = [
            f"Context version {self.context_version}, mapping version {self.mapping_version}" + ("  [DRY RUN: nothing was written]" if self.dry_run else ""),
            f"Trades evaluated: {n(self.evaluated)}  (new {n(self.inserted)}, updated {n(self.updated)}, unchanged {n(self.unchanged)})",
            f"Committee relevance (reviewed + direct): {_tri(self.committee)}",
            f"Trade-size anomalies: {_tri(self.size)}",
            f"Long disclosure delays: {_tri(self.delay)}",
            f"Large excess returns: {_tri(self.excess)}",
            f"Flagged for contextual review: {n(self.flagged)}  ({n(len(self.flagged_politicians))} politicians, {n(len(self.flagged_tickers))} tickers)",
            f"Committee relevance unknown because: " + (", ".join(f"{k} {n(v)}" for k, v in self.committee_unknown_reasons.most_common()) or "none"),
            f"Trades with a needs_review mapping that was ignored: {n(self.needs_review_matches_ignored)}",
        ]
        return "\n".join(lines)


class TradeContextAnalyzer:
    def __init__(self, session_factory: sessionmaker[Session], config: ContextConfig | None = None, today: date | None = None, mapping_version: str | None = None):
        self.factory = session_factory
        self.config = config or ContextConfig(benchmark=get_settings().benchmark_ticker)
        self.today = today or date.today()
        self.mapping_version = mapping_version

    def run(self, *, dry_run: bool = False, force: bool = False, limit: int | None = None, trade_ids: list[int] | None = None,
            politician: str | None = None, ticker: str | None = None) -> AnalysisSummary:
        cfg = self.config
        version = cfg.version_label()
        with self.factory() as session:
            mappings = load_mappings(session, self.mapping_version)
            if not mappings:
                raise AnalysisError("no committee/industry mappings are loaded; run python -m poltracker.committee_industry_report --sync first")
            matcher = CommitteeIndustryMatcher(mappings, self.mapping_version)
            summary = AnalysisSummary(version, matcher.version, dry_run)

            stmt = (select(Trade, Security.sic_code, Security.industry).join(Security, Security.id == Trade.security_id, isouter=True).order_by(Trade.id))
            if trade_ids:
                stmt = stmt.where(Trade.id.in_(trade_ids))
            if ticker:
                stmt = stmt.where(Trade.ticker == ticker.upper())
            if politician:
                if politician.isdigit():
                    stmt = stmt.where(Trade.politician_id == int(politician))
                else:
                    stmt = stmt.where(Trade.politician_id.in_(select(Politician.id).where(Politician.name.ilike(f"%{politician}%"))))
            if limit:
                stmt = stmt.limit(limit)
            targets = [(TradeInput(t.id, t.politician_id, t.ticker, t.transaction_type, t.transaction_date, t.disclosure_date, t.amount_min, t.amount_max, sic, industry))
                       for t, sic, industry in session.execute(stmt)]
            if not targets:
                return summary

            # earlier-trade sizes per politician: every trade of that politician (not just the selected ones), valid dates and a usable range only
            history: dict[int, list[tuple[date, float]]] = {}
            for pid, tx, disc, lo, hi in session.execute(
                select(Trade.politician_id, Trade.transaction_date, Trade.disclosure_date, Trade.amount_min, Trade.amount_max)
                .where(Trade.politician_id.in_({t.politician_id for t in targets}))
            ):
                value, _ = trade_size_value(lo, hi)
                if value is not None and transaction_date_problem(tx, disc, self.today) is None:
                    history.setdefault(pid, []).append((tx, value))
            for rows in history.values():
                rows.sort()

            existing = {
                c.trade_id: c for c in session.scalars(
                    select(TradeContext).where(TradeContext.context_version == version, TradeContext.mapping_version == matcher.version,
                                               TradeContext.trade_id.in_([t.id for t in targets]))
                )
            }
            assignments: dict[int, list] = {}
            series_cache: dict[str, PriceSeries] = {}
            benchmark = load_benchmark(session, cfg.benchmark)
            sec_ids = {tk: sid for tk, sid in session.execute(select(Security.ticker, Security.id)).all()}
            now = datetime.now(UTC).replace(tzinfo=None)

            # process each politician's targets in date order so the earlier-trades list only ever grows
            by_pol: dict[int, list[TradeInput]] = {}
            for t in targets:
                by_pol.setdefault(t.politician_id, []).append(t)
            for pid, trades in by_pol.items():
                if pid not in assignments:
                    assignments[pid] = load_assignments(session, pid)
                prior: list[float] = []
                hist = history.get(pid, [])
                pos = 0
                for t in sorted(trades, key=lambda x: (x.transaction_date, x.id)):
                    while pos < len(hist) and hist[pos][0] < t.transaction_date:
                        insort(prior, hist[pos][1])
                        pos += 1
                    series = None
                    if t.ticker and t.ticker in sec_ids:
                        if t.ticker not in series_cache:
                            series_cache[t.ticker] = load_series(session, sec_ids[t.ticker])
                        series = series_cache[t.ticker]
                    res = analyze_trade(t, matcher=matcher, assignments=assignments[pid], prior_sizes_sorted=prior, series=series, benchmark=benchmark, cfg=cfg, today=self.today)
                    self._count(summary, t, res)
                    digest = res.digest(version)
                    row = existing.get(t.id)
                    if row is None:
                        summary.inserted += 1
                        if not dry_run:
                            self._write(session, TradeContext(trade_id=t.id, context_version=version, mapping_version=matcher.version), res, digest, now, cfg.excess_horizon_days)
                    elif force or row.result_digest != digest:
                        summary.updated += 1
                        if not dry_run:
                            self._write(session, row, res, digest, now, cfg.excess_horizon_days)
                    else:
                        summary.unchanged += 1
            if dry_run:
                session.rollback()
            else:
                session.commit()
            return summary

    @staticmethod
    def _count(summary: AnalysisSummary, t: TradeInput, res: ContextResult) -> None:
        summary.evaluated += 1
        summary.committee[res.committee.value] += 1
        summary.size[res.size.anomaly] += 1
        summary.delay[res.delay] += 1
        summary.excess[res.excess] += 1
        if res.committee.value is None:
            summary.committee_unknown_reasons[res.committee.reason] += 1
        if res.committee.pending_review:
            summary.needs_review_matches_ignored += 1
        if res.flagged:
            summary.flagged += 1
            summary.flagged_politicians.add(t.politician_id)
            if t.ticker:
                summary.flagged_tickers.add(t.ticker)
        summary.results.append(res)

    @staticmethod
    def _write(session: Session, row: TradeContext, res: ContextResult, digest: str, now: datetime, horizon_days: int) -> None:
        leg = res.perf.transaction
        row.result_digest = digest
        row.analyzed_at = now
        row.committee_relevance = res.committee.value
        row.committee_relevance_reason = res.committee.reason
        row.trade_size_anomaly = res.size.anomaly
        row.disclosure_delay_signal = res.delay
        row.excess_return_signal = res.excess
        row.trade_size_value, row.trade_size_basis = res.size.value, res.size.basis
        row.trade_size_percentile, row.trade_size_sample_size, row.trade_size_median = res.size.percentile, res.size.sample_size, res.size.median
        row.disclosure_delay_days = res.delay_days
        row.performance_status = res.perf.status
        row.security_return = leg.return_ if leg else None
        row.spy_return = leg.benchmark_return if leg else None
        row.excess_return = leg.excess_return if leg else None
        row.excess_return_direction_adjusted = res.perf.direction_adjusted.get("transaction_excess_return")
        row.performance_anchor_date = leg.anchor_date if leg else None
        measured = leg is not None and leg.excess_return is not None
        row.performance_horizon_days = horizon_days if measured else None
        row.performance_through_date = leg.anchor_date + timedelta(days=horizon_days) if measured else None
        row.signal_count = res.count
        row.flagged_for_contextual_review = res.flagged
        if row.id is None:
            session.add(row)
            session.flush()
        else:
            row.evidence.clear()
            session.flush()
        for e in res.evidence:
            row.evidence.append(TradeContextEvidence(
                trade_id=row.trade_id, signal_type=e.signal_type, evidence_type=e.evidence_type, evidence_key=e.evidence_key,
                committee_code=e.committee_code, subcommittee_code=e.subcommittee_code or None, mapping_id=e.mapping_id, source_url=e.source_url,
                description=e.description, metadata_json=json.dumps(e.metadata, sort_keys=True, default=str) if e.metadata else None))
        session.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute deterministic trade context signals (local data only; no network, no AI)")
    parser.add_argument("--dry-run", action="store_true", help="compute and summarise, write nothing")
    parser.add_argument("--force", action="store_true", help="rewrite rows even when their result is unchanged")
    parser.add_argument("--limit", type=int, help="analyze at most N trades (lowest ids first)")
    parser.add_argument("--trade-id", type=int, action="append", help="analyze this trade (repeatable)")
    parser.add_argument("--politician", help="politician id, or part of a name")
    parser.add_argument("--ticker")
    parser.add_argument("--mapping-version", help="committee/industry mapping version (default: the most recently loaded)")
    defaults = ContextConfig()
    parser.add_argument("--delay-days", type=int, default=defaults.delay_days)
    parser.add_argument("--excess-return", type=float, default=defaults.excess_return, help="absolute excess-return threshold as a fraction (0.10 = 10 points)")
    parser.add_argument("--excess-horizon-days", type=int, default=defaults.excess_horizon_days, help="measure excess return over this many days from the transaction anchor")
    parser.add_argument("--size-percentile", type=float, default=defaults.size_percentile)
    parser.add_argument("--min-history", type=int, default=defaults.min_history)
    args = parser.parse_args(argv)
    cfg = ContextConfig(args.delay_days, args.excess_return, args.size_percentile, args.excess_horizon_days, args.min_history, get_settings().benchmark_ticker)
    analyzer = TradeContextAnalyzer(make_session_factory(), cfg, mapping_version=args.mapping_version)
    try:
        summary = analyzer.run(dry_run=args.dry_run, force=args.force, limit=args.limit, trade_ids=args.trade_id, politician=args.politician, ticker=args.ticker)
    except AnalysisError as exc:
        print(f"Cannot analyze: {exc}")
        return 1
    print(summary.to_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
