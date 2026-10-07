# Review decisions, round 1 (mapping version 2026.1-draft)

Applied 2026-10-07 from the project owner's written instruction. Only the decisions below were applied; every other row stays `needs_review`. Each modified row carries a `review_note`; rows resulting from a decision are marked `reviewed` with `reviewed_by` set to the decision's source.

| Decision | Row before | Row(s) after |
|---|---|---|
| APPROVE DIRECT | `BA00:6000-6099:direct` | `BA00:6000-6099:direct` |
| APPROVE DIRECT | `BA00/BA20:6000-6099:direct` | `BA00/BA20:6000-6099:direct` |
| APPROVE DIRECT | `BA00:6200-6299:direct` | `BA00:6200-6299:direct` |
| APPROVE DIRECT | `BA00/BA16:6200-6299:direct` | `BA00/BA16:6200-6299:direct` |
| APPROVE DIRECT | `IF00:4800-4899:direct` | `IF00:4800-4899:direct` |
| APPROVE DIRECT | `IF00/IF16:4800-4899:direct` | `IF00/IF16:4800-4899:direct` |
| APPROVE DIRECT | `IF00:4911-4939:direct` | `IF00:4911-4939:direct` |
| APPROVE DIRECT | `IF00/IF03:4911-4939:direct` | `IF00/IF03:4911-4939:direct` |
| APPROVE DIRECT | `II00:1000-1099:direct` | `II00:1000-1099:direct` |
| APPROVE DIRECT | `II00/II06:1000-1099:direct` | `II00/II06:1000-1099:direct` |
| APPROVE DIRECT | `AS00:3720-3729:direct` | `AS00:3720-3729:direct` |
| SPLIT RANGE | `BA00:6300-6499:direct` | `BA00:6300-6319:direct`, `BA00:6320-6329:related`, `BA00:6330-6499:direct` |
| SPLIT RANGE | `BA00/BA04:6300-6499:direct` | `BA00/BA04:6300-6319:direct`, `BA00/BA04:6320-6329:related`, `BA00/BA04:6330-6499:direct` |
| SPLIT RANGE | `BA00:6100-6199:direct` | `BA00:6100-6198:direct`, `BA00:6199-6199:related` |
| SPLIT RANGE | `BA00/BA20:6100-6199:direct` | `BA00/BA20:6100-6198:direct`, `BA00/BA20:6199-6199:related` |
| SPLIT RANGE | `PW00:1600-1629:direct` | `PW00:1600-1622:direct`, `PW00:1623-1629:related` |
| SPLIT RANGE | `PW00/PW12:1600-1629:direct` | `PW00/PW12:1600-1622:direct`, `PW00/PW12:1623-1629:related` |
| SPLIT RANGE | `AG00/AG16:2060-2079:direct` | `AG00/AG16:2060-2069:related`, `AG00/AG16:2070-2079:direct` |
| DOWNGRADE TO RELATED | `PW00:4730-4739:direct` | `PW00:4730-4739:related` |
| DOWNGRADE TO RELATED | `AG00/AG03:2000-2079:direct` | `AG00/AG03:2000-2079:related` |
| DOWNGRADE TO RELATED | `BA00/BA04:6500-6599:direct` | `BA00/BA04:6500-6599:related` |
| DOWNGRADE TO RELATED | `VR00/VR03:8050-8099:direct` | `VR00/VR03:8050-8099:related` |
| DOWNGRADE TO RELATED | `PW00/PW02:1623-1623:direct` | `PW00/PW02:1623-1623:related` |
| DOWNGRADE TO RELATED | `PW00/PW02:4941-4941:direct` | `PW00/PW02:4941-4941:related` |
| REMOVE | `SY00/SY15:8731-8731:direct` | removed |
| REMOVE | `SY00:8731-8731:direct` | removed |
| NEEDS MORE SOURCE REVIEW | `WM00/WM02:8000-8099:direct` | `WM00/WM02:8000-8099:direct` |
| NEEDS MORE SOURCE REVIEW | `AG00/AG22:6221-6221:direct` | `AG00/AG22:6221-6221:direct` |
| NEEDS MORE SOURCE REVIEW | `IF00/IF16:7370-7373:related` | `IF00/IF16:7370-7373:related` |
| NEEDS MORE SOURCE REVIEW | `JU00/JU03:7370-7373:related` | `JU00/JU03:7370-7373:related` |
| KEEP RELATED | `BA00:6795-6799:related` | `BA00:6795-6799:related` |
| KEEP RELATED | `BA00:6500-6599:related` | `BA00:6500-6599:related` |
| KEEP RELATED | `AP00/AP07:8000-8099:related` | `AP00/AP07:8000-8099:related` |
| KEEP RELATED | `AP00/AP10:4911-4939:related` | `AP00/AP10:4911-4939:related` |
| KEEP RELATED | `AG00:2060-2079:related` | `AG00:2060-2079:related` |
| KEEP RELATED | `BA00/BA04:1520-1531:related` | `BA00/BA04:1520-1531:related` |
| KEEP RELATED | `AG00/AG15:2400-2429:related` | `AG00/AG15:2400-2429:related` |
| KEEP RELATED | `AP00/AP01:0100-0299:related` | `AP00/AP01:0100-0299:related` |
| KEEP RELATED | `AP00/AP10:1600-1629:related` | `AP00/AP10:1600-1629:related` |
| KEEP RELATED | `HM00/HM07:4400-4499:related` | `HM00/HM07:4400-4499:related` |
| KEEP RELATED | `VR00:8050-8099:related` | `VR00:8050-8099:related` |
| KEEP RELATED | `AS00/AS35:7373-7373:related` | `AS00/AS35:7373-7373:related` |
| KEEP RELATED | `BA00:6700-6793:related` | `BA00:6700-6793:related` |
| KEEP RELATED | `IF00:4700-4729:related` | `IF00:4700-4729:related` |

