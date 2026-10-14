# Running a BI server, not just building on it

**Role** Senior Analyst, Data Analytics & AI · **Context** administering and automating a
Tableau Server estate alongside building on it · **Method only** — no server names, sites,
accounts or workbook contents.

## The question

Most analyst job descriptions stop at "builds dashboards". In practice the dashboards sit on a
server that someone has to keep correct: licences that expire, extracts that stop refreshing,
an estate spread across sites, and a platform upgrade that can take the whole thing down. I
ended up on that side of it too, and it changed how I build.

## What I did

**Automated the estate inventory, through the API rather than by hand.** Workbooks, data
sources, owners, last-viewed dates, extract schedules and subscription state, pulled into a
table I can query. Two uses, both unglamorous: knowing what exists before changing anything,
and finding what nobody has opened in a year. An estate assembled over years is never the one
people remember, and an inventory is the only honest starting point for a migration (case study
03) or a licence review.

**Ran a licence audit as a deadline problem, not a counting problem.** The counting is trivial;
the hard part is that deactivation has a date and the people affected have other jobs. What
worked was turning it into a short, specific request with the consequence stated plainly, sent
with enough lead time to be acted on, and a reminder to those who had not. The lesson that
generalises: an audit's output is not a spreadsheet, it is a set of decisions other people have
to make, and the deliverable has to be shaped for them.

**Learned the hard way that a platform operation can fail halfway.** A configuration change
applied through the admin tool left the application server and the controller in an error state:
the server was up and serving, while the operation I needed was blocked. The useful part is what
that teaches about sequencing — do the platform work in a window where being half-finished is
survivable, know in advance which user-visible function each step can break, and never schedule
one on the day a deadline depends on the thing it touches.

**Kept publishing a human action.** Scripts prepare, validate and stage; a person publishes.
This is a deliberate rule, not caution for its own sake. A script that publishes on its own will
eventually overwrite a live dashboard during a month-end close, and the cost of that is not
measured in minutes. The tooling therefore ends one step short on purpose, and the hand-over
documentation says so, so nobody assumes the last step happened.

**Treated credentials as something the artefact never carries.** Workbooks and data sources are
transformed on disk without embedded credentials; connection details are supplied by whoever
runs it, at run time, from their own environment. A workbook with an embedded credential is a
credential with a distribution mechanism.

## Outcome

An estate that could be inventoried on demand, a licence review that completed before its
deadline, and the automation that supported both the warehouse migration and the routine
publishing work — with the final publish left to a person in every case.

## What I would do differently

**Record the state before every platform operation, automatically.** I reconstructed what the
configuration had been from memory and notes. A dump of the relevant settings, taken by the same
script that applies the change, costs nothing and is exactly what you want at the worst moment.

**Separate "unused" from "unused by the people who answer email".** A dashboard with no views in
a year may still be the one a regulator asks about. The inventory needs an owner's confirmation
column, not just an access log.

**Publish the runbook with the automation.** The scripts were documented; the order to run them
in, and what each one assumes has already happened, lived in my head for too long. That is the
part a handover actually needs.
