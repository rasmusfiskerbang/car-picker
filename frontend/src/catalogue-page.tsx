import { type RefObject, useEffect, useRef, useState } from "react";

import {
  type CatalogueDataset,
  type CatalogueDatasetIndex,
} from "@/catalogue-dataset";
import { CatalogueFilterControls } from "@/catalogue-filter-controls";
import { CatalogueOfferCard } from "@/catalogue-offer-card";
import {
  catalogueSortLabel,
  matchesCatalogueSearch,
  MAX_SELECTED_OFFERS,
  sortCatalogueOffers,
  type CatalogueSearch,
  type CatalogueSort,
  type LeasingForm,
  type VehicleKind,
} from "@/catalogue-search";

export interface CatalogueOverviewProps {
  dataset: CatalogueDataset;
  index: CatalogueDatasetIndex;
  search: CatalogueSearch;
  selectedOfferIdentities: readonly string[];
  comparisonHref: string;
  offerDetailHref: (identity: string) => string;
  onSearchChange: (value: string | undefined) => void;
  onProviderChange: (value: string | undefined) => void;
  onLeasingFormChange: (value: LeasingForm | undefined) => void;
  onVehicleKindChange: (value: VehicleKind | undefined) => void;
  onSortChange: (value: CatalogueSort | undefined) => void;
  onResetFilters: () => void;
  onSelectionChange: (identity: string, selected: boolean) => void;
}

export function CatalogueOverview({
  dataset,
  index,
  search,
  selectedOfferIdentities,
  comparisonHref,
  offerDetailHref,
  onSearchChange,
  onProviderChange,
  onLeasingFormChange,
  onVehicleKindChange,
  onSortChange,
  onResetFilters,
  onSelectionChange,
}: CatalogueOverviewProps) {
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const filterTriggerRef = useRef<HTMLButtonElement>(null);
  const filterSheetRef = useRef<HTMLElement>(null);
  const wasMobileFiltersOpen = useRef(false);
  const selected = selectedOfferIdentities;
  const filteredOffers = dataset.offers.filter((offer) =>
    matchesCatalogueSearch(offer, index, search),
  );
  const displayedOffers = sortCatalogueOffers(filteredOffers, index, search.sort);

  useEffect(() => {
    if (!mobileFiltersOpen) {
      if (wasMobileFiltersOpen.current) {
        wasMobileFiltersOpen.current = false;
        filterTriggerRef.current?.focus();
      }
      return;
    }

    wasMobileFiltersOpen.current = true;
    const sheet = filterSheetRef.current;
    if (sheet !== null) {
      getFocusableElements(sheet)[0]?.focus();
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setMobileFiltersOpen(false);
        return;
      }
      if (event.key !== "Tab" || sheet === null) return;

      const focusableElements = getFocusableElements(sheet);
      if (focusableElements.length === 0) return;
      const first = focusableElements[0];
      const last = focusableElements[focusableElements.length - 1];
      const active = document.activeElement;

      if (!sheet.contains(active)) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
      } else if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [mobileFiltersOpen]);

  const resetFilters = () => {
    onResetFilters();
    setMobileFiltersOpen(false);
  };

  return (
    <>
      <main
        className="page catalogue-page"
        inert={mobileFiltersOpen}
      >
        <header className="catalogue-overview-header">
          <p className="eyebrow">Aktivt katalog</p>
          <h1>Leasingtilbud</h1>
        </header>

        <div className="catalogue-mobile-toolbar">
          <p className="catalogue-result-summary" aria-live="polite">
            {resultLabel(displayedOffers.length)}
          </p>
          <button
            ref={filterTriggerRef}
            aria-controls="mobile-filter-sheet"
            aria-expanded={mobileFiltersOpen}
            className="filter-trigger"
            type="button"
            onClick={() => setMobileFiltersOpen(true)}
          >
            Åbn filtre
          </button>
        </div>

        <div className="catalogue-layout">
          <section aria-label="Katalogtilbud" className="catalogue-results">
            <div className="catalogue-results-toolbar">
              <p className="catalogue-result-summary" aria-live="polite">
                {resultLabel(displayedOffers.length)}
              </p>
              <p className="catalogue-order-note">
                {catalogueSortLabel(search.sort)} · ingen anbefalinger
              </p>
            </div>

            <aside aria-label="Sammenligning" className="comparison-control">
              {selected.length === 0 ? (
                <p>Vælg mindst ét tilbud for at sammenligne det.</p>
              ) : (
                <a href={comparisonHref}>
                  Sammenlign {selected.length} tilbud
                </a>
              )}
            </aside>

            <div className="offer-list">
              {displayedOffers.map((offer) => (
                <CatalogueOfferCard
                  detailHref={offerDetailHref(offer.offerIdentity)}
                  index={index}
                  key={offer.offerIdentity}
                  offer={offer}
                  selected={selected.includes(offer.offerIdentity)}
                  selectionDisabled={selected.length >= MAX_SELECTED_OFFERS}
                  onSelectionChange={(isSelected) =>
                    onSelectionChange(offer.offerIdentity, isSelected)
                  }
                />
              ))}
              {displayedOffers.length === 0 && <EmptyState onReset={resetFilters} />}
            </div>
          </section>

          <aside aria-label="Katalogfiltre" className="catalogue-sidebar">
            <CatalogueFilterControls
              dataset={dataset}
              search={search}
              onLeasingFormChange={onLeasingFormChange}
              onProviderChange={onProviderChange}
              onReset={resetFilters}
              onSearchChange={onSearchChange}
              onSortChange={onSortChange}
              onVehicleKindChange={onVehicleKindChange}
            />
          </aside>
        </div>
      </main>

      {mobileFiltersOpen && (
        <MobileFilterSheet
          displayedOfferCount={displayedOffers.length}
          filterSheetRef={filterSheetRef}
          dataset={dataset}
          search={search}
          onClose={() => setMobileFiltersOpen(false)}
          onLeasingFormChange={onLeasingFormChange}
          onProviderChange={onProviderChange}
          onReset={resetFilters}
          onSearchChange={onSearchChange}
          onSortChange={onSortChange}
          onVehicleKindChange={onVehicleKindChange}
        />
      )}
    </>
  );
}

