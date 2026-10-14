# Data Analytics Portfolio — Rachdian Habi Yahya

Analytics engineering and BI work from telecommunications and enterprise revenue operations:
reconciling revenue across systems, validating a vendor's published metrics against raw data,
migrating a BI platform, and the tooling that came out of it.

**What this repository is.** Two things, kept separate:

- [`tools/`](tools/) — small, runnable libraries for problems I hit repeatedly. Each one
  carries the pitfall that motivated it, because the pitfall is usually the expensive part.
- [`case-studies/`](case-studies/) — how real projects were approached: the question, the
  method, what broke, and what I would do differently. **Method only.** No employer or
  customer data, no credentials, no internal hostnames, no vendor datasets.

**What this repository is not.** It is not a dump of work files. Everything here was written
for this repository. Project data stays with its owner, which is why the case studies carry
reasoning and numbers that are already public on my CV, and nothing else.

---

## Tools

| Tool | Problem it solves | Tests |
|---|---|---|
| [`twb-tools`](tools/twb-tools/) | Read and rewrite Tableau `.twb` XML without silently breaking the workbook — Custom SQL stored in two different forms, worksheet clones that turn every sheet red, and the element order the schema quietly requires. | 8 |
| [`mirror-verify`](tools/mirror-verify/) | Verify a local Parquet mirror against a reference row count per day. File sizes do not catch a duplicated day, a half day, or an orphan file — row counts do. | 4 |
| [`excel-report-safe`](tools/excel-report-safe/) | Write into an Excel template without destroying its conditional formatting and validation, and without the COM date shift that moves every date a day earlier in silence. | 10 |
| [`notebook-from-code`](tools/notebook-from-code/) | Generate an analysis notebook from a script: narrative separate from code, the window in one place, and a lint that refuses a hardcoded date. | 13 |

Dependency-light — `mirror-verify` needs DuckDB, `excel-report-safe` needs openpyxl to check a
workbook and Excel itself to write one, the other two need only the standard library. All four
ship with tests and synthetic fixtures, so they run without any of my data: **35 tests in total.**

## Case studies

| # | Case study | What it is about |
|---|---|---|
| 01 | [Revenue reconciliation across three systems](case-studies/01-revenue-reconciliation.md) | A reconciliation that would not close, and the two row-level defects behind it. |
| 02 | [Validating a vendor's published metric](case-studies/02-vendor-metric-validation.md) | Rebuilding a vendor's formula from raw data to find out whether we could trust its slides. |
| 03 | [Migrating a BI estate between warehouses](case-studies/03-bi-platform-migration.md) | Moving a Tableau estate to a new warehouse, and the identifier rule that broke half of it. |
| 04 | [A monitoring dashboard from scratch](case-studies/04-monitoring-dashboard.md) | Star schema, grain decisions, and designing for the handover rather than the demo. |
| 05 | [Inferring something the data does not contain](case-studies/05-inference-when-the-field-is-empty.md) | When a needed field is 100% empty: building a proxy, and proving it against ground truth. |
| 06 | [Analysis that survives new data](case-studies/06-analysis-that-survives-new-data.md) | Why a hardcoded date is a bug waiting for a month to pass, and how an analysis is wired so it can be extended. |
| 07 | [Tiered leaderboards and the threshold that decides the winner](case-studies/07-tiered-leaderboards.md) | Eligibility rules, intervals instead of sort order, and a metric that was measuring availability. |
| 08 | [Running a BI server, not just building on it](case-studies/08-running-a-bi-server.md) | Estate inventory, a licence audit as a deadline problem, and why publishing stays a human action. |
| 09 | [Cloud cost analysis from the billing data](case-studies/09-cloud-cost-analysis.md) | Which cost column, what cannot be allocated, and separating price from usage. |
| 10 | [A mart in the warehouse](case-studies/10-a-mart-in-the-warehouse.md) | Idempotent builders, guards whose thresholds come from the data, and a deployed procedure that was already wrong. |
| 11 | [Rebuilding a spreadsheet report](case-studies/11-rebuilding-a-spreadsheet-report.md) | Reproducing before replacing, and the input that had been zero for months because a join stopped matching. |
| 12 | [A template people actually maintain](case-studies/12-a-template-people-actually-maintain.md) | Writing into a shared workbook: what to leave alone, what to verify, and what to report rather than fix. |

Two further streams are too early to write up honestly — a dispatch-SLA model and a market
intelligence brief, both at the data-gathering stage. They will appear here when there is a
result to describe rather than a plan.

## How I work, in short

- **Counts first, ratios second.** A monthly rate is the month's numerator over the month's
  denominator, never the mean of daily rates. It sounds pedantic until the two disagree by
  several points during an outage.
- **Separate measured from inferred,** and state what would disprove the inferred part. A
  finding without a falsification condition is an opinion with numbers attached.
- **A validation gate beats a careful analyst.** Row counts checked twice, a build that stops
  on the first mismatch, and idempotent steps — because the analyst will be tired eventually.
- **Design for the handover.** The dashboard is finished when someone else can run it without
  me, not when it renders.

## About

Senior Analyst (C-2), Data Analytics & AI at Link Net (an Axiata company). Previously Lead Data
Analyst Mentor at Karier.mu, guest lecturer at Universitas Andalas, and mentor at Dealls and
Rakamin Academy. Master's student in Management (Digital Business Strategy), Universitas Telkom.

SQL (Redshift, BigQuery, SQL Server, DuckDB) · Python (pandas, scikit-learn) · Tableau Desktop
and Server · Looker Studio · AWS and GCP data platforms.

[LinkedIn](https://linkedin.com/in/rachdiaan) · [Portfolio](https://rachdiaan.github.io/portfolio/)

## Licence

MIT — see [LICENSE](LICENSE). The case studies are prose; the code is yours to reuse.
