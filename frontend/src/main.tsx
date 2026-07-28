import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import {
  Outlet,
  RouterProvider,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { createRoot } from "react-dom/client";
import { useState } from "react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  type CataloguePresentation,
  loadPresentation,
} from "@/presentation";
import "@/styles.css";

type PresentationOffer = CataloguePresentation["offers"][number];
type HeadlineFact =
  | PresentationOffer["advertisedMonthlyPayment"]
  | PresentationOffer["upfrontCashRequirement"]
  | PresentationOffer["nominalBaseOutlay"]
  | PresentationOffer["nominalMonthlyEquivalent"]
  | PresentationOffer["termMonths"]
  | PresentationOffer["annualMileageKm"];

const currency = new Intl.NumberFormat("da-DK");
const unavailableLabels = {
  not_stated: "Ikke oplyst af udbyderen",
  unclear: "Kan ikke afgøres ud fra kilden",
  conflicting: "Modstridende oplysninger i kilden",
  not_applicable: "Ikke relevant for denne aftale",
} as const;

function money(value: string | number) {
  return `${currency.format(Number(value))} kr.`;
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
  fact: HeadlineFact,
  formatter: (value: string | number) => string,
) {
  if (fact.state !== "known") {
    return "calculation" in fact
      ? "Kan ikke beregnes"
      : unavailableLabels[fact.state];
  }
  return formatter("valueDkk" in fact ? fact.valueDkk : fact.value);
}

function FactRow({
  label,
  fact,
  formatter = String,
}: {
  label: string;
  fact: HeadlineFact;
  formatter?: (value: string | number) => string;
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
    </div>
  );
}

function Calculation({ offer }: { offer: PresentationOffer }) {
  const evidence = offer.nominalBaseOutlay.calculation.inputEvidence;
  return (
    <details className="calculation">
      <summary>Se beregning og kildegrundlag</summary>
      <p>
        De beregnede beløb kommer fra tilbuddets dokumenterede
        basiskontantstrøm.
      </p>
      <ul>
        {evidence.map((item) => (
          <li key={`${item.sourceUrl}:${item.wording}`}>{item.wording}</li>
        ))}
      </ul>
    </details>
  );
}

