import { z } from "zod";

import {
  type CatalogueDatasetIndex,
  type CatalogueOffer,
  deriveOfferFacts,
} from "@/catalogue-dataset";
import { isKnown } from "@/catalogue-ui";
import {
  type OfferSelectionCandidate,
  parseOfferSelectionSearch,
  reconcileOfferSelection,
  withOfferSelection,
} from "@/offer-selection-search";

export { MAX_SELECTED_OFFERS } from "@/offer-selection-search";

const leasingFormSchema = z.enum([
  "financial",
  "flex",
  "operational",
  "hybrid",
]);
const vehicleKindSchema = z.enum(["combustion", "battery_electric"]);
const sortSchema = z.enum(["source", "monthly", "total", "term", "mileage"]);
const viewSchema = z.enum(["offers", "quarantined"]);
const textSchema = z
  .string()
  .trim()
  .min(1)
  .max(120)
  .optional()
  .catch(undefined);

const catalogueSearchSchema = z.object({
  search: textSchema,
  provider: textSchema,
  leasingForm: leasingFormSchema.optional().catch(undefined),
  vehicleKind: vehicleKindSchema.optional().catch(undefined),
  sort: sortSchema.optional().catch(undefined),
  view: viewSchema.optional().catch(undefined),
});

export type LeasingForm = z.infer<typeof leasingFormSchema>;
export type VehicleKind = z.infer<typeof vehicleKindSchema>;
export type CatalogueSort = z.infer<typeof sortSchema>;
export type CatalogueView = z.infer<typeof viewSchema>;

export type CatalogueSearch = {
  offers?: OfferSelectionCandidate;
  search?: string;
  provider?: string;
  leasingForm?: LeasingForm;
  vehicleKind?: VehicleKind;
  sort?: CatalogueSort;
  view?: CatalogueView;
};

export function validateCatalogueSearch(
  search: Record<string, unknown>,
): CatalogueSearch {
  const parsed = catalogueSearchSchema.parse(search);
  const result: CatalogueSearch = {};
  const offers = parseOfferSelectionSearch(search);
  const query = normalizeText(parsed.search);
  const provider = normalizeText(parsed.provider);

  if (offers.length > 0) result.offers = offers;
  if (query !== undefined) result.search = query;
  if (provider !== undefined) result.provider = provider;
  if (parsed.leasingForm !== undefined) result.leasingForm = parsed.leasingForm;
  if (parsed.vehicleKind !== undefined) result.vehicleKind = parsed.vehicleKind;
  if (parsed.sort !== undefined) result.sort = parsed.sort;
  if (parsed.view !== undefined) result.view = parsed.view;
  return result;
}

export function canonicalizeCatalogueSearch(
  search: CatalogueSearch,
  index: CatalogueDatasetIndex,
): CatalogueSearch {
  const validated = validateCatalogueSearch(search);
  const provider =
    validated.provider !== undefined &&
    index.providersById.has(validated.provider)
      ? validated.provider
      : undefined;
  const offers = reconcileOfferSelection(validated.offers ?? [], index);

  if (validated.view === "quarantined") {
    return {
      ...(provider === undefined ? {} : { provider }),
      view: "quarantined",
      ...(offers.length === 0 ? {} : { offers }),
    };
  }

  const withoutInvalidProvider =
    provider === validated.provider ? validated : withoutProvider(validated);
  const canonical =
    provider === undefined
      ? withoutProvider(withoutInvalidProvider)
      : withoutInvalidProvider;

  return offers.length > 0
    ? { ...canonical, offers }
    : withoutOffers(canonical);
}

export function catalogueSearchEquals(
  left: CatalogueSearch,
  right: CatalogueSearch,
): boolean {
  return catalogueSearchQuery(left) === catalogueSearchQuery(right);
}

export function catalogueSearchQuery(search: CatalogueSearch): string {
  return stringifyCatalogueSearchQuery(search).replace(/^\?/, "");
}

export function parseCatalogueSearchQuery(
  searchString: string,
): Record<string, unknown> {
  const params = new URLSearchParams(searchString.replace(/^\?/, ""));
  const result: Record<string, unknown> = {};

  for (const [key, value] of params) {
    const current = result[key];
    if (current === undefined) {
      result[key] = value;
    } else if (Array.isArray(current)) {
      result[key] = [...current, value];
    } else {
      result[key] = [current, value];
    }
  }
  return result;
}

