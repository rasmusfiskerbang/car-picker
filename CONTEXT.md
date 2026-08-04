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

**Leasing form**:
The normalized classification of a passenger-car leasing product explicitly offered to private individuals: financial, flex, operational, or hybrid. Its residual-risk allocation or end mechanism may still be unclear.
_Avoid_: Supported leasing form, provider form label, business leasing, split leasing, car subscription, rental, purchase

**Leasing offer**:
A single advertised private-leasing configuration: one specific car configuration, contract term, mileage allowance, base cash-flow stream, conditions, fees, and set of obligations. Multiple configurations advertised through the same provider page or source record are distinct leasing offers when any of those commercial or contractual terms differ.
_Avoid_: Car, listing, deal

**Offer identity**:
The stable identity of one atomic leasing offer within a covered provider, composed from the provider's source ID or canonical offer URL plus a source-local configuration key. Prefer a provider-issued configuration ID; otherwise use a deterministic adapter-defined key derived from the explicitly selected source values. Similar cars are not the same offer merely because their vehicle facts match.
_Avoid_: Vehicle identity, fuzzy match

**Supported vehicle kind**:
A passenger car powered exclusively by either gasoline or diesel combustion, or exclusively by a battery-electric drivetrain. Hybrid, plug-in hybrid, mild-hybrid, hydrogen, and other drivetrains are outside the catalogue scope.
_Avoid_: Gas car, hybrid vehicle, all passenger cars

**Vehicle specification**:
The evidence-backed description embedded in one leasing offer. Its common attributes are make, model, trim, model year, first-registration year, body style, and odometer reading, with each available year retaining its meaning; a combustion specification adds gasoline-or-diesel fuel type and fuel efficiency, while a battery-electric specification adds battery capacity with its gross, usable, or unstated basis, WLTP range, maximum charging power with its AC, DC, or unstated kind, and 10–80% charging time. Equivalent attributes support comparison but do not establish one shared physical vehicle or exact configuration.
_Avoid_: Shared vehicle identity, master vehicle, fuzzy vehicle match

**Catalogue candidate**:
A transiently collected leasing offer that has not yet satisfied the evidence required for inclusion in the active comparison catalogue. Catalogue admission consumes it during one catalogue refresh; the full candidate is never retained.
_Avoid_: Catalogue offer, listing

**Catalogue admission**:
The evidence-based decision that a catalogue candidate satisfies every required condition for inclusion in the active comparison catalogue. An admitted candidate becomes a catalogue offer without retaining a separate admission record; a candidate that cannot satisfy the conditions remains a quarantined candidate with structured reasons.
_Avoid_: Admission outcome, publication status, offer completeness

**Catalogue offer**:
A leasing offer admitted to the active comparison catalogue after first-party evidence establishes an authorized covered provider, private-consumer eligibility, passenger-car scope, current availability, and a classifiable contract form.
_Avoid_: Candidate, all available offers

**Offer fact state**:
The state of a comparison-relevant fact that catalogue admission does not require to be known: `known`, `not_stated`, `unclear`, `conflicting`, or `not_applicable`. Admission-guaranteed facts are direct catalogue-offer values; absence never implies zero, false, excluded, or not applicable.
_Avoid_: Nullable field, missing value

**Quarantined candidate**:
A catalogue candidate withheld from the active comparison catalogue because a required admission fact is missing, uncertain, contradictory, or malformed. Its compact current-dataset record retains only its identity, provider, canonical source, structured quarantine reasons, and supporting evidence, then disappears when the catalogue dataset is replaced.
_Avoid_: Quarantined offer, bad offer, excluded listing

**Covered provider**:
A Danish leasing company whose publicly available private-leasing offers are included in the tool's declared source scope.
_Avoid_: Dealer, the market, all providers

