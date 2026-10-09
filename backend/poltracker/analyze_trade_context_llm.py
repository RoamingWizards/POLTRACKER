"""OpenAI-written explanations of stored trade context.   python -m poltracker.analyze_trade_context_llm

Reads the deterministic `trade_context` rows and sends one trade's structured facts at a time to OpenAI, which returns a short neutral explanation. The model
decides nothing: it cannot change a signal or the flag, and this module never writes to `trade_context`. Its answer is validated against the facts it was given
(trade_context_llm.validate_explanation) and cached in `trade_context_analysis`. Only flagged trades by default; at most `--limit` API calls per run (default 25).
Safe to rerun: a trade whose facts, model and prompt are unchanged is served from the cache without a call.
"""

import argparse
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings, get_settings
from .db import make_session_factory
from .models import CommitteeAssignment, CommitteeIndustryMapping, Politician, Security, Trade, TradeContext, TradeContextAnalysis
from .trade_context import ContextConfig
from .trade_context_llm import (
    PROMPT_VERSION, Explainer, ExplanationError, ExplanationRejected, build_explainer, build_facts, input_hash, validate_explanation,
)


@dataclass
class ItemResult:
    trade_id: int
    ticker: str | None
    politician: str
    flagged: bool
    status: str  # cached | generated | would_generate | rejected | error | over_limit | unavailable
    facts: dict | None = None
    explanation: dict | None = None
    reasons: list[str] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass
class RunSummary:
    model: str
    prompt_version: str
    context_version: str | None
    mapping_version: str | None
    dry_run: bool
    max_calls: int
    selected: int = 0
    cached: int = 0
    generated: int = 0
    would_generate: int = 0
    rejected: int = 0
    errors: int = 0
    over_limit: int = 0
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    estimated_cost_usd: float | None = None
    aborted: str | None = None
    items: list[ItemResult] = field(default_factory=list, repr=False)

    def to_text(self) -> str:
        cost = f"about ${self.estimated_cost_usd:.4f} (at the configured rates)" if self.estimated_cost_usd is not None else \
            "not estimated (set POLTRACKER_TRADE_LLM_INPUT_USD_PER_MTOK and POLTRACKER_TRADE_LLM_OUTPUT_USD_PER_MTOK)"
        lines = [
            f"Model {self.model}, prompt version {self.prompt_version}, context {self.context_version} / mapping {self.mapping_version}" + ("  [dry run: no OpenAI call]" if self.dry_run else ""),
            f"Trades selected: {self.selected:,}",
            f"  served from cache: {self.cached:,}",
            f"  generated and validated: {self.generated:,}" + (f"   would generate: {self.would_generate:,}" if self.dry_run else ""),
            f"  rejected by validation (not stored): {self.rejected:,}",
            f"  errors (not stored): {self.errors:,}",
            f"  skipped, call limit {self.max_calls} reached: {self.over_limit:,}",
            f"OpenAI calls: {self.calls:,}  input tokens: {self.tokens_in:,}  output tokens: {self.tokens_out:,}  estimated cost: {cost}",
        ]
        if self.aborted:
            lines.append(f"Run stopped early: {self.aborted}")
        for it in self.items:
            if it.status in ("rejected", "error"):
                lines.append(f"  trade {it.trade_id} {it.ticker or ''} {it.status}: " + "; ".join(it.reasons))
        return "\n".join(lines)


