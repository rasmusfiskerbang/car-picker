import type { CatalogueOffer } from "@/catalogue-dataset";
import { presentVehicleFacts } from "@/offer-fact-presentation";

import { FactRow, SectionHeading } from "@/offer-detail-parts";

export function OfferDetailVehicleSection({ offer }: { offer: CatalogueOffer }) {
  const facts = presentVehicleFacts(offer);

  return (
    <section aria-labelledby="vehicle-heading" className="detail-section" id="vehicle">
      <SectionHeading eyebrow="Køretøjsfakta" id="vehicle-heading" title="Køretøj" />
      <dl className="detail-facts">
        {facts.map((fact) => (
          <FactRow key={fact.label} label={fact.label} value={fact.text} />
        ))}
      </dl>
    </section>
  );
}
