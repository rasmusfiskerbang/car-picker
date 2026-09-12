import { useState } from "react";

import {
  type CatalogueOffer,
  type CatalogueDatasetIndex,
  deriveOfferFacts,
  findOfferByIdentity,
} from "@/catalogue-dataset";
import { MAX_SELECTED_OFFERS } from "@/offer-selection-search";

export function OfferSelectionTray({
  comparisonHref,
  availableOffers,
  index,
  onAdd,
  onClear,
  onRemove,
  offerDetailHref,
  selectedOfferIdentities,
}: {
  availableOffers: readonly CatalogueOffer[];
  comparisonHref: string;
  index: CatalogueDatasetIndex;
  onAdd: (identity: string) => void;
  onClear: () => void;
  onRemove: (identity: string) => void;
  offerDetailHref: (identity: string) => string;
  selectedOfferIdentities: readonly string[];
}) {
  const [pendingOfferIdentity, setPendingOfferIdentity] = useState("");
  const selectedOffers = selectedOfferIdentities
    .map((identity) => findOfferByIdentity(index, identity))
    .filter((offer) => offer !== undefined);

  if (selectedOffers.length === 0) return null;

  const offersAvailableForAddition = availableOffers.filter(
    (offer) => !selectedOfferIdentities.includes(offer.offerIdentity),
  );
  const canAddOffer =
    selectedOfferIdentities.length < MAX_SELECTED_OFFERS &&
    offersAvailableForAddition.length > 0;

  return (
    <aside
      aria-label="Valgte tilbud"
      className="offer-selection-tray"
      data-testid="offer-selection-tray"
    >
      <div className="offer-selection-tray-summary">
        <p className="offer-selection-tray-count">
          {selectedOffers.length} tilbud valgt
        </p>
        <p className="offer-selection-tray-note">Valget følger med i URL’en.</p>
      </div>
      <ol className="offer-selection-tray-items">
        {selectedOffers.map((offer) => {
          const vehicleName = deriveOfferFacts(index, offer).vehicleName;
          return (
            <li key={offer.offerIdentity}>
              <a href={offerDetailHref(offer.offerIdentity)}>{vehicleName}</a>
              <button
                aria-label={`Fjern ${vehicleName} fra valgte tilbud`}
                type="button"
                onClick={() => onRemove(offer.offerIdentity)}
              >
                Fjern
              </button>
            </li>
          );
        })}
      </ol>
      {canAddOffer && (
        <div className="offer-selection-tray-add">
          <label htmlFor="offer-selection-add">Tilføj tilbud</label>
          <select
            id="offer-selection-add"
            aria-label="Tilføj tilbud"
            value={pendingOfferIdentity}
            onChange={(event) => setPendingOfferIdentity(event.target.value)}
          >
            <option value="">
              Vælg tilbud
            </option>
            {offersAvailableForAddition.map((offer) => (
              <option key={offer.offerIdentity} value={offer.offerIdentity}>
                {deriveOfferFacts(index, offer).vehicleName}
              </option>
            ))}
          </select>
          <button
            disabled={pendingOfferIdentity === ""}
            type="button"
            onClick={() => {
              onAdd(pendingOfferIdentity);
              setPendingOfferIdentity("");
            }}
          >
            Tilføj tilbud
          </button>
        </div>
      )}
      <div className="offer-selection-tray-actions">
        <a className="offer-selection-tray-compare" href={comparisonHref}>
          Sammenlign valgte tilbud
        </a>
        <button
          aria-label="Ryd valgte tilbud"
          className="offer-selection-tray-clear"
          type="button"
          onClick={onClear}
        >
          Ryd valgte tilbud
        </button>
      </div>
    </aside>
  );
}
