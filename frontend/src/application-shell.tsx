import { Link, useRouter, useRouterState } from "@tanstack/react-router";
import { CalendarDays, CarFront, ShieldCheck } from "lucide-react";
import { type ReactNode } from "react";

import {
  type CatalogueDataset,
  deriveCatalogueFacts,
  indexCatalogueDataset,
} from "@/catalogue-dataset";
import { cn } from "@/lib/utils";
import {
  addOffer,
  clearOfferSelection,
  offerSelectionSearch,
  reconcileOfferSelection,
  removeOffer,
  withOfferSelection,
} from "@/offer-selection-search";
import { OfferSelectionTray } from "@/offer-selection-tray";

const date = new Intl.DateTimeFormat("da-DK", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

type ApplicationShellProps = {
  children: ReactNode;
  dataset: CatalogueDataset;
};

type Destination =
  | "landing"
  | "catalogue"
  | "comparison"
  | "providers"
  | "offer"
  | "unknown";

function destinationForPath(pathname: string): Destination {
  if (pathname === "/") return "landing";
  if (pathname === "/catalogue") return "catalogue";
  if (pathname === "/compare") return "comparison";
  if (pathname === "/providers") return "providers";
  if (pathname.startsWith("/offers/")) return "offer";
  return "unknown";
}

function pageTitle(destination: Destination): string {
  if (destination === "catalogue") return "Tilbud";
  if (destination === "comparison") return "Sammenligning";
  if (destination === "providers") return "Udbydere";
  if (destination === "offer") return "Tilbuddet";
  if (destination === "unknown") return "Siden findes ikke";
  return "Forside";
}

function Brand({
  selectedOfferIdentities,
}: {
  selectedOfferIdentities: readonly string[];
}) {
  return (
    <Link
      aria-label="Bilvalg — gå til forsiden"
      className="shell-brand"
      search={offerSelectionSearch(selectedOfferIdentities)}
      to="/"
    >
      <span aria-hidden="true" className="shell-brand-mark">
        <CarFront />
      </span>
      <span>
        <span className="shell-brand-name">Bilvalg</span>
        <span className="shell-brand-caption">Privatleasing</span>
      </span>
    </Link>
  );
}

function Navigation({
  destination,
  selectedOfferIdentities,
  mobile = false,
}: {
  destination: Destination;
  selectedOfferIdentities: readonly string[];
  mobile?: boolean;
}) {
  return (
    <nav
      aria-label="Primær navigation"
      className={cn(
        mobile ? "shell-mobile-navigation" : "shell-desktop-navigation",
      )}
    >
      <Link
        aria-current={destination === "catalogue" ? "page" : undefined}
        className="shell-nav-link"
        search={offerSelectionSearch(selectedOfferIdentities)}
        to="/catalogue"
      >
        Tilbud
      </Link>
      <Link
        aria-current={destination === "comparison" ? "page" : undefined}
        className="shell-nav-link"
        search={offerSelectionSearch(selectedOfferIdentities)}
        to="/compare"
      >
        Sammenlign
      </Link>
      <Link
        aria-current={destination === "providers" ? "page" : undefined}
        className="shell-nav-link"
        search={offerSelectionSearch(selectedOfferIdentities)}
        to="/providers"
      >
        Udbydere
      </Link>
    </nav>
  );
}

function ContextBand({ dataset }: { dataset: CatalogueDataset }) {
  const providerCount = deriveCatalogueFacts(dataset).activeProviderCount;
  const providerLabel =
    providerCount === 1 ? "aktiv udbyder" : "aktive udbydere";

  return (
    <div
      aria-label={
        "Afgrænset katalog med " + providerCount + " " + providerLabel
      }
      className="shell-context-band"
    >
      <div className="shell-context-inner">
        <span className="shell-context-scope">
          <ShieldCheck aria-hidden="true" />
          Afgrænset, neutralt katalog
        </span>
        <span className="shell-context-date">
          <CalendarDays aria-hidden="true" />
          Data fra {date.format(new Date(dataset.generatedAt))}
        </span>
      </div>
    </div>
  );
}

export function ApplicationShell({ children, dataset }: ApplicationShellProps) {
  const router = useRouter();
  const index = indexCatalogueDataset(dataset);
  const location = useRouterState({
    select: (state) => state.location,
  });
  const pathname = location.pathname;
  const routeOffers = location.search.offers;
  let routeOfferIdentities: string[] = [];
  if (Array.isArray(routeOffers)) {
    routeOfferIdentities = routeOffers;
  } else if (typeof routeOffers === "string") {
    routeOfferIdentities = [routeOffers];
  }
  const selectedOfferIdentities = reconcileOfferSelection(
    routeOfferIdentities,
    index,
  );
  const destination = destinationForPath(pathname);
  const updateSelection = (offers: readonly string[]) => {
    void router.navigate({
      to: pathname,
      search: withOfferSelection(location.search, offers),
    });
  };

  return (
    <div className="application-shell">
      <header className="shell-header">
        <ContextBand dataset={dataset} />
        <div className="shell-main-row">
          <Brand selectedOfferIdentities={selectedOfferIdentities} />
          <p className="shell-page-title">{pageTitle(destination)}</p>
          <Navigation
            destination={destination}
            selectedOfferIdentities={selectedOfferIdentities}
          />
        </div>
        <Navigation
          destination={destination}
          mobile
          selectedOfferIdentities={selectedOfferIdentities}
        />
      </header>
      <div className="shell-content">{children}</div>
      <OfferSelectionTray
        availableOffers={dataset.offers}
        comparisonHref={router.history.createHref(
          router.buildLocation({
            to: "/compare",
            search: offerSelectionSearch(selectedOfferIdentities),
          }).href,
        )}
        index={index}
        offerDetailHref={(identity) =>
          router.history.createHref(
            router.buildLocation({
              to: "/offers/$identity",
              params: { identity },
              search: offerSelectionSearch(selectedOfferIdentities),
            }).href,
          )
        }
        onAdd={(identity) =>
          updateSelection(addOffer(selectedOfferIdentities, identity))
        }
        onClear={() => updateSelection(clearOfferSelection())}
        onRemove={(identity) =>
          updateSelection(removeOffer(selectedOfferIdentities, identity))
        }
        selectedOfferIdentities={selectedOfferIdentities}
      />
    </div>
  );
}
