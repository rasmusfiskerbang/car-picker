import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import { useEffect, useState } from "react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  type CataloguePresentation,
  loadPresentation,
} from "@/presentation";
import "@/styles.css";

type PresentationOffer = CataloguePresentation["offers"][number];
type ValueFact = PresentationOffer["vehicleSpecification"];
type MoneyFact = PresentationOffer["advertisedMonthlyPayment"];
type DerivedMoneyFact = PresentationOffer["nominalBaseOutlay"];
type DisplayFact = ValueFact | MoneyFact | DerivedMoneyFact;
type Evidence = { sourceUrl: string; wording: string };
type Exposure = Extract<
  PresentationOffer["exposureScenarios"],
  { state: "known" }
>["value"][number];
type Service = Extract<
  PresentationOffer["serviceArrangements"],
  { state: "known" }
>["value"][number];
type EvidenceDisplay =
  | { calculation: Extract<DerivedMoneyFact, { state: "known" }>["calculation"] }
  | { evidence: Evidence };
type ListFactValue<T> =
  | { state: "known"; evidence: Evidence; value: T[] }
  | {
      state: keyof typeof unavailableLabels;
      evidence: Evidence;
    };

const currency = new Intl.NumberFormat("da-DK");
const unavailableLabels = {
  not_stated: "Ikke oplyst af udbyderen",
  unclear: "Kan ikke afgøres ud fra kilden",
  conflicting: "Modstridende oplysninger i kilden",
  not_applicable: "Ikke relevant for denne aftale",
} as const;

const valueLabels: Record<string, string> = {
  operational: "Operationel privatleasing",
  financial: "Finansiel / flexleasing",
  hybrid: "Hybrid leasingform",
  provider: "Udbyderen bærer restværdirisikoen",
  lessee: "Den potentielle leasingtager bærer restværdirisikoen",
  shared: "Restværdirisikoen er delt",
  full: "Registreringsafgiften er betalt fuldt",
  proportional: "Registreringsafgiften betales forholdsmæssigt",
};

function money(value: string | number) {
  return `${currency.format(Number(value))} kr.`;
}

function vehicleName(offer: PresentationOffer) {
  return offer.vehicleSpecification.state === "known"
    ? String(offer.vehicleSpecification.value)
    : `Køretøj: ${unavailableLabels[offer.vehicleSpecification.state]}`;
}

function endMechanism(value: string | number) {
  const labels: Record<string, string> = {
    return_to_provider: "Bilen afleveres til udbyderen ved normalt udløb",
    designate_third_party_buyer:
      "Den potentielle leasingtager skal anvise en tredjepartskøber ved normalt udløb",
    mandatory_purchase_or_payoff:
      "Den potentielle leasingtager skal købe bilen eller betale restforpligtelsen ved normalt udløb",
  };
  return labels[String(value)] ?? "Den normale afslutning er ikke klassificeret";
}

function factValue(
  fact: DisplayFact,
  formatter: (value: string | number) => string = (value) =>
    valueLabels[String(value)] ?? String(value),
) {
  if (fact.state !== "known") {
    return "calculation" in fact
      ? "Kan ikke beregnes"
      : unavailableLabels[fact.state];
  }
  return formatter("valueDkk" in fact ? fact.valueDkk : fact.value);
}

function EvidenceDetails({
  label,
  fact,
}: {
  label: string;
  fact: EvidenceDisplay;
}) {
  if ("calculation" in fact) {
    return (
      <details className="evidence">
        <summary>Beregning for {label}</summary>
        <p>Beregnet fra tilbuddets dokumenterede betalingsstrøm.</p>
        {fact.calculation.inputEvidence.map((item) => (
          <a
            href={item.sourceUrl}
            key={`${item.sourceUrl}:${item.wording}`}
            rel="noreferrer"
          >
            {item.wording}
          </a>
        ))}
      </details>
    );
  }
  return (
    <details className="evidence">
      <summary>Kilde for {label}</summary>
      <p>{fact.evidence.wording}</p>
      <a href={fact.evidence.sourceUrl} rel="noreferrer">
        Åbn udpeget førstehåndskilde
      </a>
    </details>
  );
}

