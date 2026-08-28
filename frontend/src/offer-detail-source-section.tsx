import type { findProviderById } from "@/catalogue-dataset";

import { FactRow, SectionHeading } from "@/offer-detail-parts";

type Provider = ReturnType<typeof findProviderById>;

export function OfferDetailSourceSection({
  canonicalOfferUrl,
  provider,
  providerId,
}: {
  canonicalOfferUrl: string;
  provider: Provider;
  providerId: string;
}) {
  return (
    <section aria-labelledby="source-heading" className="detail-section" id="source">
      <SectionHeading eyebrow="Kontrollér selv" id="source-heading" title="Kilde" />
      <dl className="detail-facts">
        <FactRow label="Udbyder" value={provider?.name ?? providerId} />
        <FactRow label="Kanonisk tilbudskilde" value={canonicalOfferUrl} />
      </dl>
      <div className="detail-source-actions">
        <ProviderAction provider={provider} />
        <a
          aria-label="Åbn den kanoniske tilbudskilde"
          href={canonicalOfferUrl}
          rel="noreferrer noopener"
          target="_blank"
        >
          Åbn den kanoniske tilbudskilde
        </a>
      </div>
    </section>
  );
}

function ProviderAction({ provider }: { provider: Provider }) {
  if (provider === undefined) {
    return <p>Udbyderens websted er ikke tilgængeligt i dette datasæt.</p>;
  }

  return (
    <a
      aria-label={`Åbn ${provider.name}s websted`}
      href={provider.url}
      rel="noreferrer noopener"
      target="_blank"
    >
      Åbn {provider.name}s websted
    </a>
  );
}