class TradeContextExplanationService:
    """Never decides anything and never writes `trade_context`: it reads a context row, asks for an explanation, validates it, and caches it."""

    def __init__(self, session_factory: sessionmaker[Session], explainer: Explainer | None, *, model: str, max_calls: int = 25,
                 input_usd_per_mtok: float | None = None, output_usd_per_mtok: float | None = None, now=None):
        self._sf, self._explainer, self.model, self.max_calls = session_factory, explainer, model, max_calls
        self._rates = (input_usd_per_mtok, output_usd_per_mtok)
        self._now = now or (lambda: datetime.now(UTC).replace(tzinfo=None))

    @classmethod
    def from_settings(cls, session_factory, settings: Settings, explainer: Explainer | None, **kw):
        return cls(session_factory, explainer, model=settings.trade_llm_model, max_calls=settings.trade_llm_max_calls,
                   input_usd_per_mtok=settings.trade_llm_input_usd_per_mtok, output_usd_per_mtok=settings.trade_llm_output_usd_per_mtok, **kw)

    def run(self, *, trade_ids: list[int] | None = None, ticker: str | None = None, politician: str | None = None, flagged_only: bool = True,
            limit: int | None = None, force: bool = False, dry_run: bool = False) -> RunSummary:
        max_calls = self.max_calls if limit is None else limit
        with self._sf() as session:
            key = self._context_key(session)
            summary = RunSummary(self.model, PROMPT_VERSION, key[0], key[1], dry_run, max_calls)
            if key[1] is None:
                summary.aborted = "no committee/industry mapping is loaded, so there is no trade context"
                return summary
            known = self._known_committees(session)
            for ctx in self._select(session, key, trade_ids, ticker, politician, flagged_only):
                summary.selected += 1
                trade = session.get(Trade, ctx.trade_id)
                pol = session.get(Politician, trade.politician_id)
                security = session.get(Security, trade.security_id) if trade.security_id else None
                facts = build_facts(trade=trade, politician=pol, security=security, context=ctx, evidence=ctx.evidence)
                item = ItemResult(trade.id, trade.ticker, pol.name, bool(ctx.flagged_for_contextual_review), "", facts)
                summary.items.append(item)
                digest = input_hash(facts, self.model, PROMPT_VERSION)
                row = session.scalar(select(TradeContextAnalysis).where(
                    TradeContextAnalysis.trade_id == trade.id, TradeContextAnalysis.context_version == key[0], TradeContextAnalysis.mapping_version == key[1],
                    TradeContextAnalysis.prompt_version == PROMPT_VERSION, TradeContextAnalysis.model == self.model))
                if row is not None and row.input_hash == digest and not force:
                    item.status, item.explanation = "cached", _row_explanation(row)
                    summary.cached += 1
                    continue
                if summary.calls + summary.would_generate >= max_calls or summary.aborted:
                    item.status = "over_limit"
                    summary.over_limit += 1
                    continue
                if dry_run:
                    item.status = "would_generate"
                    summary.would_generate += 1
                    continue
                if self._explainer is None:
                    item.status, item.reasons = "unavailable", ["OPENAI_API_KEY is not set"]
                    summary.errors += 1
                    summary.aborted = "OPENAI_API_KEY is not set"
                    continue
                self._generate(session, summary, item, ctx, key, digest, row, known)
            summary.estimated_cost_usd = self._cost(summary)
        return summary

    # --- helpers ---

    def _generate(self, session: Session, summary: RunSummary, item: ItemResult, ctx: TradeContext, key, digest: str, row, known: set[str]) -> None:
        before = (self._explainer.tokens_in, self._explainer.tokens_out)
        summary.calls += 1
        try:
            try:
                explanation = self._explainer.explain(item.facts)
            finally:
                item.tokens_in, item.tokens_out = self._explainer.tokens_in - before[0], self._explainer.tokens_out - before[1]
                summary.tokens_in += item.tokens_in
                summary.tokens_out += item.tokens_out
            validate_explanation(explanation, item.facts, known)
        except ExplanationRejected as exc:
            item.status, item.reasons = "rejected", exc.reasons
            summary.rejected += 1
            return
        except ExplanationError as exc:
            item.status, item.reasons = "error", [str(exc)]
            summary.errors += 1
            if exc.fatal:
                summary.aborted = str(exc)
            return
        except Exception as exc:  # one trade's failure must not stop the others
            item.status, item.reasons = "error", [f"unexpected {type(exc).__name__}"]
            summary.errors += 1
            return
        values = dict(input_hash=digest, context_digest=ctx.result_digest, generated_for="flagged" if ctx.flagged_for_contextual_review else "manual",
                      headline=explanation.headline, summary=explanation.summary, signals_json=json.dumps(explanation.signals), limitations=explanation.limitations,
                      input_tokens=item.tokens_in, output_tokens=item.tokens_out, created_at=self._now())
        if row is None:
            row = TradeContextAnalysis(trade_id=ctx.trade_id, context_version=key[0], mapping_version=key[1], prompt_version=PROMPT_VERSION, model=self.model, **values)
            session.add(row)
        else:  # the facts changed (or --force): replace the stale text only now that the new text has passed validation
            for k, v in values.items():
                setattr(row, k, v)
        session.commit()
        item.status, item.explanation = "generated", _row_explanation(row)
        summary.generated += 1

    @staticmethod
    def _context_key(session: Session) -> tuple[str, str | None]:
        mapping_version = session.scalar(select(CommitteeIndustryMapping.mapping_version).order_by(CommitteeIndustryMapping.id.desc()).limit(1))
        return ContextConfig().version_label(), mapping_version

    @staticmethod
    def _known_committees(session: Session) -> set[str]:
        from .trade_context_llm import known_committee_phrases

        names = list(session.scalars(select(CommitteeIndustryMapping.committee_name).distinct())) + list(session.scalars(select(CommitteeIndustryMapping.subcommittee_name).distinct()))
        names += list(session.scalars(select(CommitteeAssignment.committee_name).distinct()))
        return known_committee_phrases(names)

    @staticmethod
    def _select(session: Session, key, trade_ids, ticker, politician, flagged_only) -> list[TradeContext]:
        q = select(TradeContext).join(Trade, Trade.id == TradeContext.trade_id).where(TradeContext.context_version == key[0], TradeContext.mapping_version == key[1])
        if trade_ids:  # naming a trade is an explicit request: it is explained whether or not it is flagged
            q = q.where(TradeContext.trade_id.in_(trade_ids))
        elif flagged_only:
            q = q.where(TradeContext.flagged_for_contextual_review.is_(True))
        if ticker:
            q = q.where(Trade.ticker == ticker.upper())
        if politician:
            q = q.join(Politician, Politician.id == Trade.politician_id).where(
                Trade.politician_id == int(politician) if politician.isdigit() else Politician.name.ilike(f"%{politician}%"))
        return list(session.scalars(q.order_by(TradeContext.trade_id)))

    def _cost(self, s: RunSummary) -> float | None:
        rin, rout = self._rates
        if rin is None or rout is None or not s.calls:
            return None
        return s.tokens_in / 1e6 * rin + s.tokens_out / 1e6 * rout


