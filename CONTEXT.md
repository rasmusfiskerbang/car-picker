# Car Choosing

This context describes how Danish consumers compare cars offered through private leasing.

## Language

**Prospective lessee**:
A private individual in Denmark who is seriously considering acquiring a car through a private leasing arrangement.
_Avoid_: Buyer, customer, casual browser

**Financial leasing**:
A provider label commonly associated with the prospective lessee bearing residual-value exposure or an end-of-term disposal obligation. The agreement's actual terms, rather than this label alone, determine the offer's cash flows and exposures.
_Avoid_: Leasing, guaranteed residual-risk classification

**Operational leasing**:
A provider label commonly associated with returning the car at the end of the term while the provider bears its residual-value exposure. The agreement's actual terms take precedence over the label.
_Avoid_: Leasing, guaranteed return arrangement

**Supported leasing form**:
A passenger-car leasing product explicitly offered to private individuals, including financial, flex, operational, and hybrid forms. Its residual-risk allocation, registration-tax treatment, or end mechanism may still be unclear.
_Avoid_: Business leasing, split leasing, car subscription, rental, purchase

**Leasing offer**:
A single advertised private-leasing configuration: one specific car configuration, contract term, mileage allowance, base cash-flow stream, conditions, fees, and set of obligations. Multiple configurations advertised through the same provider page or source record are distinct leasing offers when any of those commercial or contractual terms differ.
_Avoid_: Car, listing, deal

**Offer identity**:
The stable identity of one atomic leasing offer within a covered provider, composed from the provider's source ID or canonical offer URL plus a source-local configuration key. Prefer a provider-issued configuration ID; otherwise use a deterministic adapter-defined key derived from the explicitly selected source values. Similar cars are not the same offer merely because their vehicle facts match.
_Avoid_: Vehicle identity, fuzzy match

**Vehicle specification**:
The evidence-backed description of the car configuration advertised in one leasing offer, including normalized attributes used for filtering and comparison. Equivalent make, model, trim, equipment, or other attributes support comparison but do not establish that offers concern one shared physical vehicle or exact configuration.
_Avoid_: Shared vehicle identity, master vehicle, fuzzy vehicle match

**Catalogue candidate**:
A discovered leasing offer that has not yet satisfied the evidence required for inclusion in the active comparison catalogue.
_Avoid_: Catalogue offer, listing

**Catalogue offer**:
A leasing offer admitted to the active comparison catalogue after first-party evidence establishes an authorized covered provider, private-consumer eligibility, passenger-car scope, current availability, and a classifiable contract form.
_Avoid_: Candidate, all available offers

**Comparison-ready offer**:
A catalogue offer whose required facts are usable for a particular total, filter, sort, or comparison. Readiness is evaluated separately for each operation together with the facts blocking an unavailable operation; it is not stored as an offer fact and is never an overall completeness score or ranking signal.
_Avoid_: Complete offer, universally comparable offer, completeness percentage

**Offer fact state**:
The evidentiary state of a comparison-relevant fact: `known` when the designated source supports a normalized value, `not_stated` when it omits the fact, `unclear` when its wording cannot support one interpretation, `conflicting` when it contradicts itself, or `not_applicable` when the fact genuinely does not apply. Every state retains its source wording and provenance; absence never implies zero, false, excluded, or not applicable.
_Avoid_: Nullable field, missing value

**Quarantined offer**:
A catalogue candidate retained only in the current catalogue dataset and withheld from the active comparison catalogue because a required admission fact is missing, uncertain, contradictory, or malformed. It carries structured quarantine reasons and supporting evidence so coverage and source quality remain explainable, then disappears when the catalogue dataset is replaced.
_Avoid_: Bad offer, excluded listing

**Covered provider**:
A Danish leasing company whose publicly available private-leasing offers are included in the tool's declared source scope.
_Avoid_: Dealer, the market, all providers

**Catalogue dataset**:
The complete active representation of catalogue candidates from every covered provider, produced by one successful all-provider refresh. It has one generation timestamp and remains active until another dataset is built and validated as a unit, then atomically replaces and deletes its predecessor. A failure for any provider rejects the replacement and leaves the active dataset unchanged. No historical datasets or cross-refresh offer records are retained.
_Avoid_: Provider snapshot, incremental update, mixed-age catalogue, revision history, live market

