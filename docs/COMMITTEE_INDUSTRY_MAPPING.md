# Committee / industry mapping

Phase 2 of committee/sector context. It answers one narrow, explainable question: **is a company's industry within an area plausibly
relevant to the jurisdiction of a committee or subcommittee a politician sits on?** That is a contextual relationship only. It is not
evidence of wrongdoing or of non-public information. This phase flags nothing, scores nothing, uses no market data and no language model,
and makes no network call.

## Architecture

- **Data:** `data/committee_industry_mappings.json` is the reviewable source of truth. `python -m poltracker.committee_industry_report --sync`
  loads it into `committee_industry_mappings` (migration 0010, versioned; reloading a version replaces that version only).
- **Matcher:** `CommitteeIndustryMatcher` (`backend/poltracker/committee_industry.py`) takes a politician's committee/subcommittee seats and a
  security's SIC code and description and returns `relevant`, `not_relevant` or `unknown`, with every match's committee, SIC range,
  rationale, citation, source URL, the official text relied on, and the mapping version.
- **Industry key:** the SIC code (from the SEC profile enrichment), by exact code or range. The SIC description can narrow a range through an
  optional `industry_pattern`. The coarse SIC division is not used.
- **Reference:** `data/sic_codes.json` holds the official SEC SIC titles; every mapped range is checked to cover at least one real code.

## Mapping rows

Each row: chamber, committee code (the House Clerk code that `committee_assignments` uses), optional subcommittee code, names, `sic_start`/
`sic_end`, optional `industry_pattern`, `relevance_level`, `rationale` (including the official SIC titles the range covers),
`jurisdiction_text` (the official wording relied on), `source_citation`, `source_url`, `reviewed_at`, `mapping_version`.

- `direct`: the industry is squarely within the committee's (or subcommittee's) enumerated jurisdiction.
- `related`: the industry is adjacent or only partly within it (for example aircraft makers for civil aviation, hospitals for Veterans' care).
- `none`: the committee was reviewed and has no industry-specific jurisdiction (Rules, Ethics, Budget, Ways and Means as a whole, and so on). It
  has no SIC range. It exists so a politician on such a committee is `not_relevant`, not `unknown`.

## Rules

- A subcommittee mapping applies only to a member who holds that subcommittee seat. A parent committee mapping applies to every member of the
  committee. When several mappings match, they are all reported, ordered: subcommittee before committee, `direct` before `related`, narrower
  SIC range, then id. The first is the primary match.
- `unknown`, never a guess: no usable SIC (`no_sic`), no committee seats (`no_committee_assignments`), or a committee with no mapping at all
  (`unmapped_committees`). If any committee the politician holds is unmapped and nothing matched, the result is `unknown`, because the unmapped
  committee could be relevant. `not_relevant` is only asserted when every committee held is mapped and none matched.

## Sources

Committee-level rows cite the official House Rule X, clause 1 (committee jurisdictions), from the House Manual for the 119th Congress
(https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf), quoting the clauses used. Subcommittees are not defined in Rule X. Subcommittee
rows use the subcommittee's official name as published on the committee's website; only the Transportation and Infrastructure Committee
publishes explicit subcommittee jurisdiction text on that page, so for the others the committee's own written subcommittee jurisdiction was not
independently checked (each rationale says so).

## Status: a draft awaiting human review

The mappings were written from the official text by an AI assistant and have not been reviewed by a person: `reviewed_at` is empty and the
version is `2026.1-draft`. They contain judgement calls (for example which SIC codes count as `related`). They should be reviewed before any
later phase relies on them. Use is deterministic and explainable, but correctness of the table is a human decision.

## Usage

```bash
.venv/bin/alembic upgrade head                                          # migration 0010 (back up poltracker.db first)
python -m poltracker.committee_industry_report --sync                   # load data/committee_industry_mappings.json
python -m poltracker.committee_industry_report --report                 # evaluate every trade, read-only, nothing stored
```

## Measured result (scratch copy of the real database, mapping 2026.1-draft, 2026-10-07)

184 mappings (86 committee-level, 98 subcommittee-level; 103 direct, 66 related, 15 none) covering all 27 committees POLTRACKER tracks; 14 have
industry mappings and 15 were reviewed as having none. Across 5,381 trades: 4,099 are evaluable; 357 have at least one relevance match (212
with a direct match, 145 related only) involving 36 politicians and 134 tickers; 3,742 are evaluable with no match; 300 are unknown for missing
SIC data; 982 are unknown because the politician has no committee seats (all 23 senators and 3 representatives); none are unknown for an
unmapped committee.

Manual review of about 100 distinct matches found eight false positives from over-broad ranges, now fixed and pinned by regression tests: an
equities exchange under commodity markets, beverages under nutrition, payroll data processing under defense cyber and the internet
subcommittee, a patent licensor under financial services, a travel site under transportation, waste hauling under water resources, and general
measuring instruments under science.

## Limitations

- Draft, unreviewed mappings (above). SIC codes cannot express every jurisdiction; some codes mix defense and civilian firms (for example 3720-3729
  aircraft, 3730 ship and boat building), so a match means "plausibly relevant", not "this company does defense work".
- Only House committees are tracked: Senate committee assignments are not available, so all senators are `unknown`.
- Economy-wide committees (Ways and Means as a whole, Small Business, Budget, Appropriations as a whole, Judiciary on antitrust) are deliberately
  not mapped to industries, so their members are `not_relevant` for most trades. Appropriations is mapped only through its subcommittees.
- SIC comes from the SEC and can be out of date or coarse (for example holding companies); a security with no SIC (ETFs, funds, many ADRs) is `unknown`.
- Congress.gov's committee codes differ from the House Clerk codes used here; this phase uses the Clerk codes only.
- A mapping row is not an assertion that a politician acted on anything. It never leaves this module as a flag in this phase.
