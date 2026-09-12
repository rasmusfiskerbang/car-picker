import { Link } from "@tanstack/react-router";
import {
  ArrowRight,
  ChevronRight,
  ExternalLink,
  Layers3,
  Search,
} from "lucide-react";

import {
  type CatalogueDataset,
  deriveCatalogueFacts,
} from "@/catalogue-dataset";
import { offerSelectionSearch } from "@/offer-selection-search";

const number = new Intl.NumberFormat("da-DK");

type GuideStep = {
  description: string;
  icon: typeof Search;
  kicker: string;
  title: string;
};

const guideSteps: GuideStep[] = [
  {
    description:
      "Start i et dateret katalog fra navngivne udbydere — ikke i en påstand om at dække hele markedet.",
    icon: Search,
    kicker: "01 · Omfang",
    title: "Se, hvad der faktisk er med",
  },
  {
    description:
      "Sæt månedsydelse, startbetaling, beregnet total, løbetid og kilometer ved siden af hinanden.",
    icon: Layers3,
    kicker: "02 · Aftalen",
    title: "Sammenlign de samme fakta",
  },
  {
    description:
      "Læs hvordan aftalen slutter, og åbn altid det oprindelige tilbud hos udbyderen, før du går videre.",
    icon: ExternalLink,
    kicker: "03 · Kilden",
    title: "Kontrollér vilkårene selv",
  },
];

function countLabel(count: number, singular: string, plural: string): string {
  return number.format(count) + " " + (count === 1 ? singular : plural);
}

function CatalogueCallToAction({
  count,
  selectedOfferIdentities,
}: {
  count: number;
  selectedOfferIdentities: readonly string[];
}) {
  return (
    <Link
      className="landing-cta"
      search={offerSelectionSearch(selectedOfferIdentities)}
      to="/catalogue"
    >
      Se alle {number.format(count)} tilbud
      <ArrowRight aria-hidden="true" />
    </Link>
  );
}

export function LandingPage({
  dataset,
  selectedOfferIdentities,
}: {
  dataset: CatalogueDataset;
  selectedOfferIdentities: readonly string[];
}) {
  const facts = deriveCatalogueFacts(dataset);

  return (
    <main className="landing-page">
      <section className="landing-introduction">
        <p className="landing-eyebrow">Privatleasing i Danmark</p>
        <h1>
          Sammenlign aftalen,
          <br />
          ikke kun månedsprisen.
        </h1>
        <p className="landing-lede">
          Se dokumenterede privatleasingtilbud på samme grundlag — fra første
          betaling til aftalens afslutning.
        </p>
      </section>

      <section
        aria-labelledby="landing-guide-heading"
        className="landing-guide"
      >
        <h2 className="visually-hidden" id="landing-guide-heading">
          Sådan bruges Bilvalg
        </h2>
        {guideSteps.map((step, index) => (
          <article className="landing-guide-step" key={step.title}>
            <div className="landing-guide-kicker">
              <p>{step.kicker}</p>
              <step.icon aria-hidden="true" />
            </div>
            <h3>{step.title}</h3>
            <p>{step.description}</p>
            {index < guideSteps.length - 1 && (
              <span aria-hidden="true" className="landing-guide-arrow">
                <ChevronRight />
              </span>
            )}
          </article>
        ))}
      </section>

      <section className="landing-catalogue-panel">
        <div>
          <p className="landing-catalogue-count">
            {countLabel(facts.offerCount, "tilbud er", "tilbud er")} klar til
            sammenligning
          </p>
          <p className="landing-catalogue-meta">
            Fra{" "}
            {countLabel(
              facts.activeProviderCount,
              "aktiv udbyder",
              "aktive udbydere",
            )}{" "}
            · neutral kildeorden · ingen anbefalinger
          </p>
        </div>
        <CatalogueCallToAction
          count={facts.offerCount}
          selectedOfferIdentities={selectedOfferIdentities}
        />
      </section>
    </main>
  );
}
