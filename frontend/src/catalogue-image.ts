import type {
  CatalogueDatasetIndex,
  CatalogueOffer,
} from "@/catalogue-dataset";

/**
 * Provider-controlled media origins audited against the designated source
 * pages. Bilinfo hosts Fleasing's vehicle photography embedded on offer pages.
 */
export const auditedProviderImageOrigins: Readonly<
  Record<string, readonly string[]>
> = {
  terminalen: ["https://assets.terminalen.dk"],
  fleasing: ["https://fleasing.dk", "https://billeder.bilinfo.net"],
};

export function allowlistedOfferImageUrls(
  index: CatalogueDatasetIndex,
  offer: CatalogueOffer,
): string[] {
  const allowedOrigins = new Set(
    [
      offer.canonicalOfferUrl,
      index.providersById.get(offer.providerId)?.url,
      ...(auditedProviderImageOrigins[offer.providerId] ?? []),
    ]
      .map(originForHttpsUrl)
      .filter((origin): origin is string => origin !== undefined),
  );

  return offer.imageUrls.filter((imageUrl) => {
    const image = parseHttpsUrl(imageUrl);
    return image !== undefined && allowedOrigins.has(image.origin);
  });
}

function originForHttpsUrl(value: string | undefined): string | undefined {
  return value === undefined ? undefined : parseHttpsUrl(value)?.origin;
}

function parseHttpsUrl(value: string): URL | undefined {
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username !== "" || url.password !== "") {
      return undefined;
    }
    return url;
  } catch {
    return undefined;
  }
}
