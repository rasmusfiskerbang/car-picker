import {
  catalogueDatasetSchemaVersion,
  catalogueDatasetValidator,
} from "./catalogue-dataset-schema";
import type {
  BaseCashFlowEvent,
  CatalogueDataset,
  CatalogueOffer,
  Criterion,
  InactiveProvider,
  ActiveProvider,
  QuarantinedCandidate,
  State17,
} from "./generated/catalogue-dataset";

export type {
  ActiveProvider,
  CatalogueDataset,
  CatalogueOffer,
  InactiveProvider,
  QuarantinedCandidate,
} from "./generated/catalogue-dataset";

export type CatalogueQuarantineCriterion = Criterion;
export type CatalogueQuarantineFactState = State17;

export type CatalogueDatasetLoadFailureKind =
  "unavailable" | "invalid" | "incompatible";

export class CatalogueDatasetError extends Error {
  readonly kind: CatalogueDatasetLoadFailureKind;

  constructor(
    kind: CatalogueDatasetLoadFailureKind,
    message: string,
    options?: ErrorOptions,
  ) {
    super(message, options);
    this.name = "CatalogueDatasetError";
    this.kind = kind;
  }
}

export function parseCatalogueDataset(value: unknown): CatalogueDataset {
  if (isRecord(value) && "schemaVersion" in value) {
    if (value.schemaVersion !== catalogueDatasetSchemaVersion) {
      throw new CatalogueDatasetError(
        "incompatible",
        "The Catalogue Dataset uses an unsupported schema version.",
      );
    }
  }

  try {
    return catalogueDatasetValidator.parse(value);
  } catch (error) {
    throw new CatalogueDatasetError(
      "invalid",
      "The Catalogue Dataset failed its generated contract validation.",
      { cause: error },
    );
  }
}

export async function loadCatalogueDataset(
  fetcher: typeof fetch = globalThis.fetch,
): Promise<CatalogueDataset> {
  let response: Response;
  try {
    response = await fetcher("./catalogue-dataset.json", {
      cache: "no-store",
    });
  } catch (error) {
    throw new CatalogueDatasetError(
      "unavailable",
      "The Catalogue Dataset could not be fetched.",
      { cause: error },
    );
  }

  if (!response.ok) {
    throw new CatalogueDatasetError(
      "unavailable",
      "The Catalogue Dataset could not be fetched.",
    );
  }

  let value: unknown;
  try {
    value = await response.json();
  } catch (error) {
    throw new CatalogueDatasetError(
      "invalid",
      "The Catalogue Dataset is not valid JSON.",
      { cause: error },
    );
  }
  return parseCatalogueDataset(value);
}

export interface CatalogueDatasetIndex {
  readonly providersById: ReadonlyMap<
    string,
    ActiveProvider | InactiveProvider
  >;
  readonly offersByIdentity: ReadonlyMap<string, CatalogueOffer>;
}

export type FactUnavailableState = Exclude<
  CatalogueOffer["annualMileageKm"]["state"],
  "known"
>;

export type DerivedAmount =
  | { state: "available"; amountDkk: number }
  | { state: "unavailable"; factState: FactUnavailableState };

export type UpfrontCashResult =
  | { state: "available"; amountDkk: number }
  | {
      state: "unavailable";
      reasons: readonly ("no_payment_documented" | FactUnavailableState)[];
    };

export function indexCatalogueDataset(
  dataset: CatalogueDataset,
): CatalogueDatasetIndex {
  return {
    providersById: new Map(
      dataset.providers.map((provider) => [provider.id, provider]),
    ),
    offersByIdentity: new Map(
      dataset.offers.map((offer) => [offer.offerIdentity, offer]),
    ),
  };
}

export function findOfferByIdentity(
  index: CatalogueDatasetIndex,
  identity: string,
): CatalogueOffer | undefined {
  return index.offersByIdentity.get(identity);
}

export function findProviderById(
  index: CatalogueDatasetIndex,
  providerId: string,
): ActiveProvider | InactiveProvider | undefined {
  return index.providersById.get(providerId);
}

export interface CatalogueOfferFacts {
  providerName: string;
  vehicleName: string;
  upfrontCash: UpfrontCashResult;
  upfrontCashDkk: number | undefined;
  leasePayment: DerivedAmount;
  leasePaymentDkk: number | undefined;
  calculatedTotalDkk: number | undefined;
  calculatedMonthlyTotalDkk: number | undefined;
}

