# Coursework requirements and acceptance evidence

Source: assignment pasted by the user. This is an individual project.

| Requirement | Planned artifact | State |
|---|---|---|
| Topic submission: at least 500 characters including spaces | First consultation topic text | Pending |
| Problem description: 200–500 English words | Report section 1 | Pending |
| UML conceptual model, at least five classes, PlantUML | `models/conceptual.puml` (nine classes) | Source and visually checked PNG available |
| Five queries, each natural language and lambda/logic | `docs/queries-and-constraints.md`, Q1–Q5 | Drafted; teacher review pending |
| Five constraints, each natural language and lambda/logic | Same document, C1–C5 | Drafted; teacher review pending |
| At least five real objects per class | Source manifest, dataset, quality report, `artifacts/reference/real-sample.json` | Full snapshot verified; real subset has 7–11 instances per class |
| Relational implementation UML | `models/relational.puml` | Source and visually checked PNG available |
| SQL DDL/DML, all queries/constraints and outputs | `sql/`, loader source, result artifacts | Full MySQL run, reference agreement, 22 audit rows and five negative cases passed |
| Graph implementation UML | `models/graph.puml` | Source and visually checked PNG available |
| Cypher creation/loading, queries/constraints and outputs | `cypher/`, loader source, result artifacts | Full Neo4j run, 22 clean audit rows, five negative cases and empty-input regression passed; three-way comparison passed |
| Conclusion: 100–200 English words | Report section 6 | Runtime findings available; prose deferred by user |
| Three consultations | `docs/consultations.md` | Not conducted |
| UML exported as PNG/JPG | `artifacts/models/` | Three PNGs rendered with PlantUML 1.2026.8; manifest records source hashes |
| A4 PDF, 12pt Roman, single spacing | Final report build | Deferred by user |
| All source code at end of same PDF, Courier 10pt, single spacing | Generated source appendix | Deferred |

Scope: model and implement the same business problem in MySQL and Neo4j.
The wording "object-oriented" in the introduction/conclusion is interpreted in
light of the explicit GDB implementation section. Confirm terminology at the
first consultation. "PlanUML" is treated as PlantUML.

Data mining, model training, prediction evaluation, recommendation algorithms,
OPM modeling, SAP BDC deployment, and a web dashboard are not deliverables of
this scaffold. The data-mining boundary is a versioned file contract only.