function FactRow({
  label,
  fact,
  formatter,
  evidence = false,
}: {
  label: string;
  fact: DisplayFact;
  formatter?: (value: string | number) => string;
  evidence?: boolean;
}) {
  const blockingFacts =
    "blockingFacts" in fact && fact.blockingFacts.length > 0
      ? fact.blockingFacts
      : null;
  return (
    <div className="fact-row">
      <dt>{label}</dt>
      <dd>{factValue(fact, formatter)}</dd>
      {fact.state !== "known" && (
        <p className="fact-explanation">
          {blockingFacts?.join(" · ") ??
            ("evidence" in fact
              ? fact.evidence.wording
              : "De nødvendige fakta er ikke oplyst.")}
        </p>
      )}
      {evidence && <EvidenceDetails label={label} fact={fact} />}
    </div>
  );
}

function Calculation({ offer }: { offer: PresentationOffer }) {
  return (
    <details className="calculation">
      <summary>Se beregning og kildegrundlag</summary>
      <p>
        De beregnede beløb kommer fra tilbuddets dokumenterede
        basiskontantstrøm.
      </p>
      <ul>
        {offer.nominalBaseOutlay.calculation.inputEvidence.map((item) => (
          <li key={`${item.sourceUrl}:${item.wording}`}>{item.wording}</li>
        ))}
      </ul>
    </details>
  );
}

function OfferCard({
  offer,
  selected,
  onSelectionChange,
}: {
  offer: PresentationOffer;
  selected: boolean;
  onSelectionChange: (selected: boolean) => void;
}) {
  const vehicle = vehicleName(offer);
  return (
    <Card>
      <CardHeader>
        <div>
          <p className="eyebrow">{offer.provider}</p>
          <h2>{vehicle}</h2>
        </div>
        <a href={offer.providerSourceUrl} rel="noreferrer">
          Åbn førstehåndskilde
        </a>
      </CardHeader>
      <CardContent>
        <div className="offer-actions">
          <label>
            <input
              aria-label={`Vælg ${vehicle} til sammenligning`}
              checked={selected}
              onChange={(event) => onSelectionChange(event.target.checked)}
              type="checkbox"
            />
            Vælg til sammenligning
          </label>
          <a
            aria-label={`Se detaljer for ${vehicle}`}
            href={`#/offer/${encodeURIComponent(offer.offerIdentity)}`}
          >
            Se aftalevilkår og kilder
          </a>
        </div>
        <dl className="facts">
          <FactRow
            label="Normal afslutning"
            fact={offer.normalEndMechanism}
            formatter={endMechanism}
          />
          <FactRow
            label="Annonceret månedlig ydelse"
            fact={offer.advertisedMonthlyPayment}
            formatter={money}
          />
          <FactRow
            label="Kontant behov ved start"
            fact={offer.upfrontCashRequirement}
            formatter={money}
          />
          <FactRow
            label="Nominelt basisudlæg"
            fact={offer.nominalBaseOutlay}
            formatter={money}
          />
          <FactRow
            label="Nominelt månedligt gennemsnit"
            fact={offer.nominalMonthlyEquivalent}
            formatter={money}
          />
          <FactRow
            label="Fuld løbetid"
            fact={offer.termMonths}
            formatter={(value) => `${value} måneder`}
          />
          <FactRow
            label="Kilometer om året"
            fact={offer.annualMileageKm}
            formatter={(value) => `${currency.format(Number(value))} km`}
          />
        </dl>
        <Calculation offer={offer} />
      </CardContent>
    </Card>
  );
}

function ListFact<T>({
  label,
  fact,
  formatter,
}: {
  label: string;
  fact: ListFactValue<T>;
  formatter: (value: T) => string;
}) {
  return (
    <section className="detail-fact">
      <h3>{label}</h3>
      {fact.state === "known" ? (
        <ul>
          {fact.value.map((item, index) => (
            <li key={index}>{formatter(item)}</li>
          ))}
        </ul>
      ) : (
        <p>{unavailableLabels[fact.state]}</p>
      )}
      <EvidenceDetails label={label} fact={fact} />
    </section>
  );
}

function serviceText(
  service: Extract<
    PresentationOffer["serviceArrangements"],
    { state: "known" }
  >["value"][number],
) {
  const treatments = {
    included: "inkluderet",
    optional: "valgfri",
    required_external: "påkrævet eksternt",
    excluded: "udelukket",
  };
  return `${service.category}: ${treatments[service.treatment]}. ${service.scope}`;
}