**Coverage register**:
The record of which covered providers and designated offer-source scopes contribute to the active catalogue dataset, including quarantined-candidate counts and the dataset's single generation timestamp.
_Avoid_: Market coverage percentage, the whole market

**Designated offer source**:
The bounded first-party source set selected as authoritative for one covered provider's catalogue candidates: one primary structured endpoint or offer-detail surface plus only explicitly enumerated supporting documents, with deterministic rules proving which offer and version each document applies to. Missing values remain unknown rather than being enriched from unlisted, third-party, or ambiguously applicable sources.
_Avoid_: Opportunistic evidence hierarchy, fallback source, arbitrary related page

**Source evidence**:
The current-catalogue-dataset record of where an offer fact came from: the first-party source document and the exact source fragment or wording that supports its normalized value or evidentiary state. Several facts may share one source document, and each fact points back to its own supporting evidence. Evidence is discarded when the catalogue dataset is successfully replaced.
_Avoid_: Unattributed value, copied description, detached excerpt

**Base cash-flow stream**:
The single time-ordered source of truth for payments and receipts a prospective lessee faces when a leasing offer runs to normal completion. Each amount appears once as an event with its source meaning, direction, amount basis, contract-relative timing or recurrence, and refundability where relevant. It contains unavoidable contractual amounts and the payment and expected return of refundable deposits, but excludes conditional or uncertain amounts; a provider-advertised aggregate total is a separate sourced assertion.
_Avoid_: Total expense, monthly-price field, duplicated payment fields

**Upfront cash requirement**:
The sum of mandatory payments due from accepting a leasing agreement through vehicle handover, including refundable deposits and establishment or delivery fees without netting later receipts. It is unavailable when evidence cannot establish whether a mandatory amount falls within that window.
_Avoid_: Cash at signing, first payment, down payment

**Nominal base outlay**:
The face-value sum of mandatory base payments minus expected mandatory base receipts over normal contract completion, without inflation, discounting, financing cost, or opportunity cost. Conditional exposures and externally priced costs are excluded; a fully refundable deposit therefore nets to zero while still contributing to the upfront cash requirement.
_Avoid_: Total cost, present value, expected cost

**Nominal monthly equivalent**:
The nominal base outlay spread over the full advertised normal-completion term in months. It is distinct from a provider-advertised monthly payment and does not use the minimum binding period, notice period, or number of recurring instalments as its denominator.
_Avoid_: Monthly payment, advertised monthly price, average instalment

**Derived comparison value**:
A reproducible result calculated from the current evidence-backed offer facts, such as nominal base outlay, nominal monthly equivalent, or operation readiness. It is not a provider-stated offer fact and is recalculated as needed rather than becoming part of the leasing offer.
_Avoid_: Provider price, persisted offer fact, authoritative total

**Exposure scenario**:
A possible payment or receipt caused by a conditional or uncertain event, represented by its standardized kind, trigger, required inputs, and any sourced formula, rate, cap, or fixed amount. Voluntary end options remain end mechanisms; an unquantified exposure stays visible without an invented cost or probability, and unusual obligations remain representable without being forced into an unrelated kind.
_Avoid_: Base cost, guaranteed payment, voluntary end option, estimated expected cost

**Service arrangement**:
The disclosed treatment of a standardized service or external-cost category within a leasing offer: `included`, `optional`, `required_external`, or `excluded`, together with its scope, limits, and provider wording. Whether that arrangement is known is expressed separately by the offer fact state.
_Avoid_: Service fact state, assumed inclusion, unqualified bundle

**Residual-risk allocation**:
The agreement's assignment of economic gain or loss when the car's realized end value differs from its stated residual value.
_Avoid_: Leasing type

**Registration-tax treatment**:
Whether Danish registration tax is paid in full or proportionally over the leasing period. A flexleasing label describes this dimension rather than fully determining the agreement's risk or end mechanism.
_Avoid_: Leasing type

**End mechanism**:
The agreement's required conclusion, such as returning the car, designating a third-party buyer, or making a mandatory purchase or payoff.
_Avoid_: Leasing type, residual value