function OfferCard({ offer }: { offer: PresentationOffer }) {
  const vehicle =
    offer.vehicleSpecification.state === "known"
      ? offer.vehicleSpecification.value
      : `Køretøj: ${unavailableLabels[offer.vehicleSpecification.state]}`;
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

function Catalogue({ presentation }: { presentation: CataloguePresentation }) {
  const [search, setSearch] = useState("");
  const [leasingForm, setLeasingForm] = useState("all");
  const [residualRisk, setResidualRisk] = useState("all");
  const [vehicleSpecification, setVehicleSpecification] = useState("");
  const [maxUpfront, setMaxUpfront] = useState("");
  const [termMonths, setTermMonths] = useState("all");
  const [minimumMileage, setMinimumMileage] = useState("");
  const filteredOffers = presentation.offers.filter((offer) => {
    const query = search.trim().toLocaleLowerCase("da");
    const searchable = `${offer.provider} ${
      offer.vehicleSpecification.state === "known"
        ? offer.vehicleSpecification.value
        : ""
    }`.toLocaleLowerCase("da");
    const upfrontRequirement =
      offer.upfrontCashRequirement.state === "known"
        ? offer.upfrontCashRequirement.valueDkk
        : null;
    return (
      (!query || searchable.includes(query)) &&
      (!vehicleSpecification ||
        (offer.vehicleSpecification.state === "known" &&
          String(offer.vehicleSpecification.value)
            .toLocaleLowerCase("da")
            .includes(vehicleSpecification.trim().toLocaleLowerCase("da")))) &&
      (leasingForm === "all" ||
        (offer.supportedLeasingForm.state === "known" &&
          offer.supportedLeasingForm.value === leasingForm)) &&
      (residualRisk === "all" ||
        (offer.residualRiskAllocation.state === "known" &&
          offer.residualRiskAllocation.value === residualRisk)) &&
      (!maxUpfront ||
        (upfrontRequirement !== null &&
          upfrontRequirement <= Number(maxUpfront))) &&
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

  return (
    <div className="page">
      <header className="hero">
        <h1>Bilvalg</h1>
      </header>
      <p className="freshness">
        Katalogdatasæt genereret {generatedAt}. Tilbud kan være ændret eller
        udløbet siden.
      </p>
      <form className="filters" onSubmit={(event) => event.preventDefault()}>
        <div className="filter-heading">
          <h2>Filtre</h2>
          <button type="button" onClick={resetFilters}>
            Nulstil filtre
          </button>
        </div>
        <label>
          Søg i køretøjsspecifikation eller dækket udbyder
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <label>
          Filtrér køretøjsspecifikation
          <input
            type="search"
            value={vehicleSpecification}
            onChange={(event) => setVehicleSpecification(event.target.value)}
            placeholder="Fx BMW, i4 eller M50"
          />
        </label>
        <label>
          Leasingform
          <select
            value={leasingForm}
            onChange={(event) => setLeasingForm(event.target.value)}
          >
            <option value="all">Alle former</option>
            <option value="operational">Operationel</option>
            <option value="financial">Finansiel / flex</option>
            <option value="hybrid">Hybrid</option>
          </select>
        </label>
        <label>
          Restværdirisiko
          <select
            value={residualRisk}
            onChange={(event) => setResidualRisk(event.target.value)}
          >
            <option value="all">Alle fordelinger</option>
            <option value="provider">Udbyderen bærer risikoen</option>
            <option value="lessee">Den potentielle leasingtager bærer risikoen</option>
            <option value="shared">Risikoen er delt</option>
          </select>
        </label>
        <label>
          Maks. kontant behov ved start
          <input
            type="number"
            min="0"
            inputMode="numeric"
            value={maxUpfront}
            onChange={(event) => setMaxUpfront(event.target.value)}
            placeholder="Ingen grænse"
          />
        </label>
        <label>
          Fuld løbetid
          <select
            value={termMonths}
            onChange={(event) => setTermMonths(event.target.value)}
          >
            <option value="all">Alle løbetider</option>
            {availableTerms.map((term) => (
              <option key={term} value={term}>
                {term} måneder
              </option>
            ))}
          </select>
        </label>
        <label>
          Mindst kilometer om året
          <input
            type="number"
            min="0"
            inputMode="numeric"
            value={minimumMileage}
            onChange={(event) => setMinimumMileage(event.target.value)}
            placeholder="Ingen grænse"
          />
        </label>
      </form>
      <section className="offer-list" aria-label="Katalogtilbud">
        {filteredOffers.map((offer) => (
          <OfferCard key={offer.offerIdentity} offer={offer} />
        ))}
        {filteredOffers.length === 0 && (
          <div className="empty-state">
            <h2>Ingen tilbud matcher i det aktive katalog</h2>
            <p>Prøv at ændre eller nulstille filtrene.</p>
            <button type="button" onClick={resetFilters}>
              Nulstil filtre
            </button>
          </div>
        )}
      </section>
      <section className="coverage" aria-labelledby="coverage-heading">
        <h2 id="coverage-heading">Dækning af det aktive katalog</h2>
        <p>
          Dette er de dækkede udbydere og deres afgrænsede, udpegede
          tilbudskilder – ikke hele det danske marked.
        </p>
        <ul>
          {presentation.coverage.providers.map((provider) => (
            <li key={`${provider.name}:${provider.designatedSource}`}>
              <strong>{provider.name}</strong>
              <span>{provider.designatedSource}</span>
              <span>
                {provider.quarantinedCandidateCount} karantænesatte
                katalogkandidater
              </span>
            </li>
          ))}
        </ul>
      </section>
      <footer className="persistent-disclaimer">
        <strong>Ingen personlig rangering.</strong> Filtre indsnævrer kun det
        aktive katalog; den faste kilderækkefølge er ikke en anbefaling.
        Katalogdatasæt genereret {generatedAt}. Tilbud kan være ændret eller
        udløbet siden. Kataloget dækker ikke nødvendigvis hele det danske marked.
      </footer>
    </div>
  );
}

function Application() {
  const presentation = useQuery({
    queryKey: ["catalogue-presentation"],
    queryFn: loadPresentation,
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
  });
  if (presentation.isPending) {
    return <p className="message">Kataloget indlæses…</p>;
  }
  if (presentation.isError) {
    return (
      <section className="message" role="alert">
        <h1>Kataloget kan ikke vises</h1>
        <p>Katalogdata bestod ikke den nødvendige kontrol.</p>
      </section>
    );
  }
  return <Catalogue presentation={presentation.data} />;
}

const rootRoute = createRootRoute({ component: () => <Outlet /> });
const catalogueRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: Application,
});
const routeTree = rootRoute.addChildren([catalogueRoute]);
const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

const queryClient = new QueryClient();
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}>
    <RouterProvider router={router} />
  </QueryClientProvider>,
);