function exposureText(exposure: Exposure) {
  const values = [
    exposure.rateDkk != null ? `${money(exposure.rateDkk)} pr. enhed` : null,
    exposure.capDkk != null ? `loft ${money(exposure.capDkk)}` : null,
    exposure.amountDkk != null ? `fast beløb ${money(exposure.amountDkk)}` : null,
  ].filter(Boolean);
  return `${exposure.kind}: ${exposure.trigger} ${
    exposure.requiredInputs.length
      ? `Kræver: ${exposure.requiredInputs.join(", ")}.`
      : "Beløb er ikke oplyst."
  } ${values.join(" · ")}`;
}

function ScenarioCalculation({ exposure }: { exposure: Exposure }) {
  const [inputs, setInputs] = useState(() =>
    exposure.requiredInputs.map(() => ""),
  );
  const calculable =
    (exposure.kind === "excess_mileage" &&
      exposure.inputKinds?.[0] === "excess_distance_km" &&
      exposure.rateDkk != null &&
      inputs.length === 1) ||
    (exposure.kind === "residual_shortfall" &&
      exposure.formula === "residual_value_minus_sale_proceeds" &&
      exposure.inputKinds?.join(",") ===
        "residual_value_dkk,sale_proceeds_dkk" &&
      inputs.length === 2) ||
    (exposure.kind === "fixed_fee" &&
      exposure.amountDkk != null &&
      inputs.length === 0);
  if (!calculable) {
    return (
      <p>
        {exposure.kind} kan ikke beregnes uden en dokumenteret regel og alle
        nødvendige input.
      </p>
    );
  }
  const numbers = inputs.map(Number);
  const inputsValid = inputs.every(
    (value) => value !== "" && Number.isInteger(Number(value)) && Number(value) >= 0,
  );
  let result = exposure.amountDkk ?? 0;
  let arithmetic = `fast beløb ${money(result)}`;
  if (exposure.kind === "excess_mileage" && inputsValid) {
    result = numbers[0] * (exposure.rateDkk ?? 0);
    arithmetic = `${exposure.inputKinds?.[0]} (${currency.format(numbers[0])}) × ${money(exposure.rateDkk ?? 0)}`;
  }
  if (exposure.kind === "residual_shortfall" && inputsValid) {
    result = Math.max(0, numbers[0] - numbers[1]);
    arithmetic = `max(0, ${currency.format(numbers[0])} − ${currency.format(numbers[1])})`;
  }
  if (exposure.capDkk != null) result = Math.min(result, exposure.capDkk);
  if (exposure.capDkk != null) {
    arithmetic = `min(${arithmetic}, loft ${money(exposure.capDkk)})`;
  }
  return (
    <section className="scenario-calculation">
      <h4>Dit beregningseksempel</h4>
      <p>
        Dette er den potentielle leasingtagers beregningseksempel, ikke en
        prognose. Beregningseksemplet ændrer ikke tilbudets basisbeløb.
      </p>
      {exposure.requiredInputs.map((input, index) => (
        <label key={exposure.inputKinds?.[index] ?? input}>
          {exposure.inputKinds?.[index] ?? input}
          <input
            aria-label={exposure.inputKinds?.[index] ?? input}
            inputMode="numeric"
            min="0"
            onChange={(event) =>
              setInputs((current) =>
                current.map((value, position) =>
                  position === index ? event.target.value : value,
                ),
              )
            }
            type="number"
            value={inputs[index]}
          />
        </label>
      ))}
      <output role="status">
        {inputsValid || inputs.length === 0
          ? `Regnestykke: ${arithmetic} = ${money(result)}`
          : "Udfyld alle nødvendige input med hele, ikke-negative tal for at se eksemplet."}
      </output>
    </section>
  );
}