function MobileFilterSheet({
  dataset,
  displayedOfferCount,
  filterSheetRef,
  search,
  onClose,
  onLeasingFormChange,
  onProviderChange,
  onReset,
  onSearchChange,
  onSortChange,
  onVehicleKindChange,
}: {
  dataset: CatalogueDataset;
  displayedOfferCount: number;
  filterSheetRef: RefObject<HTMLElement | null>;
  search: CatalogueSearch;
  onClose: () => void;
  onLeasingFormChange: (value: LeasingForm | undefined) => void;
  onProviderChange: (value: string | undefined) => void;
  onReset: () => void;
  onSearchChange: (value: string | undefined) => void;
  onSortChange: (value: CatalogueSort | undefined) => void;
  onVehicleKindChange: (value: VehicleKind | undefined) => void;
}) {
  return (
    <div className="filter-sheet-backdrop" onClick={onClose}>
      <section
        ref={filterSheetRef}
        aria-labelledby="mobile-filter-sheet-title"
        aria-modal="true"
        className="filter-sheet"
        id="mobile-filter-sheet"
        role="dialog"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="filter-sheet-header">
          <div>
            <p className="eyebrow">Afgræns visningen</p>
            <h2 id="mobile-filter-sheet-title">Filtre</h2>
          </div>
          <div className="filter-sheet-actions">
            <button className="filter-sheet-reset" type="button" onClick={onReset}>
              Nulstil filtre
            </button>
            <button
              aria-label="Luk filtre"
              className="filter-sheet-close"
              type="button"
              onClick={onClose}
            >
              Luk
            </button>
          </div>
        </header>
        <CatalogueFilterControls
          dataset={dataset}
          heading={false}
          search={search}
          onLeasingFormChange={onLeasingFormChange}
          onProviderChange={onProviderChange}
          onReset={onReset}
          onSearchChange={onSearchChange}
          onSortChange={onSortChange}
          onVehicleKindChange={onVehicleKindChange}
        />
        <button className="filter-sheet-done" type="button" onClick={onClose}>
          Vis {resultLabel(displayedOfferCount)}
        </button>
      </section>
    </div>
  );
}

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
    ),
  );
}

function EmptyState({ onReset }: { onReset: () => void }) {
  return (
    <div className="empty-state">
      <p className="eyebrow">Inden for dette aktive katalog</p>
      <h2>Ingen tilbud matcher i det aktive katalog</h2>
      <p>Det betyder ikke, at der ikke findes andre tilbud.</p>
      <button type="button" onClick={onReset}>
        Nulstil filtre
      </button>
    </div>
  );
}

function resultLabel(count: number): string {
  return `${count} tilbud`;
}