## Removed rows (full original content preserved)

### `SY00/SY15:8731-8731:direct`

```json
{
 "chamber": "house",
 "committee_code": "SY00",
 "subcommittee_code": "SY15",
 "committee_name": "Committee on Science, Space, and Technology",
 "subcommittee_name": "Research and Technology",
 "sic_start": "8731",
 "sic_end": "8731",
 "industry_pattern": null,
 "relevance_level": "direct",
 "rationale": "Research: commercial physical and biological research. Official SIC titles in 8731-8731: 8731 Services-Commercial Physical & Biological Research.",
 "jurisdiction_text": "(1) All energy research, development, and demonstration. (2) Astronautical research and development. (3) Civil aviation research and development. (8) National Aeronautics and Space Administration. (12) Outer space, including exploration and control thereof. (14) Scientific research, development, and demonstration.",
 "source_citation": "Rules of the House of Representatives, 119th Congress, Rule X, clause 1(p)(14); subcommittee name",
 "source_url": "https://science.house.gov/subcommittees",
 "reviewed_at": null,
 "mapping_version": "2026.1-draft",
 "jurisdiction_basis": "subcommittee_name",
 "review_status": "needs_review",
 "reviewed_by": null,
 "review_note": "Review history: an earlier draft also mapped 3820-3829 (measurement technology); removed after it matched Trimble."
}
```

### `SY00:8731-8731:direct`

```json
{
 "chamber": "house",
 "committee_code": "SY00",
 "subcommittee_code": null,
 "committee_name": "Committee on Science, Space, and Technology",
 "subcommittee_name": null,
 "sic_start": "8731",
 "sic_end": "8731",
 "industry_pattern": null,
 "relevance_level": "direct",
 "rationale": "Commercial physical and biological research: 'scientific research, development, and demonstration' (Rule X 1(p)(14)). Official SIC titles in 8731-8731: 8731 Services-Commercial Physical & Biological Research.",
 "jurisdiction_text": "(1) All energy research, development, and demonstration. (2) Astronautical research and development. (3) Civil aviation research and development. (8) National Aeronautics and Space Administration. (12) Outer space, including exploration and control thereof. (14) Scientific research, development, and demonstration.",
 "source_citation": "Rules of the House of Representatives, 119th Congress, Rule X, clause 1(p)",
 "source_url": "https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf",
 "reviewed_at": null,
 "mapping_version": "2026.1-draft",
 "jurisdiction_basis": "rule_x_text",
 "review_status": "needs_review",
 "reviewed_by": null,
 "review_note": null
}
```