function OfferDetail({ offer }: { offer: PresentationOffer }) {
  const end = factValue(offer.normalEndMechanism, endMechanism);
  return (
    <main className="page detail-page">
      <a href="#">Tilbage til kataloget</a>
      <header className="detail-header">
        <p className="eyebrow">
          {offer.provider} · {vehicleName(offer)}
        </p>
        <h1>{end}</h1>
      </header>
      <section aria-labelledby="contract-heading">
        <h2 id="contract-heading">Aftalens uafhængige dimensioner</h2>
        <dl className="detail-facts">
          <FactRow
            evidence
            fact={offer.normalEndMechanism}
            formatter={endMechanism}
            label="Normal afslutning"
          />
          <FactRow
            evidence
            fact={offer.residualRiskAllocation}
            label="Restværdirisiko"
          />
          <FactRow
            evidence
            fact={offer.registrationTaxTreatment}
            label="Registreringsafgift"
          />
          <FactRow
            evidence
            fact={offer.supportedLeasingForm}
            label="Leasingform"
          />
          <FactRow
            evidence
            fact={offer.providerFormLabel}
            label="Udbyderens formbetegnelse"
          />
        </dl>
      </section>
      <section>
        <h2>Service og eksterne omkostninger</h2>
        <ListFact
          fact={offer.serviceArrangements}
          formatter={serviceText}
          label="Serviceordninger"
        />
        <ListFact
          fact={offer.exclusions}
          formatter={serviceText}
          label="Udelukket eller eksternt"
        />
      </section>
      <section>
        <h2>Betingede eksponeringer</h2>
        <ListFact
          fact={offer.exposureScenarios}
          formatter={exposureText}
          label="Mulige betalinger"
        />
        {offer.exposureScenarios.state === "known" &&
          offer.exposureScenarios.value.map((exposure, index) => (
            <ScenarioCalculation
              exposure={exposure}
              key={`${exposure.kind}:${index}`}
            />
          ))}
      </section>
      <Calculation offer={offer} />
      <p>
        Kontrollér altid aktuel pris og vilkår hos udbyderen.{" "}
        <a href={offer.providerSourceUrl} rel="noreferrer">
          Åbn udbyderens førstehåndskilde
        </a>
      </p>
    </main>
  );
}

const comparisonFields: [
  string,
  keyof PresentationOffer,
  ((value: string | number) => string)?,
][] = [
  ["Køretøj", "vehicleSpecification"],
  ["Kontant behov ved start", "upfrontCashRequirement", money],
  ["Nominelt basisudlæg", "nominalBaseOutlay", money],
  ["Nominelt månedligt gennemsnit", "nominalMonthlyEquivalent", money],
  ["Annonceret månedlig ydelse", "advertisedMonthlyPayment", money],
  ["Fuld løbetid", "termMonths", (value) => `${value} måneder`],
  ["Kilometer om året", "annualMileageKm", (value) => `${currency.format(Number(value))} km`],
  ["Normal afslutning", "normalEndMechanism", endMechanism],
  ["Leasingform", "supportedLeasingForm"],
  ["Restværdirisiko", "residualRiskAllocation"],
  ["Registreringsafgift", "registrationTaxTreatment"],
  ["Udbyderens formbetegnelse", "providerFormLabel"],
  ["Serviceordninger", "serviceArrangements"],
  ["Udelukket eller eksternt", "exclusions"],
  ["Betingede eksponeringer", "exposureScenarios"],
];

function comparisonValue(offer: PresentationOffer, key: keyof PresentationOffer) {
  const fact = offer[key] as DisplayFact;
  if (fact.state !== "known") return unavailableLabels[fact.state];
  if ("valueDkk" in fact) return fact.valueDkk;
  if (!("value" in fact)) return "";
  if (key === "serviceArrangements" || key === "exclusions") {
    return (fact.value as unknown as Service[])
      .map(serviceText)
      .join(" · ");
  }
  if (key === "exposureScenarios") {
    return (fact.value as unknown as Exposure[])
      .map(exposureText)
      .join(" · ");
  }
  return fact.value;
}

