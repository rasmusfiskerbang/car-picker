import {
  Link,
  Outlet,
  RouterProvider,
  createHashHistory,
  createRootRoute,
  createRoute,
  createRouter,
  redirect,
} from "@tanstack/react-router";
import { useEffect } from "react";

import { ApplicationShell } from "@/application-shell";
import { routePaths } from "@/generated/route-output";
import {
  type CatalogueDataset,
  findOfferByIdentity,
  indexCatalogueDataset,
} from "@/catalogue-dataset";
import { catalogueQueryClient } from "@/catalogue-query";
import {
  CatalogueDatasetProvider,
  catalogueDatasetQueryOptions,
  useCatalogueDataset,
} from "@/catalogue-loader";
import { CatalogueOverview } from "@/catalogue-page";
import { CatalogueQuarantineOverview } from "@/catalogue-quarantine";
import {
  canonicalizeCatalogueSearch,
  catalogueSearchEquals,
  catalogueSearchWithOffers,
  catalogueSearchWithPatch,
  catalogueSearchWithoutFilters,
  parseCatalogueSearchQuery,
  stringifyCatalogueSearchQuery,
  type CatalogueView,
  type CatalogueSearch,
  validateCatalogueSearch,
} from "@/catalogue-search";
import { ComparisonPage } from "@/comparison-page";
import { LandingPage } from "@/landing-page";
import { OfferDetailPage } from "@/offer-detail-page";
import { ProviderOverview } from "@/provider-overview";
import {
  canonicalizeProviderSearch,
  providerSearchEquals,
  validateProviderSearch,
} from "@/provider-search";
import {
  offerSelectionSearch,
  parseOfferSelectionQuery,
  reconcileOfferSelection,
  setOfferSelected,
  validateOfferSelectionSearch,
  withOfferSelection,
} from "@/offer-selection-search";

const rootRoute = createRootRoute({
  beforeLoad: canonicalizeSelectionBeforeLoad,
  component: RootRoute,
  loader: async () => {
    let dataset: CatalogueDataset;
    try {
      dataset = await catalogueQueryClient.ensureQueryData(
        catalogueDatasetQueryOptions,
      );
    } catch {
      return { dataset: undefined, index: undefined };
    }

    const index = indexCatalogueDataset(dataset);
    return { dataset, index };
  },
  pendingComponent: CataloguePending,
});
const landingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: routePaths.landing,
  validateSearch: validateOfferSelectionSearch,
  component: LandingRoute,
});
const catalogueRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: routePaths.catalogue,
  validateSearch: validateCatalogueSearch,
  component: CatalogueRoute,
});
const detailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: routePaths.offer,
  validateSearch: validateOfferSelectionSearch,
  component: OfferDetailRoute,
});
const comparisonRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: routePaths.comparison,
  validateSearch: validateOfferSelectionSearch,
  component: ComparisonRoute,
});
const providersRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: routePaths.providers,
  beforeLoad: canonicalizeProviderSearchBeforeLoad,
  validateSearch: validateProviderSearch,
  component: ProvidersRoute,
});
const routeTree = rootRoute.addChildren([
  landingRoute,
  catalogueRoute,
  detailRoute,
  comparisonRoute,
  providersRoute,
]);

export const router = createRouter({
  history: createHashHistory(),
  parseSearch: parseCatalogueSearchQuery,
  routeTree,
  stringifySearch: stringifyCatalogueSearchQuery,
});

type SelectionLocation = {
  pathname: string;
  search: Record<string, unknown>;
  searchStr: string;
};

async function canonicalizeSelectionBeforeLoad({
  location,
}: {
  location: SelectionLocation;
}) {
  let dataset: CatalogueDataset;
  try {
    dataset = await catalogueQueryClient.ensureQueryData(
      catalogueDatasetQueryOptions,
    );
  } catch {
    return;
  }

  redirectIfSelectionNeedsCanonicalization(
    location,
    indexCatalogueDataset(dataset),
  );
}

function redirectIfSelectionNeedsCanonicalization(
  location: SelectionLocation,
  index: ReturnType<typeof indexCatalogueDataset>,
) {
  const currentOffers = parseOfferSelectionQuery(location.searchStr);
  const offers = reconcileOfferSelection(currentOffers, index);
  if (sameOfferSelection(currentOffers, offers)) return;

  throw redirect({
    to: location.pathname,
    search: withOfferSelection(location.search, offers),
    replace: true,
    throw: true,
  });
}

