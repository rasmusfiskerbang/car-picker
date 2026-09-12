import { Link, useRouter, useRouterState } from "@tanstack/react-router";
import { CarFront } from "lucide-react";
import { type ReactNode } from "react";

import {
  type CatalogueDataset,
  indexCatalogueDataset,
} from "@/catalogue-dataset";
import { cn } from "@/lib/utils";
import {
  offerSelectionSearch,
  reconcileOfferSelection,
  removeOffer,
  withOfferSelection,
} from "@/offer-selection-search";
import { OfferSelectionTray } from "@/offer-selection-tray";

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
        <div className="shell-main-row">
          <Brand selectedOfferIdentities={selectedOfferIdentities} />
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
        onRemove={(identity) =>
          updateSelection(removeOffer(selectedOfferIdentities, identity))
        }
        selectedOfferIdentities={selectedOfferIdentities}
      />
    </div>
  );
}
