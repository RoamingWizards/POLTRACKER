# Committee / industry mappings: review packet (version 2026.1-draft)

Generated from the mapping file and the current POLTRACKER securities, trades and committee seats. Nothing here is a finding about any politician or company. A mapping only says an industry is within an area plausibly relevant to a committee's jurisdiction.

**No row has been reviewed.** Every row is `needs_review` with an empty `reviewed_at`. To approve a row, edit `data/committee_industry_mappings.json`: set `review_status` to `reviewed`, `reviewed_at` to the approval time and `reviewed_by` to your name (all three together; the loader rejects anything else), then run `--sync`.

## Summary

| Measure | Count |
|---|---|
| Mappings | 191 |
| direct | 97 |
| related | 79 |
| none (reviewed as not industry-specific) | 15 |
| committee-level / subcommittee-level | 89 / 102 |
| Explicit-jurisdiction mappings (official wording read) | 91 |
| Inferred from a subcommittee name | 88 |
| Inferred from a committee name only | 12 |
| Rows needing review / already reviewed | 144 / 47 |
| Trades in the data that have a security | 5380 |
| Trades with at least one match | 357 |
| Trades affected by a direct mapping | 181 |
| Trades affected by related-only mappings | 176 |
| Rows flagged for any scrutiny reason | 174 |
| Rows with a priority concern (broad, mixed, many matches, earlier false positive) | 34 |
| Industry rows matching no current security | 14 |
| Industry rows matching no current trade | 110 |

**Phase 3 policy:** only mappings that are both `reviewed` and `direct` may contribute to a contextual-review flag. `reviewed` + `related` is supporting context only. `needs_review` mappings never affect a flag. A trade has one committee-relevance signal with possibly several evidence records (see the docs).

## Top 20 mappings by number of affected trades

| # | Mapping | Level | Trades matched | Primary for | Securities | Politicians |
|---|---|---|---|---|---|---|
| 1 | BA00:6000-6099:direct  (Committee on Financial Services) | direct | 47 | 46 | 51 | 5 |
| 2 | BA00:6330-6499:direct  (Committee on Financial Services) | direct | 33 | 27 | 26 | 4 |
| 3 | AS00:3720-3729:direct  (Committee on Armed Services) | direct | 27 | 27 | 11 | 1 |
| 4 | BA00:6320-6329:related  (Committee on Financial Services) | related | 19 | 16 | 9 | 4 |
| 5 | BA00:6795-6799:related  (Committee on Financial Services) | related | 19 | 19 | 41 | 2 |
| 6 | BA00:6200-6299:direct  (Committee on Financial Services) | direct | 18 | 4 | 33 | 4 |
| 7 | IF00/IF16:7370-7373:related  (Committee on Energy and Commerce / Communications and Technology) | related | 18 | 18 | 75 | 3 |
| 8 | AP00/AP01:2833-2836:related  (Committee on Appropriations / Agriculture, Rural Development, Food and Drug Administration, and Related Agencies) | related | 16 | 16 | 48 | 3 |
| 9 | AP00/AP07:2833-2836:related  (Committee on Appropriations / Labor, Health and Human Services, Education, and Related Agencies) | related | 14 | 0 | 48 | 1 |
| 10 | BA00/BA16:6200-6299:direct  (Committee on Financial Services / Capital Markets) | direct | 14 | 14 | 33 | 3 |
| 11 | IF00:2833-2836:direct  (Committee on Energy and Commerce) | direct | 14 | 2 | 48 | 4 |
| 12 | SY00:3720-3729:related  (Committee on Science, Space, and Technology) | related | 13 | 11 | 11 | 2 |
| 13 | WM00/WM02:2833-2836:related  (Committee on Ways and Means / Health) | related | 13 | 13 | 48 | 4 |
| 14 | IF00/IF14:2833-2836:direct  (Committee on Energy and Commerce / Health) | direct | 12 | 12 | 48 | 3 |
| 15 | WM00/WM02:3841-3845:related  (Committee on Ways and Means / Health) | related | 12 | 12 | 24 | 1 |
| 16 | BA00:6199-6199:related  (Committee on Financial Services) | related | 11 | 4 | 6 | 4 |
| 17 | FA00:3720-3729:related  (Committee on Foreign Affairs) | related | 11 | 11 | 11 | 2 |
| 18 | BA00:6500-6599:related  (Committee on Financial Services) | related | 9 | 9 | 8 | 2 |
| 19 | AS00:3812-3812:direct  (Committee on Armed Services) | direct | 8 | 8 | 5 | 2 |
| 20 | JU00/JU03:7370-7373:related  (Committee on the Judiciary / Courts, Intellectual Property, Artificial Intelligence, and the Internet) | related | 8 | 8 | 75 | 1 |

## Rows that deserve extra scrutiny

Why a row is flagged:

- `broad_range`: broad SIC range (spans 100+ codes or covers 10+ official titles)
- `mixed_industries`: captures more than one SIC industry group among current securities (see the descriptions)
- `inferred_from_name`: jurisdiction inferred from a subcommittee or committee name, not read from official wording
- `related_level`: 'related' level (adjacent or partial relevance)
- `many_matches`: matches 25+ current trades
- `overlaps_other_committee`: overlaps a mapping of another committee
- `false_positive_history`: adjusted after a false positive found in an earlier manual review

### Priority: rows with a substantive concern (34)

Broad ranges, ranges mixing industry groups, rows matching many trades, and rows adjusted after an earlier false positive.