function Comparison({ offers }: { offers: PresentationOffer[] }) {
  return (
    <main className="page comparison-page">
      <a href="#">Tilbage til kataloget</a>
      <h1>Sammenlign tilbud</h1>
      <div className="comparison-scroll" data-testid="comparison-scroll">
        <table aria-label="Sammenligning af tilbud" className="comparison-table">
          <thead>
            <tr>
              <th scope="col">Felt</th>
              {offers.map((offer) => (
                <th key={offer.offerIdentity} scope="col">
                  {offer.provider} · {vehicleName(offer)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {comparisonFields.map(([label, key, formatter]) => (
              <tr key={key}>
                <th scope="row">{label}</th>
                {offers.map((offer) => {
                  const value = comparisonValue(offer, key);
                  return (
                    <td key={offer.offerIdentity}>
                      {formatter && typeof value !== "object"
                        ? formatter(value)
                        : valueLabels[String(value)] ?? String(value)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}

function Catalogue({ presentation }: { presentation: CataloguePresentation }) {
  const [search, setSearch] = useState("");
  const [leasingForm, setLeasingForm] = useState("all");
  const [residualRisk, setResidualRisk] = useState("all");
  const [vehicleSpecification, setVehicleSpecification] = useState("");
  const [maxUpfront, setMaxUpfront] = useState("");
  const [termMonths, setTermMonths] = useState("all");
  const [minimumMileage, setMinimumMileage] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const filteredOffers = presentation.offers.filter((offer) => {
    const query = search.trim().toLocaleLowerCase("da");
    const searchable = `${offer.provider} ${vehicleName(offer)}`.toLocaleLowerCase("da");
    const upfront =
      offer.upfrontCashRequirement.state === "known"
        ? offer.upfrontCashRequirement.valueDkk
        : null;
    return (
      (!query || searchable.includes(query)) &&
      (!vehicleSpecification ||
        vehicleName(offer)
          .toLocaleLowerCase("da")
          .includes(vehicleSpecification.trim().toLocaleLowerCase("da"))) &&
      (leasingForm === "all" ||
        (offer.supportedLeasingForm.state === "known" &&
          offer.supportedLeasingForm.value === leasingForm)) &&
      (residualRisk === "all" ||
        (offer.residualRiskAllocation.state === "known" &&
          offer.residualRiskAllocation.value === residualRisk)) &&
      (!maxUpfront || (upfront !== null && upfront <= Number(maxUpfront))) &&
      (termMonths === "all" ||
        (offer.termMonths.state === "known" &&
          offer.termMonths.value === Number(termMonths))) &&
      (!minimumMileage ||
        (offer.annualMileageKm.state === "known" &&
          Number(offer.annualMileageKm.value) >= Number(minimumMileage)))
    );
  });
  const availableTerms = [
    ...new Set(
      presentation.offers.flatMap((offer) =>
        offer.termMonths.state === "known"
          ? [Number(offer.termMonths.value)]
          : [],
      ),
    ),
  ].sort((left, right) => left - right);
  const resetFilters = () => {
    setSearch("");
    setLeasingForm("all");
    setResidualRisk("all");
    setVehicleSpecification("");
    setMaxUpfront("");
    setTermMonths("all");
    setMinimumMileage("");
  };
  const generatedAt = new Intl.DateTimeFormat("da-DK", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(presentation.generatedAt));
  const comparisonHref = `#/compare/${selected.map(encodeURIComponent).join(",")}`;

  return (
    <div className="page">
      <header className="hero"><h1>Bilvalg</h1></header>
      <p className="freshness">
        Katalogdatasæt genereret {generatedAt}. Tilbud kan være ændret eller
        udløbet siden.
      </p>
      <form className="filters" onSubmit={(event) => event.preventDefault()}>
        <div className="filter-heading">
          <h2>Filtre</h2>
          <button type="button" onClick={resetFilters}>Nulstil filtre</button>
        </div>
        <label>Søg i køretøjsspecifikation eller dækket udbyder<input type="search" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
        <label>Filtrér køretøjsspecifikation<input type="search" value={vehicleSpecification} onChange={(event) => setVehicleSpecification(event.target.value)} placeholder="Fx BMW, i4 eller M50" /></label>
        <label>Leasingform<select value={leasingForm} onChange={(event) => setLeasingForm(event.target.value)}><option value="all">Alle former</option><option value="operational">Operationel</option><option value="financial">Finansiel / flex</option><option value="hybrid">Hybrid</option></select></label>
        <label>Restværdirisiko<select value={residualRisk} onChange={(event) => setResidualRisk(event.target.value)}><option value="all">Alle fordelinger</option><option value="provider">Udbyderen bærer risikoen</option><option value="lessee">Den potentielle leasingtager bærer risikoen</option><option value="shared">Risikoen er delt</option></select></label>
        <label>Maks. kontant behov ved start<input type="number" min="0" inputMode="numeric" value={maxUpfront} onChange={(event) => setMaxUpfront(event.target.value)} placeholder="Ingen grænse" /></label>
        <label>Fuld løbetid<select value={termMonths} onChange={(event) => setTermMonths(event.target.value)}><option value="all">Alle løbetider</option>{availableTerms.map((term) => <option key={term} value={term}>{term} måneder</option>)}</select></label>
        <label>Mindst kilometer om året<input type="number" min="0" inputMode="numeric" value={minimumMileage} onChange={(event) => setMinimumMileage(event.target.value)} placeholder="Ingen grænse" /></label>
      </form>
      <aside className="comparison-control">
        {selected.length < 2 ? (
          <p>Vælg mindst to tilbud for at sammenligne dem.</p>
        ) : (
          <a href={comparisonHref}>Sammenlign {selected.length} tilbud</a>
        )}
      </aside>
      <section className="offer-list" aria-label="Katalogtilbud">
        {filteredOffers.map((offer) => (
          <OfferCard
            key={offer.offerIdentity}
            offer={offer}
            selected={selected.includes(offer.offerIdentity)}
            onSelectionChange={(checked) =>
              setSelected((current) =>
                checked
                  ? [...current, offer.offerIdentity]
                  : current.filter((identity) => identity !== offer.offerIdentity),
              )
            }
          />
        ))}
        {filteredOffers.length === 0 && <div className="empty-state"><h2>Ingen tilbud matcher i det aktive katalog</h2><p>Prøv at ændre eller nulstille filtrene.</p><button type="button" onClick={resetFilters}>Nulstil filtre</button></div>}
      </section>
      <section className="coverage" aria-labelledby="coverage-heading">
        <h2 id="coverage-heading">Dækning af det aktive katalog</h2>
        <p>Dette er de dækkede udbydere og deres afgrænsede, udpegede tilbudskilder – ikke hele det danske marked.</p>
        <ul>{presentation.coverage.providers.map((provider) => <li key={`${provider.name}:${provider.designatedSource}`}><strong>{provider.name}</strong><span>{provider.designatedSource}</span><span>{provider.quarantinedCandidateCount} karantænesatte katalogkandidater</span></li>)}</ul>
      </section>
      <footer className="persistent-disclaimer"><strong>Ingen personlig rangering.</strong> Filtre indsnævrer kun det aktive katalog; den faste kilderækkefølge er ikke en anbefaling. Katalogdatasæt genereret {generatedAt}. Tilbud kan være ændret eller udløbet siden. Kataloget dækker ikke nødvendigvis hele det danske marked.</footer>
    </div>
  );
}

function PresentationApplication({
  presentation,
}: {
  presentation: CataloguePresentation;
}) {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const updateHash = () => setHash(window.location.hash);
    window.addEventListener("hashchange", updateHash);
    return () => window.removeEventListener("hashchange", updateHash);
  }, []);
  const detailMatch = hash.match(/^#\/offer\/(.+)$/);
  if (detailMatch) {
    const identity = decodeURIComponent(detailMatch[1]);
    const offer = presentation.offers.find((item) => item.offerIdentity === identity);
    return offer ? <OfferDetail offer={offer} /> : <p className="message">Tilbuddet findes ikke i dette katalog.</p>;
  }
  const comparisonMatch = hash.match(/^#\/compare\/(.+)$/);
  if (comparisonMatch) {
    const identities = comparisonMatch[1].split(",").map(decodeURIComponent);
    const offers = identities.flatMap((identity) => {
      const offer = presentation.offers.find((item) => item.offerIdentity === identity);
      return offer ? [offer] : [];
    });
    return offers.length >= 2 ? <Comparison offers={offers} /> : <p className="message">Vælg mindst to tilbud fra kataloget.</p>;
  }
  return <Catalogue presentation={presentation} />;
}

function Application() {
  const presentation = useQuery({
    queryKey: ["catalogue-presentation"],
    queryFn: loadPresentation,
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
  });
  if (presentation.isPending) return <p className="message">Kataloget indlæses…</p>;
  if (presentation.isError) return <section className="message" role="alert"><h1>Kataloget kan ikke vises</h1><p>Katalogdata bestod ikke den nødvendige kontrol.</p></section>;
  return <PresentationApplication presentation={presentation.data} />;
}

const queryClient = new QueryClient();
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}>
    <Application />
  </QueryClientProvider>,
);