def _row_explanation(row: TradeContextAnalysis) -> dict:
    return {"headline": row.headline, "summary": row.summary, "signals": json.loads(row.signals_json), "limitations": row.limitations, "generated_for": row.generated_for}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenAI-written explanations of stored trade context (the deterministic flag is never changed)")
    parser.add_argument("--dry-run", action="store_true", help="select trades and report what would be sent; no OpenAI call, no key needed, nothing written")
    parser.add_argument("--trade-id", type=int, action="append", help="explain this trade (repeatable), flagged or not; an unflagged trade is labelled as an explanation on request")
    parser.add_argument("--ticker")
    parser.add_argument("--politician", help="politician id, or part of a name")
    parser.add_argument("--limit", type=int, help="most OpenAI calls this run (default POLTRACKER_TRADE_LLM_MAX_CALLS, 25)")
    parser.add_argument("--force", action="store_true", help="regenerate even when a valid cached explanation exists")
    parser.add_argument("--flagged-only", action=argparse.BooleanOptionalAction, default=True, help="only trades flagged for contextual review (default); --no-flagged-only widens ticker/politician selections")
    parser.add_argument("--verbose", action="store_true", help="print the facts sent and the explanation received for every trade")
    args = parser.parse_args(argv)
    settings = get_settings()
    explainer = None if args.dry_run else build_explainer(settings.openai_api_key, settings.trade_llm_model)
    if explainer is None and not args.dry_run:
        print("OPENAI_API_KEY is not set: no explanations were generated. The deterministic context is unaffected. Use --dry-run to preview what would be sent.")
        return 1
    service = TradeContextExplanationService.from_settings(make_session_factory(), settings, explainer)
    try:
        summary = service.run(trade_ids=args.trade_id, ticker=args.ticker, politician=args.politician, flagged_only=args.flagged_only, limit=args.limit, force=args.force, dry_run=args.dry_run)
    except (OperationalError, ProgrammingError) as exc:
        print(f"Cannot read the database ({type(exc.orig).__name__}). Run `alembic upgrade head` (migration 0015 adds trade_context_analysis) and `python -m poltracker.analyze_trade_context` first.")
        return 1
    print(summary.to_text())
    if args.verbose:
        for it in summary.items:
            print(f"\n--- trade {it.trade_id} {it.ticker} ({it.status}, flagged={it.flagged}, tokens {it.tokens_in}/{it.tokens_out})")
            print("facts:", json.dumps(it.facts, indent=1, default=str))
            if it.explanation:
                print("explanation:", json.dumps(it.explanation, indent=1))
    return 0 if not summary.aborted else 1


if __name__ == "__main__":
    raise SystemExit(main())
