import { queryOptions } from "@tanstack/react-query";
import { z } from "zod";

import type {
  CatalogueDataset as GeneratedCatalogueDataset,
  CatalogueOffer,
} from "@/generated/catalogue-dataset.generated";
import { catalogueDatasetJsonSchema } from "@/generated/catalogue-dataset.schema.generated";

const convertedCatalogueDatasetSchema = z.fromJSONSchema(
  catalogueDatasetJsonSchema as unknown as Parameters<typeof z.fromJSONSchema>[0],
);

// PROTOTYPE — the intended audited bridge. Both sides are generated from the
// same Pydantic serialization schema and regenerated together before builds.
const CatalogueDatasetSchema =
  convertedCatalogueDatasetSchema as z.ZodType<GeneratedCatalogueDataset>;

export type CatalogueDataset = z.infer<typeof CatalogueDatasetSchema>;
export type { CatalogueOffer };

export const catalogueDatasetQuery = queryOptions({
  queryKey: ["catalogue-dataset", "prototype-v1"],
  staleTime: Number.POSITIVE_INFINITY,
  queryFn: async (): Promise<CatalogueDataset> => {
    const response = await fetch("./catalogue-dataset.json");
    if (!response.ok) {
      throw new Error("Katalogdata kunne ikke indlæses.");
    }
    return CatalogueDatasetSchema.parse(await response.json());
  },
});

export type OfferFact =
  | { state: "known"; value: unknown }
  | {
      state: "not_stated" | "unclear" | "conflicting" | "not_applicable";
    };

export function knownValue<T>(fact: OfferFact): T | null {
  return fact.state === "known" ? (fact.value as T) : null;
}

export function vehicleName(offer: CatalogueOffer) {
  const trim = knownValue<string>(offer.vehicleSpecification.trim);
  return [
    offer.vehicleSpecification.make,
    offer.vehicleSpecification.model,
    trim,
  ]
    .filter(Boolean)
    .join(" ");
}

export function monthlyPayment(offer: CatalogueOffer) {
  const event = offer.baseCashFlowStream.find(
    (candidate) => candidate.kind === "lease_payment",
  );
  return event === undefined ? null : knownValue<number>(event.amount);
}

export function upfrontPayment(offer: CatalogueOffer) {
  const events = offer.baseCashFlowStream.filter(
    (event) => event.occursAtMonth === 0 && event.direction === "payment",
  );
  const values = events.map((event) => knownValue<number>(event.amount));
  if (values.some((value) => value === null)) return null;
  return values.reduce<number>((total, value) => total + (value ?? 0), 0);
}

export function endMechanism(offer: CatalogueOffer) {
  const value = knownValue<string>(offer.normalEndMechanism);
  const labels: Record<string, string> = {
    return_to_provider: "Aflever bilen ved aftalens udløb",
    designate_third_party_buyer: "Du skal anvise en tredjepartskøber",
    mandatory_purchase_or_payoff: "Du skal købe bilen eller indfri restbeløbet",
    other: "Aftalen har en anden afslutning",
  };
  return value === null ? "Afslutningen er ikke tydeligt oplyst" : labels[value];
}

export function riskAllocation(offer: CatalogueOffer) {
  const value = knownValue<string>(offer.residualRiskAllocation);
  const labels: Record<string, string> = {
    provider: "Udbyderen bærer restværdirisikoen",
    lessee: "Du bærer restværdirisikoen",
    shared: "Restværdirisikoen er delt",
  };
  return value === null ? "Restværdirisikoen er uklar" : labels[value];
}