| Row | Level | Reasons | Trades matched | Securities |
|---|---|---|---|---|
| BA00:6330-6499:direct (Committee on Financial Services) | direct | broad_range, mixed_industries, many_matches | 33 | 26 |
| BA00:6000-6099:direct (Committee on Financial Services) | direct | mixed_industries, many_matches | 47 | 51 |
| BA00/BA04:6330-6499:direct (Committee on Financial Services / Housing and Insurance) | direct | broad_range, mixed_industries, inferred_from_name | 6 | 26 |
| AP00/AP07:8000-8099:related (Committee on Appropriations / Labor, Health and Human Services, Education, and Related Agencies) | related | broad_range, mixed_industries, inferred_from_name, related_level, overlaps_other_committee | 4 | 15 |
| WM00/WM02:8000-8099:direct (Committee on Ways and Means / Health) | direct | broad_range, mixed_industries, inferred_from_name, overlaps_other_committee | 2 | 15 |
| AG00/AG03:2000-2079:related (Committee on Agriculture / Nutrition and Foreign Agriculture) | related | broad_range, mixed_industries, inferred_from_name, related_level | 0 | 16 |
| IF00/IF14:8000-8099:direct (Committee on Energy and Commerce / Health) | direct | broad_range, mixed_industries, inferred_from_name, overlaps_other_committee | 0 | 15 |
| IF00:8000-8099:direct (Committee on Energy and Commerce) | direct | broad_range, mixed_industries, overlaps_other_committee | 0 | 15 |
| AS00:3720-3729:direct (Committee on Armed Services) | direct | many_matches, overlaps_other_committee | 27 | 11 |
| BA00:6200-6299:direct (Committee on Financial Services) | direct | mixed_industries, overlaps_other_committee | 18 | 33 |
| BA00/BA16:6200-6299:direct (Committee on Financial Services / Capital Markets) | direct | mixed_industries, inferred_from_name, overlaps_other_committee | 14 | 33 |
| BA00:6500-6599:related (Committee on Financial Services) | related | mixed_industries, related_level | 9 | 8 |
| IF00/IF16:4800-4899:direct (Committee on Energy and Commerce / Communications and Technology) | direct | mixed_industries, inferred_from_name | 3 | 19 |
| IF00:4800-4899:direct (Committee on Energy and Commerce) | direct | mixed_industries | 3 | 19 |
| AP00/AP10:4911-4939:related (Committee on Appropriations / Energy and Water Development and Related Agencies) | related | mixed_industries, inferred_from_name, related_level, overlaps_other_committee | 2 | 35 |
| IF00/IF03:4911-4939:direct (Committee on Energy and Commerce / Energy) | direct | mixed_industries, inferred_from_name, overlaps_other_committee | 2 | 35 |
| IF00:4911-4939:direct (Committee on Energy and Commerce) | direct | mixed_industries, overlaps_other_committee | 2 | 35 |
| AG00:2060-2079:related (Committee on Agriculture) | related | mixed_industries, related_level | 1 | 3 |
| BA00/BA04:1520-1531:related (Committee on Financial Services / Housing and Insurance) | related | mixed_industries, inferred_from_name, related_level | 1 | 7 |
| BA00/BA20:6000-6099:direct (Committee on Financial Services / Financial Institutions) | direct | mixed_industries, inferred_from_name | 1 | 51 |
| II00:1000-1099:direct (Committee on Natural Resources) | direct | mixed_industries | 1 | 12 |
| AG00/AG15:2400-2429:related (Committee on Agriculture / Forestry and Horticulture) | related | mixed_industries, inferred_from_name, related_level | 0 | 2 |
| AG00:0100-0299:direct (Committee on Agriculture) | direct | broad_range, overlaps_other_committee | 0 | 1 |
| AG00:2010-2029:direct (Committee on Agriculture) | direct | mixed_industries | 0 | 3 |
| AP00/AP01:0100-0299:related (Committee on Appropriations / Agriculture, Rural Development, Food and Drug Administration, and Related Agencies) | related | broad_range, inferred_from_name, related_level, overlaps_other_committee | 0 | 1 |
| AP00/AP10:1600-1629:related (Committee on Appropriations / Energy and Water Development and Related Agencies) | related | mixed_industries, inferred_from_name, related_level, overlaps_other_committee | 0 | 6 |
| BA00/BA04:6500-6599:related (Committee on Financial Services / Housing and Insurance) | related | mixed_industries, inferred_from_name, related_level | 0 | 8 |
| HM00/HM07:4400-4499:related (Committee on Homeland Security / Transportation and Maritime Security) | related | mixed_industries, inferred_from_name, related_level, overlaps_other_committee | 0 | 6 |
| II00/II06:1000-1099:direct (Committee on Natural Resources / Energy and Mineral Resources) | direct | mixed_industries, inferred_from_name | 0 | 12 |
| PW00/PW07:4400-4499:direct (Committee on Transportation and Infrastructure / Coast Guard and Maritime Transportation) | direct | mixed_industries, overlaps_other_committee | 0 | 6 |
| PW00:4400-4499:direct (Committee on Transportation and Infrastructure) | direct | mixed_industries, overlaps_other_committee | 0 | 6 |
| SY00:3760-3769:direct (Committee on Science, Space, and Technology) | direct | overlaps_other_committee, false_positive_history | 0 | 2 |
| VR00/VR03:8050-8099:related (Committee on Veterans' Affairs / Health) | related | mixed_industries, inferred_from_name, related_level, overlaps_other_committee | 0 | 15 |
| VR00:8050-8099:related (Committee on Veterans' Affairs) | related | mixed_industries, related_level, overlaps_other_committee | 0 | 15 |

### Routine: flagged only for name inference, related level or overlap (140)

These are flagged in their entries below. The first group applies to nearly every subcommittee row, so it is not repeated here.

## SIC ranges that capture more than one industry group among current securities

Grouped by the first three digits of the SIC code (a SIC industry group). Whether the groups are *materially* different is for the reviewer to judge.

- **AG00/AG03:2000-2079:related** (Committee on Agriculture / Nutrition and Foreign Agriculture): [200] 2000 Food and Kindred Products (5); [201] 2011 Meat Packing Plants (1), 2015 Poultry Slaughtering and Processing (1); [202] 2024 Ice Cream & Frozen Desserts (1); [203] 2030 Canned, Frozen & Preservd Fruit, Veg & Food Specialties (1), 2033 Canned, Fruits, Veg, Preserves, Jams & Jellies (1); [204] 2040 Grain Mill Products (3); [206] 2060 Sugar & Confectionery Products (1); [207] 2070 Fats & Oils (2)
- **AP00/AP07:8000-8099:related** (Committee on Appropriations / Labor, Health and Human Services, Education, and Related Agencies): [805] 8050 Services-Nursing & Personal Care Facilities (1); [806] 8060 Services-Hospitals (1), 8062 Services-General Medical & Surgical Hospitals, NEC (4); [807] 8071 Services-Medical Laboratories (6); [808] 8082 Services-Home Health Care Services (1); [809] 8090 Services-Misc Health & Allied Services, NEC (1), 8093 Services-Specialty Outpatient Facilities, NEC (1)
- **IF00/IF14:8000-8099:direct** (Committee on Energy and Commerce / Health): [805] 8050 Services-Nursing & Personal Care Facilities (1); [806] 8060 Services-Hospitals (1), 8062 Services-General Medical & Surgical Hospitals, NEC (4); [807] 8071 Services-Medical Laboratories (6); [808] 8082 Services-Home Health Care Services (1); [809] 8090 Services-Misc Health & Allied Services, NEC (1), 8093 Services-Specialty Outpatient Facilities, NEC (1)
- **IF00:8000-8099:direct** (Committee on Energy and Commerce): [805] 8050 Services-Nursing & Personal Care Facilities (1); [806] 8060 Services-Hospitals (1), 8062 Services-General Medical & Surgical Hospitals, NEC (4); [807] 8071 Services-Medical Laboratories (6); [808] 8082 Services-Home Health Care Services (1); [809] 8090 Services-Misc Health & Allied Services, NEC (1), 8093 Services-Specialty Outpatient Facilities, NEC (1)
- **VR00/VR03:8050-8099:related** (Committee on Veterans' Affairs / Health): [805] 8050 Services-Nursing & Personal Care Facilities (1); [806] 8060 Services-Hospitals (1), 8062 Services-General Medical & Surgical Hospitals, NEC (4); [807] 8071 Services-Medical Laboratories (6); [808] 8082 Services-Home Health Care Services (1); [809] 8090 Services-Misc Health & Allied Services, NEC (1), 8093 Services-Specialty Outpatient Facilities, NEC (1)
- **VR00:8050-8099:related** (Committee on Veterans' Affairs): [805] 8050 Services-Nursing & Personal Care Facilities (1); [806] 8060 Services-Hospitals (1), 8062 Services-General Medical & Surgical Hospitals, NEC (4); [807] 8071 Services-Medical Laboratories (6); [808] 8082 Services-Home Health Care Services (1); [809] 8090 Services-Misc Health & Allied Services, NEC (1), 8093 Services-Specialty Outpatient Facilities, NEC (1)
- **WM00/WM02:8000-8099:direct** (Committee on Ways and Means / Health): [805] 8050 Services-Nursing & Personal Care Facilities (1); [806] 8060 Services-Hospitals (1), 8062 Services-General Medical & Surgical Hospitals, NEC (4); [807] 8071 Services-Medical Laboratories (6); [808] 8082 Services-Home Health Care Services (1); [809] 8090 Services-Misc Health & Allied Services, NEC (1), 8093 Services-Specialty Outpatient Facilities, NEC (1)
- **BA00/BA04:6330-6499:direct** (Committee on Financial Services / Housing and Insurance): [633] 6331 Fire, Marine & Casualty Insurance (16); [636] 6361 Title Insurance (1); [639] 6399 Insurance Carriers, NEC (1); [641] 6411 Insurance Agents, Brokers & Service (8)
- **BA00/BA16:6200-6299:direct** (Committee on Financial Services / Capital Markets): [620] 6200 Security & Commodity Brokers, Dealers, Exchanges & Services (6); [621] 6211 Security Brokers, Dealers & Flotation Companies (11); [622] 6221 Commodity Contracts Brokers & Dealers (5); [628] 6282 Investment Advice (11)
- **BA00:6200-6299:direct** (Committee on Financial Services): [620] 6200 Security & Commodity Brokers, Dealers, Exchanges & Services (6); [621] 6211 Security Brokers, Dealers & Flotation Companies (11); [622] 6221 Commodity Contracts Brokers & Dealers (5); [628] 6282 Investment Advice (11)
- **BA00:6330-6499:direct** (Committee on Financial Services): [633] 6331 Fire, Marine & Casualty Insurance (16); [636] 6361 Title Insurance (1); [639] 6399 Insurance Carriers, NEC (1); [641] 6411 Insurance Agents, Brokers & Service (8)
- **IF00/IF16:4800-4899:direct** (Committee on Energy and Commerce / Communications and Technology): [481] 4812 Radiotelephone Communications (1), 4813 Telephone Communications (No Radiotelephone) (5); [483] 4832 Radio Broadcasting Stations (2), 4833 Television Broadcasting Stations (5); [484] 4841 Cable & Other Pay Television Services (4); [489] 4899 Communications Services, NEC (2)
- **IF00:4800-4899:direct** (Committee on Energy and Commerce): [481] 4812 Radiotelephone Communications (1), 4813 Telephone Communications (No Radiotelephone) (5); [483] 4832 Radio Broadcasting Stations (2), 4833 Television Broadcasting Stations (5); [484] 4841 Cable & Other Pay Television Services (4); [489] 4899 Communications Services, NEC (2)
- **AP00/AP10:4911-4939:related** (Committee on Appropriations / Energy and Water Development and Related Agencies): [491] 4911 Electric Services (14); [492] 4922 Natural Gas Transmission (6), 4923 Natural Gas Transmisison & Distribution (1), 4924 Natural Gas Distribution (4); [493] 4931 Electric & Other Services Combined (9), 4932 Gas & Other Services Combined (1)
- **BA00/BA04:6500-6599:related** (Committee on Financial Services / Housing and Insurance): [650] 6500 Real Estate (4); [651] 6510 Real Estate Operators (No Developers) & Lessors (1); [653] 6531 Real Estate Agents & Managers (For Others) (3)
- **BA00:6500-6599:related** (Committee on Financial Services): [650] 6500 Real Estate (4); [651] 6510 Real Estate Operators (No Developers) & Lessors (1); [653] 6531 Real Estate Agents & Managers (For Others) (3)
- **IF00/IF03:4911-4939:direct** (Committee on Energy and Commerce / Energy): [491] 4911 Electric Services (14); [492] 4922 Natural Gas Transmission (6), 4923 Natural Gas Transmisison & Distribution (1), 4924 Natural Gas Distribution (4); [493] 4931 Electric & Other Services Combined (9), 4932 Gas & Other Services Combined (1)
- **IF00:4911-4939:direct** (Committee on Energy and Commerce): [491] 4911 Electric Services (14); [492] 4922 Natural Gas Transmission (6), 4923 Natural Gas Transmisison & Distribution (1), 4924 Natural Gas Distribution (4); [493] 4931 Electric & Other Services Combined (9), 4932 Gas & Other Services Combined (1)
- **II00/II06:1000-1099:direct** (Committee on Natural Resources / Energy and Mineral Resources): [100] 1000 Metal Mining (5); [104] 1040 Gold and Silver Ores (6); [109] 1090 Miscellaneous Metal Ores (1)
- **II00:1000-1099:direct** (Committee on Natural Resources): [100] 1000 Metal Mining (5); [104] 1040 Gold and Silver Ores (6); [109] 1090 Miscellaneous Metal Ores (1)
- **AG00/AG15:2400-2429:related** (Committee on Agriculture / Forestry and Horticulture): [240] 2400 Lumber & Wood Products (No Furniture) (1); [242] 2421 Sawmills & Planting Mills, General (1)
- **AG00:2010-2029:direct** (Committee on Agriculture): [201] 2011 Meat Packing Plants (1), 2015 Poultry Slaughtering and Processing (1); [202] 2024 Ice Cream & Frozen Desserts (1)
- **AG00:2060-2079:related** (Committee on Agriculture): [206] 2060 Sugar & Confectionery Products (1); [207] 2070 Fats & Oils (2)
- **AP00/AP10:1600-1629:related** (Committee on Appropriations / Energy and Water Development and Related Agencies): [160] 1600 Heavy Construction Other Than Bldg Const - Contractors (3); [162] 1623 Water, Sewer, Pipeline, Comm & Power Line Construction (3)
- **BA00/BA04:1520-1531:related** (Committee on Financial Services / Housing and Insurance): [152] 1520 General Bldg Contractors - Residential Bldgs (2); [153] 1531 Operative Builders (5)
- **BA00/BA20:6000-6099:direct** (Committee on Financial Services / Financial Institutions): [602] 6021 National Commercial Banks (18), 6022 State Commercial Banks (19), 6029 Commercial Banks, NEC (11); [603] 6035 Savings Institution, Federally Chartered (2), 6036 Savings Institutions, Not Federally Chartered (1)
- **BA00:6000-6099:direct** (Committee on Financial Services): [602] 6021 National Commercial Banks (18), 6022 State Commercial Banks (19), 6029 Commercial Banks, NEC (11); [603] 6035 Savings Institution, Federally Chartered (2), 6036 Savings Institutions, Not Federally Chartered (1)
- **HM00/HM07:4400-4499:related** (Committee on Homeland Security / Transportation and Maritime Security): [440] 4400 Water Transportation (4); [441] 4412 Deep Sea Foreign Transportation of  Freight (2)
- **PW00/PW07:4400-4499:direct** (Committee on Transportation and Infrastructure / Coast Guard and Maritime Transportation): [440] 4400 Water Transportation (4); [441] 4412 Deep Sea Foreign Transportation of  Freight (2)
- **PW00:4400-4499:direct** (Committee on Transportation and Infrastructure): [440] 4400 Water Transportation (4); [441] 4412 Deep Sea Foreign Transportation of  Freight (2)

## Review entries, by committee and subcommittee


### AG00: Committee on Agriculture

#### `AG00:0100-0299:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 0100-0299
- **Official SIC titles covered:** 0100 Agricultural Production-Crops
- **Rationale:** Crop and livestock production is 'agriculture generally' and 'agricultural production and marketing' (Rule X 1(a)(2),(7)). Official SIC titles in 0100-0299: 0100 Agricultural Production-Crops.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 1 securities (0100 Agricultural Production-Crops x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CTVA.
- **Overlaps other committees:** AP00/AP01 0100-0299 (related)
- **Scrutiny:** `broad_range`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00:0700-0799:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 0700-0799
- **Official SIC titles covered:** none in the SEC table (the SEC lists only codes assigned to registrants)
- **Rationale:** Agricultural services are part of agriculture generally (Rule X 1(a)(2)). Official SIC titles in 0700-0799: no official SIC title in this range.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 0 securities (no current security in this range)
- **Trades matched:** 0 by 0 politicians (primary match for 0).
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00:0800-0899:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 0800-0899
- **Official SIC titles covered:** none in the SEC table (the SEC lists only codes assigned to registrants)
- **Rationale:** Forestry in general belongs to Agriculture (Rule X 1(a)(15)); forest reserves from the public domain belong to Natural Resources. Official SIC titles in 0800-0899: no official SIC title in this range.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 0 securities (no current security in this range)
- **Trades matched:** 0 by 0 politicians (primary match for 0).
- **Overlaps other committees:** II00 0800-0899 (related)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00:2010-2029:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 2010-2029
- **Official SIC titles covered:** 2011 Meat Packing Plants; 2013 Sausages & Other Prepared Meat Products; 2015 Poultry Slaughtering And Processing; 2020 Dairy Products; 2024 Ice Cream & Frozen Desserts
- **Rationale:** Meat, poultry and dairy processing: 'inspection of livestock, poultry, meat products' and 'dairy industry' (Rule X 1(a)(11),(14)). Official SIC titles in 2010-2029: 2011 Meat Packing Plants; 2013 Sausages & Other Prepared Meat Products; 2015 Poultry Slaughtering And Processing; 2020 Dairy Products; 2024 Ice Cream & Frozen Desserts.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 3 securities (2011 Meat Packing Plants x1, 2015 Poultry Slaughtering and Processing x1, 2024 Ice Cream & Frozen Desserts x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: HRL, MICC, TSN.
- **Scrutiny:** `mixed_industries`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00:2040-2049:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 2040-2049
- **Official SIC titles covered:** 2040 Grain Mill Products
- **Rationale:** Grain mill products process agricultural commodities (Rule X 1(a)(7)). Official SIC titles in 2040-2049: 2040 Grain Mill Products.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 3 securities (2040 Grain Mill Products x3)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: GIS, INGR, K.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00:2060-2079:related`  related  |  reviewed

- **Scope:** committee level
- **SIC range:** 2060-2079
- **Official SIC titles covered:** 2060 Sugar & Confectionery Products; 2070 Fats & Oils
- **Rationale:** Sugar, confectionery, fats and oils process agricultural commodities (Rule X 1(a)(7)); sugar trade agreements sit elsewhere. Official SIC titles in 2060-2079: 2060 Sugar & Confectionery Products; 2070 Fats & Oils.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 3 securities (2060 Sugar & Confectionery Products x1, 2070 Fats & Oils x2)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: ADM, BG, HSY.
- **Scrutiny:** `mixed_industries`; `related_level`
- **Review note:** Kept as related (owner decision 2026-10-07): supporting context only; never triggers a flag by itself.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00:2090-2099:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 2090-2099
- **Official SIC titles covered:** 2090 Miscellaneous Food Preparations & Kindred Products; 2092 Prepared Fresh Or Frozen Fish & Seafoods
- **Rationale:** Miscellaneous food preparations, including seafood products, fall under food inspection (Rule X 1(a)(14)). Official SIC titles in 2090-2099: 2090 Miscellaneous Food Preparations & Kindred Products; 2092 Prepared Fresh Or Frozen Fish & Seafoods.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (2090 Miscellaneous Food Preparations & Kindred Products x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: MKC, UTZ.
- **Overlaps other committees:** II00/II13 2091-2092 (related)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00:2870-2879:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 2870-2879
- **Official SIC titles covered:** 2870 Agricultural Chemicals
- **Rationale:** Agricultural chemicals: 'agricultural and industrial chemistry' (Rule X 1(a)(3)). Official SIC titles in 2870-2879: 2870 Agricultural Chemicals.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 4 securities (2870 Agricultural Chemicals x4)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CF, ICL, MOS, NTR.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00:3523-3523:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 3523-3523
- **Official SIC titles covered:** 3523 Farm Machinery & Equipment
- **Rationale:** Farm machinery and equipment: 'agricultural engineering' (Rule X 1(a)(17)). Official SIC titles in 3523-3523: 3523 Farm Machinery & Equipment.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 1 securities (3523 Farm Machinery & Equipment x1)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: DE.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00:5150-5159:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 5150-5159
- **Official SIC titles covered:** 5150 Wholesale-Farm Product Raw Materials
- **Rationale:** Farm-product raw materials wholesaling is part of agricultural marketing (Rule X 1(a)(7)). Official SIC titles in 5150-5159: 5150 Wholesale-Farm Product Raw Materials.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 0 securities (no current security in this range)
- **Trades matched:** 0 by 0 politicians (primary match for 0).
- **Scrutiny:** `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00:6221-6221:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 6221-6221
- **Official SIC titles covered:** 6221 Commodity Contracts Brokers & Dealers
- **Rationale:** Commodity contracts brokers and dealers: 'commodity exchanges' (Rule X 1(a)(9)). Official SIC titles in 6221-6221: 6221 Commodity Contracts Brokers & Dealers.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 5 securities (6221 Commodity Contracts Brokers & Dealers x5)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: BITB, IBIT, PALL, PPLT, SLV.
- **Overlaps other committees:** BA00 6200-6299 (direct); BA00/BA16 6200-6299 (direct)
- **Scrutiny:** `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG22:6221-6221:direct`  direct  |  needs_review

- **Scope:** subcommittee AG22 (Commodity Markets, Digital Assets, and Rural Development)
- **SIC range:** 6221-6221
- **Official SIC titles covered:** 6221 Commodity Contracts Brokers & Dealers
- **Rationale:** Commodity contracts brokers and dealers: commodity markets (Rule X 1(a)(9)). Official SIC titles in 6221-6221: 6221 Commodity Contracts Brokers & Dealers.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(9); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 5 securities (6221 Commodity Contracts Brokers & Dealers x5)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: BITB, IBIT, PALL, PPLT, SLV.
- **Overlaps other committees:** BA00 6200-6299 (direct); BA00/BA16 6200-6299 (direct)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Review note:** Needs more source review (owner decision 2026-10-07): the current 6221 securities are commodity-linked ETFs, not exchanges or brokers; decide whether they count as 'commodity markets'. Overlaps Financial Services 6200-6299. Earlier history: Review history: an earlier draft also mapped 6200 (security and commodity brokers, general) here; it was removed after manual review because it matched Nasdaq, an equities exchange, not a commodity market.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG14:0700-0799:direct`  direct  |  needs_review

- **Scope:** subcommittee AG14 (Conservation, Research, and Biotechnology)
- **SIC range:** 0700-0799
- **Official SIC titles covered:** none in the SEC table (the SEC lists only codes assigned to registrants)
- **Rationale:** Agricultural services and research (Rule X 1(a)(5)). Official SIC titles in 0700-0799: no official SIC title in this range.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(3),(5); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 0 securities (no current security in this range)
- **Trades matched:** 0 by 0 politicians (primary match for 0).
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG14:2870-2879:direct`  direct  |  needs_review

- **Scope:** subcommittee AG14 (Conservation, Research, and Biotechnology)
- **SIC range:** 2870-2879
- **Official SIC titles covered:** 2870 Agricultural Chemicals
- **Rationale:** Agricultural chemicals: conservation, research and agricultural biotechnology inputs (Rule X 1(a)(3),(5)). Official SIC titles in 2870-2879: 2870 Agricultural Chemicals.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(3),(5); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 4 securities (2870 Agricultural Chemicals x4)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CF, ICL, MOS, NTR.
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG15:0180-0189:direct`  direct  |  needs_review

- **Scope:** subcommittee AG15 (Forestry and Horticulture)
- **SIC range:** 0180-0189
- **Official SIC titles covered:** none in the SEC table (the SEC lists only codes assigned to registrants)
- **Rationale:** Horticultural specialties. Official SIC titles in 0180-0189: no official SIC title in this range.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(15); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 0 securities (no current security in this range)
- **Trades matched:** 0 by 0 politicians (primary match for 0).
- **Overlaps other committees:** AP00/AP01 0100-0299 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG15:0800-0899:direct`  direct  |  needs_review

- **Scope:** subcommittee AG15 (Forestry and Horticulture)
- **SIC range:** 0800-0899
- **Official SIC titles covered:** none in the SEC table (the SEC lists only codes assigned to registrants)
- **Rationale:** Forestry (Rule X 1(a)(15)). Official SIC titles in 0800-0899: no official SIC title in this range.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(15); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 0 securities (no current security in this range)
- **Trades matched:** 0 by 0 politicians (primary match for 0).
- **Overlaps other committees:** II00 0800-0899 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG15:2400-2429:related`  related  |  reviewed

- **Scope:** subcommittee AG15 (Forestry and Horticulture)
- **SIC range:** 2400-2429
- **Official SIC titles covered:** 2400 Lumber & Wood Products (No Furniture); 2421 Sawmills & Planting Mills, General
- **Rationale:** Lumber and wood products come from forestry (Rule X 1(a)(15)). Official SIC titles in 2400-2429: 2400 Lumber & Wood Products (No Furniture); 2421 Sawmills & Planting Mills, General.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(15); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 2 securities (2400 Lumber & Wood Products (No Furniture) x1, 2421 Sawmills & Planting Mills, General x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: LPX, UFPI.
- **Scrutiny:** `mixed_industries`; `inferred_from_name`; `related_level`
- **Review note:** Kept as related (owner decision 2026-10-07): supporting context only; never triggers a flag by itself.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG16:0100-0199:direct`  direct  |  needs_review

- **Scope:** subcommittee AG16 (General Farm Commodities, Risk Management, and Credit)
- **SIC range:** 0100-0199
- **Official SIC titles covered:** 0100 Agricultural Production-Crops
- **Rationale:** Crop production: general farm commodities (Rule X 1(a)(7)). Official SIC titles in 0100-0199: 0100 Agricultural Production-Crops.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(7),(13); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 1 securities (0100 Agricultural Production-Crops x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CTVA.
- **Overlaps other committees:** AP00/AP01 0100-0299 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG16:2040-2049:direct`  direct  |  needs_review

- **Scope:** subcommittee AG16 (General Farm Commodities, Risk Management, and Credit)
- **SIC range:** 2040-2049
- **Official SIC titles covered:** 2040 Grain Mill Products
- **Rationale:** Grain mill products. Official SIC titles in 2040-2049: 2040 Grain Mill Products.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(7),(13); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 3 securities (2040 Grain Mill Products x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: GIS, INGR, K.
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG16:2060-2069:related`  related  |  reviewed

- **Scope:** subcommittee AG16 (General Farm Commodities, Risk Management, and Credit)
- **SIC range:** 2060-2069
- **Official SIC titles covered:** 2060 Sugar & Confectionery Products
- **Rationale:** Sugar, fats and oils processing of farm commodities. Official SIC titles in 2060-2069: 2060 Sugar & Confectionery Products.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(7),(13); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 1 securities (2060 Sugar & Confectionery Products x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: HSY.
- **Scrutiny:** `inferred_from_name`; `related_level`
- **Review note:** Split from 2060-2079 direct (owner decision 2026-10-07): Fats and oils processing of farm commodities (2070-2079) stays direct; sugar and confectionery (2060-2069) is largely consumer goods and is separated as related. This piece is related.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG16:2070-2079:direct`  direct  |  reviewed

- **Scope:** subcommittee AG16 (General Farm Commodities, Risk Management, and Credit)
- **SIC range:** 2070-2079
- **Official SIC titles covered:** 2070 Fats & Oils
- **Rationale:** Sugar, fats and oils processing of farm commodities. Official SIC titles in 2070-2079: 2070 Fats & Oils.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(7),(13); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 2 securities (2070 Fats & Oils x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: ADM, BG.
- **Scrutiny:** `inferred_from_name`
- **Review note:** Split from 2060-2079 direct (owner decision 2026-10-07): Fats and oils processing of farm commodities (2070-2079) stays direct; sugar and confectionery (2060-2069) is largely consumer goods and is separated as related. This piece is direct.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG29:0200-0299:direct`  direct  |  needs_review

- **Scope:** subcommittee AG29 (Livestock, Dairy, and Poultry)
- **SIC range:** 0200-0299
- **Official SIC titles covered:** none in the SEC table (the SEC lists only codes assigned to registrants)
- **Rationale:** Livestock production (Rule X 1(a)(8),(14)). Official SIC titles in 0200-0299: no official SIC title in this range.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(8),(11),(14); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 0 securities (no current security in this range)
- **Trades matched:** 0 by 0 politicians (primary match for 0).
- **Overlaps other committees:** AP00/AP01 0100-0299 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG29:2010-2019:direct`  direct  |  needs_review

- **Scope:** subcommittee AG29 (Livestock, Dairy, and Poultry)
- **SIC range:** 2010-2019
- **Official SIC titles covered:** 2011 Meat Packing Plants; 2013 Sausages & Other Prepared Meat Products; 2015 Poultry Slaughtering And Processing
- **Rationale:** Meat packing and poultry processing (Rule X 1(a)(14)). Official SIC titles in 2010-2019: 2011 Meat Packing Plants; 2013 Sausages & Other Prepared Meat Products; 2015 Poultry Slaughtering And Processing.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(8),(11),(14); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 2 securities (2011 Meat Packing Plants x1, 2015 Poultry Slaughtering and Processing x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: HRL, TSN.
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG29:2020-2029:direct`  direct  |  needs_review

- **Scope:** subcommittee AG29 (Livestock, Dairy, and Poultry)
- **SIC range:** 2020-2029
- **Official SIC titles covered:** 2020 Dairy Products; 2024 Ice Cream & Frozen Desserts
- **Rationale:** Dairy products (Rule X 1(a)(11)). Official SIC titles in 2020-2029: 2020 Dairy Products; 2024 Ice Cream & Frozen Desserts.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(8),(11),(14); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 1 securities (2024 Ice Cream & Frozen Desserts x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: MICC.
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG03:2000-2079:related`  related  |  reviewed

- **Scope:** subcommittee AG03 (Nutrition and Foreign Agriculture)
- **SIC range:** 2000-2079
- **Official SIC titles covered:** 2000 Food And Kindred Products; 2011 Meat Packing Plants; 2013 Sausages & Other Prepared Meat Products; 2015 Poultry Slaughtering And Processing; 2020 Dairy Products; 2024 Ice Cream & Frozen Desserts; 2030 Canned, Frozen & Preservd Fruit, Veg & Food Specialties; 2033 Canned, Fruits, Veg, Preserves, Jams & Jellies; 2040 Grain Mill Products; 2050 Bakery Products; 2052 Cookies & Crackers; 2060 Sugar & Confectionery Products; +1 more
- **Rationale:** Food and kindred products: human nutrition (Rule X 1(a)(16)) and agricultural marketing. Beverages (2080-2089) are not mapped here. Official SIC titles in 2000-2079: 2000 Food And Kindred Products; 2011 Meat Packing Plants; 2013 Sausages & Other Prepared Meat Products; 2015 Poultry Slaughtering And Processing; 2020 Dairy Products; 2024 Ice Cream & Frozen Desserts; +7 more.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(16); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 16 securities (2000 Food and Kindred Products x5, 2011 Meat Packing Plants x1, 2015 Poultry Slaughtering and Processing x1, 2024 Ice Cream & Frozen Desserts x1, 2030 Canned, Frozen & Preservd Fruit, Veg & Food Specialties x1, 2033 Canned, Fruits, Veg, Preserves, Jams & Jellies x1, 2040 Grain Mill Products x3, 2060 Sugar & Confectionery Products x1, 2070 Fats & Oils x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: ADM, BG, CAG, CPB, FLO, GIS, HRL, HSY.
- **Scrutiny:** `broad_range`; `mixed_industries`; `inferred_from_name`; `related_level`
- **Review note:** Downgraded from direct to related (owner decision 2026-10-07): broad food manufacturing is a stretch for a nutrition-programs subcommittee; the committee-level meat, dairy and grain rows cover the clear cases. Earlier history: Review history: an earlier draft mapped 2000-2099; beverages (2080-2089) were excluded after it matched PepsiCo, which is not 'human nutrition'.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG03:2090-2099:direct`  direct  |  needs_review

- **Scope:** subcommittee AG03 (Nutrition and Foreign Agriculture)
- **SIC range:** 2090-2099
- **Official SIC titles covered:** 2090 Miscellaneous Food Preparations & Kindred Products; 2092 Prepared Fresh Or Frozen Fish & Seafoods
- **Rationale:** Miscellaneous food preparations: human nutrition (Rule X 1(a)(16)). Official SIC titles in 2090-2099: 2090 Miscellaneous Food Preparations & Kindred Products; 2092 Prepared Fresh Or Frozen Fish & Seafoods.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(16); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 2 securities (2090 Miscellaneous Food Preparations & Kindred Products x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: MKC, UTZ.
- **Overlaps other committees:** II00/II13 2091-2092 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG03:5140-5149:related`  related  |  needs_review

- **Scope:** subcommittee AG03 (Nutrition and Foreign Agriculture)
- **SIC range:** 5140-5149
- **Official SIC titles covered:** 5140 Wholesale-Groceries & Related Products; 5141 Wholesale-Groceries, General Line
- **Rationale:** Grocery wholesaling supplies food nutrition programs' markets. Official SIC titles in 5140-5149: 5140 Wholesale-Groceries & Related Products; 5141 Wholesale-Groceries, General Line.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(16); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 4 securities (5140 Wholesale-Groceries & Related Products x3, 5141 Wholesale-Groceries, General Line x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: DPZ, PFGC, SYY, USFD.
- **Scrutiny:** `inferred_from_name`; `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AG00/AG03:5411-5411:related`  related  |  needs_review

- **Scope:** subcommittee AG03 (Nutrition and Foreign Agriculture)
- **SIC range:** 5411-5411
- **Official SIC titles covered:** 5411 Retail-Grocery Stores
- **Rationale:** Grocery retail is the consumer end of food and nutrition policy. Official SIC titles in 5411-5411: 5411 Retail-Grocery Stores.
- **Official jurisdiction wording used:** (2) Agriculture generally. (3) Agricultural and industrial chemistry. (7) Agricultural production and marketing and stabilization of prices of agricultural products, and commodities. (9) Commodity exchanges. (11) Dairy industry. (14) Inspection of livestock, poultry, meat products, and seafood and seafood products. (15) Forestry in general. (16) Human nutrition. (17) Plant industry, soils, and agricultural engineering.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(a)(16); subcommittee name  <https://agriculture.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 3 securities (5411 Retail-Grocery Stores x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: ACI, KR, SFM.
- **Scrutiny:** `inferred_from_name`; `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### AP00: Committee on Appropriations

#### `AP00:none:none`  none  |  needs_review

- **Scope:** committee level
- **SIC range:** none (reviewed as having no industry-specific jurisdiction)
- **Rationale:** The full Appropriations Committee funds the whole Government; its industry relevance is carried by its subcommittees' mappings, so a seat on the full committee alone is not mapped to an industry.
- **Official jurisdiction wording used:** Reviewed for industry-specific jurisdiction; none identified in the official text.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X (clause for this committee) or the committee's establishing resolution  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `committee_name`: inferred from the committee name, not verified
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AP00/AP01:0100-0299:related`  related  |  reviewed

- **Scope:** subcommittee AP01 (Agriculture, Rural Development, Food and Drug Administration, and Related Agencies)
- **SIC range:** 0100-0299
- **Official SIC titles covered:** 0100 Agricultural Production-Crops
- **Rationale:** Agriculture appropriations fund USDA programs. Official SIC titles in 0100-0299: 0100 Agricultural Production-Crops.
- **Official jurisdiction wording used:** Rule X 1(b): appropriations for the Government; each subcommittee's official name states the agencies whose funding it handles.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(b) (appropriations); subcommittee name  <https://appropriations.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 1 securities (0100 Agricultural Production-Crops x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CTVA.
- **Overlaps other committees:** AG00 0100-0299 (direct); AG00/AG15 0180-0189 (direct); AG00/AG16 0100-0199 (direct); AG00/AG29 0200-0299 (direct)
- **Scrutiny:** `broad_range`; `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Review note:** Kept as related (owner decision 2026-10-07): supporting context only; never triggers a flag by itself.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AP00/AP01:2833-2836:related`  related  |  needs_review

- **Scope:** subcommittee AP01 (Agriculture, Rural Development, Food and Drug Administration, and Related Agencies)
- **SIC range:** 2833-2836
- **Official SIC titles covered:** 2833 Medicinal Chemicals & Botanical Products; 2834 Pharmaceutical Preparations; 2835 In Vitro & In Vivo Diagnostic Substances; 2836 Biological Products, (No Diagnostic Substances)
- **Rationale:** Agriculture-FDA appropriations fund the Food and Drug Administration. Official SIC titles in 2833-2836: 2833 Medicinal Chemicals & Botanical Products; 2834 Pharmaceutical Preparations; 2835 In Vitro & In Vivo Diagnostic Substances; 2836 Biological Products, (No Diagnostic Substances).
- **Official jurisdiction wording used:** Rule X 1(b): appropriations for the Government; each subcommittee's official name states the agencies whose funding it handles.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(b) (appropriations); subcommittee name  <https://appropriations.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 48 securities (2833 Medicinal Chemicals & Botanical Products x1, 2834 Pharmaceutical Preparations x35, 2835 In Vitro & In Vivo Diagnostic Substances x1, 2836 Biological Products, (No Diagnostic Substances) x11)
- **Trades matched:** 16 by 3 politicians (primary match for 16). Examples: ABBV, ABT, AGIO, ALKS, ALNY, AMGN, ARGX, ARQT.
- **Overlaps other committees:** IF00 2833-2836 (direct); IF00/IF14 2833-2836 (direct); VR00/VR03 2833-2836 (related); WM00/WM02 2833-2836 (related)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AP00/AP19:3760-3769:related`  related  |  needs_review

- **Scope:** subcommittee AP19 (Commerce, Justice, Science, and Related Agencies)
- **SIC range:** 3760-3769
- **Official SIC titles covered:** 3760 Guided Missiles & Space Vehicles & Parts
- **Rationale:** Commerce, Justice, Science appropriations fund NASA. Official SIC titles in 3760-3769: 3760 Guided Missiles & Space Vehicles & Parts.
- **Official jurisdiction wording used:** Rule X 1(b): appropriations for the Government; each subcommittee's official name states the agencies whose funding it handles.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(b) (appropriations); subcommittee name  <https://appropriations.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 2 securities (3760 Guided Missiles & Space Vehicles & Parts x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: LMT, VOYG.
- **Overlaps other committees:** AS00 3760-3769 (direct); AS00/AS29 3760-3769 (direct); SY00 3760-3769 (direct); SY00/SY16 3760-3769 (direct); FA00 3760-3769 (related)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AP00/AP02:3480-3489:direct`  direct  |  needs_review

- **Scope:** subcommittee AP02 (Defense)
- **SIC range:** 3480-3489
- **Official SIC titles covered:** 3480 Ordnance & Accessories, (No Vehicles/Guided Missiles)
- **Rationale:** Defense appropriations fund ordnance procurement. Official SIC titles in 3480-3489: 3480 Ordnance & Accessories, (No Vehicles/Guided Missiles).
- **Official jurisdiction wording used:** Rule X 1(b): appropriations for the Government; each subcommittee's official name states the agencies whose funding it handles.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(b) (appropriations); subcommittee name  <https://appropriations.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 1 securities (3480 Ordnance & Accessories, (No Vehicles/Guided Missiles) x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: AXON.
- **Overlaps other committees:** AS00 3480-3489 (direct); AS00/AS25 3480-3489 (direct); FA00 3480-3489 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AP00/AP02:3720-3729:direct`  direct  |  needs_review

- **Scope:** subcommittee AP02 (Defense)
- **SIC range:** 3720-3729
- **Official SIC titles covered:** 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec
- **Rationale:** Defense appropriations fund aircraft. Official SIC titles in 3720-3729: 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec.
- **Official jurisdiction wording used:** Rule X 1(b): appropriations for the Government; each subcommittee's official name states the agencies whose funding it handles.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(b) (appropriations); subcommittee name  <https://appropriations.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 11 securities (3720 Aircraft & Parts x1, 3721 Aircraft x2, 3724 Aircraft Engines & Engine Parts x5, 3728 Aircraft Parts & Auxiliary Equipment, NEC x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: AVAV, BA, DCO, ESLT, HEI.A, HON, HONA, RTX.
- **Overlaps other committees:** AS00 3720-3729 (direct); AS00/AS25 3720-3729 (direct); PW00 3720-3729 (related); PW00/PW05 3720-3729 (related); SY00 3720-3729 (related); SY00/SY16 3720-3729 (direct); FA00 3720-3729 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AP00/AP02:3730-3732:direct`  direct  |  needs_review

- **Scope:** subcommittee AP02 (Defense)
- **SIC range:** 3730-3732
- **Official SIC titles covered:** 3730 Ship & Boat Building & Repairing
- **Rationale:** Defense appropriations fund shipbuilding. Official SIC titles in 3730-3732: 3730 Ship & Boat Building & Repairing.
- **Official jurisdiction wording used:** Rule X 1(b): appropriations for the Government; each subcommittee's official name states the agencies whose funding it handles.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(b) (appropriations); subcommittee name  <https://appropriations.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 2 securities (3730 Ship & Boat Building & Repairing x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: GD, HII.
- **Overlaps other committees:** AS00 3730-3732 (direct); AS00/AS28 3730-3732 (direct); PW00/PW07 3730-3732 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AP00/AP02:3760-3769:direct`  direct  |  needs_review

- **Scope:** subcommittee AP02 (Defense)
- **SIC range:** 3760-3769
- **Official SIC titles covered:** 3760 Guided Missiles & Space Vehicles & Parts
- **Rationale:** Defense appropriations fund missiles and space systems. Official SIC titles in 3760-3769: 3760 Guided Missiles & Space Vehicles & Parts.
- **Official jurisdiction wording used:** Rule X 1(b): appropriations for the Government; each subcommittee's official name states the agencies whose funding it handles.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(b) (appropriations); subcommittee name  <https://appropriations.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 2 securities (3760 Guided Missiles & Space Vehicles & Parts x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: LMT, VOYG.
- **Overlaps other committees:** AS00 3760-3769 (direct); AS00/AS29 3760-3769 (direct); SY00 3760-3769 (direct); SY00/SY16 3760-3769 (direct); FA00 3760-3769 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AP00/AP02:3812-3812:direct`  direct  |  needs_review

- **Scope:** subcommittee AP02 (Defense)
- **SIC range:** 3812-3812
- **Official SIC titles covered:** 3812 Search, Detection, Navagation, Guidance, Aeronautical Sys
- **Rationale:** Defense appropriations fund defense electronics. Official SIC titles in 3812-3812: 3812 Search, Detection, Navagation, Guidance, Aeronautical Sys.
- **Official jurisdiction wording used:** Rule X 1(b): appropriations for the Government; each subcommittee's official name states the agencies whose funding it handles.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(b) (appropriations); subcommittee name  <https://appropriations.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 5 securities (3812 Search, Detection, Navigation, Guidance, Aeronautical Sys x5)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: DRS, GRMN, LHX, NOC, TDY.
- **Overlaps other committees:** AS00 3812-3812 (direct); AS00/AS29 3812-3812 (direct); FA00 3812-3812 (related); HM00 3812-3812 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AP00/AP10:1311-1311:related`  related  |  needs_review

- **Scope:** subcommittee AP10 (Energy and Water Development and Related Agencies)
- **SIC range:** 1311-1311
- **Official SIC titles covered:** 1311 Crude Petroleum & Natural Gas
- **Rationale:** Energy and Water appropriations fund Department of Energy programs. Official SIC titles in 1311-1311: 1311 Crude Petroleum & Natural Gas.
- **Official jurisdiction wording used:** Rule X 1(b): appropriations for the Government; each subcommittee's official name states the agencies whose funding it handles.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(b) (appropriations); subcommittee name  <https://appropriations.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 22 securities (1311 Crude Petroleum & Natural Gas x22)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: AESI, APA, CHRD, CNQ, CTRA, DMLP, DVN, EOG.
- **Overlaps other committees:** IF00 1311-1311 (direct); IF00/IF03 1311-1311 (direct); II00 1311-1311 (related); II00/II06 1311-1311 (direct)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AP00/AP10:1600-1629:related`  related  |  reviewed

- **Scope:** subcommittee AP10 (Energy and Water Development and Related Agencies)
- **SIC range:** 1600-1629
- **Official SIC titles covered:** 1600 Heavy Construction Other Than Bldg Const - Contractors; 1623 Water, Sewer, Pipeline, Comm & Power Line Construction
- **Rationale:** Energy and Water appropriations fund Army Corps of Engineers construction. Official SIC titles in 1600-1629: 1600 Heavy Construction Other Than Bldg Const - Contractors; 1623 Water, Sewer, Pipeline, Comm & Power Line Construction.
- **Official jurisdiction wording used:** Rule X 1(b): appropriations for the Government; each subcommittee's official name states the agencies whose funding it handles.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(b) (appropriations); subcommittee name  <https://appropriations.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 6 securities (1600 Heavy Construction Other Than Bldg Const - Contractors x3, 1623 Water, Sewer, Pipeline, Comm & Power Line Construction x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: DY, FLR, J, MTZ, PRIM, STRL.
- **Overlaps other committees:** PW00 1600-1622 (direct); PW00 1623-1629 (related); PW00/PW12 1600-1622 (direct); PW00/PW12 1623-1629 (related); PW00/PW02 1623-1623 (related)
- **Scrutiny:** `mixed_industries`; `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Review note:** Kept as related (owner decision 2026-10-07): supporting context only; never triggers a flag by itself.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AP00/AP10:4911-4939:related`  related  |  reviewed

- **Scope:** subcommittee AP10 (Energy and Water Development and Related Agencies)
- **SIC range:** 4911-4939
- **Official SIC titles covered:** 4911 Electric Services; 4922 Natural Gas Transmission; 4923 Natural Gas Transmisison & Distribution; 4924 Natural Gas Distribution; 4931 Electric & Other Services Combined; 4932 Gas & Other Services Combined
- **Rationale:** Energy and Water appropriations fund power programs and the Department of Energy. Official SIC titles in 4911-4939: 4911 Electric Services; 4922 Natural Gas Transmission; 4923 Natural Gas Transmisison & Distribution; 4924 Natural Gas Distribution; 4931 Electric & Other Services Combined; 4932 Gas & Other Services Combined.
- **Official jurisdiction wording used:** Rule X 1(b): appropriations for the Government; each subcommittee's official name states the agencies whose funding it handles.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(b) (appropriations); subcommittee name  <https://appropriations.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 35 securities (4911 Electric Services x14, 4922 Natural Gas Transmission x6, 4923 Natural Gas Transmisison & Distribution x1, 4924 Natural Gas Distribution x4, 4931 Electric & Other Services Combined x9, 4932 Gas & Other Services Combined x1)
- **Trades matched:** 2 by 1 politician (primary match for 2). Examples: AEE, AEP, ATO, BEP, CEG, CMS, CNP, D.
- **Overlaps other committees:** IF00 4911-4939 (direct); IF00/IF03 4911-4939 (direct); IF00/IF03 4922-4924 (direct)
- **Scrutiny:** `mixed_industries`; `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Review note:** Kept as related (owner decision 2026-10-07): supporting context only; never triggers a flag by itself.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AP00/AP07:2833-2836:related`  related  |  needs_review

- **Scope:** subcommittee AP07 (Labor, Health and Human Services, Education, and Related Agencies)
- **SIC range:** 2833-2836
- **Official SIC titles covered:** 2833 Medicinal Chemicals & Botanical Products; 2834 Pharmaceutical Preparations; 2835 In Vitro & In Vivo Diagnostic Substances; 2836 Biological Products, (No Diagnostic Substances)
- **Rationale:** Labor-HHS appropriations fund NIH and HHS programs. Official SIC titles in 2833-2836: 2833 Medicinal Chemicals & Botanical Products; 2834 Pharmaceutical Preparations; 2835 In Vitro & In Vivo Diagnostic Substances; 2836 Biological Products, (No Diagnostic Substances).
- **Official jurisdiction wording used:** Rule X 1(b): appropriations for the Government; each subcommittee's official name states the agencies whose funding it handles.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(b) (appropriations); subcommittee name  <https://appropriations.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 48 securities (2833 Medicinal Chemicals & Botanical Products x1, 2834 Pharmaceutical Preparations x35, 2835 In Vitro & In Vivo Diagnostic Substances x1, 2836 Biological Products, (No Diagnostic Substances) x11)
- **Trades matched:** 14 by 1 politician (primary match for 0). Examples: ABBV, ABT, AGIO, ALKS, ALNY, AMGN, ARGX, ARQT.
- **Overlaps other committees:** IF00 2833-2836 (direct); IF00/IF14 2833-2836 (direct); VR00/VR03 2833-2836 (related); WM00/WM02 2833-2836 (related)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AP00/AP07:8000-8099:related`  related  |  reviewed

- **Scope:** subcommittee AP07 (Labor, Health and Human Services, Education, and Related Agencies)
- **SIC range:** 8000-8099
- **Official SIC titles covered:** 8000 Services-Health Services; 8011 Services-Offices & Clinics Of Doctors Of Medicine; 8050 Services-Nursing & Personal Care Facilities; 8051 Services-Skilled Nursing Care Facilities; 8060 Services-Hospitals; 8062 Services-General Medical & Surgical Hospitals, Nec; 8071 Services-Medical Laboratories; 8082 Services-Home Health Care Services; 8090 Services-Misc Health & Allied Services, Nec; 8093 Services-Specialty Outpatient Facilities, Nec
- **Rationale:** Labor-HHS appropriations fund health programs. Official SIC titles in 8000-8099: 8000 Services-Health Services; 8011 Services-Offices & Clinics Of Doctors Of Medicine; 8050 Services-Nursing & Personal Care Facilities; 8051 Services-Skilled Nursing Care Facilities; 8060 Services-Hospitals; 8062 Services-General Medical & Surgical Hospitals, Nec; +4 more.
- **Official jurisdiction wording used:** Rule X 1(b): appropriations for the Government; each subcommittee's official name states the agencies whose funding it handles.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(b) (appropriations); subcommittee name  <https://appropriations.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 15 securities (8050 Services-Nursing & Personal Care Facilities x1, 8060 Services-Hospitals x1, 8062 Services-General Medical & Surgical Hospitals, NEC x4, 8071 Services-Medical Laboratories x6, 8082 Services-Home Health Care Services x1, 8090 Services-Misc Health & Allied Services, NEC x1, 8093 Services-Specialty Outpatient Facilities, NEC x1)
- **Trades matched:** 4 by 1 politician (primary match for 4). Examples: CON, DGX, DVA, EHC, EXAS, GH, HCA, LH.
- **Overlaps other committees:** IF00 8000-8099 (direct); IF00/IF14 8000-8099 (direct); VR00 8050-8099 (related); VR00/VR03 8050-8099 (related); WM00/WM02 8000-8099 (direct)
- **Scrutiny:** `broad_range`; `mixed_industries`; `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Review note:** Kept as related (owner decision 2026-10-07): supporting context only; never triggers a flag by itself.
- **Decision:** [ ] approve   [ ] change   [ ] remove


### AS00: Committee on Armed Services

#### `AS00:3480-3489:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 3480-3489
- **Official SIC titles covered:** 3480 Ordnance & Accessories, (No Vehicles/Guided Missiles)
- **Rationale:** Ordnance and accessories: weapons and ammunition for 'the common defense' (Rule X 1(c)(2),(4)). Official SIC titles in 3480-3489: 3480 Ordnance & Accessories, (No Vehicles/Guided Missiles).
- **Official jurisdiction wording used:** (2) Common defense generally. (4) The Department of Defense generally. (9) ... maintenance of the U.S. shipbuilding and ship repair industrial base. (11) Scientific research and development in support of the armed services. (15) Strategic and critical materials necessary for the common defense.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(c)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 1 securities (3480 Ordnance & Accessories, (No Vehicles/Guided Missiles) x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: AXON.
- **Overlaps other committees:** FA00 3480-3489 (related); AP00/AP02 3480-3489 (direct)
- **Scrutiny:** `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AS00:3720-3729:direct`  direct  |  reviewed

- **Scope:** committee level
- **SIC range:** 3720-3729
- **Official SIC titles covered:** 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec
- **Rationale:** Aircraft and aircraft parts include military aircraft procured by the Department of Defense (Rule X 1(c)(4)). Official SIC titles in 3720-3729: 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec.
- **Official jurisdiction wording used:** (2) Common defense generally. (4) The Department of Defense generally. (9) ... maintenance of the U.S. shipbuilding and ship repair industrial base. (11) Scientific research and development in support of the armed services. (15) Strategic and critical materials necessary for the common defense.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(c)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 11 securities (3720 Aircraft & Parts x1, 3721 Aircraft x2, 3724 Aircraft Engines & Engine Parts x5, 3728 Aircraft Parts & Auxiliary Equipment, NEC x3)
- **Trades matched:** 27 by 1 politician (primary match for 27). Examples: AVAV, BA, DCO, ESLT, HEI.A, HON, HONA, RTX.
- **Overlaps other committees:** PW00 3720-3729 (related); PW00/PW05 3720-3729 (related); SY00 3720-3729 (related); SY00/SY16 3720-3729 (direct); FA00 3720-3729 (related); AP00/AP02 3720-3729 (direct)
- **Scrutiny:** `many_matches`; `overlaps_other_committee`
- **Review note:** Approved direct (owner decision 2026-10-07). The SIC range mixes civilian and military aviation; it is approved direct because the matched suppliers are mainly defense-industrial-base firms, but a civil-only aircraft supplier would match too.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AS00:3730-3732:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 3730-3732
- **Official SIC titles covered:** 3730 Ship & Boat Building & Repairing
- **Rationale:** Ship building and repairing: 'U.S. shipbuilding and ship repair industrial base' (Rule X 1(c)(9)). Includes some civilian boat builders. Official SIC titles in 3730-3732: 3730 Ship & Boat Building & Repairing.
- **Official jurisdiction wording used:** (2) Common defense generally. (4) The Department of Defense generally. (9) ... maintenance of the U.S. shipbuilding and ship repair industrial base. (11) Scientific research and development in support of the armed services. (15) Strategic and critical materials necessary for the common defense.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(c)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (3730 Ship & Boat Building & Repairing x2)
- **Trades matched:** 2 by 1 politician (primary match for 2). Examples: GD, HII.
- **Overlaps other committees:** PW00/PW07 3730-3732 (related); AP00/AP02 3730-3732 (direct)
- **Scrutiny:** `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AS00:3760-3769:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 3760-3769
- **Official SIC titles covered:** 3760 Guided Missiles & Space Vehicles & Parts
- **Rationale:** Guided missiles and space vehicles and parts (Rule X 1(c)(2),(4)). Official SIC titles in 3760-3769: 3760 Guided Missiles & Space Vehicles & Parts.
- **Official jurisdiction wording used:** (2) Common defense generally. (4) The Department of Defense generally. (9) ... maintenance of the U.S. shipbuilding and ship repair industrial base. (11) Scientific research and development in support of the armed services. (15) Strategic and critical materials necessary for the common defense.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(c)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (3760 Guided Missiles & Space Vehicles & Parts x2)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: LMT, VOYG.
- **Overlaps other committees:** SY00 3760-3769 (direct); SY00/SY16 3760-3769 (direct); FA00 3760-3769 (related); AP00/AP02 3760-3769 (direct); AP00/AP19 3760-3769 (related)
- **Scrutiny:** `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AS00:3812-3812:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 3812-3812
- **Official SIC titles covered:** 3812 Search, Detection, Navagation, Guidance, Aeronautical Sys
- **Rationale:** Search, detection, navigation, guidance and aeronautical systems: defense electronics (Rule X 1(c)(4),(11)). Official SIC titles in 3812-3812: 3812 Search, Detection, Navagation, Guidance, Aeronautical Sys.
- **Official jurisdiction wording used:** (2) Common defense generally. (4) The Department of Defense generally. (9) ... maintenance of the U.S. shipbuilding and ship repair industrial base. (11) Scientific research and development in support of the armed services. (15) Strategic and critical materials necessary for the common defense.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(c)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 5 securities (3812 Search, Detection, Navigation, Guidance, Aeronautical Sys x5)
- **Trades matched:** 8 by 2 politicians (primary match for 8). Examples: DRS, GRMN, LHX, NOC, TDY.
- **Overlaps other committees:** FA00 3812-3812 (related); HM00 3812-3812 (related); AP00/AP02 3812-3812 (direct)
- **Scrutiny:** `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AS00/AS35:7373-7373:related`  related  |  reviewed

- **Scope:** subcommittee AS35 (Cyber, Information Technologies, and  Innovation)
- **SIC range:** 7373-7373
- **Official SIC titles covered:** 7373 Services-Computer Integrated Systems Design
- **Rationale:** Computer integrated systems design: DoD cyber and information technology. Generic data processing (7374) is not mapped. Official SIC titles in 7373-7373: 7373 Services-Computer Integrated Systems Design.
- **Official jurisdiction wording used:** (2) Common defense generally. (4) The Department of Defense generally. (9) ... maintenance of the U.S. shipbuilding and ship repair industrial base. (11) Scientific research and development in support of the armed services. (15) Strategic and critical materials necessary for the common defense.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(c); subcommittee name  <https://armedservices.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 8 securities (7373 Services-Computer Integrated Systems Design x8)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CACI, GDDY, IONQ, JKHY, KD, LDOS, QNT, SAIC.
- **Overlaps other committees:** IF00/IF16 7370-7373 (related); JU00/JU03 7370-7373 (related)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Review note:** Kept as related (owner decision 2026-10-07): supporting context only; never triggers a flag by itself. Earlier history: Review history: an earlier draft mapped 7373-7374; 7374 (data processing) was excluded after it matched ADP, a payroll processor.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AS00/AS28:3730-3732:direct`  direct  |  needs_review

- **Scope:** subcommittee AS28 (Seapower and Projection Forces)
- **SIC range:** 3730-3732
- **Official SIC titles covered:** 3730 Ship & Boat Building & Repairing
- **Rationale:** Seapower: ship building and repairing (Rule X 1(c)(9)). Official SIC titles in 3730-3732: 3730 Ship & Boat Building & Repairing.
- **Official jurisdiction wording used:** (2) Common defense generally. (4) The Department of Defense generally. (9) ... maintenance of the U.S. shipbuilding and ship repair industrial base. (11) Scientific research and development in support of the armed services. (15) Strategic and critical materials necessary for the common defense.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(c)(9); subcommittee name  <https://armedservices.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 2 securities (3730 Ship & Boat Building & Repairing x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: GD, HII.
- **Overlaps other committees:** PW00/PW07 3730-3732 (related); AP00/AP02 3730-3732 (direct)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AS00/AS29:3760-3769:direct`  direct  |  needs_review

- **Scope:** subcommittee AS29 (Strategic Forces)
- **SIC range:** 3760-3769
- **Official SIC titles covered:** 3760 Guided Missiles & Space Vehicles & Parts
- **Rationale:** Strategic forces: missiles and space systems. Official SIC titles in 3760-3769: 3760 Guided Missiles & Space Vehicles & Parts.
- **Official jurisdiction wording used:** (2) Common defense generally. (4) The Department of Defense generally. (9) ... maintenance of the U.S. shipbuilding and ship repair industrial base. (11) Scientific research and development in support of the armed services. (15) Strategic and critical materials necessary for the common defense.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(c); subcommittee name  <https://armedservices.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 2 securities (3760 Guided Missiles & Space Vehicles & Parts x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: LMT, VOYG.
- **Overlaps other committees:** SY00 3760-3769 (direct); SY00/SY16 3760-3769 (direct); FA00 3760-3769 (related); AP00/AP02 3760-3769 (direct); AP00/AP19 3760-3769 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AS00/AS29:3812-3812:direct`  direct  |  needs_review

- **Scope:** subcommittee AS29 (Strategic Forces)
- **SIC range:** 3812-3812
- **Official SIC titles covered:** 3812 Search, Detection, Navagation, Guidance, Aeronautical Sys
- **Rationale:** Missile warning, guidance and navigation systems. Official SIC titles in 3812-3812: 3812 Search, Detection, Navagation, Guidance, Aeronautical Sys.
- **Official jurisdiction wording used:** (2) Common defense generally. (4) The Department of Defense generally. (9) ... maintenance of the U.S. shipbuilding and ship repair industrial base. (11) Scientific research and development in support of the armed services. (15) Strategic and critical materials necessary for the common defense.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(c); subcommittee name  <https://armedservices.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 5 securities (3812 Search, Detection, Navigation, Guidance, Aeronautical Sys x5)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: DRS, GRMN, LHX, NOC, TDY.
- **Overlaps other committees:** FA00 3812-3812 (related); HM00 3812-3812 (related); AP00/AP02 3812-3812 (direct)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AS00/AS25:3480-3489:direct`  direct  |  needs_review

- **Scope:** subcommittee AS25 (Tactical Air and Land Forces)
- **SIC range:** 3480-3489
- **Official SIC titles covered:** 3480 Ordnance & Accessories, (No Vehicles/Guided Missiles)
- **Rationale:** Ordnance and ammunition for tactical forces. Official SIC titles in 3480-3489: 3480 Ordnance & Accessories, (No Vehicles/Guided Missiles).
- **Official jurisdiction wording used:** (2) Common defense generally. (4) The Department of Defense generally. (9) ... maintenance of the U.S. shipbuilding and ship repair industrial base. (11) Scientific research and development in support of the armed services. (15) Strategic and critical materials necessary for the common defense.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(c); subcommittee name  <https://armedservices.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 1 securities (3480 Ordnance & Accessories, (No Vehicles/Guided Missiles) x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: AXON.
- **Overlaps other committees:** FA00 3480-3489 (related); AP00/AP02 3480-3489 (direct)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `AS00/AS25:3720-3729:direct`  direct  |  needs_review

- **Scope:** subcommittee AS25 (Tactical Air and Land Forces)
- **SIC range:** 3720-3729
- **Official SIC titles covered:** 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec
- **Rationale:** Tactical air forces: aircraft, engines and parts. Official SIC titles in 3720-3729: 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec.
- **Official jurisdiction wording used:** (2) Common defense generally. (4) The Department of Defense generally. (9) ... maintenance of the U.S. shipbuilding and ship repair industrial base. (11) Scientific research and development in support of the armed services. (15) Strategic and critical materials necessary for the common defense.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(c); subcommittee name  <https://armedservices.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 11 securities (3720 Aircraft & Parts x1, 3721 Aircraft x2, 3724 Aircraft Engines & Engine Parts x5, 3728 Aircraft Parts & Auxiliary Equipment, NEC x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: AVAV, BA, DCO, ESLT, HEI.A, HON, HONA, RTX.
- **Overlaps other committees:** PW00 3720-3729 (related); PW00/PW05 3720-3729 (related); SY00 3720-3729 (related); SY00/SY16 3720-3729 (direct); FA00 3720-3729 (related); AP00/AP02 3720-3729 (direct)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### BA00: Committee on Financial Services

#### `BA00:6000-6099:direct`  direct  |  reviewed

- **Scope:** committee level
- **SIC range:** 6000-6099
- **Official SIC titles covered:** 6021 National Commercial Banks; 6022 State Commercial Banks; 6029 Commercial Banks, Nec; 6035 Savings Institution, Federally Chartered; 6036 Savings Institutions, Not Federally Chartered; 6099 Functions Related To Depository Banking, Nec
- **Rationale:** Depository institutions: 'banks and banking, including deposit insurance' (Rule X 1(h)(1)). Official SIC titles in 6000-6099: 6021 National Commercial Banks; 6022 State Commercial Banks; 6029 Commercial Banks, Nec; 6035 Savings Institution, Federally Chartered; 6036 Savings Institutions, Not Federally Chartered; 6099 Functions Related To Depository Banking, Nec.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 51 securities (6021 National Commercial Banks x18, 6022 State Commercial Banks x19, 6029 Commercial Banks, NEC x11, 6035 Savings Institution, Federally Chartered x2, 6036 Savings Institutions, Not Federally Chartered x1)
- **Trades matched:** 47 by 5 politicians (primary match for 46). Examples: ABCB, ALLY, BAC, BBT, BBVA, BCLYF, BCS, BK.
- **Scrutiny:** `mixed_industries`; `many_matches`
- **Review note:** Approved direct (owner decision 2026-10-07).
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00:6100-6198:direct`  direct  |  reviewed

- **Scope:** committee level
- **SIC range:** 6100-6198
- **Official SIC titles covered:** 6111 Federal & Federally-Sponsored Credit Agencies; 6141 Personal Credit Institutions; 6153 Short-Term Business Credit Institutions; 6159 Miscellaneous Business Credit Institution; 6162 Mortgage Bankers & Loan Correspondents; 6163 Loan Brokers; 6172 Finance Lessors; 6189 Asset-Backed Securities
- **Rationale:** Non-depository credit institutions: 'money and credit' (Rule X 1(h)(7)). Official SIC titles in 6100-6198: 6111 Federal & Federally-Sponsored Credit Agencies; 6141 Personal Credit Institutions; 6153 Short-Term Business Credit Institutions; 6159 Miscellaneous Business Credit Institution; 6162 Mortgage Bankers & Loan Correspondents; 6163 Loan Brokers; +2 more.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 1 securities (6159 Miscellaneous Business Credit Institution x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: IX.
- **Review note:** Split from 6100-6199 direct (owner decision 2026-10-07): Credit institutions (6100-6198) stay direct; SIC 6199 'Finance Services' is a catch-all that mixes card issuers with crypto and advisory firms, so it is separated and treated as related. This piece is direct.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00:6199-6199:related`  related  |  reviewed

- **Scope:** committee level
- **SIC range:** 6199-6199
- **Official SIC titles covered:** 6199 Finance Services
- **Rationale:** Non-depository credit institutions: 'money and credit' (Rule X 1(h)(7)). Official SIC titles in 6199-6199: 6199 Finance Services.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 6 securities (6199 Finance Services x6)
- **Trades matched:** 11 by 4 politicians (primary match for 4). Examples: AXP, COIN, IREN, MSTR, PWP, SYF.
- **Scrutiny:** `related_level`
- **Review note:** Split from 6100-6199 direct (owner decision 2026-10-07): Credit institutions (6100-6198) stay direct; SIC 6199 'Finance Services' is a catch-all that mixes card issuers with crypto and advisory firms, so it is separated and treated as related. This piece is related.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00:6200-6299:direct`  direct  |  reviewed

- **Scope:** committee level
- **SIC range:** 6200-6299
- **Official SIC titles covered:** 6200 Security & Commodity Brokers, Dealers, Exchanges & Services; 6211 Security Brokers, Dealers & Flotation Companies; 6221 Commodity Contracts Brokers & Dealers; 6282 Investment Advice
- **Rationale:** Security and commodity brokers, dealers, exchanges and investment services: 'securities and exchanges' (Rule X 1(h)(9)). Official SIC titles in 6200-6299: 6200 Security & Commodity Brokers, Dealers, Exchanges & Services; 6211 Security Brokers, Dealers & Flotation Companies; 6221 Commodity Contracts Brokers & Dealers; 6282 Investment Advice.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 33 securities (6200 Security & Commodity Brokers, Dealers, Exchanges & Services x6, 6211 Security Brokers, Dealers & Flotation Companies x11, 6221 Commodity Contracts Brokers & Dealers x5, 6282 Investment Advice x11)
- **Trades matched:** 18 by 4 politicians (primary match for 4). Examples: AMP, APO, ARES, BEN, BITB, BLK, BX, CBOE.
- **Overlaps other committees:** AG00 6221-6221 (direct); AG00/AG22 6221-6221 (direct)
- **Scrutiny:** `mixed_industries`; `overlaps_other_committee`
- **Review note:** Approved direct (owner decision 2026-10-07).
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00:6300-6319:direct`  direct  |  reviewed

- **Scope:** committee level
- **SIC range:** 6300-6319
- **Official SIC titles covered:** 6311 Life Insurance
- **Rationale:** Insurance carriers, agents and brokers: 'insurance generally' (Rule X 1(h)(4)). Official SIC titles in 6300-6319: 6311 Life Insurance.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 3 securities (6311 Life Insurance x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: GL, MET, PRU.
- **Review note:** Split from 6300-6499 direct (owner decision 2026-10-07): Ordinary insurance (life, casualty, title, brokers) stays direct; health-plan insurers (6320-6329) are separated and treated as related, so they are not a blanket direct Financial Services match. This piece is direct.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00:6320-6329:related`  related  |  reviewed

- **Scope:** committee level
- **SIC range:** 6320-6329
- **Official SIC titles covered:** 6321 Accident & Health Insurance; 6324 Hospital & Medical Service Plans
- **Rationale:** Insurance carriers, agents and brokers: 'insurance generally' (Rule X 1(h)(4)). Official SIC titles in 6320-6329: 6321 Accident & Health Insurance; 6324 Hospital & Medical Service Plans.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 9 securities (6321 Accident & Health Insurance x3, 6324 Hospital & Medical Service Plans x6)
- **Trades matched:** 19 by 4 politicians (primary match for 16). Examples: AFL, CI, CNC, ELV, HUM, MOH, PFG, UNH.
- **Overlaps other committees:** IF00 6320-6324 (related); IF00/IF14 6320-6324 (related); WM00/WM02 6320-6324 (direct)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Review note:** Split from 6300-6499 direct (owner decision 2026-10-07): Ordinary insurance (life, casualty, title, brokers) stays direct; health-plan insurers (6320-6329) are separated and treated as related, so they are not a blanket direct Financial Services match. This piece is related.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00:6330-6499:direct`  direct  |  reviewed

- **Scope:** committee level
- **SIC range:** 6330-6499
- **Official SIC titles covered:** 6331 Fire, Marine & Casualty Insurance; 6351 Surety Insurance; 6361 Title Insurance; 6399 Insurance Carriers, Nec; 6411 Insurance Agents, Brokers & Service
- **Rationale:** Insurance carriers, agents and brokers: 'insurance generally' (Rule X 1(h)(4)). Official SIC titles in 6330-6499: 6331 Fire, Marine & Casualty Insurance; 6351 Surety Insurance; 6361 Title Insurance; 6399 Insurance Carriers, Nec; 6411 Insurance Agents, Brokers & Service.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 26 securities (6331 Fire, Marine & Casualty Insurance x16, 6361 Title Insurance x1, 6399 Insurance Carriers, NEC x1, 6411 Insurance Agents, Brokers & Service x8)
- **Trades matched:** 33 by 4 politicians (primary match for 27). Examples: ACGL, AFG, AIG, AIZ, AJG, ALL, AON, BRK.B.
- **Scrutiny:** `broad_range`; `mixed_industries`; `many_matches`
- **Review note:** Split from 6300-6499 direct (owner decision 2026-10-07): Ordinary insurance (life, casualty, title, brokers) stays direct; health-plan insurers (6320-6329) are separated and treated as related, so they are not a blanket direct Financial Services match. This piece is direct.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00:6500-6599:related`  related  |  reviewed

- **Scope:** committee level
- **SIC range:** 6500-6599
- **Official SIC titles covered:** 6500 Real Estate; 6510 Real Estate Operators (No Developers) & Lessors; 6512 Operators Of Nonresidential Buildings; 6513 Operators Of Apartment Buildings; 6519 Lessors Of Real Property, Nec; 6531 Real Estate Agents & Managers (For Others); 6532 Real Estate Dealers (For Their Own Account); 6552 Land Subdividers & Developers (No Cemeteries)
- **Rationale:** Real estate: 'public and private housing' and 'urban development' (Rule X 1(h)(8),(10)). Official SIC titles in 6500-6599: 6500 Real Estate; 6510 Real Estate Operators (No Developers) & Lessors; 6512 Operators Of Nonresidential Buildings; 6513 Operators Of Apartment Buildings; 6519 Lessors Of Real Property, Nec; 6531 Real Estate Agents & Managers (For Others); +2 more.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 8 securities (6500 Real Estate x4, 6510 Real Estate Operators (No Developers) & Lessors x1, 6531 Real Estate Agents & Managers (For Others) x3)
- **Trades matched:** 9 by 2 politicians (primary match for 9). Examples: COMP, EFC, FSV, GTY, INVH, JLL, OPEN, UE.
- **Scrutiny:** `mixed_industries`; `related_level`
- **Review note:** Kept as related (owner decision 2026-10-07): supporting context only; never triggers a flag by itself.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00:6700-6793:related`  related  |  reviewed

- **Scope:** committee level
- **SIC range:** 6700-6793
- **Official SIC titles covered:** 6770 Blank Checks; 6792 Oil Royalty Traders
- **Rationale:** Holding and other investment offices, including REITs, are securities issuers (Rule X 1(h)(9)). Official SIC titles in 6700-6793: 6770 Blank Checks; 6792 Oil Royalty Traders.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 1 securities (6792 Oil Royalty Traders x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: LB.
- **Scrutiny:** `related_level`
- **Review note:** Kept as related (owner decision 2026-10-07): supporting context only; never triggers a flag by itself. Earlier history: Review history: an earlier draft mapped 6700-6799; 6794 (patent owners and lessors) was excluded after it matched Dolby Laboratories.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00:6795-6799:related`  related  |  reviewed

- **Scope:** committee level
- **SIC range:** 6795-6799
- **Official SIC titles covered:** 6795 Mineral Royalty Traders; 6798 Real Estate Investment Trusts; 6799 Investors, Nec
- **Rationale:** Mineral royalty trusts and REITs are securities issuers (Rule X 1(h)(9)). Patent owners and lessors (6794) are not mapped here. Official SIC titles in 6795-6799: 6795 Mineral Royalty Traders; 6798 Real Estate Investment Trusts; 6799 Investors, Nec.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 41 securities (6795 Mineral Royalty Traders x1, 6798 Real Estate Investment Trusts x40)
- **Trades matched:** 19 by 2 politicians (primary match for 19). Examples: ADC, ALEX, AMH, AMT, ARE, AVB, BXP, CCI.
- **Scrutiny:** `related_level`
- **Review note:** Kept as related (owner decision 2026-10-07): supporting context only; never triggers a flag by itself. Earlier history: Review history: an earlier draft mapped 6700-6799; 6794 (patent owners and lessors) was excluded after it matched Dolby Laboratories.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00:7320-7320:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 7320-7320
- **Official SIC titles covered:** 7320 Services-Consumer Credit Reporting, Collection Agencies
- **Rationale:** Consumer credit reporting: money and credit (Rule X 1(h)(7)). Official SIC titles in 7320-7320: 7320 Services-Consumer Credit Reporting, Collection Agencies.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 3 securities (7320 Services-Consumer Credit Reporting, Collection Agencies x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: EFX, MCO, SPGI.
- **Scrutiny:** `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00/BA16:6200-6299:direct`  direct  |  reviewed

- **Scope:** subcommittee BA16 (Capital Markets)
- **SIC range:** 6200-6299
- **Official SIC titles covered:** 6200 Security & Commodity Brokers, Dealers, Exchanges & Services; 6211 Security Brokers, Dealers & Flotation Companies; 6221 Commodity Contracts Brokers & Dealers; 6282 Investment Advice
- **Rationale:** Capital markets: securities brokers, dealers and exchanges. Official SIC titles in 6200-6299: 6200 Security & Commodity Brokers, Dealers, Exchanges & Services; 6211 Security Brokers, Dealers & Flotation Companies; 6221 Commodity Contracts Brokers & Dealers; 6282 Investment Advice.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)(9); subcommittee name  <https://financialservices.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 33 securities (6200 Security & Commodity Brokers, Dealers, Exchanges & Services x6, 6211 Security Brokers, Dealers & Flotation Companies x11, 6221 Commodity Contracts Brokers & Dealers x5, 6282 Investment Advice x11)
- **Trades matched:** 14 by 3 politicians (primary match for 14). Examples: AMP, APO, ARES, BEN, BITB, BLK, BX, CBOE.
- **Overlaps other committees:** AG00 6221-6221 (direct); AG00/AG22 6221-6221 (direct)
- **Scrutiny:** `mixed_industries`; `inferred_from_name`; `overlaps_other_committee`
- **Review note:** Approved direct (owner decision 2026-10-07).
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00/BA16:6770-6770:direct`  direct  |  needs_review

- **Scope:** subcommittee BA16 (Capital Markets)
- **SIC range:** 6770-6770
- **Official SIC titles covered:** 6770 Blank Checks
- **Rationale:** Blank check companies are securities issuers. Official SIC titles in 6770-6770: 6770 Blank Checks.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)(9); subcommittee name  <https://financialservices.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 0 securities (no current security in this range)
- **Trades matched:** 0 by 0 politicians (primary match for 0).
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00/BA20:6000-6099:direct`  direct  |  reviewed

- **Scope:** subcommittee BA20 (Financial Institutions)
- **SIC range:** 6000-6099
- **Official SIC titles covered:** 6021 National Commercial Banks; 6022 State Commercial Banks; 6029 Commercial Banks, Nec; 6035 Savings Institution, Federally Chartered; 6036 Savings Institutions, Not Federally Chartered; 6099 Functions Related To Depository Banking, Nec
- **Rationale:** Financial institutions: depository institutions. Official SIC titles in 6000-6099: 6021 National Commercial Banks; 6022 State Commercial Banks; 6029 Commercial Banks, Nec; 6035 Savings Institution, Federally Chartered; 6036 Savings Institutions, Not Federally Chartered; 6099 Functions Related To Depository Banking, Nec.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)(1),(7); subcommittee name  <https://financialservices.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 51 securities (6021 National Commercial Banks x18, 6022 State Commercial Banks x19, 6029 Commercial Banks, NEC x11, 6035 Savings Institution, Federally Chartered x2, 6036 Savings Institutions, Not Federally Chartered x1)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: ABCB, ALLY, BAC, BBT, BBVA, BCLYF, BCS, BK.
- **Scrutiny:** `mixed_industries`; `inferred_from_name`
- **Review note:** Approved direct (owner decision 2026-10-07).
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00/BA20:6100-6198:direct`  direct  |  reviewed

- **Scope:** subcommittee BA20 (Financial Institutions)
- **SIC range:** 6100-6198
- **Official SIC titles covered:** 6111 Federal & Federally-Sponsored Credit Agencies; 6141 Personal Credit Institutions; 6153 Short-Term Business Credit Institutions; 6159 Miscellaneous Business Credit Institution; 6162 Mortgage Bankers & Loan Correspondents; 6163 Loan Brokers; 6172 Finance Lessors; 6189 Asset-Backed Securities
- **Rationale:** Financial institutions: credit institutions. Official SIC titles in 6100-6198: 6111 Federal & Federally-Sponsored Credit Agencies; 6141 Personal Credit Institutions; 6153 Short-Term Business Credit Institutions; 6159 Miscellaneous Business Credit Institution; 6162 Mortgage Bankers & Loan Correspondents; 6163 Loan Brokers; +2 more.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)(1),(7); subcommittee name  <https://financialservices.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 1 securities (6159 Miscellaneous Business Credit Institution x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: IX.
- **Scrutiny:** `inferred_from_name`
- **Review note:** Split from 6100-6199 direct (owner decision 2026-10-07): Credit institutions (6100-6198) stay direct; SIC 6199 'Finance Services' is a catch-all that mixes card issuers with crypto and advisory firms, so it is separated and treated as related. This piece is direct.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00/BA20:6199-6199:related`  related  |  reviewed

- **Scope:** subcommittee BA20 (Financial Institutions)
- **SIC range:** 6199-6199
- **Official SIC titles covered:** 6199 Finance Services
- **Rationale:** Financial institutions: credit institutions. Official SIC titles in 6199-6199: 6199 Finance Services.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)(1),(7); subcommittee name  <https://financialservices.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 6 securities (6199 Finance Services x6)
- **Trades matched:** 7 by 2 politicians (primary match for 7). Examples: AXP, COIN, IREN, MSTR, PWP, SYF.
- **Scrutiny:** `inferred_from_name`; `related_level`
- **Review note:** Split from 6100-6199 direct (owner decision 2026-10-07): Credit institutions (6100-6198) stay direct; SIC 6199 'Finance Services' is a catch-all that mixes card issuers with crypto and advisory firms, so it is separated and treated as related. This piece is related.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00/BA04:1520-1531:related`  related  |  reviewed

- **Scope:** subcommittee BA04 (Housing and Insurance)
- **SIC range:** 1520-1531
- **Official SIC titles covered:** 1520 General Bldg Contractors - Residential Bldgs; 1531 Operative Builders
- **Rationale:** Residential builders supply private housing (Rule X 1(h)(8)). Official SIC titles in 1520-1531: 1520 General Bldg Contractors - Residential Bldgs; 1531 Operative Builders.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)(4),(8); subcommittee name  <https://financialservices.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 7 securities (1520 General Bldg Contractors - Residential Bldgs x2, 1531 Operative Builders x5)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: DHI, IBP, LEN, LGIH, NVR, TMHC, TPH.
- **Scrutiny:** `mixed_industries`; `inferred_from_name`; `related_level`
- **Review note:** Kept as related (owner decision 2026-10-07): supporting context only; never triggers a flag by itself.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00/BA04:6300-6319:direct`  direct  |  reviewed

- **Scope:** subcommittee BA04 (Housing and Insurance)
- **SIC range:** 6300-6319
- **Official SIC titles covered:** 6311 Life Insurance
- **Rationale:** Insurance. Official SIC titles in 6300-6319: 6311 Life Insurance.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)(4),(8); subcommittee name  <https://financialservices.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 3 securities (6311 Life Insurance x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: GL, MET, PRU.
- **Scrutiny:** `inferred_from_name`
- **Review note:** Split from 6300-6499 direct (owner decision 2026-10-07): Ordinary insurance (life, casualty, title, brokers) stays direct; health-plan insurers (6320-6329) are separated and treated as related, so they are not a blanket direct Financial Services match. This piece is direct.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00/BA04:6320-6329:related`  related  |  reviewed

- **Scope:** subcommittee BA04 (Housing and Insurance)
- **SIC range:** 6320-6329
- **Official SIC titles covered:** 6321 Accident & Health Insurance; 6324 Hospital & Medical Service Plans
- **Rationale:** Insurance. Official SIC titles in 6320-6329: 6321 Accident & Health Insurance; 6324 Hospital & Medical Service Plans.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)(4),(8); subcommittee name  <https://financialservices.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 9 securities (6321 Accident & Health Insurance x3, 6324 Hospital & Medical Service Plans x6)
- **Trades matched:** 3 by 1 politician (primary match for 3). Examples: AFL, CI, CNC, ELV, HUM, MOH, PFG, UNH.
- **Overlaps other committees:** IF00 6320-6324 (related); IF00/IF14 6320-6324 (related); WM00/WM02 6320-6324 (direct)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Review note:** Split from 6300-6499 direct (owner decision 2026-10-07): Ordinary insurance (life, casualty, title, brokers) stays direct; health-plan insurers (6320-6329) are separated and treated as related, so they are not a blanket direct Financial Services match. This piece is related.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00/BA04:6330-6499:direct`  direct  |  reviewed

- **Scope:** subcommittee BA04 (Housing and Insurance)
- **SIC range:** 6330-6499
- **Official SIC titles covered:** 6331 Fire, Marine & Casualty Insurance; 6351 Surety Insurance; 6361 Title Insurance; 6399 Insurance Carriers, Nec; 6411 Insurance Agents, Brokers & Service
- **Rationale:** Insurance. Official SIC titles in 6330-6499: 6331 Fire, Marine & Casualty Insurance; 6351 Surety Insurance; 6361 Title Insurance; 6399 Insurance Carriers, Nec; 6411 Insurance Agents, Brokers & Service.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)(4),(8); subcommittee name  <https://financialservices.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 26 securities (6331 Fire, Marine & Casualty Insurance x16, 6361 Title Insurance x1, 6399 Insurance Carriers, NEC x1, 6411 Insurance Agents, Brokers & Service x8)
- **Trades matched:** 6 by 1 politician (primary match for 6). Examples: ACGL, AFG, AIG, AIZ, AJG, ALL, AON, BRK.B.
- **Scrutiny:** `broad_range`; `mixed_industries`; `inferred_from_name`
- **Review note:** Split from 6300-6499 direct (owner decision 2026-10-07): Ordinary insurance (life, casualty, title, brokers) stays direct; health-plan insurers (6320-6329) are separated and treated as related, so they are not a blanket direct Financial Services match. This piece is direct.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00/BA04:6500-6599:related`  related  |  reviewed

- **Scope:** subcommittee BA04 (Housing and Insurance)
- **SIC range:** 6500-6599
- **Official SIC titles covered:** 6500 Real Estate; 6510 Real Estate Operators (No Developers) & Lessors; 6512 Operators Of Nonresidential Buildings; 6513 Operators Of Apartment Buildings; 6519 Lessors Of Real Property, Nec; 6531 Real Estate Agents & Managers (For Others); 6532 Real Estate Dealers (For Their Own Account); 6552 Land Subdividers & Developers (No Cemeteries)
- **Rationale:** Housing: real estate. Official SIC titles in 6500-6599: 6500 Real Estate; 6510 Real Estate Operators (No Developers) & Lessors; 6512 Operators Of Nonresidential Buildings; 6513 Operators Of Apartment Buildings; 6519 Lessors Of Real Property, Nec; 6531 Real Estate Agents & Managers (For Others); +2 more.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)(4),(8); subcommittee name  <https://financialservices.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 8 securities (6500 Real Estate x4, 6510 Real Estate Operators (No Developers) & Lessors x1, 6531 Real Estate Agents & Managers (For Others) x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: COMP, EFC, FSV, GTY, INVH, JLL, OPEN, UE.
- **Scrutiny:** `mixed_industries`; `inferred_from_name`; `related_level`
- **Review note:** Downgraded from direct to related (owner decision 2026-10-07): real estate agents and operators relate only indirectly to housing policy; consistent with the committee-level related row.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `BA00/BA04:6798-6798:related`  related  |  needs_review

- **Scope:** subcommittee BA04 (Housing and Insurance)
- **SIC range:** 6798-6798
- **Official SIC titles covered:** 6798 Real Estate Investment Trusts
- **Rationale:** REITs hold real estate. Official SIC titles in 6798-6798: 6798 Real Estate Investment Trusts.
- **Official jurisdiction wording used:** (1) Banks and banking, including deposit insurance and Federal monetary policy. (3) Financial aid to commerce and industry (other than transportation). (4) Insurance generally. (7) Money and credit. (8) Public and private housing. (9) Securities and exchanges. (10) Urban development.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(h)(4),(8); subcommittee name  <https://financialservices.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 40 securities (6798 Real Estate Investment Trusts x40)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: ADC, ALEX, AMH, AMT, ARE, AVB, BXP, CCI.
- **Scrutiny:** `inferred_from_name`; `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### BU00: Committee on the Budget

#### `BU00:none:none`  none  |  needs_review

- **Scope:** committee level
- **SIC range:** none (reviewed as having no industry-specific jurisdiction)
- **Rationale:** Budget process and budget resolutions (Rule X 1(d)) are economy-wide, not tied to an industry.
- **Official jurisdiction wording used:** Reviewed for industry-specific jurisdiction; none identified in the official text.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X (clause for this committee) or the committee's establishing resolution  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **Decision:** [ ] approve   [ ] change   [ ] remove


### EC00: Joint Economic Committee

#### `EC00:none:none`  none  |  needs_review

- **Scope:** committee level
- **SIC range:** none (reviewed as having no industry-specific jurisdiction)
- **Rationale:** The Joint Economic Committee studies the economy as a whole; it has no industry-specific jurisdiction.
- **Official jurisdiction wording used:** Reviewed for industry-specific jurisdiction; none identified in the official text.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X (clause for this committee) or the committee's establishing resolution  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `committee_name`: inferred from the committee name, not verified
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### ED00: Committee on Education and Workforce

#### `ED00:7360-7369:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 7360-7369
- **Official SIC titles covered:** 7361 Services-Employment Agencies; 7363 Services-Help Supply Services
- **Rationale:** Help supply and staffing services: labor standards, wages and hours (Rule X 1(e)(5),(11)). Official SIC titles in 7360-7369: 7361 Services-Employment Agencies; 7363 Services-Help Supply Services.
- **Official jurisdiction wording used:** (5) Labor standards and statistics. (6) Education or labor generally. (14) Department of Education. (15) Department of Labor.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(e)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 1 securities (7363 Services-Help Supply Services x1)
- **Trades matched:** 2 by 1 politician (primary match for 2). Examples: MAN.
- **Scrutiny:** `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `ED00:8200-8299:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 8200-8299
- **Official SIC titles covered:** 8200 Services-Educational Services
- **Rationale:** Educational services: 'education or labor generally' (Rule X 1(e)(6)). Official SIC titles in 8200-8299: 8200 Services-Educational Services.
- **Official jurisdiction wording used:** (5) Labor standards and statistics. (6) Education or labor generally. (14) Department of Education. (15) Department of Labor.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(e)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 1 securities (8200 Services-Educational Services x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: LRN.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `ED00/ED14:8200-8299:direct`  direct  |  needs_review

- **Scope:** subcommittee ED14 (Early Childhood, Elementary, and Secondary Education)
- **SIC range:** 8200-8299
- **Official SIC titles covered:** 8200 Services-Educational Services
- **Rationale:** Elementary and secondary education. Official SIC titles in 8200-8299: 8200 Services-Educational Services.
- **Official jurisdiction wording used:** (5) Labor standards and statistics. (6) Education or labor generally. (14) Department of Education. (15) Department of Labor.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(e)(6); subcommittee name  <https://edworkforce.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 1 securities (8200 Services-Educational Services x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: LRN.
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `ED00/ED13:8200-8299:direct`  direct  |  needs_review

- **Scope:** subcommittee ED13 (Higher Education and Workforce Development)
- **SIC range:** 8200-8299
- **Official SIC titles covered:** 8200 Services-Educational Services
- **Rationale:** Higher education. Official SIC titles in 8200-8299: 8200 Services-Educational Services.
- **Official jurisdiction wording used:** (5) Labor standards and statistics. (6) Education or labor generally. (14) Department of Education. (15) Department of Labor.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(e)(6); subcommittee name  <https://edworkforce.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 1 securities (8200 Services-Educational Services x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: LRN.
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### FA00: Committee on Foreign Affairs

#### `FA00:3480-3489:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 3480-3489
- **Official SIC titles covered:** 3480 Ordnance & Accessories, (No Vehicles/Guided Missiles)
- **Rationale:** Ordnance: arms export controls (Rule X 1(i)(4)). Official SIC titles in 3480-3489: 3480 Ordnance & Accessories, (No Vehicles/Guided Missiles).
- **Official jurisdiction wording used:** (4) Export controls, including nonproliferation of nuclear technology and nuclear hardware. (11) Measures to foster commercial intercourse with foreign nations and to safeguard American business interests abroad. (12) International economic policy.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(i)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 1 securities (3480 Ordnance & Accessories, (No Vehicles/Guided Missiles) x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: AXON.
- **Overlaps other committees:** AS00 3480-3489 (direct); AS00/AS25 3480-3489 (direct); AP00/AP02 3480-3489 (direct)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `FA00:3720-3729:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 3720-3729
- **Official SIC titles covered:** 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec
- **Rationale:** Aircraft: defense export controls (Rule X 1(i)(4)). Official SIC titles in 3720-3729: 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec.
- **Official jurisdiction wording used:** (4) Export controls, including nonproliferation of nuclear technology and nuclear hardware. (11) Measures to foster commercial intercourse with foreign nations and to safeguard American business interests abroad. (12) International economic policy.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(i)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 11 securities (3720 Aircraft & Parts x1, 3721 Aircraft x2, 3724 Aircraft Engines & Engine Parts x5, 3728 Aircraft Parts & Auxiliary Equipment, NEC x3)
- **Trades matched:** 11 by 2 politicians (primary match for 11). Examples: AVAV, BA, DCO, ESLT, HEI.A, HON, HONA, RTX.
- **Overlaps other committees:** AS00 3720-3729 (direct); AS00/AS25 3720-3729 (direct); PW00 3720-3729 (related); PW00/PW05 3720-3729 (related); SY00 3720-3729 (related); SY00/SY16 3720-3729 (direct); AP00/AP02 3720-3729 (direct)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `FA00:3760-3769:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 3760-3769
- **Official SIC titles covered:** 3760 Guided Missiles & Space Vehicles & Parts
- **Rationale:** Missiles and space vehicles: export controls and nonproliferation (Rule X 1(i)(4)). Official SIC titles in 3760-3769: 3760 Guided Missiles & Space Vehicles & Parts.
- **Official jurisdiction wording used:** (4) Export controls, including nonproliferation of nuclear technology and nuclear hardware. (11) Measures to foster commercial intercourse with foreign nations and to safeguard American business interests abroad. (12) International economic policy.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(i)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (3760 Guided Missiles & Space Vehicles & Parts x2)
- **Trades matched:** 2 by 1 politician (primary match for 2). Examples: LMT, VOYG.
- **Overlaps other committees:** AS00 3760-3769 (direct); AS00/AS29 3760-3769 (direct); SY00 3760-3769 (direct); SY00/SY16 3760-3769 (direct); AP00/AP02 3760-3769 (direct); AP00/AP19 3760-3769 (related)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `FA00:3812-3812:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 3812-3812
- **Official SIC titles covered:** 3812 Search, Detection, Navagation, Guidance, Aeronautical Sys
- **Rationale:** Defense electronics: export controls (Rule X 1(i)(4)). Official SIC titles in 3812-3812: 3812 Search, Detection, Navagation, Guidance, Aeronautical Sys.
- **Official jurisdiction wording used:** (4) Export controls, including nonproliferation of nuclear technology and nuclear hardware. (11) Measures to foster commercial intercourse with foreign nations and to safeguard American business interests abroad. (12) International economic policy.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(i)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 5 securities (3812 Search, Detection, Navigation, Guidance, Aeronautical Sys x5)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: DRS, GRMN, LHX, NOC, TDY.
- **Overlaps other committees:** AS00 3812-3812 (direct); AS00/AS29 3812-3812 (direct); HM00 3812-3812 (related); AP00/AP02 3812-3812 (direct)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### GO00: Committee on Oversight and Government Reform

#### `GO00:none:none`  none  |  needs_review

- **Scope:** committee level
- **SIC range:** none (reviewed as having no industry-specific jurisdiction)
- **Rationale:** Government-wide oversight and operations (Rule X 1(n)) is not tied to an industry.
- **Official jurisdiction wording used:** Reviewed for industry-specific jurisdiction; none identified in the official text.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X (clause for this committee) or the committee's establishing resolution  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `committee_name`: inferred from the committee name, not verified
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### HA00: Committee on House Administration

#### `HA00:none:none`  none  |  needs_review

- **Scope:** committee level
- **SIC range:** none (reviewed as having no industry-specific jurisdiction)
- **Rationale:** House administration, elections and congressional operations are not tied to an industry.
- **Official jurisdiction wording used:** Reviewed for industry-specific jurisdiction; none identified in the official text.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X (clause for this committee) or the committee's establishing resolution  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `committee_name`: inferred from the committee name, not verified
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### HM00: Committee on Homeland Security

#### `HM00:3812-3812:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 3812-3812
- **Official SIC titles covered:** 3812 Search, Detection, Navagation, Guidance, Aeronautical Sys
- **Rationale:** Detection and navigation systems used in border, port and transportation security (Rule X 1(j)(3)(A),(F)). Official SIC titles in 3812-3812: 3812 Search, Detection, Navagation, Guidance, Aeronautical Sys.
- **Official jurisdiction wording used:** (3) Functions of the Department of Homeland Security relating to: (A) Border and port security. (B) Customs. (D) Domestic preparedness for and collective response to terrorism. (E) Research and development. (F) Transportation security. (G) Cybersecurity.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(j)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 5 securities (3812 Search, Detection, Navigation, Guidance, Aeronautical Sys x5)
- **Trades matched:** 1 by 1 politician (primary match for 0). Examples: DRS, GRMN, LHX, NOC, TDY.
- **Overlaps other committees:** AS00 3812-3812 (direct); AS00/AS29 3812-3812 (direct); FA00 3812-3812 (related); AP00/AP02 3812-3812 (direct)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `HM00:3844-3844:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 3844-3844
- **Official SIC titles covered:** 3844 X-Ray Apparatus & Tubes & Related Irradiation Apparatus
- **Rationale:** X-ray apparatus used in security screening (Rule X 1(j)(3)(F)). Official SIC titles in 3844-3844: 3844 X-Ray Apparatus & Tubes & Related Irradiation Apparatus.
- **Official jurisdiction wording used:** (3) Functions of the Department of Homeland Security relating to: (A) Border and port security. (B) Customs. (D) Domestic preparedness for and collective response to terrorism. (E) Research and development. (F) Transportation security. (G) Cybersecurity.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(j)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (3844 X-Ray Apparatus & Tubes & Related Irradiation Apparatus x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: GEHC, HOLX.
- **Overlaps other committees:** IF00 3841-3845 (direct); IF00/IF14 3841-3845 (direct); WM00/WM02 3841-3845 (related)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `HM00/HM07:4011-4013:related`  related  |  needs_review

- **Scope:** subcommittee HM07 (Transportation and Maritime Security)
- **SIC range:** 4011-4013
- **Official SIC titles covered:** 4011 Railroads, Line-Haul Operating; 4013 Railroad Switching & Terminal Establishments
- **Rationale:** Railroads: transportation security. Official SIC titles in 4011-4013: 4011 Railroads, Line-Haul Operating; 4013 Railroad Switching & Terminal Establishments.
- **Official jurisdiction wording used:** (3) Functions of the Department of Homeland Security relating to: (A) Border and port security. (B) Customs. (D) Domestic preparedness for and collective response to terrorism. (E) Research and development. (F) Transportation security. (G) Cybersecurity.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(j)(3)(F); subcommittee name  <https://homeland.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 5 securities (4011 Railroads, Line-Haul Operating x5)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: CP, CSX, FIP, NSC, UNP.
- **Overlaps other committees:** PW00 4011-4013 (direct); PW00/PW14 4011-4013 (direct)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `HM00/HM07:4400-4499:related`  related  |  reviewed

- **Scope:** subcommittee HM07 (Transportation and Maritime Security)
- **SIC range:** 4400-4499
- **Official SIC titles covered:** 4400 Water Transportation; 4412 Deep Sea Foreign Transportation Of Freight
- **Rationale:** Water transportation: maritime security. Official SIC titles in 4400-4499: 4400 Water Transportation; 4412 Deep Sea Foreign Transportation Of Freight.
- **Official jurisdiction wording used:** (3) Functions of the Department of Homeland Security relating to: (A) Border and port security. (B) Customs. (D) Domestic preparedness for and collective response to terrorism. (E) Research and development. (F) Transportation security. (G) Cybersecurity.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(j)(3)(F); subcommittee name  <https://homeland.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 6 securities (4400 Water Transportation x4, 4412 Deep Sea Foreign Transportation of  Freight x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CCL, ICON, NCLH, RCL, SFL, VIK.
- **Overlaps other committees:** PW00 4400-4499 (direct); PW00/PW07 4400-4499 (direct)
- **Scrutiny:** `mixed_industries`; `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Review note:** Kept as related (owner decision 2026-10-07): supporting context only; never triggers a flag by itself.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `HM00/HM07:4500-4599:related`  related  |  needs_review

- **Scope:** subcommittee HM07 (Transportation and Maritime Security)
- **SIC range:** 4500-4599
- **Official SIC titles covered:** 4512 Air Transportation, Scheduled; 4513 Air Courier Services; 4522 Air Transportation, Nonscheduled; 4581 Airports, Flying Fields & Airport Terminal Services
- **Rationale:** Air transportation: transportation security. Official SIC titles in 4500-4599: 4512 Air Transportation, Scheduled; 4513 Air Courier Services; 4522 Air Transportation, Nonscheduled; 4581 Airports, Flying Fields & Airport Terminal Services.
- **Official jurisdiction wording used:** (3) Functions of the Department of Homeland Security relating to: (A) Border and port security. (B) Customs. (D) Domestic preparedness for and collective response to terrorism. (E) Research and development. (F) Transportation security. (G) Cybersecurity.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(j)(3)(F); subcommittee name  <https://homeland.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 6 securities (4512 Air Transportation, Scheduled x5, 4513 Air Courier Services x1)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: ALK, DAL, FDX, LUV, UAL, VLRS.
- **Overlaps other committees:** PW00 4500-4599 (direct); PW00/PW05 4500-4599 (direct)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### IF00: Committee on Energy and Commerce

#### `IF00:1200-1299:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 1200-1299
- **Official SIC titles covered:** 1220 Bituminous Coal & Lignite Mining; 1221 Bituminous Coal & Lignite Surface Mining
- **Rationale:** Coal mining: fossil fuel energy resources (Rule X 1(f)(6)). Official SIC titles in 1200-1299: 1220 Bituminous Coal & Lignite Mining; 1221 Bituminous Coal & Lignite Surface Mining.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 1 securities (1221 Bituminous Coal & Lignite Surface Mining x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: ARLP.
- **Overlaps other committees:** II00 1200-1299 (direct); II00/II06 1200-1299 (direct)
- **Scrutiny:** `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:1311-1311:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 1311-1311
- **Official SIC titles covered:** 1311 Crude Petroleum & Natural Gas
- **Rationale:** Crude petroleum and natural gas: 'exploration, production ... of energy resources, including all fossil fuels' (Rule X 1(f)(6)). Official SIC titles in 1311-1311: 1311 Crude Petroleum & Natural Gas.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 22 securities (1311 Crude Petroleum & Natural Gas x22)
- **Trades matched:** 6 by 2 politicians (primary match for 3). Examples: AESI, APA, CHRD, CNQ, CTRA, DMLP, DVN, EOG.
- **Overlaps other committees:** II00 1311-1311 (related); II00/II06 1311-1311 (direct); AP00/AP10 1311-1311 (related)
- **Scrutiny:** `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:1381-1389:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 1381-1389
- **Official SIC titles covered:** 1381 Drilling Oil & Gas Wells; 1382 Oil & Gas Field Exploration Services; 1389 Oil & Gas Field Services, Nec
- **Rationale:** Oil and gas field services support energy resource production (Rule X 1(f)(6)). Official SIC titles in 1381-1389: 1381 Drilling Oil & Gas Wells; 1382 Oil & Gas Field Exploration Services; 1389 Oil & Gas Field Services, Nec.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 4 securities (1382 Oil & Gas Field Exploration Services x1, 1389 Oil & Gas Field Services, NEC x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: HAL, PBA, SLB, WBI.
- **Overlaps other committees:** II00/II06 1381-1389 (related)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:2833-2836:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 2833-2836
- **Official SIC titles covered:** 2833 Medicinal Chemicals & Botanical Products; 2834 Pharmaceutical Preparations; 2835 In Vitro & In Vivo Diagnostic Substances; 2836 Biological Products, (No Diagnostic Substances)
- **Rationale:** Drugs and biologicals: biomedical research and public health (Rule X 1(f)(1),(3),(12)). Official SIC titles in 2833-2836: 2833 Medicinal Chemicals & Botanical Products; 2834 Pharmaceutical Preparations; 2835 In Vitro & In Vivo Diagnostic Substances; 2836 Biological Products, (No Diagnostic Substances).
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 48 securities (2833 Medicinal Chemicals & Botanical Products x1, 2834 Pharmaceutical Preparations x35, 2835 In Vitro & In Vivo Diagnostic Substances x1, 2836 Biological Products, (No Diagnostic Substances) x11)
- **Trades matched:** 14 by 4 politicians (primary match for 2). Examples: ABBV, ABT, AGIO, ALKS, ALNY, AMGN, ARGX, ARQT.
- **Overlaps other committees:** VR00/VR03 2833-2836 (related); AP00/AP01 2833-2836 (related); AP00/AP07 2833-2836 (related); WM00/WM02 2833-2836 (related)
- **Scrutiny:** `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:2911-2911:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 2911-2911
- **Official SIC titles covered:** 2911 Petroleum Refining
- **Rationale:** Petroleum refining: marketing and pricing of energy resources (Rule X 1(f)(6)). Official SIC titles in 2911-2911: 2911 Petroleum Refining.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 8 securities (2911 Petroleum Refining x8)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: BP, COP, CVX, IMO, MPC, PSX, VLO, XOM.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:3661-3669:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 3661-3669
- **Official SIC titles covered:** 3661 Telephone & Telegraph Apparatus; 3663 Radio & Tv Broadcasting & Communications Equipment; 3669 Communications Equipment, Nec
- **Rationale:** Communications equipment (Rule X 1(f)(14)). Official SIC titles in 3661-3669: 3661 Telephone & Telegraph Apparatus; 3663 Radio & Tv Broadcasting & Communications Equipment; 3669 Communications Equipment, Nec.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 9 securities (3661 Telephone & Telegraph Apparatus x2, 3663 Radio & Tv Broadcasting & Communications Equipment x5, 3669 Communications Equipment, NEC x2)
- **Trades matched:** 2 by 1 politician (primary match for 2). Examples: CIEN, ESE, FN, LITE, MSI, NOK, QCOM, UI.
- **Scrutiny:** `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:3841-3845:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 3841-3845
- **Official SIC titles covered:** 3841 Surgical & Medical Instruments & Apparatus; 3842 Orthopedic, Prosthetic & Surgical Appliances & Supplies; 3843 Dental Equipment & Supplies; 3844 X-Ray Apparatus & Tubes & Related Irradiation Apparatus; 3845 Electromedical & Electrotherapeutic Apparatus
- **Rationale:** Medical instruments and devices: health (Rule X 1(f)(3)). Official SIC titles in 3841-3845: 3841 Surgical & Medical Instruments & Apparatus; 3842 Orthopedic, Prosthetic & Surgical Appliances & Supplies; 3843 Dental Equipment & Supplies; 3844 X-Ray Apparatus & Tubes & Related Irradiation Apparatus; 3845 Electromedical & Electrotherapeutic Apparatus.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 24 securities (3841 Surgical & Medical Instruments & Apparatus x13, 3842 Orthopedic, Prosthetic & Surgical Appliances & Supplies x7, 3844 X-Ray Apparatus & Tubes & Related Irradiation Apparatus x2, 3845 Electromedical & Electrotherapeutic Apparatus x2)
- **Trades matched:** 6 by 1 politician (primary match for 0). Examples: ALGN, AORT, ATRC, BAX, BDX, BSX, CDRE, DXCM.
- **Overlaps other committees:** HM00 3844-3844 (related); WM00/WM02 3841-3845 (related)
- **Scrutiny:** `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:3851-3851:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 3851-3851
- **Official SIC titles covered:** 3851 Ophthalmic Goods
- **Rationale:** Ophthalmic goods are medical products (Rule X 1(f)(3)). Official SIC titles in 3851-3851: 3851 Ophthalmic Goods.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (3851 Ophthalmic Goods x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: ALC, COO.
- **Scrutiny:** `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:4610-4619:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 4610-4619
- **Official SIC titles covered:** 4610 Pipe Lines (No Natural Gas)
- **Rationale:** Pipelines are regulated for rates by FERC, within E&C jurisdiction (Rule X 1(f)(10)). Official SIC titles in 4610-4619: 4610 Pipe Lines (No Natural Gas).
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (4610 Pipe Lines (No Natural Gas) x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: DINO, ENB.
- **Overlaps other committees:** PW00 4600-4619 (related); PW00/PW14 4610-4619 (direct)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:4700-4729:related`  related  |  reviewed

- **Scope:** committee level
- **SIC range:** 4700-4729
- **Official SIC titles covered:** 4700 Transportation Services
- **Rationale:** Travel arrangement and tour services: 'travel and tourism' (Rule X 1(f)(15)). Official SIC titles in 4700-4729: 4700 Transportation Services.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (4700 Transportation Services x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: BKNG, EXPE.
- **Scrutiny:** `related_level`
- **Review note:** Kept as related (owner decision 2026-10-07): supporting context only; never triggers a flag by itself. Earlier history: Review history: added when 4700-4729 (travel arrangement) was removed from Transportation and Infrastructure after a false positive on Booking Holdings.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:4800-4899:direct`  direct  |  reviewed

- **Scope:** committee level
- **SIC range:** 4800-4899
- **Official SIC titles covered:** 4812 Radiotelephone Communications; 4813 Telephone Communications (No Radiotelephone); 4822 Telegraph & Other Message Communications; 4832 Radio Broadcasting Stations; 4833 Television Broadcasting Stations; 4841 Cable & Other Pay Television Services; 4899 Communications Services, Nec
- **Rationale:** Communications services: 'regulation of interstate and foreign communications' (Rule X 1(f)(14)). Official SIC titles in 4800-4899: 4812 Radiotelephone Communications; 4813 Telephone Communications (No Radiotelephone); 4822 Telegraph & Other Message Communications; 4832 Radio Broadcasting Stations; 4833 Television Broadcasting Stations; 4841 Cable & Other Pay Television Services; +1 more.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 19 securities (4812 Radiotelephone Communications x1, 4813 Telephone Communications (No Radiotelephone) x5, 4832 Radio Broadcasting Stations x2, 4833 Television Broadcasting Stations x5, 4841 Cable & Other Pay Television Services x4, 4899 Communications Services, NEC x2)
- **Trades matched:** 3 by 2 politicians (primary match for 0). Examples: AMX, CHTR, CMCSA, FOX, FOXA, FWONK, KT, LBRDK.
- **Scrutiny:** `mixed_industries`
- **Review note:** Approved direct (owner decision 2026-10-07).
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:4911-4939:direct`  direct  |  reviewed

- **Scope:** committee level
- **SIC range:** 4911-4939
- **Official SIC titles covered:** 4911 Electric Services; 4922 Natural Gas Transmission; 4923 Natural Gas Transmisison & Distribution; 4924 Natural Gas Distribution; 4931 Electric & Other Services Combined; 4932 Gas & Other Services Combined
- **Rationale:** Electric, gas and combined utilities: 'generation and marketing of power ... ratemaking for all power' (Rule X 1(f)(9),(10)). Official SIC titles in 4911-4939: 4911 Electric Services; 4922 Natural Gas Transmission; 4923 Natural Gas Transmisison & Distribution; 4924 Natural Gas Distribution; 4931 Electric & Other Services Combined; 4932 Gas & Other Services Combined.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 35 securities (4911 Electric Services x14, 4922 Natural Gas Transmission x6, 4923 Natural Gas Transmisison & Distribution x1, 4924 Natural Gas Distribution x4, 4931 Electric & Other Services Combined x9, 4932 Gas & Other Services Combined x1)
- **Trades matched:** 2 by 2 politicians (primary match for 0). Examples: AEE, AEP, ATO, BEP, CEG, CMS, CNP, D.
- **Overlaps other committees:** AP00/AP10 4911-4939 (related)
- **Scrutiny:** `mixed_industries`; `overlaps_other_committee`
- **Review note:** Approved direct (owner decision 2026-10-07).
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:5122-5122:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 5122-5122
- **Official SIC titles covered:** 5122 Wholesale-Drugs, Proprietaries & Druggists' Sundries
- **Rationale:** Drug wholesaling is part of the drug supply chain (Rule X 1(f)(3)). Official SIC titles in 5122-5122: 5122 Wholesale-Drugs, Proprietaries & Druggists' Sundries.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 3 securities (5122 Wholesale-Drugs, Proprietaries & Druggists' Sundries x3)
- **Trades matched:** 1 by 1 politician (primary match for 0). Examples: CAH, COR, MCK.
- **Scrutiny:** `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:5912-5912:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 5912-5912
- **Official SIC titles covered:** 5912 Retail-Drug Stores And Proprietary Stores
- **Rationale:** Drug stores dispense health products (Rule X 1(f)(3)). Official SIC titles in 5912-5912: 5912 Retail-Drug Stores And Proprietary Stores.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (5912 Retail-Drug Stores and Proprietary Stores x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CVS, WBA.
- **Scrutiny:** `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:6320-6324:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 6320-6324
- **Official SIC titles covered:** 6321 Accident & Health Insurance; 6324 Hospital & Medical Service Plans
- **Rationale:** Accident, health and medical service plans finance health care (Rule X 1(f)(3)). Official SIC titles in 6320-6324: 6321 Accident & Health Insurance; 6324 Hospital & Medical Service Plans.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 9 securities (6321 Accident & Health Insurance x3, 6324 Hospital & Medical Service Plans x6)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: AFL, CI, CNC, ELV, HUM, MOH, PFG, UNH.
- **Overlaps other committees:** BA00 6320-6329 (related); BA00/BA04 6320-6329 (related); WM00/WM02 6320-6324 (direct)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:7011-7011:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 7011-7011
- **Official SIC titles covered:** 7011 Hotels & Motels
- **Rationale:** Hotels and motels: 'travel and tourism' (Rule X 1(f)(15)). Official SIC titles in 7011-7011: 7011 Hotels & Motels.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 8 securities (7011 Hotels & Motels x8)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: FLL, H, HLT, IHG, LVS, MAR, MGM, WYNN.
- **Scrutiny:** `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00:8000-8099:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 8000-8099
- **Official SIC titles covered:** 8000 Services-Health Services; 8011 Services-Offices & Clinics Of Doctors Of Medicine; 8050 Services-Nursing & Personal Care Facilities; 8051 Services-Skilled Nursing Care Facilities; 8060 Services-Hospitals; 8062 Services-General Medical & Surgical Hospitals, Nec; 8071 Services-Medical Laboratories; 8082 Services-Home Health Care Services; 8090 Services-Misc Health & Allied Services, Nec; 8093 Services-Specialty Outpatient Facilities, Nec
- **Rationale:** Health services: 'health and health facilities' (Rule X 1(f)(3)). Official SIC titles in 8000-8099: 8000 Services-Health Services; 8011 Services-Offices & Clinics Of Doctors Of Medicine; 8050 Services-Nursing & Personal Care Facilities; 8051 Services-Skilled Nursing Care Facilities; 8060 Services-Hospitals; 8062 Services-General Medical & Surgical Hospitals, Nec; +4 more.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 15 securities (8050 Services-Nursing & Personal Care Facilities x1, 8060 Services-Hospitals x1, 8062 Services-General Medical & Surgical Hospitals, NEC x4, 8071 Services-Medical Laboratories x6, 8082 Services-Home Health Care Services x1, 8090 Services-Misc Health & Allied Services, NEC x1, 8093 Services-Specialty Outpatient Facilities, NEC x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CON, DGX, DVA, EHC, EXAS, GH, HCA, LH.
- **Overlaps other committees:** VR00 8050-8099 (related); VR00/VR03 8050-8099 (related); AP00/AP07 8000-8099 (related); WM00/WM02 8000-8099 (direct)
- **Scrutiny:** `broad_range`; `mixed_industries`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF16:3661-3669:direct`  direct  |  needs_review

- **Scope:** subcommittee IF16 (Communications and Technology)
- **SIC range:** 3661-3669
- **Official SIC titles covered:** 3661 Telephone & Telegraph Apparatus; 3663 Radio & Tv Broadcasting & Communications Equipment; 3669 Communications Equipment, Nec
- **Rationale:** Communications equipment. Official SIC titles in 3661-3669: 3661 Telephone & Telegraph Apparatus; 3663 Radio & Tv Broadcasting & Communications Equipment; 3669 Communications Equipment, Nec.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(14); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 9 securities (3661 Telephone & Telegraph Apparatus x2, 3663 Radio & Tv Broadcasting & Communications Equipment x5, 3669 Communications Equipment, NEC x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CIEN, ESE, FN, LITE, MSI, NOK, QCOM, UI.
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF16:4800-4899:direct`  direct  |  reviewed

- **Scope:** subcommittee IF16 (Communications and Technology)
- **SIC range:** 4800-4899
- **Official SIC titles covered:** 4812 Radiotelephone Communications; 4813 Telephone Communications (No Radiotelephone); 4822 Telegraph & Other Message Communications; 4832 Radio Broadcasting Stations; 4833 Television Broadcasting Stations; 4841 Cable & Other Pay Television Services; 4899 Communications Services, Nec
- **Rationale:** Communications services. Official SIC titles in 4800-4899: 4812 Radiotelephone Communications; 4813 Telephone Communications (No Radiotelephone); 4822 Telegraph & Other Message Communications; 4832 Radio Broadcasting Stations; 4833 Television Broadcasting Stations; 4841 Cable & Other Pay Television Services; +1 more.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(14); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 19 securities (4812 Radiotelephone Communications x1, 4813 Telephone Communications (No Radiotelephone) x5, 4832 Radio Broadcasting Stations x2, 4833 Television Broadcasting Stations x5, 4841 Cable & Other Pay Television Services x4, 4899 Communications Services, NEC x2)
- **Trades matched:** 3 by 2 politicians (primary match for 3). Examples: AMX, CHTR, CMCSA, FOX, FOXA, FWONK, KT, LBRDK.
- **Scrutiny:** `mixed_industries`; `inferred_from_name`
- **Review note:** Approved direct (owner decision 2026-10-07).
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF16:7370-7373:related`  related  |  needs_review

- **Scope:** subcommittee IF16 (Communications and Technology)
- **SIC range:** 7370-7373
- **Official SIC titles covered:** 7370 Services-Computer Programming, Data Processing, Etc.; 7371 Services-Computer Programming Services; 7372 Services-Prepackaged Software; 7373 Services-Computer Integrated Systems Design
- **Rationale:** Computer, software and data services: 'Technology' in the subcommittee's name. Official SIC titles in 7370-7373: 7370 Services-Computer Programming, Data Processing, Etc.; 7371 Services-Computer Programming Services; 7372 Services-Prepackaged Software; 7373 Services-Computer Integrated Systems Design.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(14); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 75 securities (7370 Services-Computer Programming, Data Processing, Etc. x11, 7371 Services-Computer Programming Services x7, 7372 Services-Prepackaged Software x49, 7373 Services-Computer Integrated Systems Design x8)
- **Trades matched:** 18 by 3 politicians (primary match for 18). Examples: ACIW, ADBE, ADSK, ALKT, APP, APPF, AZPN, BBAI.
- **Overlaps other committees:** AS00/AS35 7373-7373 (related); JU00/JU03 7370-7373 (related)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Review note:** Needs more source review (owner decision 2026-10-07): based only on the word 'Technology' in the subcommittee name; verify the published jurisdiction before relying on it. Earlier history: Review history: an earlier draft mapped 7370-7374; 7374 (data processing) was excluded after it matched ADP and Toast.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF03:1200-1299:direct`  direct  |  needs_review

- **Scope:** subcommittee IF03 (Energy)
- **SIC range:** 1200-1299
- **Official SIC titles covered:** 1220 Bituminous Coal & Lignite Mining; 1221 Bituminous Coal & Lignite Surface Mining
- **Rationale:** Coal: fossil fuels. Official SIC titles in 1200-1299: 1220 Bituminous Coal & Lignite Mining; 1221 Bituminous Coal & Lignite Surface Mining.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(6),(9),(10); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 1 securities (1221 Bituminous Coal & Lignite Surface Mining x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: ARLP.
- **Overlaps other committees:** II00 1200-1299 (direct); II00/II06 1200-1299 (direct)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF03:1311-1311:direct`  direct  |  needs_review

- **Scope:** subcommittee IF03 (Energy)
- **SIC range:** 1311-1311
- **Official SIC titles covered:** 1311 Crude Petroleum & Natural Gas
- **Rationale:** Crude petroleum and natural gas. Official SIC titles in 1311-1311: 1311 Crude Petroleum & Natural Gas.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(6),(9),(10); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 22 securities (1311 Crude Petroleum & Natural Gas x22)
- **Trades matched:** 3 by 1 politician (primary match for 3). Examples: AESI, APA, CHRD, CNQ, CTRA, DMLP, DVN, EOG.
- **Overlaps other committees:** II00 1311-1311 (related); II00/II06 1311-1311 (direct); AP00/AP10 1311-1311 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF03:1381-1389:direct`  direct  |  needs_review

- **Scope:** subcommittee IF03 (Energy)
- **SIC range:** 1381-1389
- **Official SIC titles covered:** 1381 Drilling Oil & Gas Wells; 1382 Oil & Gas Field Exploration Services; 1389 Oil & Gas Field Services, Nec
- **Rationale:** Oil and gas field services. Official SIC titles in 1381-1389: 1381 Drilling Oil & Gas Wells; 1382 Oil & Gas Field Exploration Services; 1389 Oil & Gas Field Services, Nec.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(6),(9),(10); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 4 securities (1382 Oil & Gas Field Exploration Services x1, 1389 Oil & Gas Field Services, NEC x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: HAL, PBA, SLB, WBI.
- **Overlaps other committees:** II00/II06 1381-1389 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF03:2911-2911:direct`  direct  |  needs_review

- **Scope:** subcommittee IF03 (Energy)
- **SIC range:** 2911-2911
- **Official SIC titles covered:** 2911 Petroleum Refining
- **Rationale:** Petroleum refining. Official SIC titles in 2911-2911: 2911 Petroleum Refining.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(6),(9),(10); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 8 securities (2911 Petroleum Refining x8)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: BP, COP, CVX, IMO, MPC, PSX, VLO, XOM.
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF03:4610-4619:direct`  direct  |  needs_review

- **Scope:** subcommittee IF03 (Energy)
- **SIC range:** 4610-4619
- **Official SIC titles covered:** 4610 Pipe Lines (No Natural Gas)
- **Rationale:** Oil pipelines (FERC). Official SIC titles in 4610-4619: 4610 Pipe Lines (No Natural Gas).
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(6),(9),(10); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 2 securities (4610 Pipe Lines (No Natural Gas) x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: DINO, ENB.
- **Overlaps other committees:** PW00 4600-4619 (related); PW00/PW14 4610-4619 (direct)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF03:4911-4939:direct`  direct  |  reviewed

- **Scope:** subcommittee IF03 (Energy)
- **SIC range:** 4911-4939
- **Official SIC titles covered:** 4911 Electric Services; 4922 Natural Gas Transmission; 4923 Natural Gas Transmisison & Distribution; 4924 Natural Gas Distribution; 4931 Electric & Other Services Combined; 4932 Gas & Other Services Combined
- **Rationale:** Electric and gas utilities. Official SIC titles in 4911-4939: 4911 Electric Services; 4922 Natural Gas Transmission; 4923 Natural Gas Transmisison & Distribution; 4924 Natural Gas Distribution; 4931 Electric & Other Services Combined; 4932 Gas & Other Services Combined.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(6),(9),(10); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 35 securities (4911 Electric Services x14, 4922 Natural Gas Transmission x6, 4923 Natural Gas Transmisison & Distribution x1, 4924 Natural Gas Distribution x4, 4931 Electric & Other Services Combined x9, 4932 Gas & Other Services Combined x1)
- **Trades matched:** 2 by 2 politicians (primary match for 0). Examples: AEE, AEP, ATO, BEP, CEG, CMS, CNP, D.
- **Overlaps other committees:** AP00/AP10 4911-4939 (related)
- **Scrutiny:** `mixed_industries`; `inferred_from_name`; `overlaps_other_committee`
- **Review note:** Approved direct (owner decision 2026-10-07).
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF03:4922-4924:direct`  direct  |  needs_review

- **Scope:** subcommittee IF03 (Energy)
- **SIC range:** 4922-4924
- **Official SIC titles covered:** 4922 Natural Gas Transmission; 4923 Natural Gas Transmisison & Distribution; 4924 Natural Gas Distribution
- **Rationale:** Natural gas transmission and distribution (FERC). Official SIC titles in 4922-4924: 4922 Natural Gas Transmission; 4923 Natural Gas Transmisison & Distribution; 4924 Natural Gas Distribution.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(6),(9),(10); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 11 securities (4922 Natural Gas Transmission x6, 4923 Natural Gas Transmisison & Distribution x1, 4924 Natural Gas Distribution x4)
- **Trades matched:** 2 by 2 politicians (primary match for 2). Examples: ATO, EPD, ET, KMI, LNG, NGG, OKE, SR.
- **Overlaps other committees:** AP00/AP10 4911-4939 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF18:2810-2819:related`  related  |  needs_review

- **Scope:** subcommittee IF18 (Environment)
- **SIC range:** 2810-2819
- **Official SIC titles covered:** 2810 Industrial Inorganic Chemicals
- **Rationale:** Industrial inorganic chemicals: environmental and chemical regulation. Official SIC titles in 2810-2819: 2810 Industrial Inorganic Chemicals.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 3 securities (2810 Industrial Inorganic Chemicals x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: APD, LIN, MTX.
- **Scrutiny:** `inferred_from_name`; `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF18:2860-2869:related`  related  |  needs_review

- **Scope:** subcommittee IF18 (Environment)
- **SIC range:** 2860-2869
- **Official SIC titles covered:** 2860 Industrial Organic Chemicals
- **Rationale:** Industrial organic chemicals: environmental and chemical regulation. Official SIC titles in 2860-2869: 2860 Industrial Organic Chemicals.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 2 securities (2860 Industrial Organic Chemicals x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: IFF, LYB.
- **Scrutiny:** `inferred_from_name`; `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF18:4950-4959:direct`  direct  |  needs_review

- **Scope:** subcommittee IF18 (Environment)
- **SIC range:** 4950-4959
- **Official SIC titles covered:** 4950 Sanitary Services; 4953 Refuse Systems; 4955 Hazardous Waste Management
- **Rationale:** Sanitary services including refuse and hazardous waste: environmental regulation. Official SIC titles in 4950-4959: 4950 Sanitary Services; 4953 Refuse Systems; 4955 Hazardous Waste Management.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 4 securities (4953 Refuse Systems x3, 4955 Hazardous Waste Management x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CLH, RSG, WCN, WM.
- **Overlaps other committees:** PW00/PW14 4955-4955 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF14:2833-2836:direct`  direct  |  needs_review

- **Scope:** subcommittee IF14 (Health)
- **SIC range:** 2833-2836
- **Official SIC titles covered:** 2833 Medicinal Chemicals & Botanical Products; 2834 Pharmaceutical Preparations; 2835 In Vitro & In Vivo Diagnostic Substances; 2836 Biological Products, (No Diagnostic Substances)
- **Rationale:** Drugs and biologicals. Official SIC titles in 2833-2836: 2833 Medicinal Chemicals & Botanical Products; 2834 Pharmaceutical Preparations; 2835 In Vitro & In Vivo Diagnostic Substances; 2836 Biological Products, (No Diagnostic Substances).
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(1),(3),(12); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 48 securities (2833 Medicinal Chemicals & Botanical Products x1, 2834 Pharmaceutical Preparations x35, 2835 In Vitro & In Vivo Diagnostic Substances x1, 2836 Biological Products, (No Diagnostic Substances) x11)
- **Trades matched:** 12 by 3 politicians (primary match for 12). Examples: ABBV, ABT, AGIO, ALKS, ALNY, AMGN, ARGX, ARQT.
- **Overlaps other committees:** VR00/VR03 2833-2836 (related); AP00/AP01 2833-2836 (related); AP00/AP07 2833-2836 (related); WM00/WM02 2833-2836 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF14:3841-3845:direct`  direct  |  needs_review

- **Scope:** subcommittee IF14 (Health)
- **SIC range:** 3841-3845
- **Official SIC titles covered:** 3841 Surgical & Medical Instruments & Apparatus; 3842 Orthopedic, Prosthetic & Surgical Appliances & Supplies; 3843 Dental Equipment & Supplies; 3844 X-Ray Apparatus & Tubes & Related Irradiation Apparatus; 3845 Electromedical & Electrotherapeutic Apparatus
- **Rationale:** Medical devices. Official SIC titles in 3841-3845: 3841 Surgical & Medical Instruments & Apparatus; 3842 Orthopedic, Prosthetic & Surgical Appliances & Supplies; 3843 Dental Equipment & Supplies; 3844 X-Ray Apparatus & Tubes & Related Irradiation Apparatus; 3845 Electromedical & Electrotherapeutic Apparatus.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(1),(3),(12); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 24 securities (3841 Surgical & Medical Instruments & Apparatus x13, 3842 Orthopedic, Prosthetic & Surgical Appliances & Supplies x7, 3844 X-Ray Apparatus & Tubes & Related Irradiation Apparatus x2, 3845 Electromedical & Electrotherapeutic Apparatus x2)
- **Trades matched:** 6 by 1 politician (primary match for 6). Examples: ALGN, AORT, ATRC, BAX, BDX, BSX, CDRE, DXCM.
- **Overlaps other committees:** HM00 3844-3844 (related); WM00/WM02 3841-3845 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF14:3851-3851:direct`  direct  |  needs_review

- **Scope:** subcommittee IF14 (Health)
- **SIC range:** 3851-3851
- **Official SIC titles covered:** 3851 Ophthalmic Goods
- **Rationale:** Ophthalmic goods. Official SIC titles in 3851-3851: 3851 Ophthalmic Goods.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(1),(3),(12); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 2 securities (3851 Ophthalmic Goods x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: ALC, COO.
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF14:5122-5122:related`  related  |  needs_review

- **Scope:** subcommittee IF14 (Health)
- **SIC range:** 5122-5122
- **Official SIC titles covered:** 5122 Wholesale-Drugs, Proprietaries & Druggists' Sundries
- **Rationale:** Drug wholesaling. Official SIC titles in 5122-5122: 5122 Wholesale-Drugs, Proprietaries & Druggists' Sundries.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(1),(3),(12); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 3 securities (5122 Wholesale-Drugs, Proprietaries & Druggists' Sundries x3)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: CAH, COR, MCK.
- **Scrutiny:** `inferred_from_name`; `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF14:5912-5912:related`  related  |  needs_review

- **Scope:** subcommittee IF14 (Health)
- **SIC range:** 5912-5912
- **Official SIC titles covered:** 5912 Retail-Drug Stores And Proprietary Stores
- **Rationale:** Drug retailing. Official SIC titles in 5912-5912: 5912 Retail-Drug Stores And Proprietary Stores.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(1),(3),(12); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 2 securities (5912 Retail-Drug Stores and Proprietary Stores x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CVS, WBA.
- **Scrutiny:** `inferred_from_name`; `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF14:6320-6324:related`  related  |  needs_review

- **Scope:** subcommittee IF14 (Health)
- **SIC range:** 6320-6324
- **Official SIC titles covered:** 6321 Accident & Health Insurance; 6324 Hospital & Medical Service Plans
- **Rationale:** Health insurance and plans. Official SIC titles in 6320-6324: 6321 Accident & Health Insurance; 6324 Hospital & Medical Service Plans.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(1),(3),(12); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 9 securities (6321 Accident & Health Insurance x3, 6324 Hospital & Medical Service Plans x6)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: AFL, CI, CNC, ELV, HUM, MOH, PFG, UNH.
- **Overlaps other committees:** BA00 6320-6329 (related); BA00/BA04 6320-6329 (related); WM00/WM02 6320-6324 (direct)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `IF00/IF14:8000-8099:direct`  direct  |  needs_review

- **Scope:** subcommittee IF14 (Health)
- **SIC range:** 8000-8099
- **Official SIC titles covered:** 8000 Services-Health Services; 8011 Services-Offices & Clinics Of Doctors Of Medicine; 8050 Services-Nursing & Personal Care Facilities; 8051 Services-Skilled Nursing Care Facilities; 8060 Services-Hospitals; 8062 Services-General Medical & Surgical Hospitals, Nec; 8071 Services-Medical Laboratories; 8082 Services-Home Health Care Services; 8090 Services-Misc Health & Allied Services, Nec; 8093 Services-Specialty Outpatient Facilities, Nec
- **Rationale:** Health services and facilities. Official SIC titles in 8000-8099: 8000 Services-Health Services; 8011 Services-Offices & Clinics Of Doctors Of Medicine; 8050 Services-Nursing & Personal Care Facilities; 8051 Services-Skilled Nursing Care Facilities; 8060 Services-Hospitals; 8062 Services-General Medical & Surgical Hospitals, Nec; +4 more.
- **Official jurisdiction wording used:** (1) Biomedical research and development. (3) Health and health facilities. (6) Exploration, production, storage, supply, marketing, pricing, and regulation of energy resources, including all fossil fuels, solar energy, and other unconventional or renewable energy resources. (9) The generation and marketing of power; reliability and interstate transmission of, and ratemaking for, all power. (10) ... all functions of the Federal Energy Regulatory Commission. (13) Regulation of the domestic nuclear energy industry. (14) Regulation of interstate and foreign communications. (15) Travel and tourism.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(f)(1),(3),(12); subcommittee name  <https://energycommerce.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 15 securities (8050 Services-Nursing & Personal Care Facilities x1, 8060 Services-Hospitals x1, 8062 Services-General Medical & Surgical Hospitals, NEC x4, 8071 Services-Medical Laboratories x6, 8082 Services-Home Health Care Services x1, 8090 Services-Misc Health & Allied Services, NEC x1, 8093 Services-Specialty Outpatient Facilities, NEC x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CON, DGX, DVA, EHC, EXAS, GH, HCA, LH.
- **Overlaps other committees:** VR00 8050-8099 (related); VR00/VR03 8050-8099 (related); AP00/AP07 8000-8099 (related); WM00/WM02 8000-8099 (direct)
- **Scrutiny:** `broad_range`; `mixed_industries`; `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### IG00: Permanent Select Committee on Intelligence

#### `IG00:none:none`  none  |  needs_review

- **Scope:** committee level
- **SIC range:** none (reviewed as having no industry-specific jurisdiction)
- **Rationale:** The Permanent Select Committee on Intelligence oversees intelligence agencies, not a commercial industry.
- **Official jurisdiction wording used:** Reviewed for industry-specific jurisdiction; none identified in the official text.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X (clause for this committee) or the committee's establishing resolution  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `committee_name`: inferred from the committee name, not verified
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### II00: Committee on Natural Resources

#### `II00:0800-0899:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 0800-0899
- **Official SIC titles covered:** none in the SEC table (the SEC lists only codes assigned to registrants)
- **Rationale:** Forestry on public lands (Rule X 1(m)(2),(19)). Official SIC titles in 0800-0899: no official SIC title in this range.
- **Official jurisdiction wording used:** (1) Fisheries and wildlife. (4) Geological Survey. (11) Mineral land laws and claims. (12) Mineral resources of public lands. (13) Mining interests generally. (17) Petroleum conservation on public lands. (19) Public lands generally, including entry, easements, and grazing thereon. (21) Trans-Alaska Oil Pipeline.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(m)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 0 securities (no current security in this range)
- **Trades matched:** 0 by 0 politicians (primary match for 0).
- **Overlaps other committees:** AG00 0800-0899 (related); AG00/AG15 0800-0899 (direct)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `II00:0900-0999:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 0900-0999
- **Official SIC titles covered:** none in the SEC table (the SEC lists only codes assigned to registrants)
- **Rationale:** Fishing: 'fisheries and wildlife' (Rule X 1(m)(1)). Official SIC titles in 0900-0999: no official SIC title in this range.
- **Official jurisdiction wording used:** (1) Fisheries and wildlife. (4) Geological Survey. (11) Mineral land laws and claims. (12) Mineral resources of public lands. (13) Mining interests generally. (17) Petroleum conservation on public lands. (19) Public lands generally, including entry, easements, and grazing thereon. (21) Trans-Alaska Oil Pipeline.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(m)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 0 securities (no current security in this range)
- **Trades matched:** 0 by 0 politicians (primary match for 0).
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `II00:1000-1099:direct`  direct  |  reviewed

- **Scope:** committee level
- **SIC range:** 1000-1099
- **Official SIC titles covered:** 1000 Metal Mining; 1040 Gold And Silver Ores; 1090 Miscellaneous Metal Ores
- **Rationale:** Metal mining: 'mining interests generally' and 'mineral resources of public lands' (Rule X 1(m)(12),(13)). Official SIC titles in 1000-1099: 1000 Metal Mining; 1040 Gold And Silver Ores; 1090 Miscellaneous Metal Ores.
- **Official jurisdiction wording used:** (1) Fisheries and wildlife. (4) Geological Survey. (11) Mineral land laws and claims. (12) Mineral resources of public lands. (13) Mining interests generally. (17) Petroleum conservation on public lands. (19) Public lands generally, including entry, easements, and grazing thereon. (21) Trans-Alaska Oil Pipeline.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(m)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 12 securities (1000 Metal Mining x5, 1040 Gold and Silver Ores x6, 1090 Miscellaneous Metal Ores x1)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: ARIS, BHP, CCJ, CLF, FCX, FNV, IAG, NEM.
- **Scrutiny:** `mixed_industries`
- **Review note:** Approved direct (owner decision 2026-10-07).
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `II00:1200-1299:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 1200-1299
- **Official SIC titles covered:** 1220 Bituminous Coal & Lignite Mining; 1221 Bituminous Coal & Lignite Surface Mining
- **Rationale:** Coal mining on public lands (Rule X 1(m)(12),(13)). Official SIC titles in 1200-1299: 1220 Bituminous Coal & Lignite Mining; 1221 Bituminous Coal & Lignite Surface Mining.
- **Official jurisdiction wording used:** (1) Fisheries and wildlife. (4) Geological Survey. (11) Mineral land laws and claims. (12) Mineral resources of public lands. (13) Mining interests generally. (17) Petroleum conservation on public lands. (19) Public lands generally, including entry, easements, and grazing thereon. (21) Trans-Alaska Oil Pipeline.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(m)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 1 securities (1221 Bituminous Coal & Lignite Surface Mining x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: ARLP.
- **Overlaps other committees:** IF00 1200-1299 (direct); IF00/IF03 1200-1299 (direct)
- **Scrutiny:** `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `II00:1311-1311:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 1311-1311
- **Official SIC titles covered:** 1311 Crude Petroleum & Natural Gas
- **Rationale:** Oil and gas extraction on public lands: 'petroleum conservation on public lands' (Rule X 1(m)(17)); energy markets belong to Energy and Commerce. Official SIC titles in 1311-1311: 1311 Crude Petroleum & Natural Gas.
- **Official jurisdiction wording used:** (1) Fisheries and wildlife. (4) Geological Survey. (11) Mineral land laws and claims. (12) Mineral resources of public lands. (13) Mining interests generally. (17) Petroleum conservation on public lands. (19) Public lands generally, including entry, easements, and grazing thereon. (21) Trans-Alaska Oil Pipeline.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(m)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 22 securities (1311 Crude Petroleum & Natural Gas x22)
- **Trades matched:** 2 by 1 politician (primary match for 2). Examples: AESI, APA, CHRD, CNQ, CTRA, DMLP, DVN, EOG.
- **Overlaps other committees:** IF00 1311-1311 (direct); IF00/IF03 1311-1311 (direct); AP00/AP10 1311-1311 (related)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `II00:1400-1499:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 1400-1499
- **Official SIC titles covered:** 1400 Mining & Quarrying Of Nonmetallic Minerals (No Fuels)
- **Rationale:** Mining and quarrying of nonmetallic minerals (Rule X 1(m)(12),(13)). Official SIC titles in 1400-1499: 1400 Mining & Quarrying Of Nonmetallic Minerals (No Fuels).
- **Official jurisdiction wording used:** (1) Fisheries and wildlife. (4) Geological Survey. (11) Mineral land laws and claims. (12) Mineral resources of public lands. (13) Mining interests generally. (17) Petroleum conservation on public lands. (19) Public lands generally, including entry, easements, and grazing thereon. (21) Trans-Alaska Oil Pipeline.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(m)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (1400 Mining & Quarrying of  Nonmetallic Minerals (No Fuels) x2)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: MLM, SQM.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `II00/II06:1000-1099:direct`  direct  |  reviewed

- **Scope:** subcommittee II06 (Energy and Mineral Resources)
- **SIC range:** 1000-1099
- **Official SIC titles covered:** 1000 Metal Mining; 1040 Gold And Silver Ores; 1090 Miscellaneous Metal Ores
- **Rationale:** Mineral resources: metal mining. Official SIC titles in 1000-1099: 1000 Metal Mining; 1040 Gold And Silver Ores; 1090 Miscellaneous Metal Ores.
- **Official jurisdiction wording used:** (1) Fisheries and wildlife. (4) Geological Survey. (11) Mineral land laws and claims. (12) Mineral resources of public lands. (13) Mining interests generally. (17) Petroleum conservation on public lands. (19) Public lands generally, including entry, easements, and grazing thereon. (21) Trans-Alaska Oil Pipeline.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(m)(12),(13),(17); subcommittee name  <https://naturalresources.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 12 securities (1000 Metal Mining x5, 1040 Gold and Silver Ores x6, 1090 Miscellaneous Metal Ores x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: ARIS, BHP, CCJ, CLF, FCX, FNV, IAG, NEM.
- **Scrutiny:** `mixed_industries`; `inferred_from_name`
- **Review note:** Approved direct (owner decision 2026-10-07).
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `II00/II06:1200-1299:direct`  direct  |  needs_review

- **Scope:** subcommittee II06 (Energy and Mineral Resources)
- **SIC range:** 1200-1299
- **Official SIC titles covered:** 1220 Bituminous Coal & Lignite Mining; 1221 Bituminous Coal & Lignite Surface Mining
- **Rationale:** Coal. Official SIC titles in 1200-1299: 1220 Bituminous Coal & Lignite Mining; 1221 Bituminous Coal & Lignite Surface Mining.
- **Official jurisdiction wording used:** (1) Fisheries and wildlife. (4) Geological Survey. (11) Mineral land laws and claims. (12) Mineral resources of public lands. (13) Mining interests generally. (17) Petroleum conservation on public lands. (19) Public lands generally, including entry, easements, and grazing thereon. (21) Trans-Alaska Oil Pipeline.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(m)(12),(13),(17); subcommittee name  <https://naturalresources.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 1 securities (1221 Bituminous Coal & Lignite Surface Mining x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: ARLP.
- **Overlaps other committees:** IF00 1200-1299 (direct); IF00/IF03 1200-1299 (direct)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `II00/II06:1311-1311:direct`  direct  |  needs_review

- **Scope:** subcommittee II06 (Energy and Mineral Resources)
- **SIC range:** 1311-1311
- **Official SIC titles covered:** 1311 Crude Petroleum & Natural Gas
- **Rationale:** Crude petroleum and natural gas on federal lands. Official SIC titles in 1311-1311: 1311 Crude Petroleum & Natural Gas.
- **Official jurisdiction wording used:** (1) Fisheries and wildlife. (4) Geological Survey. (11) Mineral land laws and claims. (12) Mineral resources of public lands. (13) Mining interests generally. (17) Petroleum conservation on public lands. (19) Public lands generally, including entry, easements, and grazing thereon. (21) Trans-Alaska Oil Pipeline.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(m)(12),(13),(17); subcommittee name  <https://naturalresources.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 22 securities (1311 Crude Petroleum & Natural Gas x22)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: AESI, APA, CHRD, CNQ, CTRA, DMLP, DVN, EOG.
- **Overlaps other committees:** IF00 1311-1311 (direct); IF00/IF03 1311-1311 (direct); AP00/AP10 1311-1311 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `II00/II06:1381-1389:related`  related  |  needs_review

- **Scope:** subcommittee II06 (Energy and Mineral Resources)
- **SIC range:** 1381-1389
- **Official SIC titles covered:** 1381 Drilling Oil & Gas Wells; 1382 Oil & Gas Field Exploration Services; 1389 Oil & Gas Field Services, Nec
- **Rationale:** Oil and gas field services. Official SIC titles in 1381-1389: 1381 Drilling Oil & Gas Wells; 1382 Oil & Gas Field Exploration Services; 1389 Oil & Gas Field Services, Nec.
- **Official jurisdiction wording used:** (1) Fisheries and wildlife. (4) Geological Survey. (11) Mineral land laws and claims. (12) Mineral resources of public lands. (13) Mining interests generally. (17) Petroleum conservation on public lands. (19) Public lands generally, including entry, easements, and grazing thereon. (21) Trans-Alaska Oil Pipeline.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(m)(12),(13),(17); subcommittee name  <https://naturalresources.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 4 securities (1382 Oil & Gas Field Exploration Services x1, 1389 Oil & Gas Field Services, NEC x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: HAL, PBA, SLB, WBI.
- **Overlaps other committees:** IF00 1381-1389 (related); IF00/IF03 1381-1389 (direct)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `II00/II06:1400-1499:direct`  direct  |  needs_review

- **Scope:** subcommittee II06 (Energy and Mineral Resources)
- **SIC range:** 1400-1499
- **Official SIC titles covered:** 1400 Mining & Quarrying Of Nonmetallic Minerals (No Fuels)
- **Rationale:** Nonmetallic mineral mining. Official SIC titles in 1400-1499: 1400 Mining & Quarrying Of Nonmetallic Minerals (No Fuels).
- **Official jurisdiction wording used:** (1) Fisheries and wildlife. (4) Geological Survey. (11) Mineral land laws and claims. (12) Mineral resources of public lands. (13) Mining interests generally. (17) Petroleum conservation on public lands. (19) Public lands generally, including entry, easements, and grazing thereon. (21) Trans-Alaska Oil Pipeline.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(m)(12),(13),(17); subcommittee name  <https://naturalresources.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 2 securities (1400 Mining & Quarrying of  Nonmetallic Minerals (No Fuels) x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: MLM, SQM.
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `II00/II13:0900-0999:direct`  direct  |  needs_review

- **Scope:** subcommittee II13 (Water, Wildlife and Fisheries)
- **SIC range:** 0900-0999
- **Official SIC titles covered:** none in the SEC table (the SEC lists only codes assigned to registrants)
- **Rationale:** Fisheries and wildlife: fishing. Official SIC titles in 0900-0999: no official SIC title in this range.
- **Official jurisdiction wording used:** (1) Fisheries and wildlife. (4) Geological Survey. (11) Mineral land laws and claims. (12) Mineral resources of public lands. (13) Mining interests generally. (17) Petroleum conservation on public lands. (19) Public lands generally, including entry, easements, and grazing thereon. (21) Trans-Alaska Oil Pipeline.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(m)(1); subcommittee name  <https://naturalresources.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 0 securities (no current security in this range)
- **Trades matched:** 0 by 0 politicians (primary match for 0).
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `II00/II13:2091-2092:related`  related  |  needs_review

- **Scope:** subcommittee II13 (Water, Wildlife and Fisheries)
- **SIC range:** 2091-2092
- **Official SIC titles covered:** 2092 Prepared Fresh Or Frozen Fish & Seafoods
- **Rationale:** Fish processing. Official SIC titles in 2091-2092: 2092 Prepared Fresh Or Frozen Fish & Seafoods.
- **Official jurisdiction wording used:** (1) Fisheries and wildlife. (4) Geological Survey. (11) Mineral land laws and claims. (12) Mineral resources of public lands. (13) Mining interests generally. (17) Petroleum conservation on public lands. (19) Public lands generally, including entry, easements, and grazing thereon. (21) Trans-Alaska Oil Pipeline.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(m)(1); subcommittee name  <https://naturalresources.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 0 securities (no current security in this range)
- **Trades matched:** 0 by 0 politicians (primary match for 0).
- **Overlaps other committees:** AG00 2090-2099 (related); AG00/AG03 2090-2099 (direct)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### IT00: Joint Committee on Taxation

#### `IT00:none:none`  none  |  needs_review

- **Scope:** committee level
- **SIC range:** none (reviewed as having no industry-specific jurisdiction)
- **Rationale:** The Joint Committee on Taxation staffs tax legislation across the economy; it has no industry-specific jurisdiction.
- **Official jurisdiction wording used:** Reviewed for industry-specific jurisdiction; none identified in the official text.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X (clause for this committee) or the committee's establishing resolution  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `committee_name`: inferred from the committee name, not verified
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### JL00: Joint Committee on the Library

#### `JL00:none:none`  none  |  needs_review

- **Scope:** committee level
- **SIC range:** none (reviewed as having no industry-specific jurisdiction)
- **Rationale:** The Joint Committee on the Library oversees the Library of Congress; not tied to an industry.
- **Official jurisdiction wording used:** Reviewed for industry-specific jurisdiction; none identified in the official text.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X (clause for this committee) or the committee's establishing resolution  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `committee_name`: inferred from the committee name, not verified
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### JP00: Joint Committee on Printing

#### `JP00:none:none`  none  |  needs_review

- **Scope:** committee level
- **SIC range:** none (reviewed as having no industry-specific jurisdiction)
- **Rationale:** The Joint Committee on Printing oversees congressional printing; not tied to a commercial industry.
- **Official jurisdiction wording used:** Reviewed for industry-specific jurisdiction; none identified in the official text.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X (clause for this committee) or the committee's establishing resolution  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `committee_name`: inferred from the committee name, not verified
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### JU00: Committee on the Judiciary

#### `JU00:6794-6794:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 6794-6794
- **Official SIC titles covered:** 6794 Patent Owners & Lessors
- **Rationale:** Patent owners and lessors: 'patents ... copyrights, and trademarks' (Rule X 1(l)(14)). Official SIC titles in 6794-6794: 6794 Patent Owners & Lessors.
- **Official jurisdiction wording used:** (14) Patents, the Patent and Trademark Office, copyrights, and trademarks. (16) Protection of trade and commerce against unlawful restraints and monopolies.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(l)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 1 securities (6794 Patent Owners & Lessors x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: DLB.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `JU00/JU03:7370-7373:related`  related  |  needs_review

- **Scope:** subcommittee JU03 (Courts, Intellectual Property, Artificial Intelligence, and the Internet)
- **SIC range:** 7370-7373
- **Official SIC titles covered:** 7370 Services-Computer Programming, Data Processing, Etc.; 7371 Services-Computer Programming Services; 7372 Services-Prepackaged Software; 7373 Services-Computer Integrated Systems Design
- **Rationale:** Computer, software and internet services: the subcommittee's 'Artificial Intelligence, and the Internet'. Official SIC titles in 7370-7373: 7370 Services-Computer Programming, Data Processing, Etc.; 7371 Services-Computer Programming Services; 7372 Services-Prepackaged Software; 7373 Services-Computer Integrated Systems Design.
- **Official jurisdiction wording used:** (14) Patents, the Patent and Trademark Office, copyrights, and trademarks. (16) Protection of trade and commerce against unlawful restraints and monopolies.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(l)(14); subcommittee name  <https://judiciary.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 75 securities (7370 Services-Computer Programming, Data Processing, Etc. x11, 7371 Services-Computer Programming Services x7, 7372 Services-Prepackaged Software x49, 7373 Services-Computer Integrated Systems Design x8)
- **Trades matched:** 8 by 1 politician (primary match for 8). Examples: ACIW, ADBE, ADSK, ALKT, APP, APPF, AZPN, BBAI.
- **Overlaps other committees:** AS00/AS35 7373-7373 (related); IF00/IF16 7370-7373 (related)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Review note:** Needs more source review (owner decision 2026-10-07): based only on 'Artificial Intelligence, and the Internet' in the subcommittee name; verify the published jurisdiction before relying on it. Earlier history: Review history: an earlier draft mapped 7370-7374; 7374 (data processing) was excluded after it matched ADP.
- **Decision:** [ ] approve   [ ] change   [ ] remove


### PW00: Committee on Transportation and Infrastructure

#### `PW00:1600-1622:direct`  direct  |  reviewed

- **Scope:** committee level
- **SIC range:** 1600-1622
- **Official SIC titles covered:** 1600 Heavy Construction Other Than Bldg Const - Contractors
- **Rationale:** Heavy construction (highways, bridges, dams, water and sewer): 'public works ... bridges and dams', 'roads' (Rule X 1(r)(10),(17),(19)). Official SIC titles in 1600-1622: 1600 Heavy Construction Other Than Bldg Const - Contractors.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 3 securities (1600 Heavy Construction Other Than Bldg Const - Contractors x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: FLR, J, STRL.
- **Overlaps other committees:** AP00/AP10 1600-1629 (related)
- **Scrutiny:** `overlaps_other_committee`
- **Review note:** Split from 1600-1629 direct (owner decision 2026-10-07): Highway, bridge and street construction (1600-1622) stays direct; 1623-1629 (water, sewer, pipeline, power and communication-line contractors) mixes utility and telecom contractors and is separated as related. This piece is direct.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00:1623-1629:related`  related  |  reviewed

- **Scope:** committee level
- **SIC range:** 1623-1629
- **Official SIC titles covered:** 1623 Water, Sewer, Pipeline, Comm & Power Line Construction
- **Rationale:** Heavy construction (highways, bridges, dams, water and sewer): 'public works ... bridges and dams', 'roads' (Rule X 1(r)(10),(17),(19)). Official SIC titles in 1623-1629: 1623 Water, Sewer, Pipeline, Comm & Power Line Construction.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 3 securities (1623 Water, Sewer, Pipeline, Comm & Power Line Construction x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: DY, MTZ, PRIM.
- **Overlaps other committees:** AP00/AP10 1600-1629 (related)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Review note:** Split from 1600-1629 direct (owner decision 2026-10-07): Highway, bridge and street construction (1600-1622) stays direct; 1623-1629 (water, sewer, pipeline, power and communication-line contractors) mixes utility and telecom contractors and is separated as related. This piece is related.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00:3720-3729:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 3720-3729
- **Official SIC titles covered:** 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec
- **Rationale:** Aircraft and parts supply civil aviation (Rule X 1(r)(20)); military aircraft belong to Armed Services. Official SIC titles in 3720-3729: 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 11 securities (3720 Aircraft & Parts x1, 3721 Aircraft x2, 3724 Aircraft Engines & Engine Parts x5, 3728 Aircraft Parts & Auxiliary Equipment, NEC x3)
- **Trades matched:** 5 by 2 politicians (primary match for 2). Examples: AVAV, BA, DCO, ESLT, HEI.A, HON, HONA, RTX.
- **Overlaps other committees:** AS00 3720-3729 (direct); AS00/AS25 3720-3729 (direct); SY00 3720-3729 (related); SY00/SY16 3720-3729 (direct); FA00 3720-3729 (related); AP00/AP02 3720-3729 (direct)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00:3743-3743:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 3743-3743
- **Official SIC titles covered:** 3743 Railroad Equipment
- **Rationale:** Railroad equipment supplies railroads (Rule X 1(r)(20)). Official SIC titles in 3743-3743: 3743 Railroad Equipment.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 1 securities (3743 Railroad Equipment x1)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: WAB.
- **Scrutiny:** `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00:4011-4013:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 4011-4013
- **Official SIC titles covered:** 4011 Railroads, Line-Haul Operating; 4013 Railroad Switching & Terminal Establishments
- **Rationale:** Railroads: 'transportation, including ... railroads' (Rule X 1(r)(20)). Official SIC titles in 4011-4013: 4011 Railroads, Line-Haul Operating; 4013 Railroad Switching & Terminal Establishments.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 5 securities (4011 Railroads, Line-Haul Operating x5)
- **Trades matched:** 3 by 2 politicians (primary match for 3). Examples: CP, CSX, FIP, NSC, UNP.
- **Overlaps other committees:** HM00/HM07 4011-4013 (related)
- **Scrutiny:** `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00:4100-4199:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 4100-4199
- **Official SIC titles covered:** 4100 Local & Suburban Transit & Interurban Hwy Passenger Trans
- **Rationale:** Local and suburban transit and highway passenger transportation (Rule X 1(r)(19),(20)). Official SIC titles in 4100-4199: 4100 Local & Suburban Transit & Interurban Hwy Passenger Trans.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 0 securities (no current security in this range)
- **Trades matched:** 0 by 0 politicians (primary match for 0).
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00:4200-4299:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 4200-4299
- **Official SIC titles covered:** 4210 Trucking & Courier Services (No Air); 4213 Trucking (No Local); 4220 Public Warehousing & Storage; 4231 Terminal Maintenance Facilities For Motor Freight Transport
- **Rationale:** Trucking and warehousing: transportation and roads (Rule X 1(r)(19),(20)). Official SIC titles in 4200-4299: 4210 Trucking & Courier Services (No Air); 4213 Trucking (No Local); 4220 Public Warehousing & Storage; 4231 Terminal Maintenance Facilities For Motor Freight Transport.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 4 securities (4210 Trucking & Courier Services (No Air) x1, 4213 Trucking (No Local) x3)
- **Trades matched:** 2 by 2 politicians (primary match for 1). Examples: ODFL, SAIA, SNDR, UPS.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00:4400-4499:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 4400-4499
- **Official SIC titles covered:** 4400 Water Transportation; 4412 Deep Sea Foreign Transportation Of Freight
- **Rationale:** Water transportation: 'water transportation' and 'merchant marine' (Rule X 1(r)(12),(20)). Official SIC titles in 4400-4499: 4400 Water Transportation; 4412 Deep Sea Foreign Transportation Of Freight.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 6 securities (4400 Water Transportation x4, 4412 Deep Sea Foreign Transportation of  Freight x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CCL, ICON, NCLH, RCL, SFL, VIK.
- **Overlaps other committees:** HM00/HM07 4400-4499 (related)
- **Scrutiny:** `mixed_industries`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00:4500-4599:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 4500-4599
- **Official SIC titles covered:** 4512 Air Transportation, Scheduled; 4513 Air Courier Services; 4522 Air Transportation, Nonscheduled; 4581 Airports, Flying Fields & Airport Terminal Services
- **Rationale:** Air transportation and airports: 'civil aviation' (Rule X 1(r)(20)). Official SIC titles in 4500-4599: 4512 Air Transportation, Scheduled; 4513 Air Courier Services; 4522 Air Transportation, Nonscheduled; 4581 Airports, Flying Fields & Airport Terminal Services.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 6 securities (4512 Air Transportation, Scheduled x5, 4513 Air Courier Services x1)
- **Trades matched:** 1 by 1 politician (primary match for 0). Examples: ALK, DAL, FDX, LUV, UAL, VLRS.
- **Overlaps other committees:** HM00/HM07 4500-4599 (related)
- **Scrutiny:** `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00:4600-4619:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 4600-4619
- **Official SIC titles covered:** 4610 Pipe Lines (No Natural Gas)
- **Rationale:** Pipelines: pipeline transportation safety, shared with Energy and Commerce. Official SIC titles in 4600-4619: 4610 Pipe Lines (No Natural Gas).
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (4610 Pipe Lines (No Natural Gas) x2)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: DINO, ENB.
- **Overlaps other committees:** IF00 4610-4619 (related); IF00/IF03 4610-4619 (direct)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00:4730-4739:related`  related  |  reviewed

- **Scope:** committee level
- **SIC range:** 4730-4739
- **Official SIC titles covered:** 4731 Arrangement Of Transportation Of Freight & Cargo
- **Rationale:** Arrangement of freight transportation (Rule X 1(r)(20)). Travel agencies (4700-4729) are not mapped here. Official SIC titles in 4730-4739: 4731 Arrangement Of Transportation Of Freight & Cargo.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 3 securities (4731 Arrangement of  Transportation of  Freight & Cargo x3)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: BCO, CHRW, EXPD.
- **Scrutiny:** `related_level`
- **Review note:** Downgraded from direct to related (owner decision 2026-10-07): freight brokers and forwarders are intermediaries, not the transportation modes or infrastructure the committee's jurisdiction names. Earlier history: Review history: an earlier draft mapped 4700-4799 as transportation services; travel agencies (4700-4729) were excluded after it matched Booking Holdings and moved to Energy and Commerce 'travel and tourism' as related.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00:8711-8711:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 8711-8711
- **Official SIC titles covered:** 8711 Services-Engineering Services
- **Rationale:** Engineering services design transportation infrastructure (Rule X 1(r)(20)). Official SIC titles in 8711-8711: 8711 Services-Engineering Services.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (8711 Services-Engineering Services x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: ACM, VSEC.
- **Scrutiny:** `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00/PW05:3720-3729:related`  related  |  needs_review

- **Scope:** subcommittee PW05 (Aviation)
- **SIC range:** 3720-3729
- **Official SIC titles covered:** 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec
- **Rationale:** Aircraft and parts supply civil aviation. Official SIC titles in 3720-3729: 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)(20); Subcommittee jurisdiction published at https://transportation.house.gov/subcommittees  <https://transportation.house.gov/subcommittees>
- **Jurisdiction basis:** `committee_published_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 11 securities (3720 Aircraft & Parts x1, 3721 Aircraft x2, 3724 Aircraft Engines & Engine Parts x5, 3728 Aircraft Parts & Auxiliary Equipment, NEC x3)
- **Trades matched:** 3 by 1 politician (primary match for 3). Examples: AVAV, BA, DCO, ESLT, HEI.A, HON, HONA, RTX.
- **Overlaps other committees:** AS00 3720-3729 (direct); AS00/AS25 3720-3729 (direct); SY00 3720-3729 (related); SY00/SY16 3720-3729 (direct); FA00 3720-3729 (related); AP00/AP02 3720-3729 (direct)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00/PW05:4500-4599:direct`  direct  |  needs_review

- **Scope:** subcommittee PW05 (Aviation)
- **SIC range:** 4500-4599
- **Official SIC titles covered:** 4512 Air Transportation, Scheduled; 4513 Air Courier Services; 4522 Air Transportation, Nonscheduled; 4581 Airports, Flying Fields & Airport Terminal Services
- **Rationale:** Civil aviation: 'all aspects of civil aviation, including safety, infrastructure, labor, commerce' (committee-published). Official SIC titles in 4500-4599: 4512 Air Transportation, Scheduled; 4513 Air Courier Services; 4522 Air Transportation, Nonscheduled; 4581 Airports, Flying Fields & Airport Terminal Services.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)(20); Subcommittee jurisdiction published at https://transportation.house.gov/subcommittees  <https://transportation.house.gov/subcommittees>
- **Jurisdiction basis:** `committee_published_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 6 securities (4512 Air Transportation, Scheduled x5, 4513 Air Courier Services x1)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: ALK, DAL, FDX, LUV, UAL, VLRS.
- **Overlaps other committees:** HM00/HM07 4500-4599 (related)
- **Scrutiny:** `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00/PW07:3730-3732:related`  related  |  needs_review

- **Scope:** subcommittee PW07 (Coast Guard and Maritime Transportation)
- **SIC range:** 3730-3732
- **Official SIC titles covered:** 3730 Ship & Boat Building & Repairing
- **Rationale:** Ship building and repairing supplies the merchant marine. Official SIC titles in 3730-3732: 3730 Ship & Boat Building & Repairing.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)(1),(12); Subcommittee jurisdiction published at https://transportation.house.gov/subcommittees  <https://transportation.house.gov/subcommittees>
- **Jurisdiction basis:** `committee_published_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (3730 Ship & Boat Building & Repairing x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: GD, HII.
- **Overlaps other committees:** AS00 3730-3732 (direct); AS00/AS28 3730-3732 (direct); AP00/AP02 3730-3732 (direct)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00/PW07:4400-4499:direct`  direct  |  needs_review

- **Scope:** subcommittee PW07 (Coast Guard and Maritime Transportation)
- **SIC range:** 4400-4499
- **Official SIC titles covered:** 4400 Water Transportation; 4412 Deep Sea Foreign Transportation Of Freight
- **Rationale:** Water transportation: maritime transportation and the merchant marine. Official SIC titles in 4400-4499: 4400 Water Transportation; 4412 Deep Sea Foreign Transportation Of Freight.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)(1),(12); Subcommittee jurisdiction published at https://transportation.house.gov/subcommittees  <https://transportation.house.gov/subcommittees>
- **Jurisdiction basis:** `committee_published_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 6 securities (4400 Water Transportation x4, 4412 Deep Sea Foreign Transportation of  Freight x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CCL, ICON, NCLH, RCL, SFL, VIK.
- **Overlaps other committees:** HM00/HM07 4400-4499 (related)
- **Scrutiny:** `mixed_industries`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00/PW12:1600-1622:direct`  direct  |  reviewed

- **Scope:** subcommittee PW12 (Highways and Transit)
- **SIC range:** 1600-1622
- **Official SIC titles covered:** 1600 Heavy Construction Other Than Bldg Const - Contractors
- **Rationale:** Highway and bridge construction. Official SIC titles in 1600-1622: 1600 Heavy Construction Other Than Bldg Const - Contractors.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)(10),(19); Subcommittee jurisdiction published at https://transportation.house.gov/subcommittees  <https://transportation.house.gov/subcommittees>
- **Jurisdiction basis:** `committee_published_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 3 securities (1600 Heavy Construction Other Than Bldg Const - Contractors x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: FLR, J, STRL.
- **Overlaps other committees:** AP00/AP10 1600-1629 (related)
- **Scrutiny:** `overlaps_other_committee`
- **Review note:** Split from 1600-1629 direct (owner decision 2026-10-07): Highway, bridge and street construction (1600-1622) stays direct; 1623-1629 (water, sewer, pipeline, power and communication-line contractors) mixes utility and telecom contractors and is separated as related. This piece is direct.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00/PW12:1623-1629:related`  related  |  reviewed

- **Scope:** subcommittee PW12 (Highways and Transit)
- **SIC range:** 1623-1629
- **Official SIC titles covered:** 1623 Water, Sewer, Pipeline, Comm & Power Line Construction
- **Rationale:** Highway and bridge construction. Official SIC titles in 1623-1629: 1623 Water, Sewer, Pipeline, Comm & Power Line Construction.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)(10),(19); Subcommittee jurisdiction published at https://transportation.house.gov/subcommittees  <https://transportation.house.gov/subcommittees>
- **Jurisdiction basis:** `committee_published_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 3 securities (1623 Water, Sewer, Pipeline, Comm & Power Line Construction x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: DY, MTZ, PRIM.
- **Overlaps other committees:** AP00/AP10 1600-1629 (related)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Review note:** Split from 1600-1629 direct (owner decision 2026-10-07): Highway, bridge and street construction (1600-1622) stays direct; 1623-1629 (water, sewer, pipeline, power and communication-line contractors) mixes utility and telecom contractors and is separated as related. This piece is related.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00/PW12:4100-4199:direct`  direct  |  needs_review

- **Scope:** subcommittee PW12 (Highways and Transit)
- **SIC range:** 4100-4199
- **Official SIC titles covered:** 4100 Local & Suburban Transit & Interurban Hwy Passenger Trans
- **Rationale:** Transit. Official SIC titles in 4100-4199: 4100 Local & Suburban Transit & Interurban Hwy Passenger Trans.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)(10),(19); Subcommittee jurisdiction published at https://transportation.house.gov/subcommittees  <https://transportation.house.gov/subcommittees>
- **Jurisdiction basis:** `committee_published_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 0 securities (no current security in this range)
- **Trades matched:** 0 by 0 politicians (primary match for 0).
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00/PW12:4200-4299:related`  related  |  needs_review

- **Scope:** subcommittee PW12 (Highways and Transit)
- **SIC range:** 4200-4299
- **Official SIC titles covered:** 4210 Trucking & Courier Services (No Air); 4213 Trucking (No Local); 4220 Public Warehousing & Storage; 4231 Terminal Maintenance Facilities For Motor Freight Transport
- **Rationale:** Trucking uses the highway system. Official SIC titles in 4200-4299: 4210 Trucking & Courier Services (No Air); 4213 Trucking (No Local); 4220 Public Warehousing & Storage; 4231 Terminal Maintenance Facilities For Motor Freight Transport.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)(10),(19); Subcommittee jurisdiction published at https://transportation.house.gov/subcommittees  <https://transportation.house.gov/subcommittees>
- **Jurisdiction basis:** `committee_published_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 4 securities (4210 Trucking & Courier Services (No Air) x1, 4213 Trucking (No Local) x3)
- **Trades matched:** 1 by 1 politician (primary match for 1). Examples: ODFL, SAIA, SNDR, UPS.
- **Scrutiny:** `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00/PW14:3743-3743:related`  related  |  needs_review

- **Scope:** subcommittee PW14 (Railroads, Pipelines, and Hazardous Materials)
- **SIC range:** 3743-3743
- **Official SIC titles covered:** 3743 Railroad Equipment
- **Rationale:** Railroad equipment. Official SIC titles in 3743-3743: 3743 Railroad Equipment.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)(20); Subcommittee jurisdiction published at https://transportation.house.gov/subcommittees  <https://transportation.house.gov/subcommittees>
- **Jurisdiction basis:** `committee_published_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 1 securities (3743 Railroad Equipment x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: WAB.
- **Scrutiny:** `related_level`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00/PW14:4011-4013:direct`  direct  |  needs_review

- **Scope:** subcommittee PW14 (Railroads, Pipelines, and Hazardous Materials)
- **SIC range:** 4011-4013
- **Official SIC titles covered:** 4011 Railroads, Line-Haul Operating; 4013 Railroad Switching & Terminal Establishments
- **Rationale:** Railroads: 'economic and safety regulation of railroads' (committee-published). Official SIC titles in 4011-4013: 4011 Railroads, Line-Haul Operating; 4013 Railroad Switching & Terminal Establishments.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)(20); Subcommittee jurisdiction published at https://transportation.house.gov/subcommittees  <https://transportation.house.gov/subcommittees>
- **Jurisdiction basis:** `committee_published_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 5 securities (4011 Railroads, Line-Haul Operating x5)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CP, CSX, FIP, NSC, UNP.
- **Overlaps other committees:** HM00/HM07 4011-4013 (related)
- **Scrutiny:** `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00/PW14:4610-4619:direct`  direct  |  needs_review

- **Scope:** subcommittee PW14 (Railroads, Pipelines, and Hazardous Materials)
- **SIC range:** 4610-4619
- **Official SIC titles covered:** 4610 Pipe Lines (No Natural Gas)
- **Rationale:** Pipelines (pipeline safety). Official SIC titles in 4610-4619: 4610 Pipe Lines (No Natural Gas).
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)(20); Subcommittee jurisdiction published at https://transportation.house.gov/subcommittees  <https://transportation.house.gov/subcommittees>
- **Jurisdiction basis:** `committee_published_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (4610 Pipe Lines (No Natural Gas) x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: DINO, ENB.
- **Overlaps other committees:** IF00 4610-4619 (related); IF00/IF03 4610-4619 (direct)
- **Scrutiny:** `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00/PW14:4955-4955:related`  related  |  needs_review

- **Scope:** subcommittee PW14 (Railroads, Pipelines, and Hazardous Materials)
- **SIC range:** 4955-4955
- **Official SIC titles covered:** 4955 Hazardous Waste Management
- **Rationale:** Hazardous waste management: hazardous materials. Official SIC titles in 4955-4955: 4955 Hazardous Waste Management.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)(20); Subcommittee jurisdiction published at https://transportation.house.gov/subcommittees  <https://transportation.house.gov/subcommittees>
- **Jurisdiction basis:** `committee_published_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 1 securities (4955 Hazardous Waste Management x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CLH.
- **Overlaps other committees:** IF00/IF18 4950-4959 (direct)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00/PW02:1623-1623:related`  related  |  reviewed

- **Scope:** subcommittee PW02 (Water Resources and Environment)
- **SIC range:** 1623-1623
- **Official SIC titles covered:** 1623 Water, Sewer, Pipeline, Comm & Power Line Construction
- **Rationale:** Water, sewer, pipeline and communication line construction: water resources infrastructure. Official SIC titles in 1623-1623: 1623 Water, Sewer, Pipeline, Comm & Power Line Construction.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)(3),(14),(17); Subcommittee jurisdiction published at https://transportation.house.gov/subcommittees  <https://transportation.house.gov/subcommittees>
- **Jurisdiction basis:** `committee_published_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 3 securities (1623 Water, Sewer, Pipeline, Comm & Power Line Construction x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: DY, MTZ, PRIM.
- **Overlaps other committees:** AP00/AP10 1600-1629 (related)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Review note:** Downgraded from direct to related (owner decision 2026-10-07): SIC 1623 mixes water and sewer construction with pipeline, power and communication-line construction. Earlier history: Review history: an earlier draft also mapped 4950-4959 (sanitary services) here; removed after it matched Republic Services and Waste Connections (waste hauling is not water resources).
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `PW00/PW02:4941-4941:related`  related  |  reviewed

- **Scope:** subcommittee PW02 (Water Resources and Environment)
- **SIC range:** 4941-4941
- **Official SIC titles covered:** 4941 Water Supply
- **Rationale:** Water supply. Official SIC titles in 4941-4941: 4941 Water Supply.
- **Official jurisdiction wording used:** (1) Coast Guard. (10) Construction or maintenance of roads. (12) Merchant marine. (14) Oil and other pollution of navigable waters. (17) Public works for the benefit of navigation, including bridges and dams. (19) Roads and the safety thereof. (20) Transportation, including civil aviation, railroads, water transportation, transportation safety, transportation infrastructure, transportation labor, and railroad retirement.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(r)(3),(14),(17); Subcommittee jurisdiction published at https://transportation.house.gov/subcommittees  <https://transportation.house.gov/subcommittees>
- **Jurisdiction basis:** `committee_published_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (4941 Water Supply x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: AWK, WTRG.
- **Scrutiny:** `related_level`
- **Review note:** Downgraded from direct to related (owner decision 2026-10-07): drinking-water supply utilities connect only indirectly to water resources and water pollution control (drinking water is mainly Energy and Commerce). Earlier history: Review history: an earlier draft also mapped 4950-4959 (sanitary services) here; removed after it matched Republic Services and Waste Connections.
- **Decision:** [ ] approve   [ ] change   [ ] remove


### QJ00: Select Subcommittee to Investigate the Remaining Questions Surrounding January 6, 2021

#### `QJ00:none:none`  none  |  needs_review

- **Scope:** committee level
- **SIC range:** none (reviewed as having no industry-specific jurisdiction)
- **Rationale:** A select investigative subcommittee on January 6, 2021 events; not tied to an industry.
- **Official jurisdiction wording used:** Reviewed for industry-specific jurisdiction; none identified in the official text.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X (clause for this committee) or the committee's establishing resolution  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `committee_name`: inferred from the committee name, not verified
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### RU00: Committee on Rules

#### `RU00:none:none`  none  |  needs_review

- **Scope:** committee level
- **SIC range:** none (reviewed as having no industry-specific jurisdiction)
- **Rationale:** The Committee on Rules sets House procedure; not tied to an industry.
- **Official jurisdiction wording used:** Reviewed for industry-specific jurisdiction; none identified in the official text.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X (clause for this committee) or the committee's establishing resolution  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `committee_name`: inferred from the committee name, not verified
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### SM00: Committee on Small Business

#### `SM00:none:none`  none  |  needs_review

- **Scope:** committee level
- **SIC range:** none (reviewed as having no industry-specific jurisdiction)
- **Rationale:** Small business assistance and federal procurement by small firms (Rule X 1(q)) cut across all industries.
- **Official jurisdiction wording used:** Reviewed for industry-specific jurisdiction; none identified in the official text.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X (clause for this committee) or the committee's establishing resolution  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **Decision:** [ ] approve   [ ] change   [ ] remove


### SO00: Committee on Ethics

#### `SO00:none:none`  none  |  needs_review

- **Scope:** committee level
- **SIC range:** none (reviewed as having no industry-specific jurisdiction)
- **Rationale:** The Committee on Ethics oversees Member conduct; not tied to an industry.
- **Official jurisdiction wording used:** Reviewed for industry-specific jurisdiction; none identified in the official text.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X (clause for this committee) or the committee's establishing resolution  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `committee_name`: inferred from the committee name, not verified
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### SY00: Committee on Science, Space, and Technology

#### `SY00:3720-3729:related`  related  |  needs_review

- **Scope:** committee level
- **SIC range:** 3720-3729
- **Official SIC titles covered:** 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec
- **Rationale:** Aircraft: civil aviation research and development, NASA aeronautics (Rule X 1(p)(3),(8)). Official SIC titles in 3720-3729: 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec.
- **Official jurisdiction wording used:** (1) All energy research, development, and demonstration. (2) Astronautical research and development. (3) Civil aviation research and development. (8) National Aeronautics and Space Administration. (12) Outer space, including exploration and control thereof. (14) Scientific research, development, and demonstration.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(p)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 11 securities (3720 Aircraft & Parts x1, 3721 Aircraft x2, 3724 Aircraft Engines & Engine Parts x5, 3728 Aircraft Parts & Auxiliary Equipment, NEC x3)
- **Trades matched:** 13 by 2 politicians (primary match for 11). Examples: AVAV, BA, DCO, ESLT, HEI.A, HON, HONA, RTX.
- **Overlaps other committees:** AS00 3720-3729 (direct); AS00/AS25 3720-3729 (direct); PW00 3720-3729 (related); PW00/PW05 3720-3729 (related); FA00 3720-3729 (related); AP00/AP02 3720-3729 (direct)
- **Scrutiny:** `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `SY00:3760-3769:direct`  direct  |  needs_review

- **Scope:** committee level
- **SIC range:** 3760-3769
- **Official SIC titles covered:** 3760 Guided Missiles & Space Vehicles & Parts
- **Rationale:** Guided missiles and space vehicles: space exploration and NASA (Rule X 1(p)(2),(8),(12)). Official SIC titles in 3760-3769: 3760 Guided Missiles & Space Vehicles & Parts.
- **Official jurisdiction wording used:** (1) All energy research, development, and demonstration. (2) Astronautical research and development. (3) Civil aviation research and development. (8) National Aeronautics and Space Administration. (12) Outer space, including exploration and control thereof. (14) Scientific research, development, and demonstration.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(p)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 2 securities (3760 Guided Missiles & Space Vehicles & Parts x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: LMT, VOYG.
- **Overlaps other committees:** AS00 3760-3769 (direct); AS00/AS29 3760-3769 (direct); FA00 3760-3769 (related); AP00/AP02 3760-3769 (direct); AP00/AP19 3760-3769 (related)
- **Scrutiny:** `overlaps_other_committee`; `false_positive_history`
- **Review note:** Review history: an earlier draft also mapped 3820-3829 (measuring instruments) for NIST standards; removed after it matched Trimble.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `SY00/SY16:3720-3729:direct`  direct  |  needs_review

- **Scope:** subcommittee SY16 (Space and Aeronautics)
- **SIC range:** 3720-3729
- **Official SIC titles covered:** 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec
- **Rationale:** Aeronautics: aircraft and parts. Official SIC titles in 3720-3729: 3720 Aircraft & Parts; 3721 Aircraft; 3724 Aircraft Engines & Engine Parts; 3728 Aircraft Parts & Auxiliary Equipment, Nec.
- **Official jurisdiction wording used:** (1) All energy research, development, and demonstration. (2) Astronautical research and development. (3) Civil aviation research and development. (8) National Aeronautics and Space Administration. (12) Outer space, including exploration and control thereof. (14) Scientific research, development, and demonstration.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(p)(2),(3),(12); subcommittee name  <https://science.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 11 securities (3720 Aircraft & Parts x1, 3721 Aircraft x2, 3724 Aircraft Engines & Engine Parts x5, 3728 Aircraft Parts & Auxiliary Equipment, NEC x3)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: AVAV, BA, DCO, ESLT, HEI.A, HON, HONA, RTX.
- **Overlaps other committees:** AS00 3720-3729 (direct); AS00/AS25 3720-3729 (direct); PW00 3720-3729 (related); PW00/PW05 3720-3729 (related); FA00 3720-3729 (related); AP00/AP02 3720-3729 (direct)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `SY00/SY16:3760-3769:direct`  direct  |  needs_review

- **Scope:** subcommittee SY16 (Space and Aeronautics)
- **SIC range:** 3760-3769
- **Official SIC titles covered:** 3760 Guided Missiles & Space Vehicles & Parts
- **Rationale:** Space: missiles and space vehicles. Official SIC titles in 3760-3769: 3760 Guided Missiles & Space Vehicles & Parts.
- **Official jurisdiction wording used:** (1) All energy research, development, and demonstration. (2) Astronautical research and development. (3) Civil aviation research and development. (8) National Aeronautics and Space Administration. (12) Outer space, including exploration and control thereof. (14) Scientific research, development, and demonstration.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(p)(2),(3),(12); subcommittee name  <https://science.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 2 securities (3760 Guided Missiles & Space Vehicles & Parts x2)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: LMT, VOYG.
- **Overlaps other committees:** AS00 3760-3769 (direct); AS00/AS29 3760-3769 (direct); FA00 3760-3769 (related); AP00/AP02 3760-3769 (direct); AP00/AP19 3760-3769 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove


### VR00: Committee on Veterans' Affairs

#### `VR00:8050-8099:related`  related  |  reviewed

- **Scope:** committee level
- **SIC range:** 8050-8099
- **Official SIC titles covered:** 8050 Services-Nursing & Personal Care Facilities; 8051 Services-Skilled Nursing Care Facilities; 8060 Services-Hospitals; 8062 Services-General Medical & Surgical Hospitals, Nec; 8071 Services-Medical Laboratories; 8082 Services-Home Health Care Services; 8090 Services-Misc Health & Allied Services, Nec; 8093 Services-Specialty Outpatient Facilities, Nec
- **Rationale:** Hospitals and health facilities provide veterans' medical care (Rule X 1(s)(8)). Official SIC titles in 8050-8099: 8050 Services-Nursing & Personal Care Facilities; 8051 Services-Skilled Nursing Care Facilities; 8060 Services-Hospitals; 8062 Services-General Medical & Surgical Hospitals, Nec; 8071 Services-Medical Laboratories; 8082 Services-Home Health Care Services; +2 more.
- **Official jurisdiction wording used:** (1) Veterans' measures generally. (8) Veterans' hospitals, medical care, and treatment of veterans.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(s)  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **In POLTRACKER data:** 15 securities (8050 Services-Nursing & Personal Care Facilities x1, 8060 Services-Hospitals x1, 8062 Services-General Medical & Surgical Hospitals, NEC x4, 8071 Services-Medical Laboratories x6, 8082 Services-Home Health Care Services x1, 8090 Services-Misc Health & Allied Services, NEC x1, 8093 Services-Specialty Outpatient Facilities, NEC x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CON, DGX, DVA, EHC, EXAS, GH, HCA, LH.
- **Overlaps other committees:** IF00 8000-8099 (direct); IF00/IF14 8000-8099 (direct); AP00/AP07 8000-8099 (related); WM00/WM02 8000-8099 (direct)
- **Scrutiny:** `mixed_industries`; `related_level`; `overlaps_other_committee`
- **Review note:** Kept as related (owner decision 2026-10-07): supporting context only; never triggers a flag by itself.
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `VR00/VR03:2833-2836:related`  related  |  needs_review

- **Scope:** subcommittee VR03 (Health)
- **SIC range:** 2833-2836
- **Official SIC titles covered:** 2833 Medicinal Chemicals & Botanical Products; 2834 Pharmaceutical Preparations; 2835 In Vitro & In Vivo Diagnostic Substances; 2836 Biological Products, (No Diagnostic Substances)
- **Rationale:** Drugs purchased for veterans' care. Official SIC titles in 2833-2836: 2833 Medicinal Chemicals & Botanical Products; 2834 Pharmaceutical Preparations; 2835 In Vitro & In Vivo Diagnostic Substances; 2836 Biological Products, (No Diagnostic Substances).
- **Official jurisdiction wording used:** (1) Veterans' measures generally. (8) Veterans' hospitals, medical care, and treatment of veterans.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(s)(8); subcommittee name  <https://veterans.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 48 securities (2833 Medicinal Chemicals & Botanical Products x1, 2834 Pharmaceutical Preparations x35, 2835 In Vitro & In Vivo Diagnostic Substances x1, 2836 Biological Products, (No Diagnostic Substances) x11)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: ABBV, ABT, AGIO, ALKS, ALNY, AMGN, ARGX, ARQT.
- **Overlaps other committees:** IF00 2833-2836 (direct); IF00/IF14 2833-2836 (direct); AP00/AP01 2833-2836 (related); AP00/AP07 2833-2836 (related); WM00/WM02 2833-2836 (related)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `VR00/VR03:8050-8099:related`  related  |  reviewed

- **Scope:** subcommittee VR03 (Health)
- **SIC range:** 8050-8099
- **Official SIC titles covered:** 8050 Services-Nursing & Personal Care Facilities; 8051 Services-Skilled Nursing Care Facilities; 8060 Services-Hospitals; 8062 Services-General Medical & Surgical Hospitals, Nec; 8071 Services-Medical Laboratories; 8082 Services-Home Health Care Services; 8090 Services-Misc Health & Allied Services, Nec; 8093 Services-Specialty Outpatient Facilities, Nec
- **Rationale:** Health: veterans' hospitals and medical care. Official SIC titles in 8050-8099: 8050 Services-Nursing & Personal Care Facilities; 8051 Services-Skilled Nursing Care Facilities; 8060 Services-Hospitals; 8062 Services-General Medical & Surgical Hospitals, Nec; 8071 Services-Medical Laboratories; 8082 Services-Home Health Care Services; +2 more.
- **Official jurisdiction wording used:** (1) Veterans' measures generally. (8) Veterans' hospitals, medical care, and treatment of veterans.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(s)(8); subcommittee name  <https://veterans.house.gov/subcommittees>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 15 securities (8050 Services-Nursing & Personal Care Facilities x1, 8060 Services-Hospitals x1, 8062 Services-General Medical & Surgical Hospitals, NEC x4, 8071 Services-Medical Laboratories x6, 8082 Services-Home Health Care Services x1, 8090 Services-Misc Health & Allied Services, NEC x1, 8093 Services-Specialty Outpatient Facilities, NEC x1)
- **Trades matched:** 0 by 0 politicians (primary match for 0). Examples: CON, DGX, DVA, EHC, EXAS, GH, HCA, LH.
- **Overlaps other committees:** IF00 8000-8099 (direct); IF00/IF14 8000-8099 (direct); AP00/AP07 8000-8099 (related); WM00/WM02 8000-8099 (direct)
- **Scrutiny:** `mixed_industries`; `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Review note:** Downgraded from direct to related (owner decision 2026-10-07): direct jurisdiction over private health providers is not established; the VA is itself the provider. Consistent with the committee-level related row.
- **Decision:** [ ] approve   [ ] change   [ ] remove


### WM00: Committee on Ways and Means

#### `WM00:none:none`  none  |  needs_review

- **Scope:** committee level
- **SIC range:** none (reviewed as having no industry-specific jurisdiction)
- **Rationale:** Taxes, tariffs, trade agreements and Social Security (Rule X 1(t)) are economy-wide rather than industry-specific; the Health Subcommittee is mapped separately.
- **Official jurisdiction wording used:** Reviewed for industry-specific jurisdiction; none identified in the official text.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X (clause for this committee) or the committee's establishing resolution  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `rule_x_text`: explicitly verified (official wording read)
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `WM00/WM02:2833-2836:related`  related  |  needs_review

- **Scope:** subcommittee WM02 (Health)
- **SIC range:** 2833-2836
- **Official SIC titles covered:** 2833 Medicinal Chemicals & Botanical Products; 2834 Pharmaceutical Preparations; 2835 In Vitro & In Vivo Diagnostic Substances; 2836 Biological Products, (No Diagnostic Substances)
- **Rationale:** Drugs paid for by Medicare. Official SIC titles in 2833-2836: 2833 Medicinal Chemicals & Botanical Products; 2834 Pharmaceutical Preparations; 2835 In Vitro & In Vivo Diagnostic Substances; 2836 Biological Products, (No Diagnostic Substances).
- **Official jurisdiction wording used:** (9) National social security (except health care and facilities programs that are supported from general revenues as opposed to payroll deductions).
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(t)(9) and 1(f)(3); subcommittee name  <https://waysandmeans.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 48 securities (2833 Medicinal Chemicals & Botanical Products x1, 2834 Pharmaceutical Preparations x35, 2835 In Vitro & In Vivo Diagnostic Substances x1, 2836 Biological Products, (No Diagnostic Substances) x11)
- **Trades matched:** 13 by 4 politicians (primary match for 13). Examples: ABBV, ABT, AGIO, ALKS, ALNY, AMGN, ARGX, ARQT.
- **Overlaps other committees:** IF00 2833-2836 (direct); IF00/IF14 2833-2836 (direct); VR00/VR03 2833-2836 (related); AP00/AP01 2833-2836 (related); AP00/AP07 2833-2836 (related)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `WM00/WM02:3841-3845:related`  related  |  needs_review

- **Scope:** subcommittee WM02 (Health)
- **SIC range:** 3841-3845
- **Official SIC titles covered:** 3841 Surgical & Medical Instruments & Apparatus; 3842 Orthopedic, Prosthetic & Surgical Appliances & Supplies; 3843 Dental Equipment & Supplies; 3844 X-Ray Apparatus & Tubes & Related Irradiation Apparatus; 3845 Electromedical & Electrotherapeutic Apparatus
- **Rationale:** Medical devices paid for by Medicare. Official SIC titles in 3841-3845: 3841 Surgical & Medical Instruments & Apparatus; 3842 Orthopedic, Prosthetic & Surgical Appliances & Supplies; 3843 Dental Equipment & Supplies; 3844 X-Ray Apparatus & Tubes & Related Irradiation Apparatus; 3845 Electromedical & Electrotherapeutic Apparatus.
- **Official jurisdiction wording used:** (9) National social security (except health care and facilities programs that are supported from general revenues as opposed to payroll deductions).
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(t)(9) and 1(f)(3); subcommittee name  <https://waysandmeans.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 24 securities (3841 Surgical & Medical Instruments & Apparatus x13, 3842 Orthopedic, Prosthetic & Surgical Appliances & Supplies x7, 3844 X-Ray Apparatus & Tubes & Related Irradiation Apparatus x2, 3845 Electromedical & Electrotherapeutic Apparatus x2)
- **Trades matched:** 12 by 1 politician (primary match for 12). Examples: ALGN, AORT, ATRC, BAX, BDX, BSX, CDRE, DXCM.
- **Overlaps other committees:** IF00 3841-3845 (direct); IF00/IF14 3841-3845 (direct); HM00 3844-3844 (related)
- **Scrutiny:** `inferred_from_name`; `related_level`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `WM00/WM02:6320-6324:direct`  direct  |  needs_review

- **Scope:** subcommittee WM02 (Health)
- **SIC range:** 6320-6324
- **Official SIC titles covered:** 6321 Accident & Health Insurance; 6324 Hospital & Medical Service Plans
- **Rationale:** Health insurance plans including Medicare Advantage. Official SIC titles in 6320-6324: 6321 Accident & Health Insurance; 6324 Hospital & Medical Service Plans.
- **Official jurisdiction wording used:** (9) National social security (except health care and facilities programs that are supported from general revenues as opposed to payroll deductions).
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(t)(9) and 1(f)(3); subcommittee name  <https://waysandmeans.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 9 securities (6321 Accident & Health Insurance x3, 6324 Hospital & Medical Service Plans x6)
- **Trades matched:** 2 by 1 politician (primary match for 2). Examples: AFL, CI, CNC, ELV, HUM, MOH, PFG, UNH.
- **Overlaps other committees:** IF00 6320-6324 (related); IF00/IF14 6320-6324 (related); BA00 6320-6329 (related); BA00/BA04 6320-6329 (related)
- **Scrutiny:** `inferred_from_name`; `overlaps_other_committee`
- **Decision:** [ ] approve   [ ] change   [ ] remove

#### `WM00/WM02:8000-8099:direct`  direct  |  needs_review

- **Scope:** subcommittee WM02 (Health)
- **SIC range:** 8000-8099
- **Official SIC titles covered:** 8000 Services-Health Services; 8011 Services-Offices & Clinics Of Doctors Of Medicine; 8050 Services-Nursing & Personal Care Facilities; 8051 Services-Skilled Nursing Care Facilities; 8060 Services-Hospitals; 8062 Services-General Medical & Surgical Hospitals, Nec; 8071 Services-Medical Laboratories; 8082 Services-Home Health Care Services; 8090 Services-Misc Health & Allied Services, Nec; 8093 Services-Specialty Outpatient Facilities, Nec
- **Rationale:** Health: Medicare payments to hospitals, nursing and home health providers (Ways and Means holds Medicare programs funded by payroll deductions, Rule X 1(t)(9) with 1(f)(3)). Official SIC titles in 8000-8099: 8000 Services-Health Services; 8011 Services-Offices & Clinics Of Doctors Of Medicine; 8050 Services-Nursing & Personal Care Facilities; 8051 Services-Skilled Nursing Care Facilities; 8060 Services-Hospitals; 8062 Services-General Medical & Surgical Hospitals, Nec; +4 more.
- **Official jurisdiction wording used:** (9) National social security (except health care and facilities programs that are supported from general revenues as opposed to payroll deductions).
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X, clause 1(t)(9) and 1(f)(3); subcommittee name  <https://waysandmeans.house.gov/subcommittees/>
- **Jurisdiction basis:** `subcommittee_name`: inferred from the subcommittee name, not verified
- **In POLTRACKER data:** 15 securities (8050 Services-Nursing & Personal Care Facilities x1, 8060 Services-Hospitals x1, 8062 Services-General Medical & Surgical Hospitals, NEC x4, 8071 Services-Medical Laboratories x6, 8082 Services-Home Health Care Services x1, 8090 Services-Misc Health & Allied Services, NEC x1, 8093 Services-Specialty Outpatient Facilities, NEC x1)
- **Trades matched:** 2 by 2 politicians (primary match for 2). Examples: CON, DGX, DVA, EHC, EXAS, GH, HCA, LH.
- **Overlaps other committees:** IF00 8000-8099 (direct); IF00/IF14 8000-8099 (direct); VR00 8050-8099 (related); VR00/VR03 8050-8099 (related); AP00/AP07 8000-8099 (related)
- **Scrutiny:** `broad_range`; `mixed_industries`; `inferred_from_name`; `overlaps_other_committee`
- **Review note:** Needs more source review (owner decision 2026-10-07): verify the Health Subcommittee's published jurisdiction (Medicare Parts A and B); Rule X gives Ways and Means only payroll-funded health programs. Do not treat as direct until verified.
- **Decision:** [ ] approve   [ ] change   [ ] remove


### ZS00: Select Committee on the Strategic Competition Between the United States and the Chinese Communist Party

#### `ZS00:none:none`  none  |  needs_review

- **Scope:** committee level
- **SIC range:** none (reviewed as having no industry-specific jurisdiction)
- **Rationale:** The Select Committee on the Chinese Communist Party investigates strategic competition generally; it has no enumerated industry jurisdiction.
- **Official jurisdiction wording used:** Reviewed for industry-specific jurisdiction; none identified in the official text.
- **Citation / source:** Rules of the House of Representatives, 119th Congress, Rule X (clause for this committee) or the committee's establishing resolution  <https://www.govinfo.gov/content/pkg/HMAN-119/pdf/HMAN-119.pdf>
- **Jurisdiction basis:** `committee_name`: inferred from the committee name, not verified
- **Scrutiny:** `inferred_from_name`
- **Decision:** [ ] approve   [ ] change   [ ] remove