async function canonicalizeProviderSearchBeforeLoad({
  location,
}: {
  location: SelectionLocation;
}) {
  let dataset: CatalogueDataset;
  try {
    dataset = await catalogueQueryClient.ensureQueryData(
      catalogueDatasetQueryOptions,
    );
  } catch {
    return;
  }

  const providerSearch = validateProviderSearch(location.search);
  const canonicalSearch = canonicalizeProviderSearch(
    providerSearch,
    indexCatalogueDataset(dataset),
  );
  if (providerSearchEquals(providerSearch, canonicalSearch)) return;

  throw redirect({
    to: routePaths.providers,
    search: canonicalSearch,
    replace: true,
    throw: true,
  });
}

function sameOfferSelection(
  left: readonly string[],
  right: readonly string[],
): boolean {
  return (
    left.length === right.length &&
    left.every((offer, index) => offer === right[index])
  );
}

function RootRoute() {
  const { dataset, index } = rootRoute.useLoaderData();
  if (dataset === undefined || index === undefined) {
    return (
      <main className="unavailable-catalogue" role="alert">
        <h1>Kataloget kan ikke vises</h1>
        <p>
          Der er ikke et gyldigt katalogdatasæt tilgængeligt lige nu. Ingen
          katalogtilbud vises.
        </p>
      </main>
    );
  }

  return (
    <CatalogueDatasetProvider dataset={dataset} index={index}>
      <ApplicationShell dataset={dataset}>
        <Outlet />
      </ApplicationShell>
    </CatalogueDatasetProvider>
  );
}

function CataloguePending() {
  return <main className="unavailable-catalogue">Kataloget indlæses…</main>;
}

function LandingRoute() {
  const { dataset } = useCatalogueDataset();
  const { offers = [] } = landingRoute.useSearch();
  return <LandingPage dataset={dataset} selectedOfferIdentities={offers} />;
}

function CatalogueRoute() {
  const { dataset, index } = useCatalogueDataset();
  const catalogueSearch = catalogueRoute.useSearch();
  const navigate = catalogueRoute.useNavigate();
  const canonicalSearch = canonicalizeCatalogueSearch(catalogueSearch, index);
  const needsCanonicalization = !catalogueSearchEquals(
    catalogueSearch,
    canonicalSearch,
  );

  useEffect(() => {
    if (!needsCanonicalization) return;
    void navigate({ search: canonicalSearch, replace: true });
  }, [canonicalSearch, navigate, needsCanonicalization]);

  const catalogueViewHref = (view: CatalogueView) =>
    router.history.createHref(
      router.buildLocation({
        to: routePaths.catalogue,
        search: catalogueSearchForView(
          canonicalSearch.provider,
          view,
          canonicalSearch.offers ?? [],
        ),
      }).href,
    );

  if (canonicalSearch.view === "quarantined") {
    return (
      <CatalogueQuarantineOverview
        dataset={dataset}
        index={index}
        offersHref={catalogueViewHref("offers")}
        providerId={canonicalSearch.provider}
      />
    );
  }

  const updateSearch = (
    update: (current: CatalogueSearch) => CatalogueSearch,
  ) => {
    void navigate({
      search: (current) => canonicalizeCatalogueSearch(update(current), index),
    });
  };
  const selectedOfferIdentities = canonicalSearch.offers ?? [];

  return (
    <CatalogueOverview
      dataset={dataset}
      index={index}
      search={canonicalSearch}
      selectedOfferIdentities={selectedOfferIdentities}
      offerDetailHref={(identity) =>
        router.history.createHref(
          router.buildLocation({
            to: routePaths.offer,
            params: { identity },
            search: offerSelectionSearch(selectedOfferIdentities),
          }).href,
        )
      }
      onSearchChange={(value) =>
        updateSearch((current) =>
          catalogueSearchWithPatch(current, { search: value }),
        )
      }
      onProviderChange={(value) =>
        updateSearch((current) =>
          catalogueSearchWithPatch(current, { provider: value }),
        )
      }
      onLeasingFormChange={(value) =>
        updateSearch((current) =>
          catalogueSearchWithPatch(current, { leasingForm: value }),
        )
      }
      onVehicleKindChange={(value) =>
        updateSearch((current) =>
          catalogueSearchWithPatch(current, { vehicleKind: value }),
        )
      }
      onSortChange={(value) =>
        updateSearch((current) =>
          catalogueSearchWithPatch(current, { sort: value }),
        )
      }
      onResetFilters={() =>
        updateSearch((current) => catalogueSearchWithoutFilters(current))
      }
      onSelectionChange={(identity, selected) =>
        updateSearch((current) => {
          const nextOffers = setOfferSelected(
            current.offers ?? [],
            identity,
            selected,
          );
          return catalogueSearchWithOffers(current, nextOffers);
        })
      }
    />
  );
}