export function deriveOfferFacts(
  index: CatalogueDatasetIndex,
  offer: CatalogueOffer,
): CatalogueOfferFacts {
  const vehicle = offer.vehicleSpecification;
  const trim = isKnown(vehicle.trim) ? vehicle.trim.value : undefined;
  const leasePayment = deriveLeasePayment(offer.baseCashFlowStream);
  const upfrontCash = deriveUpfrontCash(offer.baseCashFlowStream);
  return {
    providerName:
      index.providersById.get(offer.providerId)?.name ?? offer.providerId,
    vehicleName: trim
      ? `${vehicle.make} ${vehicle.model} ${trim}`
      : `${vehicle.make} ${vehicle.model}`,
    upfrontCash,
    upfrontCashDkk:
      upfrontCash.state === "available" ? upfrontCash.amountDkk : undefined,
    leasePayment,
    leasePaymentDkk:
      leasePayment.state === "available" ? leasePayment.amountDkk : undefined,
    calculatedTotalDkk: availableAmount(offer.calculatedTotal),
    calculatedMonthlyTotalDkk: availableAmount(offer.calculatedMonthlyTotal),
  };
}

function deriveLeasePayment(events: BaseCashFlowEvent[]): DerivedAmount {
  const leasePayment = events.find((event) => event.kind === "lease_payment");
  if (leasePayment === undefined) {
    return { state: "unavailable", factState: "not_stated" };
  }
  return deriveAmount(leasePayment.amount);
}

function deriveUpfrontCash(events: BaseCashFlowEvent[]): UpfrontCashResult {
  const startingPayments = events.filter(
    (event) => event.month === 0 && event.direction === "payment",
  );
  if (startingPayments.length === 0) {
    return { state: "unavailable", reasons: ["no_payment_documented"] };
  }

  const unavailableStates = [
    ...new Set(
      startingPayments.flatMap((event) =>
        event.amount.state === "known" ? [] : [event.amount.state],
      ),
    ),
  ];
  if (unavailableStates.length > 0) {
    return { state: "unavailable", reasons: unavailableStates };
  }

  return {
    state: "available",
    amountDkk: startingPayments.reduce(
      (total, event) =>
        total + (event.amount.state === "known" ? event.amount.value : 0),
      0,
    ),
  };
}

function deriveAmount(fact: BaseCashFlowEvent["amount"]): DerivedAmount {
  return fact.state === "known"
    ? { state: "available", amountDkk: fact.value }
    : { state: "unavailable", factState: fact.state };
}

export interface CatalogueFacts {
  generatedAt: string;
  providerCount: number;
  activeProviderCount: number;
  inactiveProviderCount: number;
  offerCount: number;
  quarantinedCandidateCount: number;
}

export interface ProviderFacts {
  provider: ActiveProvider | InactiveProvider;
  offerCount: number;
  quarantinedCandidateCount: number;
}

export function deriveCatalogueFacts(
  dataset: CatalogueDataset,
): CatalogueFacts {
  const activeProviderCount = dataset.providers.filter(
    (provider) => provider.status === "active",
  ).length;
  return {
    generatedAt: dataset.generatedAt,
    providerCount: dataset.providers.length,
    activeProviderCount,
    inactiveProviderCount: dataset.providers.length - activeProviderCount,
    offerCount: dataset.offers.length,
    quarantinedCandidateCount: dataset.quarantinedCandidates.length,
  };
}

export function deriveProviderFacts(
  dataset: CatalogueDataset,
): ProviderFacts[] {
  const offerCounts = countByProvider(dataset.offers);
  const quarantinedCandidateCounts = countByProvider(
    dataset.quarantinedCandidates,
  );

  return dataset.providers.map((provider) => ({
    provider,
    offerCount: offerCounts.get(provider.id) ?? 0,
    quarantinedCandidateCount: quarantinedCandidateCounts.get(provider.id) ?? 0,
  }));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isKnown<T extends { state: string }>(
  fact: T,
): fact is Extract<T, { state: "known" }> {
  return fact.state === "known";
}

function availableAmount(
  result: CatalogueOffer["calculatedTotal"],
): number | undefined {
  return result.state === "available" ? result.value.amountDkk : undefined;
}

function countByProvider(
  records: readonly { providerId: string }[],
): Map<string, number> {
  const counts = new Map<string, number>();
  for (const record of records) {
    counts.set(record.providerId, (counts.get(record.providerId) ?? 0) + 1);
  }
  return counts;
}
