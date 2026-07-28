import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import {
  Outlet,
  RouterProvider,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { createRoot } from "react-dom/client";

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
  not_stated: "Ikke oplyst",
  unclear: "Uklart",
  conflicting: "Modstridende",
  not_applicable: "Ikke relevant",
} as const;

function money(value: string | number) {
  return `${currency.format(Number(value))} kr.`;
}

function factValue(
  fact: HeadlineFact,
  formatter: (value: string | number) => string,
) {
  if (fact.state !== "known") return unavailableLabels[fact.state];
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
  return (
    <div className="fact-row">
      <dt>{label}</dt>
      <dd>{factValue(fact, formatter)}</dd>
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
  return (
    <div className="page">
      <header className="hero">
        <p className="eyebrow">Evidensbaseret privatleasing</p>
        <h1>Bilvalg</h1>
        <p>
          Sammenlign kildebelagte leasingtilbud uden skjulte antagelser om
          manglende fakta.
        </p>
      </header>
      <section className="offer-list" aria-label="Katalogtilbud">
        {presentation.offers.map((offer) => (
          <OfferCard key={offer.offerIdentity} offer={offer} />
        ))}
      </section>
      <footer>
        Tilbud kan være ændret eller udløbet siden data blev indsamlet.
        Kataloget dækker muligvis ikke hele det danske marked.
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
