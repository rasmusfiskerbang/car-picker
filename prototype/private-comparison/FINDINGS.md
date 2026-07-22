# Prototype findings for issue #8

This prototype tests three different information hierarchies against the same in-memory state
and illustrative leasing offers. It does not validate commercial data or production code.

## Provisional design answer

Use **A — Roligt overblik** as the catalogue shell. It gives a prospective lessee the best
mobile-friendly path from filtering to scanning without turning the page into a price ranking.
Carry two ideas from the other variants into a production design:

- use C's plain-language, end-of-term obligation sentence as the first explanatory fact on every
  offer; provider labels such as “flexleasing” remain secondary;
- use B's dense row structure for the side-by-side comparison, where repeated field alignment is
  more useful than editorial cards.

This recommendation still needs the owner's explicit selection before the issue is closed.

## Decisions supported by all three variants

- Show advertised monthly payment, upfront cash requirement, nominal base outlay, term, and
  mileage together. Never let the monthly payment stand alone.
- Put the normal end mechanism and residual-risk allocation before service extras or vehicle
  decoration.
- Render `not_stated` or unclear facts as named blockers. Do not convert them to zero and do not
  compute a nominal total while a required base cash-flow fact is missing.
- Keep filters descriptive: leasing form, residual-risk allocation, cash requirement, term, and
  vehicle facts. Preserve a neutral source order and explicitly state that filtering is not a
  personalized ranking.
- Put catalogue generation timestamp and duration in persistent chrome. Put retrieval time,
  designated first-party source, and supporting wording in offer details and alongside comparison
  facts.
- On mobile, replace the dense catalogue table with stacked rows, but keep comparison truly
  side-by-side inside a horizontally scrollable region with the row labels pinned.

## Deliberately unresolved

- Final tone and density require owner feedback after switching between A, B, and C.
- The prototype uses illustrative cash flows and source excerpts. Production copy must come from
  the active catalogue dataset and its source evidence.
- Search, filters, and selection are in memory. The prototype does not test persistence, data
  acquisition, personalized ranking, or mutations.
