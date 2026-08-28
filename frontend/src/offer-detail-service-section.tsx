import type { CatalogueOffer } from "@/catalogue-dataset";
import {
  presentService,
  type ServicePresentation,
} from "@/offer-fact-presentation";

import { SectionHeading } from "@/offer-detail-parts";

export function OfferDetailServiceSection({ offer }: { offer: CatalogueOffer }) {
  return (
    <section aria-labelledby="service-heading" className="detail-section" id="service">
      <SectionHeading
        eyebrow="Service og eksterne forhold"
        id="service-heading"
        title="Service"
      />
      <ServiceContent service={presentService(offer.serviceArrangements)} />
    </section>
  );
}

function ServiceContent({ service }: { service: ServicePresentation }) {
  if (service.kind === "unavailable") return <p>{service.text}</p>;
  if (service.kind === "empty") return <p>{service.text}</p>;

  return (
    <ul className="service-list">
      {service.arrangements.map((arrangement) => (
        <li key={`${arrangement.category}:${arrangement.treatment}`}>
          <div className="service-list-heading">
            <strong>{arrangement.category}</strong>
            <span>{arrangement.treatment}</span>
          </div>
          <p>{arrangement.summary}</p>
          <p className="service-limit">
            <span>Grænser: </span>
            {arrangement.limits}
          </p>
        </li>
      ))}
    </ul>
  );
}
