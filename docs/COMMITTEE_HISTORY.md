# Committee seat history

Phase 3 needs to know whether a politician held a committee seat **on the transaction date**, not only today. The House Clerk's `MemberData.xml` lists the seats
members hold now and gives no dates, so this phase adds dated committee history from an official House record: **adopted House resolutions**.

Run: `python -m poltracker.enrich_committee_history --congress 119` (and `--congress 118`). Options: `--scope committee-relevant|all`, `--politician-ids`,
`--clerk-xml FILE`, `--cache-dir DIR`, `--dry-run`. It writes only `committee_assignments` (migration 0014). Cost: one Clerk download and one govinfo bulk file per
session (about 3 MB each), cached with `--cache-dir`.

## Source

The House elects members to standing committees, and removes them, by resolution ("Electing Members to certain standing committees of the House of
Representatives"). GPO publishes each on govinfo, with the date the House agreed to it:
`https://www.govinfo.gov/bulkdata/BILLS/{congress}/{session}/hres/BILLS-{congress}-{session}-hres.zip`.

- Only the **engrossed** text (`...eh.xml`) counts. A resolution the House never adopted establishes nothing. Every "Removing ..." resolution of the 119th Congress
  was introduced and never adopted, so none is used.
- The date is the one printed on the engrossed text ("In the House of Representatives, U. S., January 14, 2025").
- Names are matched to Bioguide IDs with the Clerk roster's own formal names (`Mr. Green of Texas`). A name that could mean more than one member, including a member
  who has since left (kept from the roster's vacancy records), is set aside, never guessed, and marks every member it might be as `history_complete = false`.
- Committee level only. Subcommittee assignments are made by the committees, not by House resolution, so they have no history here.

## What a record establishes

| Field | Meaning |
|---|---|
| `temporal_precision` | `exact_date` (start and end from adopted resolutions), `congress` (an official source establishes service for that whole Congress; supported, not used today), or `current_snapshot` (the Clerk snapshot: the seat existed on `verified_through`) |
| `start_date`, `end_date` | the adoption dates of the electing and removing resolutions; never inferred from the snapshot or from Congress boundaries |
| `verified_through` | for a seat with no end: the latest date an official source confirms it. Only the 119th Congress has one (the snapshot's publish date, and only if the snapshot still lists the seat) |
| `history_complete` | the scan placed every name that could be this member, so absence from the record is evidence of absence |
| `source_url`, `source_type`, `verified_at`, `congress_number` | provenance |

A member elected twice to a committee with no removal in between is not assumed continuous: the seat counts from the later election.

## How context signals use it (engine 2026.3)

- A committee-level reviewed-direct mapping is **temporally verified** when a dated seat covers the transaction date.
- A **subcommittee-only** match stays `current_assignment_only`: a verified committee seat never promotes a subcommittee inference to a committee fact.
- A current seat is **contradicted** when the official record shows it was not held on the transaction date: the seat began later, ended earlier, or (for a Congress other
  than the snapshot's) the Congress's resolutions were read for this member and the committee is not among them. The trade is then not committee-relevant, and the
  rejected match is kept as evidence (`rejected_current_assignment`).
- Without dated history a seat stays `current_assignment_only` and cannot flag.

## Limits

- A resignation from a committee is made by letter, not by resolution, so an open seat is trusted only up to the snapshot date, and not at all for the 118th Congress, which has
  no end-of-Congress confirmation.
- Standing committees only (Intelligence, Ethics, joint and select committees are not elected by these resolutions).
- Senate members have no committee data; their trades stay unknown.
- Congresses before the 118th have not been ingested. They are not needed for trades from the last year.
