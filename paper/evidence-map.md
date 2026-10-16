# Evidence map

| Future claim | Required evidence | Current status |
|---|---|---|
| Nine business classes | model sources and data dictionary | Source available |
| Five real instances per class | real source manifest + quality.json + parent-complete real sample | Full snapshot and real sample verified |
| Repeatable data preparation | deterministic tests and real source hash recheck | Verified snapshot with seven matching source hashes |
| Correct query outputs | fixed real arithmetic + Python reference + both engine outputs | Both engines passed nine real-case checks and full Python-reference comparison |
| Equivalent query semantics | same dataset/parameters + saved-file comparison | All five queries and audits agree across both engines and Python |
| Constraints hold | source validation + both engine audits + negative cases | Each engine has 22 clean audit rows and five negative cases; Neo4j zero-input regression passed |
| Runtime/performance comparison | versioned scripts, plans and repeated timings | Both engine plans and one timing/run recorded; no controlled benchmark |
| Integration with data-mining project | contract validation against actual external output | Interface only |
| Teacher accepted project | consultation records | Pending |

No quantitative performance or data quality findings belong in the report
until the corresponding real artifacts exist. Synthetic fixtures are identified
as tests and never used as evidence of real business data.
