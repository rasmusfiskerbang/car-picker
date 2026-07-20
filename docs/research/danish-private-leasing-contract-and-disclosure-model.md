# Danish private-leasing contract and disclosure model

Research snapshot: 20 July 2026

Scope: passenger-car leasing offered to a private individual in Denmark

Decision ticket: [Establish the Danish private-leasing contract and disclosure model](https://github.com/rasmusfiskerbang/car-picker/issues/3)

This note is product research, not legal advice. It separates binding rules from regulator interpretation, tax guidance, provider practice, and product-model inference.

## Decision-grade answer

The comparison service should not treat a provider's leasing label as the contract model. It should model four independent dimensions:

1. **Customer scope**: whether the offer is actually available to a private individual and whether displayed amounts are consumer amounts.
2. **Residual-value risk allocation**: whether the prospective lessee or the covered provider bears the financial risk that the car realizes less than its expected value at the end.
3. **Registration-tax treatment**: whether full registration tax or proportionate registration tax under section 3 b of the Registration Tax Act is used. “Flexleasing” describes the latter tax treatment in market usage; it does not, by itself, completely describe the parties' obligations.
4. **End-of-term mechanism**: return, purchase right, purchase obligation, nomination right, nomination obligation, extension, or some combination, including the conditions and the VAT/registration-tax basis of any stated residual value.

This separation follows from three high-trust sources. The Danish Consumer Ombudsman says that leasing has no single fixed definition and that agreements vary materially. Finanstilsynet's anti-money-laundering guidance distinguishes financial from operational leasing by **who bears residual-value risk**: the lessee in financial leasing and the lessor in operational leasing. Motorstyrelsen's rules separately require a section 3 b contract to state any purchase or nomination rights and obligations, without making those terms synonymous with the tax method. ([Consumer Ombudsman — Leasing](https://forbrugerombudsmanden.dk/alle-emner/andre-brancher/leasing), [Finanstilsynet AML guidance, section 1.1.3](https://www.retsinformation.dk/eli/retsinfo/2020/9864), [Motorstyrelsen — Leasing vehicles](https://info.skat.dk/data.aspx?oid=1947431))

The first-party market evidence points the same way. Fleggaard describes operational leasing as the provider bearing service, repair, and residual-value risk, and financial/flex leasing as the lessee bearing service, repair, residual-value, and resale risk. Selected Car Leasing describes its private flexleasing as financial leasing where the private lessee bears the residual value. These are provider practices, not universal legal definitions, but they show why a comparison service must preserve obligations rather than trust names. ([Fleggaard Flexleasing](https://www.fleggaard-leasing.dk/flexleasing), [Selected Car Leasing — Flexleasing](https://scleasing.dk/flexleasing/))

For the agreed normal-completion comparison:

- known, unavoidable contractual payments and receipts belong in the **base cash-flow stream**;
- a refundable deposit is an initial outflow and an expected end receipt, while a non-refundable first payment is only an outflow;
- a residual value is **not automatically a lessee cash flow**;
- a mandatory purchase/payoff by the prospective lessee is a base end cash flow;
- a third-party buyer paying the provider is not the prospective lessee's cash flow;
- the prospective lessee's liability for a residual-value shortfall is an **exposure scenario**, because its amount depends on a future realization price;
- excess mileage, damage, abnormal wear, late return, early termination, theft/total loss, and other conditional consequences are exposure scenarios, not base cost;
- legally or contractually required but individually priced external costs, such as insurance when excluded from the offer, must be shown as excluded/unknown rather than silently estimated into the base stream.

## Authority map

| Status | What the sources establish | Product consequence |
| --- | --- | --- |
| **Binding law** | Consumer-facing commercial practices may not omit, hide, or ambiguously present material information. At a purchase invitation, price including VAT and taxes is material; if the nature of the product prevents advance calculation, the calculation method must be stated. ([Marketing Practices Act sections 5–6](https://www.retsinformation.dk/eli/lta/2024/1420)) | Preserve the source price, VAT/tax basis, mandatory price components, and calculation caveats. Do not present an ex-VAT provider amount as a private consumer amount without a supported conversion. |
| **Binding law** | For distance/off-premises non-financial services, pre-contract information includes total price including taxes and other costs, duration, termination conditions, minimum obligation, and deposits/financial guarantees where relevant. ([Consumer Contracts Act section 8](https://www.retsinformation.dk/eli/lta/2025/1184)) | These concepts belong in the offer schema even where a catalogue page omits them; omission should produce `unknown`, not a guessed value. |
| **Binding law** | Ongoing service agreements can generally be terminated with one month's notice after five months, but where the annual price and provider's one-off cost/value-loss thresholds in section 28(4) are met, termination may begin after 11 months. Standard forms must state the notice/binding rule clearly. ([Consumer Contracts Act section 28](https://www.retsinformation.dk/eli/lta/2025/1184)) | Keep advertised term, minimum binding period, earliest effective exit, notice, and early-exit cash flows as distinct fields. Do not infer binding period solely from the advertised term. |
| **Binding law** | A lease without a purchase obligation is generally outside the Consumer Credit Agreements Act, but motor-vehicle leasing is still subject to the payment-capacity assessment in section 52 a. A purchase obligation in the lease or a separate agreement removes that exclusion. ([Consumer Credit Agreements Act section 3(1)(5)](https://www.retsinformation.dk/eli/lta/2019/817), [Act no. 2221/2020, section 6](https://www.retsinformation.dk/eli/lta/2020/2221)) | Purchase obligation must be preserved exactly. It changes both cash-flow treatment and the applicable consumer-credit regime; it is not equivalent to a purchase option or a nomination obligation. |
| **Binding law** | Where the Consumer Credit Agreements Act applies, current pre-contract disclosures include credit type, total credit, term, cash price, borrowing rate, APR, total payable, payment amount/count/frequency, mandatory ancillary services, security, withdrawal status, and early-repayment terms. ([Consumer Credit Agreements Act section 7 a](https://www.retsinformation.dk/eli/lta/2019/817)) | Preserve these source disclosures in a credit-specific block. Do not manufacture an APR or credit amount for leases outside the Act or where the provider has not supplied the legally defined inputs. |
| **Binding law / tax administration** | For proportionate registration tax, the provider must own the vehicle and there must be a real lease. The written contract must identify the parties and vehicle, specify equipment, all exchanged payments, term, and end/early-termination conditions including purchase and nomination rights/obligations. ([Motorstyrelsen — Leasing vehicles, contract requirements](https://info.skat.dk/data.aspx?oid=1947431)) | Vehicle identity/equipment, every contractual payment, exact period, end mechanism, and early termination are first-class comparison facts. |
| **Binding law / tax administration** | The provider is ordinarily liable for proportionate registration tax and interest; a user can also become liable if using a vehicle while knowing correct tax was not paid. The tax is charged for the agreed period at age-dependent rates and interest is added on the remaining calculated tax. ([Motorstyrelsen — calculation and liability](https://info.skat.dk/data.aspx?oid=1947431)) | Record the tax method and whether/how it is included in advertised payments. Do not show the statutory proportionate tax as a second consumer payment when it is already embedded in a leasing payment. |
| **Binding law** | Motor-vehicle third-party liability insurance is mandatory; the duty rests on the owner or person with permanent use of a registrable vehicle. ([Road Traffic Act sections 105–106](https://www.retsinformation.dk/eli/lta/2026/118)) | Preserve whether liability insurance is included. Comprehensive insurance is not the same legal requirement; it should be represented as a separate contract requirement when the provider requires it. |
| **Regulator interpretation** | There is no general statutory withdrawal right for ordinary private car leasing without transfer of ownership, including qualifying distance contracts. A purchase obligation, symbolic-price transfer, or other intended ownership transfer can change that conclusion. ([Consumer Ombudsman, 24 March 2023](https://forbrugerombudsmanden.dk/find-sager/sager/forbrugeraftaleloven/fortsat-ikke-lovkrav-om-fortrydelsesret-ved-privatleasing-af-biler)) | Never assume a cooling-off period. Preserve any contractual withdrawal/cancellation right and distinguish it from ordinary termination. |
| **Regulator interpretation** | The monthly price alone can be misleading. The Consumer Ombudsman has required the total cost for the marketed period and clear disclosure of what is included/excluded, and has specifically treated the first payment, total price, and binding period as information that should not be hidden behind another click. ([2010 leasing price case](https://forbrugerombudsmanden.dk/find-sager/sager/markedsfoeringsloven/sager-efter-markedsfoeringsloven/vildledning/prisoplysninger-ved-billeasing), [2016 online-leasing advance opinion](https://forbrugerombudsmanden.dk/find-sager/sager/markedsfoeringsloven/sager-efter-markedsfoeringsloven/kreditoplysninger/forhaandsbesked-vedr-online-markedsfoering-af-privatleasingaftale)) | Catalogue cards should show signing cash, recurring payment, marketed total/base outlay when computable, term, and binding period together—not lead with a bare monthly payment. |
| **Regulator interpretation** | Consumer lease terms must be clear and understandable; unreasonable terms can be set aside under Contracts Act sections 38 b and 38 c. ([Consumer Ombudsman — Leasing](https://forbrugerombudsmanden.dk/alle-emner/andre-brancher/leasing)) | Retain source wording and source links for material obligations. A normalized label is an aid, not a substitute for the contract. |
| **Market practice** | A current Toyota private-leasing campaign publishes monthly payment, first payment, annual mileage, 36-month term, 12-month minimum payment, full-period total, included service/delivery, and excluded periodic tax, insurance, and equipment. ([Toyota Yaris private leasing](https://www.toyota.dk/kampagner/yaris-active-pl-jan26-ID-22-2026)) | This is a useful minimum extraction target for operational-style campaign offers, not proof that every provider discloses the same set. |
| **Market practice** | The FDM/Finance & Leasing-based Volkswagen Semler contract distinguishes non-refundable extraordinary lease payment from fees, monthly payments, insurance, mileage rates, service, early termination, and return inspection. It also states that the lessee has neither right nor duty to buy. ([Volkswagen Semler private-leasing contract, version 1 September 2023](https://www.vwsf.dk/content/dam/bluelabel/valid/www-vwsf-dk/documents/Privatleasing%20kontrakt%20version%2001.09.2023.pdf)) | Upfront-payment semantics, asymmetric mileage rates, included-service scope, and end rights cannot be collapsed into generic `deposit`, `monthlyPrice`, or `residualValue` fields. |

## Contract-form comparison

The table describes the decisive allocation, not a guarantee attached to a marketing label.

| Question | Operational allocation | Financial allocation | Must preserve |
| --- | --- | --- | --- |
| Who bears ordinary market-value risk at normal end? | Covered provider | Prospective lessee, commonly through residual-value/shortfall liability or a nomination obligation | Risk bearer; exact liability formula; whether upside belongs to lessee, provider, or buyer |
| What normally happens at the end? | Car is returned; provider realizes it | Car may be sold to a nominated third party, refinanced/re-leased, or dealt with under a purchase mechanism | Every right and obligation; end counterparty; deadlines; buyer eligibility; fees |
| Is stated residual value a consumer payment? | Usually an internal provider assumption and may not be disclosed | Often a contract reference amount, but not necessarily paid by the prospective lessee | Amount; currency; incl./excl. VAT; incl./excl. registration tax; who pays whom; whether mandatory, optional, or only a shortfall reference |
| Who pays service, repairs, and maintenance? | Often provider under an included service agreement, with exclusions | Often prospective lessee, unless separately included | Inclusion state and scope for service, repairs, wear parts, tyres, roadside help, replacement car, and required workshops |
| Is mileage limited? | Commonly yes, with over/under-kilometre settlement | Can be unlimited, but kilometres still affect realized value and residual exposure | Contract allowance and settlement rates; expected usage underpinning residual value even where no hard cap exists |
| What creates end exposure? | Damage, abnormal wear, excess mileage, missing equipment, return/inspection fees, late return | Market-value shortfall plus condition, maintenance, resale, and any purchase/nomination consequences | Separate named exposure scenarios; never one undifferentiated “risk” badge |

Fleggaard's first-party explanation expressly assigns service, repairs, residual value, and resale differently between its operational and financial/flex products, including shortfall liability when sale proceeds are below residual value. Selected similarly states that financial flex lessees bear the residual value and that mileage can affect it even where the agreement has no fixed mileage limit. ([Fleggaard Flexleasing](https://www.fleggaard-leasing.dk/flexleasing), [Selected Car Leasing — private cars](https://scleasing.dk/biler-leasing-privat/))

Operational leasing is not “all-inclusive.” Ayvens, for example, says its used-car private leasing includes financing, maintenance, and repairs, but excludes tyres, periodic tax, fuel/charging, and insurance unless selected. Its return guide lists additional fees and condition consequences. ([Ayvens private leasing](https://www.ayvens.com/da-dk/leasing-med-ayvens/leasingloesninger/privatleasing/), [Ayvens private-leasing return guide, September 2025](https://www.ayvens.com/-/media/ayvens/public/dk/ayvens_afleveringsguide_privatleasing_sep2025.pdf))

## Canonical facts to extract and preserve

Every normalized fact should retain its source value, source wording where interpretation matters, source URL, retrieval time, and confidence/provenance. A missing value is a fact about disclosure quality; it must remain `unknown` rather than becoming zero, false, included, or not applicable.

### Offer, provider, and vehicle

- covered provider, contractual lessor, intermediary/vehicle supplier if different;
- source URL, offer identifier, first seen, last checked, advertised validity/registration deadline, and contract/guide version;
- private eligibility and any credit approval condition;
- make, model, variant, model year, first-registration date, odometer, fuel/powertrain, VIN when disclosed, and included factory/aftermarket equipment;
- new/used status, availability/delivery timing, and whether the pictured/configured vehicle differs from the priced vehicle.

These are contract facts under the section 3 b tax regime, and Toyota's current campaign illustrates why offer validity, registration deadline, and pictured variant also matter in marketing. ([Motorstyrelsen — contract requirements](https://info.skat.dk/data.aspx?oid=1947431), [Toyota Yaris private leasing](https://www.toyota.dk/kampagner/yaris-active-pl-jan26-ID-22-2026))

### Independent classification axes

- provider's verbatim product labels;
- normalized residual-risk allocation: `provider`, `prospective_lessee`, `shared`, `unclear`;
- normalized registration-tax method: `full`, `proportionate_section_3b`, `unclear`;
- end mechanisms as a set: `return`, `purchase_right`, `purchase_obligation`, `nomination_right`, `nomination_obligation`, `extension`, `re_lease`, `unclear`;
- Consumer Credit Agreements Act indicator: purchase obligation disclosed/absent/unknown, with no automated legal conclusion when facts are incomplete;
- where the Act applies: source-stated credit type, cash price, total credit, borrowing rate, APR, total payable, payment schedule, mandatory ancillary service, security, withdrawal status, and early-repayment terms;
- ownership transfer intended/absent/unknown and owner/user identities where disclosed.

The Consumer Ombudsman warns that there is no fixed leasing definition. Finanstilsynet's guidance makes residual-risk allocation the operational/financial discriminator, while the credit statute uses purchase obligation as a separate legal discriminator. ([Consumer Ombudsman — Leasing](https://forbrugerombudsmanden.dk/alle-emner/andre-brancher/leasing), [Finanstilsynet AML guidance](https://www.retsinformation.dk/eli/retsinfo/2020/9864), [Consumer Credit Agreements Act](https://www.retsinformation.dk/eli/lta/2019/817))

### Base cash-flow stream

Store payments as dated or rule-based events, not only aggregate fields:

- amount, currency, due date/timing rule, payer, payee, VAT basis, tax basis, recurrence, and mandatory/optional status;
- initial ordinary payment and any delivery-to-month-end pro-rating;
- non-refundable extraordinary lease payment/first payment;
- refundable deposit or security and its contractual return timing/conditions;
- establishment/document, delivery, registration/plate, inspection, return, billing, and other unavoidable fees;
- every recurring schedule, including stepped or variable payments, index/reference-rate rule, and number of payments;
- known receipts, including contractual under-mileage refunds and refundable-security returns;
- mandatory end payment only where the prospective lessee actually must pay it.

The Volkswagen Semler standard form shows why these distinctions are necessary: the first ordinary payment may be prorated and larger, the extraordinary payment is separate and non-refundable on ordinary termination, establishment and return costs are separate, and other variable charges sit outside the advertised contract total. ([Volkswagen Semler private-leasing contract](https://www.vwsf.dk/content/dam/bluelabel/valid/www-vwsf-dk/documents/Privatleasing%20kontrakt%20version%2001.09.2023.pdf))

For a stated residual value, additionally preserve:

- value date, expected kilometres and vehicle condition assumption;
- whether amount is inclusive/exclusive of VAT and registration tax;
- whether it is a sale price, payoff, purchase price, guarantee reference, or provider-only calculation;
- prospective lessee's exact obligation: pay, purchase, nominate a buyer, guarantee a shortfall, or none;
- sale process, valuation authority, buyer restrictions, costs, shortfall formula, surplus treatment, and deadline.

Selected says its financial private offers can end through resale to a third party, own payoff, or re-calculation/re-leasing, while Fleggaard states that a lessee owes the difference if realized price is below the expected residual value. That evidence supports scenario modelling; it does not justify turning every displayed residual value into a base outflow. ([Selected Car Leasing — private leasing](https://scleasing.dk/privatleasing/), [Fleggaard Flexleasing](https://www.fleggaard-leasing.dk/flexleasing))

### Mileage, use, and return

- total and annual kilometre allowance, measurement period, pro-rating on early exit, change mechanism;
- over-kilometre rate and under-kilometre refund rate separately, including caps;
- expected kilometres used to set a financial residual value even when no hard kilometre ceiling exists;
- geographic/use restrictions, permitted drivers/subleasing, smoking/animal restrictions where disclosed;
- required service intervals, workshop restrictions, documentation, tyres, keys/cables/equipment to return;
- return date and location, transport cost, independent/lessor inspection, right to attend, applicable condition guide/version;
- definition of ordinary wear versus chargeable damage, pricing method, administration fees, and late-return consequence.

The Volkswagen Semler contract has different over- and under-kilometre terms, proportionate settlement on early termination, an independent return review, and a separate condition annex. Ayvens publishes specific return-condition and missing-item charges. These are provider practices but are material comparison facts. ([Volkswagen Semler private-leasing contract](https://www.vwsf.dk/content/dam/bluelabel/valid/www-vwsf-dk/documents/Privatleasing%20kontrakt%20version%2001.09.2023.pdf), [Ayvens return guide](https://www.ayvens.com/-/media/ayvens/public/dk/ayvens_afleveringsguide_privatleasing_sep2025.pdf))

### Included services and required external costs

Represent each item as `included`, `optional`, `required_external`, `excluded`, or `unknown`, with scope/limits:

- scheduled service;
- maintenance and mechanical/electrical repairs;
- wear parts and tyres/seasonal wheel changes;
- roadside assistance and replacement car;
- liability insurance, comprehensive insurance, deductible, and insurance-administration fee;
- periodic vehicle tax (weight, green-owner, or CO2 tax);
- fuel/electricity, AdBlue/fluids, tolls, and parking;
- warranty/reclamation coverage and provider responsibility if manufacturer warranty expires.

Toyota's current campaign includes service, establishment, and delivery but excludes periodic tax, insurance, and equipment. Ayvens uses a different bundle. The Volkswagen Semler form requires liability and comprehensive insurance even though insurance may be either included or external. ([Toyota Yaris private leasing](https://www.toyota.dk/kampagner/yaris-active-pl-jan26-ID-22-2026), [Ayvens private leasing](https://www.ayvens.com/da-dk/leasing-med-ayvens/leasingloesninger/privatleasing/), [Volkswagen Semler private-leasing contract](https://www.vwsf.dk/content/dam/bluelabel/valid/www-vwsf-dk/documents/Privatleasing%20kontrakt%20version%2001.09.2023.pdf))

### Duration, cancellation, and adverse events

- contract term, tax period if different, start/delivery rule, minimum binding period;
- notice method/period, earliest notice date, earliest effective end date;
- contractual withdrawal right if any, explicitly separate from termination;
- treatment of upfront payments, fees, mileage, service, return, and tax on ordinary early termination;
- termination for breach and damages formula;
- death, theft, total loss, invalid tax approval, delayed delivery, and provider insolvency consequences where disclosed;
- whether rates/fees are fixed, variable, or changeable and the change/exit mechanism;
- complaint body and contract-standard affiliation, if disclosed.

The FDM/Finance & Leasing-derived Volkswagen Semler form permits exit after 11 months with one month's notice, keeps the extraordinary payment and establishment costs, and settles mileage proportionately. That is evidence of one widely used standard, not a default to impute to every offer. ([Volkswagen Semler private-leasing contract](https://www.vwsf.dk/content/dam/bluelabel/valid/www-vwsf-dk/documents/Privatleasing%20kontrakt%20version%2001.09.2023.pdf), [Finance & Leasing — Leasing](https://finansogleasing.dk/leasing/))

## Normalization and comparison rules

1. **Keep raw and normalized values together.** Never overwrite “scrap value,” “residual value,” “first payment,” or a provider's leasing label with the service's interpretation.
2. **Compute signing cash separately.** It is the gross liquidity required through delivery/start, including refundable security. Do not call it a down payment or deposit unless the source does.
3. **Compute nominal base outlay from the event stream.** Sum the prospective lessee's base outflows less base receipts over normal completion. A refundable deposit normally nets to zero nominally but remains visible in signing cash and timing.
4. **Compute nominal monthly equivalent only when the base stream is complete.** Divide nominal base outlay by the contract months and label it as a service-derived comparison value, not the provider's monthly payment.
5. **Do not add a residual value by default.** Add it only when the prospective lessee has an unconditional end payment. Otherwise display the value and its shortfall formula in the residual-value exposure scenario.
6. **Do not estimate conditional exposure into the headline.** Mileage, damage, wear, early exit, and residual shortfall require user-selected scenarios. Show the formula/rate and missing inputs.
7. **Keep required external costs visible but outside an incomplete base total.** If periodic tax or insurance is required and excluded but its amount is absent or person-specific, show `required_external: amount unknown`; do not use zero.
8. **Normalize VAT only with a known basis.** For a private comparison, the main display should be gross consumer cash flows. Preserve the source net value and transformation. Never mechanically add VAT to a residual value without knowing the transaction and contractual wording.
9. **Use provider total as evidence, not unquestioned truth.** Store the provider's advertised total and independently derived total. If they differ, flag the offer for review and explain which payments were counted.
10. **Gate derived metrics on completeness.** At minimum, term, all mandatory upfront amounts, recurring schedule/payment count, known mandatory fees, and VAT basis must be known. Otherwise derived total/monthly equivalent is unavailable, with the missing fields named.
11. **Compare like scenarios.** Mileage allowance, duration, vehicle condition/age, and included services must accompany any cross-offer comparison. A cheaper monthly payment with a higher first payment or residual exposure is not intrinsically cheaper.

## Facts that must never be normalized away

- provider's original form labels and contract wording;
- who owns the car and who bears residual-value risk;
- return versus purchase/nomination right versus obligation;
- whether a stated residual value is incl./excl. VAT and registration tax, and who pays it;
- first-payment semantics and refundability;
- provider monthly payment versus service-derived monthly equivalent;
- advertised term versus minimum binding period and notice;
- full versus proportionate registration tax and whether tax is embedded in payments;
- fixed, stepped, indexed, or otherwise variable recurring payments;
- annual/total mileage, expected mileage, over-rate, under-rate, and caps;
- service/repair/tyre/insurance/periodic-tax inclusion and exact exclusions;
- condition guide, inspection method, normal-wear rules, return fees, and late-return consequences;
- missing information, conflicting values, source age, and confidence.

## Residual legal and evidentiary uncertainty

- **The actual agreements control classification.** “Financial,” “operational,” “flex,” “private leasing,” and similar labels are not enough to decide the prospective lessee's rights. The service can derive a residual-risk view from disclosed facts, but should show `unclear` and source wording rather than purport to make a legal classification when contract material is absent or contradictory. ([Consumer Ombudsman — Leasing](https://forbrugerombudsmanden.dk/alle-emner/andre-brancher/leasing))
- **Consumer-law routes depend on the end mechanism.** Ordinary private leasing without intended ownership transfer is treated differently from a purchase obligation, symbolic-price transfer, masked credit purchase, or other ownership transfer. Whether Consumer Contracts Act non-financial-service disclosures, financial-service disclosures, and/or credit-specific duties apply requires the complete transaction, including separate agreements. ([Consumer Ombudsman 2023 withdrawal opinion](https://forbrugerombudsmanden.dk/find-sager/sager/forbrugeraftaleloven/fortsat-ikke-lovkrav-om-fortrydelsesret-ved-privatleasing-af-biler), [Consumer Credit Agreements Act section 3](https://www.retsinformation.dk/eli/lta/2019/817))
- **The statutory termination date should not be inferred from price alone.** Consumer Contracts Act section 28 has fact-specific thresholds concerning annual price and the provider's one-off costs/value loss. Record the disclosed binding and notice terms, flag apparent conflicts for review, and do not have the catalogue announce a legal earliest-exit date from scraped prices alone. ([Consumer Contracts Act section 28](https://www.retsinformation.dk/eli/lta/2025/1184))
- **VAT and registration-tax treatment at realization is transaction-specific.** A residual value stated excluding VAT and registration tax cannot safely be grossed up without knowing who buys, where the vehicle is sold/registered, and what the contract requires. Preserve the basis and suppress a gross end cash flow unless the transaction is explicit.
- **A provider page is evidence of an advertised offer, not the whole agreement.** Fee lists, return guides, service annexes, insurance terms, and the signed contract can change or qualify it. The comparison should rank source authority per field and surface conflicts rather than letting the newest scrape overwrite a contractual document.
- **The legal snapshot will age.** Act no. 1322/2025 takes effect on 20 November 2026. Provider-supervision legislation and administrative tax guidance can also change. Legal-rule assertions need effective dates and scheduled revalidation before launch; this artifact should not become evergreen legal logic.

## Product-spec consequences

- The first catalogue should support `financial`, `operational`, and `unclear` as **derived residual-risk views**, while displaying provider labels verbatim.
- “Flexleasing” should be a registration-tax attribute, not the parent category for all obligations.
- Catalogue cards should present signing cash, provider monthly payment, term, minimum binding period, and derived nominal base outlay/monthly equivalent when complete. Financial offers also need a prominent residual-value exposure summary.
- Side-by-side comparison should have separate sections for base cash flow, end mechanism/residual exposure, mileage, condition/return, included services, and required external costs.
- Missing material terms should reduce a disclosure-completeness indicator and suppress misleading totals; incomplete offers may remain discoverable.
- Each normalized obligation should link to its source excerpt/page and carry a retrieval timestamp because provider pages, fee lists, and return guides change.
- Legal-rule metadata needs an effective date. In particular, Act no. 1322 of 20 November 2025 changes consumer-credit legislation from 20 November 2026, after this research snapshot. The exact impact should be rechecked before launch and versioned rather than silently applied to older offers. ([Act no. 1322/2025](https://www.retsinformation.dk/eli/lta/2025/1322/pdf))

## Sources and their evidentiary role

### Legislation and public authorities

- [Marketing Practices Act, consolidated act no. 1420 of 2 December 2024](https://www.retsinformation.dk/eli/lta/2024/1420) — binding marketing rules.
- [Consumer Contracts Act, consolidated act no. 1184 of 28 September 2025](https://www.retsinformation.dk/eli/lta/2025/1184) — binding pre-contract information, termination, and withdrawal framework.
- [Consumer Credit Agreements Act, consolidated act no. 817 of 6 August 2019](https://www.retsinformation.dk/eli/lta/2019/817) and [Act no. 2221 of 29 December 2020](https://www.retsinformation.dk/eli/lta/2020/2221) — current lease exclusion/purchase-obligation distinction and motor-leasing payment-capacity rule.
- [Act no. 1322 of 20 November 2025](https://www.retsinformation.dk/eli/lta/2025/1322/pdf) — enacted future changes effective 20 November 2026; change horizon, not current rules at the snapshot date.
- [Motorstyrelsen, Legal Guide I.A.1.7.2 — Leasing vehicles](https://info.skat.dk/data.aspx?oid=1947431) — current administrative tax guidance and section 3 b contract requirements.
- [Finanstilsynet AML guidance, section 1.1.3](https://www.retsinformation.dk/eli/retsinfo/2020/9864) — regulator definition used for financial-versus-operational residual-risk allocation.
- [Consumer Ombudsman — Leasing](https://forbrugerombudsmanden.dk/alle-emner/andre-brancher/leasing) — current regulator overview, clarity/unfair-terms rules, and complaint routes.
- [Consumer Ombudsman 2010 leasing price case](https://forbrugerombudsmanden.dk/find-sager/sager/markedsfoeringsloven/sager-efter-markedsfoeringsloven/vildledning/prisoplysninger-ved-billeasing) and [2016 online-leasing advance opinion](https://forbrugerombudsmanden.dk/find-sager/sager/markedsfoeringsloven/sager-efter-markedsfoeringsloven/kreditoplysninger/forhaandsbesked-vedr-online-markedsfoering-af-privatleasingaftale) — regulator interpretation of prominent price/term disclosure; older statutory numbering, so used as interpretation rather than current section citation.
- [Consumer Ombudsman 2023 private-leasing withdrawal opinion](https://forbrugerombudsmanden.dk/find-sager/sager/forbrugeraftaleloven/fortsat-ikke-lovkrav-om-fortrydelsesret-ved-privatleasing-af-biler) — current regulator interpretation of section 18.
- [Road Traffic Act, consolidated act no. 118 of 12 January 2026, sections 105–106](https://www.retsinformation.dk/eli/lta/2026/118) — statutory motor-liability insurance requirement.

### First-party provider and contract material

- [Volkswagen Semler private-leasing contract, version 1 September 2023](https://www.vwsf.dk/content/dam/bluelabel/valid/www-vwsf-dk/documents/Privatleasing%20kontrakt%20version%2001.09.2023.pdf) — detailed FDM/Finance & Leasing-based operational-style contract practice.
- [Toyota Yaris private-leasing campaign](https://www.toyota.dk/kampagner/yaris-active-pl-jan26-ID-22-2026) — current consumer campaign disclosure example.
- [Ayvens private leasing](https://www.ayvens.com/da-dk/leasing-med-ayvens/leasingloesninger/privatleasing/) and [return guide, September 2025](https://www.ayvens.com/-/media/ayvens/public/dk/ayvens_afleveringsguide_privatleasing_sep2025.pdf) — included/excluded service and return-charge practice.
- [Fleggaard Flexleasing](https://www.fleggaard-leasing.dk/flexleasing) — first-party operational/financial allocation and residual shortfall description.
- [Selected Car Leasing — Flexleasing](https://scleasing.dk/flexleasing/), [private leasing](https://scleasing.dk/privatleasing/), and [private cars](https://scleasing.dk/biler-leasing-privat/) — first-party private financial/flex end mechanisms, residual risk, and mileage practice.
- [Finance & Leasing — Leasing](https://finansogleasing.dk/leasing/) — industry statement that its consumer operational-leasing standard was developed with FDM and is widely used by relevant members.