function OfferDetailRoute() {
  const { identity } = detailRoute.useParams();
  const search = detailRoute.useSearch();
  const navigate = detailRoute.useNavigate();
  const { dataset, index } = useCatalogueDataset();
  const decodedIdentity = decodeOfferIdentity(identity);
  const offer =
    decodedIdentity === undefined
      ? undefined
      : findOfferByIdentity(index, decodedIdentity);
  const selectedOfferIdentities = reconcileOfferSelection(
    search.offers ?? [],
    index,
  );

  return offer ? (
    <OfferDetailPage
      dataset={dataset}
      index={index}
      offer={offer}
      selectedOfferIdentities={selectedOfferIdentities}
      onSelectionChange={(selected) => {
        if (decodedIdentity === undefined) return;
        const next = setOfferSelected(
          selectedOfferIdentities,
          decodedIdentity,
          selected,
        );
        void navigate({ search: offerSelectionSearch(next) });
      }}
    />
  ) : (
    <main className="message route-message">
      <h1>Tilbuddet findes ikke i dette katalog</h1>
      <p>
        Den angivne Offer Identity findes ikke blandt de validerede Catalogue
        Offers i det aktive katalog.
      </p>
      <Link
        search={offerSelectionSearch(selectedOfferIdentities)}
        to={routePaths.catalogue}
      >
        Tilbage til kataloget
      </Link>
    </main>
  );
}

function decodeOfferIdentity(identity: string): string | undefined {
  try {
    return decodeURIComponent(identity);
  } catch {
    return undefined;
  }
}

function ComparisonRoute() {
  const { index } = useCatalogueDataset();
  const { offers = [] } = comparisonRoute.useSearch();
  const selectedOfferIdentities = reconcileOfferSelection(offers, index);
  const selectedOffers = selectedOfferIdentities
    .map((identity) => findOfferByIdentity(index, identity))
    .filter((offer) => offer !== undefined);

  if (selectedOffers.length === 0) {
    return (
      <main className="message route-message">
        <h1>Sammenlign tilbud</h1>
        <p>Vælg mindst ét tilbud fra kataloget for at se dets aftalefakta.</p>
      </main>
    );
  }

  return <ComparisonPage index={index} offers={selectedOffers} />;
}

function ProvidersRoute() {
  const { dataset } = useCatalogueDataset();
  const providerSearch = providersRoute.useSearch();
  const selectedOfferIdentities = providerSearch.offers ?? [];
  return (
    <ProviderOverview
      catalogueHref={(providerId, view) =>
        router.history.createHref(
          router.buildLocation({
            to: routePaths.catalogue,
            search: catalogueSearchForView(
              providerId,
              view,
              selectedOfferIdentities,
            ),
          }).href,
        )
      }
      dataset={dataset}
      providerSelectionHref={(providerId) =>
        router.history.createHref(
          router.buildLocation({
            to: routePaths.providers,
            search: {
              provider: providerId,
              ...offerSelectionSearch(selectedOfferIdentities),
            },
          }).href,
        )
      }
      selectedProviderId={providerSearch.provider}
    />
  );
}

function catalogueSearchForView(
  providerId: string | undefined,
  view: CatalogueView,
  offers: readonly string[],
): CatalogueSearch {
  const search: CatalogueSearch = {};
  if (providerId !== undefined) search.provider = providerId;
  if (view === "quarantined") search.view = view;
  if (offers.length > 0) {
    return {
      ...search,
      ...offerSelectionSearch(offers),
    };
  }
  return search;
}

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export function AppRouter() {
  return <RouterProvider router={router} />;
}
