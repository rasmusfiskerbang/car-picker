import type { CatalogueOffer, CatalogueOfferFacts } from "@/catalogue-dataset";
import { presentContractFacts } from "@/offer-fact-presentation";

import { FactRow, SectionHeading } from "@/offer-detail-parts";

export function OfferDetailContractSection({
  facts,
  offer,
}: {
  facts: CatalogueOfferFacts;
  offer: CatalogueOffer;
}) {
  const presentedFacts = presentContractFacts(offer, facts);

  return (
    <section aria-labelledby="contract-heading" className="detail-section" id="contract">
      <SectionHeading eyebrow="Aftalefakta" id="contract-heading" title="Aftale" />
      <dl className="detail-facts">
        {presentedFacts.map((fact) => (
          <FactRow key={fact.label} label={fact.label} value={fact.text} />
        ))}
      </dl>
    </section>
  );
}
