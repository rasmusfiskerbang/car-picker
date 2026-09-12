import { z } from "zod";

import type { CatalogueDatasetIndex } from "@/catalogue-dataset";

export const MAX_SELECTED_OFFERS = 5;

const offerSelectionSearchSchema = z.object({
  offers: z
    .union([z.string().trim(), z.array(z.string().trim())])
    .optional()
    .catch(undefined),
});

declare const offerSelectionBrand: unique symbol;

export type RawOfferSelection = readonly string[];

export type OfferSelectionCandidate = readonly string[];

export type OfferSelection = OfferSelectionCandidate & {
  readonly [offerSelectionBrand]: true;
};

export type OfferSelectionSearch = {
  offers?: OfferSelection;
};

export function parseOfferSelectionSearch(
  search: Record<string, unknown>,
): OfferSelectionCandidate {
  const parsed = offerSelectionSearchSchema.safeParse(search);
  if (!parsed.success || parsed.data.offers === undefined) return [];

  const offers = Array.isArray(parsed.data.offers)
    ? parsed.data.offers
    : [parsed.data.offers];
  return uniqueNonEmpty(offers);
}

export function parseOfferSelectionQuery(
  searchString: string,
): RawOfferSelection {
  const params = new URLSearchParams(searchString.replace(/^\?/, ""));
  return params.getAll("offers");
}

export function validateOfferSelectionSearch(
  search: Record<string, unknown>,
): OfferSelectionSearch {
  const offers = canonicalizeOfferSelection(parseOfferSelectionSearch(search));
  return offers.length === 0 ? {} : { offers };
}

export function offerSelectionSearch(
  offers: readonly string[],
): OfferSelectionSearch {
  const canonicalOffers = canonicalizeOfferSelection(offers);
  return canonicalOffers.length === 0 ? {} : { offers: canonicalOffers };
}

export function canonicalizeOfferSelection(
  offers: OfferSelectionCandidate,
): OfferSelection {
  return asOfferSelection(uniqueNonEmpty(offers).slice(0, MAX_SELECTED_OFFERS));
}

export function reconcileOfferSelection(
  offers: OfferSelectionCandidate,
  index: CatalogueDatasetIndex,
): OfferSelection {
  return asOfferSelection(
    uniqueNonEmpty(offers)
      .filter((identity) => index.offersByIdentity.has(identity))
      .slice(0, MAX_SELECTED_OFFERS),
  );
}

export function addOffer(
  offers: OfferSelectionCandidate,
  identity: string,
): OfferSelection {
  const current = canonicalizeOfferSelection(offers);
  const normalizedIdentity = identity.trim();
  if (
    normalizedIdentity === "" ||
    current.includes(normalizedIdentity) ||
    current.length >= MAX_SELECTED_OFFERS
  ) {
    return current;
  }
  return asOfferSelection([...current, normalizedIdentity]);
}

export function toggleOffer(
  offers: OfferSelectionCandidate,
  identity: string,
): OfferSelection {
  const current = canonicalizeOfferSelection(offers);
  const normalizedIdentity = identity.trim();
  return setOfferSelected(
    current,
    normalizedIdentity,
    !current.includes(normalizedIdentity),
  );
}

export function setOfferSelected(
  offers: OfferSelectionCandidate,
  identity: string,
  selected: boolean,
): OfferSelection {
  if (selected) return addOffer(offers, identity);
  return removeOffer(offers, identity);
}

export function removeOffer(
  offers: OfferSelectionCandidate,
  identity: string,
): OfferSelection {
  const normalizedIdentity = identity.trim();
  return asOfferSelection(
    canonicalizeOfferSelection(offers).filter(
      (currentIdentity) => currentIdentity !== normalizedIdentity,
    ),
  );
}

export function clearOfferSelection(): OfferSelection {
  return asOfferSelection([]);
}

export function withOfferSelection<T extends Record<string, unknown>>(
  search: T,
  offers: OfferSelectionCandidate,
): Omit<T, "offers"> & OfferSelectionSearch {
  const { offers: _offers, ...withoutSelection } = search;
  return { ...withoutSelection, ...offerSelectionSearch(offers) };
}

function asOfferSelection(offers: string[]): OfferSelection {
  return offers as unknown as OfferSelection;
}

function uniqueNonEmpty(offers: readonly string[]): string[] {
  return [
    ...new Set(
      offers
        .map((offer) => offer.trim())
        .filter((offer) => offer.length > 0),
    ),
  ];
}
