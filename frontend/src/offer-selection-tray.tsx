import { GitCompareArrows, X } from "lucide-react";

import {
  type CatalogueDatasetIndex,
  deriveOfferFacts,
  findOfferByIdentity,
} from "@/catalogue-dataset";

export function OfferSelectionTray({
  comparisonHref,
  index,
  onRemove,
  offerDetailHref,
  selectedOfferIdentities,
}: {
  comparisonHref: string;
  index: CatalogueDatasetIndex;
  onRemove: (identity: string) => void;
  offerDetailHref: (identity: string) => string;
  selectedOfferIdentities: readonly string[];
}) {
  const selectedOffers = selectedOfferIdentities
    .map((identity) => findOfferByIdentity(index, identity))
    .filter((offer) => offer !== undefined);

  if (selectedOffers.length < 2) return null;

  return (
    <aside
      aria-label="Valgte tilbud"
      className="offer-selection-tray"
      data-testid="offer-selection-tray"
    >
      <ol className="offer-selection-tray-items">
        {selectedOffers.map((offer) => {
          const vehicleName = deriveOfferFacts(index, offer).vehicleName;
          return (
            <li key={offer.offerIdentity}>
              <a href={offerDetailHref(offer.offerIdentity)}>{vehicleName}</a>
              <button
                aria-label={`Fjern ${vehicleName} fra valgte tilbud`}
                title={`Fjern ${vehicleName}`}
                type="button"
                onClick={() => onRemove(offer.offerIdentity)}
              >
                <X aria-hidden="true" />
              </button>
            </li>
          );
        })}
      </ol>
      <a
        aria-label="Sammenlign valgte tilbud"
        className="offer-selection-tray-compare"
        href={comparisonHref}
        title="Sammenlign valgte tilbud"
      >
        <GitCompareArrows aria-hidden="true" />
      </a>
    </aside>
  );
}