## Decisions that were interpreted, for the owner to confirm

- Health-plan insurers (6320-6329) and catch-all 6199 were separated as **related** (the instruction said not to treat them as blanket direct).
- The 1623-1629 piece of heavy construction and the 2060-2069 sugar/confectionery piece were separated as **related**.
- Approved direct only the bank, securities, communications, energy-utility, mining and aircraft/defense rows. Other rows proposed as APPROVE DIRECT (Energy and Commerce Health 8000-8099, Agriculture 0100-0299 and 2010-2029, Transportation water transportation 4400-4499, Science space 3760-3769) were not in those categories and stay `needs_review`.
- Both the sub-level and the committee-level rows were treated alike for each approved or split range.
- The sibling row Agriculture/Nutrition 2090-2099 (direct, miscellaneous food preparations) was not named in the instruction and stays `needs_review` and direct; it is inconsistent with the downgraded 2000-2079 row and needs a decision.
- The other Ways and Means Health rows (6320-6324 direct, 2833-2836 and 3841-3845 related) were not named and stay `needs_review`.

## Owner clarifications (2026-10-07)

- Confirmed related: health-plan insurers 6320-6329, SIC 6199, 1623-1629, 2060-2069.
- Agriculture/Nutrition 2090-2099 stays direct and `needs_review`, with a note that it should be reconciled with the more conservative handling of adjacent broad food ranges; preliminary preference is related unless official text clearly supports direct.
- Left untouched until separately reviewed: Energy and Commerce Health 8000-8099, Agriculture 0100-0299 and 2010-2029, water transportation 4400-4499, Science space 3760-3769, remaining Ways and Means Health rows. Round 2 proposals for them are in `docs/review/round2/`.
- The dataset version stays `2026.1-draft` for all rows; per-row state lives in `review_status` / `reviewed_at` / `reviewed_by`. Promote the whole set to `2026.1` when the review cycle is complete and the set is frozen for Phase 3.

## Round 2 (applied 2026-10-07)

Only these decisions were applied; the other round 2 proposals are in `docs/review/round2/` and remain unapplied.

| Decision | Row before | Row after |
|---|---|---|
| Downgrade | `AS00:3812-3812:direct` | `AS00:3812-3812:related` |
| Related, not direct | `AG00:6221-6221:direct`, `AG00/AG22:6221-6221:direct` | `...:related` |
| Downgrade | `AG00:2040-2049:direct` | `AG00:2040-2049:related` |
| Downgrade | `AG00:3523-3523:direct` | `AG00:3523-3523:related` |
| Downgrade | `WM00/WM02:8000-8099:direct` | `WM00/WM02:8000-8099:related` |
| Downgrade | `WM00/WM02:6320-6324:direct` | `WM00/WM02:6320-6324:related` |
| Downgrade | `AG00/AG03:2090-2099:direct` | `AG00/AG03:2090-2099:related` |
| Approve full range, re-sourced | `IF00/IF14:8000-8099:direct`, `IF00:8000-8099:direct` | same, reviewed |
| Related, re-sourced, reviewed | `IF00/IF16:7370-7373:related` | same, reviewed |
| Approve direct, re-sourced | `JU00/JU03:7370-7373:related` | `JU00/JU03:7370-7373:direct` |
| Approve direct, re-sourced | `SY00/SY16:3760-3769:direct` | same, reviewed |

Official text read on 2026-10-07: E&C Health, E&C Communications & Technology and Science Space and Aeronautics subcommittee pages, and the Judiciary Committee Rules of Procedure, 119th Congress (adopted January 15, 2025), section VI. Their wording is stored in each row's `jurisdiction_text`.

Notes on the sources: the E&C Health text says "the health sector broadly" but does not contain the phrase "health delivery systems"; the Judiciary subcommittee web page says "information technology" and omits "emerging technologies", which the Rules of Procedure PDF contains.