**Provider registry**:
The single authoritative, wholly publication-safe record of every provider considered for the catalogue. Each provider has one explicit stable provider ID, a display name, one general public website URL, and is either `active` or `inactive`. Catalogue offers and provider adapters refer to the stable provider ID, so a display-name or website change does not change provider identity. An active provider has passed source-access assessment and participates in catalogue retrieval. Its registry record contains neither evidence references nor designated-source configuration: the provider adapter owns the bounded retrieval scope and supporting source mechanics, while source audits remain supporting documents found by repository convention rather than competing provider state. An inactive provider has one current reason: `deferred`, `ineligible`, or `blocked`, together with its explanation. Blocking covers access restrictions, owner choice, and authenticated provider requests without creating a special withdrawal state, removal deadline, or withdrawal-triggered refresh; existing offers remain in the dated active catalogue dataset until the next successful ordinary catalogue refresh replaces it. Eligibility and activation happen together, so no eligible-but-not-onboarded state is retained. The registry validates the current record shapes but does not enforce a strict transition graph or retain transition history. Every registry field is safe to publish; contacts, credentials, correspondence, authentication notes, and private operational commentary do not belong in it.
_Avoid_: Provider assessment register, provider control, provider access list, exclusion list, covered-provider list

**Catalogue dataset**:
The complete publication-safe active representation produced by one successful all-provider refresh. It contains one dated copy of the Provider Registry's publication-safe records, normalized Catalogue Offers, and compact Quarantined Candidates. Provider participation and counts are derived from those records; designated source scope remains in Provider Adapter code and source audits rather than a separate coverage record. The dataset has one generation timestamp and remains active until another dataset is built and validated as a unit, then atomically replaces and deletes its predecessor. A failure for any provider rejects the replacement and leaves the active dataset unchanged. No historical datasets or cross-refresh offer records are retained.
_Avoid_: Provider snapshot, incremental update, mixed-age catalogue, revision history, live market

**Designated offer source**:
The bounded first-party source set selected as authoritative for one covered provider's catalogue candidates: one primary structured endpoint or offer-detail surface plus only explicitly enumerated supporting documents, with deterministic rules proving which offer and version each document applies to. Missing values remain unknown rather than being enriched from unlisted, third-party, or ambiguously applicable sources.
_Avoid_: Opportunistic evidence hierarchy, fallback source, arbitrary related page

**Catalogue refresh**:
One all-covered-provider attempt to produce and validate a complete replacement catalogue dataset. Its run diagnostics are transient; only a successfully replaced catalogue dataset remains active.
_Avoid_: Provider refresh, incremental sync, refresh history

**Source evidence**:
The first-party source URL and exact fragment or wording retained with a quarantined candidate to support a failed catalogue-admission reason. It is not retained on catalogue offers and is discarded when the catalogue dataset is successfully replaced.
_Avoid_: Offer provenance, copied description, detached excerpt

**Private-consumer VAT basis**:
The VAT treatment of an advertised amount explicitly offered to a private individual. An unqualified private-consumer price is VAT-inclusive; explicit excluding or contradictory VAT wording takes precedence and remains visible.
_Avoid_: Unknown VAT basis for an unqualified private price, silent gross-up

**Base cash-flow stream**:
The single time-ordered source of truth for payments and receipts a prospective lessee faces when a leasing offer runs to normal completion. Each amount appears once as a normalized event with its standardized meaning, direction, DKK amount or offer fact state, contract-relative timing or recurrence, and refundability where relevant. It contains unavoidable contractual amounts and the payment and expected return of refundable deposits, but excludes conditional amounts.
_Avoid_: Total expense, monthly-price field, duplicated payment fields

**Provider-advertised monthly payment**:
The known amount of the standardized recurring lease-payment event in a catalogue offer's base cash-flow stream. It is never stored separately; contradictory headline and cash-flow amounts block catalogue admission.
_Avoid_: Separate headline price

**Service arrangement**:
The normalized treatment of a standardized service or external-cost category within a leasing offer: `included`, `optional`, `required_external`, or `excluded`, together with its scope and limits. Whether that arrangement is known is expressed separately by the offer fact state; the arrangement is a dated interpretation rather than a retained provider quotation.
_Avoid_: Service fact state, assumed inclusion, unqualified bundle, provider wording

**Residual-risk allocation**:
The agreement's assignment of economic gain or loss when the car's realized end value differs from its stated residual value.
_Avoid_: Leasing type

**End mechanism**:
The agreement's required conclusion, such as returning the car, designating a third-party buyer, or making a mandatory purchase or payoff.
_Avoid_: Leasing type, residual value
