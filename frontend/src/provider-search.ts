import { z } from "zod";

import type { CatalogueDatasetIndex } from "@/catalogue-dataset";
import {
  type OfferSelectionCandidate,
  parseOfferSelectionSearch,
  reconcileOfferSelection,
} from "@/offer-selection-search";
import { stringifyCatalogueSearchQuery } from "@/catalogue-search";

const providerSearchSchema = z.object({
  provider: z.string().trim().min(1).max(120).optional().catch(undefined),
});

export type ProviderSearch = {
  provider?: string;
  offers?: OfferSelectionCandidate;
};

export function validateProviderSearch(
  search: Record<string, unknown>,
): ProviderSearch {
  const parsed = providerSearchSchema.parse(search);
  const offers = parseOfferSelectionSearch(search);
  const result: ProviderSearch = {};
  if (parsed.provider !== undefined) result.provider = parsed.provider;
  if (offers.length > 0) result.offers = offers;
  return result;
}

export function canonicalizeProviderSearch(
  search: ProviderSearch,
  index: CatalogueDatasetIndex,
): ProviderSearch {
  const validated = validateProviderSearch(search);
  const provider =
    validated.provider !== undefined && index.providersById.has(validated.provider)
      ? validated.provider
      : undefined;
  const offers = reconcileOfferSelection(validated.offers ?? [], index);
  return {
    ...(provider === undefined ? {} : { provider }),
    ...(offers.length === 0 ? {} : { offers }),
  };
}

export function providerSearchEquals(
  left: ProviderSearch,
  right: ProviderSearch,
): boolean {
  return providerSearchQuery(left) === providerSearchQuery(right);
}

export function providerSearchQuery(search: ProviderSearch): string {
  return stringifyCatalogueSearchQuery(search).replace(/^\?/, "");
}