export function stringifyCatalogueSearchQuery(
  search: Record<string, unknown>,
): string {
  const params = new URLSearchParams();
  const orderedKeys = [
    "search",
    "provider",
    "view",
    "leasingForm",
    "vehicleKind",
    "sort",
    "offers",
    ...Object.keys(search).filter(
      (key) =>
        ![
          "search",
          "provider",
          "view",
          "leasingForm",
          "vehicleKind",
          "sort",
          "offers",
        ].includes(key),
    ),
  ];
  for (const key of orderedKeys) {
    const value = search[key];
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      for (const item of value) params.append(key, String(item));
    } else {
      params.append(key, String(value));
    }
  }
  const query = params.toString();
  return query === "" ? "" : `?${query}`;
}

export function catalogueSearchWithPatch(
  current: CatalogueSearch,
  patch: Partial<CatalogueSearch>,
): CatalogueSearch {
  return validateCatalogueSearch({ ...current, ...patch });
}

export function catalogueSearchWithOffers(
  current: CatalogueSearch,
  offers: readonly string[],
): CatalogueSearch {
  return validateCatalogueSearch(withOfferSelection(current, offers));
}

export function catalogueSearchWithoutFilters(
  current: CatalogueSearch,
): CatalogueSearch {
  return validateCatalogueSearch({ offers: current.offers });
}

export function matchesCatalogueSearch(
  offer: CatalogueOffer,
  index: CatalogueDatasetIndex,
  search: CatalogueSearch,
): boolean {
  const offerFacts = deriveOfferFacts(index, offer);
  const query = search.search?.toLocaleLowerCase("da") ?? "";
  const searchable =
    `${offerFacts.providerName} ${offerFacts.vehicleName}`.toLocaleLowerCase(
      "da",
    );

  return (
    (!query || searchable.includes(query)) &&
    (!search.provider || offer.providerId === search.provider) &&
    (!search.leasingForm ||
      offer.supportedLeasingForm === search.leasingForm) &&
    (!search.vehicleKind ||
      offer.vehicleSpecification.kind === search.vehicleKind)
  );
}

export function sortCatalogueOffers(
  offers: CatalogueOffer[],
  index: CatalogueDatasetIndex,
  sort: CatalogueSort | undefined,
): CatalogueOffer[] {
  if (sort === undefined || sort === "source") return offers;

  const sourceOrder = new Map(
    offers.map((offer, position) => [offer.offerIdentity, position]),
  );
  return [...offers].sort((left, right) => {
    const comparison = compareOptional(
      sortValue(left, index, sort),
      sortValue(right, index, sort),
    );
    return (
      comparison ||
      sourceOrder.get(left.offerIdentity)! -
        sourceOrder.get(right.offerIdentity)!
    );
  });
}

export function catalogueSortLabel(sort: CatalogueSort | undefined): string {
  if (sort === "monthly") return "Månedlig betaling · lavest først";
  if (sort === "total") return "Beregnet total · lavest først";
  if (sort === "term") return "Løbetid · kortest først";
  if (sort === "mileage") return "Kilometer · lavest først";
  return "Kilderækkefølge";
}

function sortValue(
  offer: CatalogueOffer,
  index: CatalogueDatasetIndex,
  sort: Exclude<CatalogueSort, "source">,
): number | undefined {
  const facts = deriveOfferFacts(index, offer);
  if (sort === "monthly") return facts.leasePaymentDkk;
  if (sort === "total") return facts.calculatedTotalDkk;
  if (sort === "term") return offer.termMonths;
  return isKnown(offer.annualMileageKm)
    ? offer.annualMileageKm.value
    : undefined;
}

function compareOptional(
  left: number | undefined,
  right: number | undefined,
): number {
  if (left === undefined && right === undefined) return 0;
  if (left === undefined) return 1;
  if (right === undefined) return -1;
  return left - right;
}

function normalizeText(value: string | undefined): string | undefined {
  const normalized = value?.trim();
  return normalized === "" ? undefined : normalized;
}

function withoutOffers(search: CatalogueSearch): CatalogueSearch {
  const { offers: _offers, ...withoutSelectedOffers } = search;
  return withoutSelectedOffers;
}

function withoutProvider(search: CatalogueSearch): CatalogueSearch {
  const { provider: _provider, ...withoutSelectedProvider } = search;
  return withoutSelectedProvider;
}
