# Rebuilding a spreadsheet report, and the metric that was always zero

**Role** Senior Analyst, Data Analytics & AI · **Context** a marketing performance report built
on spreadsheet scripts, rebuilt on the warehouse · **Method only** — no campaign data, channel
names or figures.

## The question

A marketing-efficiency report ran on a spreadsheet with attached scripts: eight tabs, formulas
reaching across them, a script pulling data on a timer. It produced a number people quoted in
meetings. The ask was to rebuild it properly on the warehouse.

The first job on any rebuild like this is not the rebuild. It is: **does the current report
agree with itself, and does anyone know how the headline number is defined?**

## What I did

**Reproduced the existing output before changing anything.** Not because the old report is
authoritative, but because a rebuild that produces different numbers has two possible
explanations — the new one is right, or the new one is broken — and you cannot tell them apart
without first matching. Matching also finds the undocumented rules, because the only way to
reproduce a number is to discover every filter baked into it.

**Found one input stuck at zero.** One of the components feeding the efficiency metric was zero
in every period. Not low, not noisy: zero. In a spreadsheet, a zero in a denominator position
tends to be caught by an `IFERROR` somewhere and surfaces as a blank or a dash, so the report had
been showing a plausible figure built on a missing component for a long time.

The cause was a join that no longer matched: the identifier the script used to connect two
sources had changed on one side, so every lookup failed and the count came back empty. A failed
join returns nothing, which looks exactly like "there was nothing", and that is the whole
difficulty — **zero and absent are different facts that most reports render identically.**

**Made the rebuilt version distinguish them.** Zero gets reported as zero; a missing join gets
reported as missing, with the count of unmatched keys next to it. One extra row on a data-quality
panel, and the class of error that caused this becomes impossible to ship silently.

**Rewrote the metric definition in one place.** The efficiency figure had been assembled across
several tabs, so no single cell contained it and nobody could state it in a sentence. In the
rebuild it is one query with the definition written above it, and the definition was agreed out
loud before it was implemented.

**Kept the spreadsheet alive during the transition.** Both ran in parallel for a period, with a
comparison of the two outputs each cycle. Switching off the old report on the day the new one
launches is how you discover a disagreement in front of an audience.

## Outcome

The report moved to a live warehouse query with a single stated definition of the headline
metric, a data-quality panel that separates zero from absent, and a parallel-run period before
the old version was retired. The zero-valued input was the finding that mattered most, and it
came out of the reproduction step rather than the rebuild.

## What I would do differently

**Check every input for a constant before modelling anything.** A column that never varies is
either a constant or a defect, and it takes one query to find out. I found this one by reading
formulas, which took much longer and was luck as much as method.

**Ask what the number is used for before reproducing it.** Part of the old logic turned out to be
irrelevant to the decision the report supported, and I faithfully reproduced it before anyone
questioned whether it should exist. Reproduce to understand; then ask what should change.

**Write the definition down and get it confirmed in writing.** Verbal agreement on a metric lasts
until two people quote it differently in the same meeting.
