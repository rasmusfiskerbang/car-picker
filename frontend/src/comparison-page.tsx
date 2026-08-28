import {
  type KeyboardEvent,
  type ReactNode,
  useEffect,
  useRef,
} from "react";
import { Link } from "@tanstack/react-router";

import {
  CatalogueCashFlowColumn,
  CatalogueCashFlowSharedChart,
  normalizedViewingDate,
} from "@/catalogue-cash-flow";
import {
  type CatalogueDatasetIndex,
  type CatalogueOffer,
  deriveOfferFacts,
} from "@/catalogue-dataset";
import {
  presentContractFacts,
  presentServiceFact,
  presentSourceFacts,
  presentVehicleFacts,
  type PresentedFact,
} from "@/offer-fact-presentation";
import { offerSelectionSearch } from "@/offer-selection-search";

type ComparisonCell = {
  content: ReactNode;
  unavailable?: boolean;
};

type ComparisonRow = {
  label: string;
  values: (offer: CatalogueOffer) => ComparisonCell;
};

type RowComparisonSection = {
  kind: "rows";
  key: string;
  rows: readonly ComparisonRow[];
  title: string;
};

type SharedContentComparisonSection = {
  content: ReactNode;
  key: string;
  kind: "shared-content";
  title: string;
};

type ComparisonSection =
  | RowComparisonSection
  | SharedContentComparisonSection;

export function ComparisonPage({
  index,
  offers,
}: {
  index: CatalogueDatasetIndex;
  offers: readonly CatalogueOffer[];
}) {
  const selectedOfferIdentities = offers.map((offer) => offer.offerIdentity);

  return (
    <main className="page comparison-page">
      <Link
        className="comparison-back-link"
        search={offerSelectionSearch(selectedOfferIdentities)}
        to="/catalogue"
      >
        Tilbage til kataloget
      </Link>
      <h1>Sammenlign tilbud</h1>
      <ComparisonMatrix
        index={index}
        offers={offers}
        selectedOfferIdentities={selectedOfferIdentities}
      />
    </main>
  );
}

function ComparisonMatrix({
  index,
  offers,
  selectedOfferIdentities,
}: {
  index: CatalogueDatasetIndex;
  offers: readonly CatalogueOffer[];
  selectedOfferIdentities: readonly string[];
}) {
  const tableMinWidth = `${12 + offers.length * 15}rem`;
  const referenceDate = normalizedViewingDate();
  const sections = comparisonSections(index, offers, referenceDate);
  const tableRef = useRef<HTMLTableElement>(null);

  useEffect(() => {
    const table = tableRef.current;
    const header = table?.tHead;
    const firstCell = header?.querySelector("th");
    if (table === null || header == null || firstCell == null) return;

    const updateHeaderPosition = () => {
      const cellStyle = getComputedStyle(firstCell);
      const headerTopInRem = Number.parseFloat(
        cellStyle.getPropertyValue("--comparison-header-top"),
      );
      const rootFontSize = Number.parseFloat(
        getComputedStyle(document.documentElement).fontSize,
      );
      const stickyTop = headerTopInRem * rootFontSize;
      const tableRect = table.getBoundingClientRect();
      const headerHeight = header.getBoundingClientRect().height;
      const headerIsInView =
        tableRect.top < stickyTop &&
        tableRect.bottom > stickyTop + headerHeight;
      let offset = 0;
      if (headerIsInView) offset = stickyTop - tableRect.top;
      header.style.transform = `translateY(${offset}px)`;
    };

    updateHeaderPosition();
    window.addEventListener("resize", updateHeaderPosition);
    window.addEventListener("scroll", updateHeaderPosition, { passive: true });
    return () => {
      window.removeEventListener("resize", updateHeaderPosition);
      window.removeEventListener("scroll", updateHeaderPosition);
    };
  }, []);

  return (
    <div className="comparison-surface">
      <div
        aria-label="Sammenligning af tilbud"
        className="comparison-scroll"
        data-testid="comparison-scroll"
        role="region"
        tabIndex={0}
        onKeyDown={scrollComparison}
      >
        <table
          aria-label="Sammenligning af tilbud"
          className="comparison-table"
          ref={tableRef}
          style={{ minWidth: tableMinWidth }}
        >
          <caption className="visually-hidden">
            Faktuel sammenligning af de valgte tilbud
          </caption>
          <thead>
            <ComparisonHeaderRow
              index={index}
              offers={offers}
              selectedOfferIdentities={selectedOfferIdentities}
            />
          </thead>
          {sections.map((section) => (
            <tbody key={section.key}>
              <tr className="comparison-section-row">
                <th colSpan={offers.length + 1} scope="colgroup">
                  {section.title}
                </th>
              </tr>
              {renderSection(section, offers)}
            </tbody>
          ))}
        </table>
      </div>
    </div>
  );
}

function ComparisonHeaderRow({
  index,
  offers,
  selectedOfferIdentities,
}: {
  index: CatalogueDatasetIndex;
  offers: readonly CatalogueOffer[];
  selectedOfferIdentities: readonly string[];
}) {
  return (
    <tr>
      <th className="comparison-label-cell" scope="col">
        Faktum
      </th>
      {offers.map((offer) => (
        <th key={offer.offerIdentity} scope="col">
          <Link
            params={{ identity: offer.offerIdentity }}
            search={offerSelectionSearch(selectedOfferIdentities)}
            to="/offers/$identity"
          >
            {vehicleName(index, offer)}
          </Link>
        </th>
      ))}
    </tr>
  );
}

function renderSection(
  section: ComparisonSection,
  offers: readonly CatalogueOffer[],
): ReactNode {
  if (section.kind === "shared-content") return section.content;
  return section.rows.map((row) => (
    <ComparisonRowView key={row.label} offers={offers} row={row} />
  ));
}

function ComparisonRowView({
  offers,
  row,
}: {
  offers: readonly CatalogueOffer[];
  row: ComparisonRow;
}) {
  return (
    <tr>
      <th className="comparison-label-cell" scope="row">
        {row.label}
      </th>
      {offers.map((offer) => {
        const cell = row.values(offer);
        return (
          <td
            className={comparisonCellClass(cell)}
            key={offer.offerIdentity}
          >
            {cell.content}
          </td>
        );
      })}
    </tr>
  );
}

function comparisonSections(
  index: CatalogueDatasetIndex,
  offers: readonly CatalogueOffer[],
  referenceDate: Date,
): ComparisonSection[] {
  const row = (
    label: string,
    values: (offer: CatalogueOffer) => ComparisonCell,
  ): ComparisonRow => ({ label, values });
  const vehicleRow = (label: string): ComparisonRow =>
    row(label, (offer) => presentedFactCell(presentVehicleFacts(offer, true), label));
  const contractRow = (label: string): ComparisonRow =>
    row(label, (offer) => {
      const facts = deriveOfferFacts(index, offer);
      return presentedFactCell(
        presentContractFacts(offer, facts, true),
        label,
      );
    });

  return [
    {
      kind: "rows",
      key: "vehicle",
      title: "Køretøj",
      rows: [
        vehicleRow("Mærke"),
        vehicleRow("Model"),
        vehicleRow("Variant"),
        vehicleRow("Modelår"),
        vehicleRow("Førstegangsregistrering"),
        vehicleRow("Karrosseri"),
        vehicleRow("Kilometertal"),
        vehicleRow("Drivmiddel"),
        vehicleRow("Brændstof"),
        vehicleRow("Brændstoføkonomi"),
        vehicleRow("Batterikapacitet"),
        vehicleRow("WLTP-rækkevidde"),
        vehicleRow("Maksimal ladeeffekt"),
        vehicleRow("Ladetid fra 10 til 80 %"),
      ],
    },
    {
      kind: "rows",
      key: "contract",
      title: "Aftale",
      rows: [
        contractRow("Leasingform"),
        contractRow("Udbyderens formbetegnelse"),
        contractRow("Fuld løbetid"),
        contractRow("Kilometer om året"),
        contractRow("Normal afslutning"),
        contractRow("Restværdirisiko"),
        contractRow("Annonceret samlet betaling"),
        contractRow("Nominelt basisudlæg"),
        contractRow("Nominelt månedligt gennemsnit"),
        contractRow("Månedlig betaling"),
        contractRow("Kontant behov ved start"),
      ],
    },
    {
      kind: "rows",
      key: "service",
      title: "Service",
      rows: [
        row("Serviceordninger", (offer) => presentServiceCell(offer)),
      ],
    },
    {
      kind: "shared-content",
      key: "cash-flow",
      title: "Kontantstrøm",
      content: (
        <>
          <tr className="comparison-cash-flow-shared-row">
            <td colSpan={offers.length + 1}>
              <CatalogueCashFlowSharedChart
                offers={offers}
                referenceDate={referenceDate}
              />
            </td>
          </tr>
          <tr className="comparison-cash-flow-columns-row">
            <th className="comparison-label-cell" scope="row">
              Detaljer
            </th>
            {offers.map((offer) => (
              <td key={offer.offerIdentity}>
                <CatalogueCashFlowColumn
                  offer={offer}
                  referenceDate={referenceDate}
                />
              </td>
            ))}
          </tr>
        </>
      ),
    },
    {
      kind: "rows",
      key: "source",
      title: "Kilde",
      rows: [
        row("Udbyder", (offer) =>
          textCell(presentSourceFacts(index, offer).providerName),
        ),
        row("Kanonisk tilbudskilde", (offer) => sourceCell(index, offer)),
      ],
    },
  ];
}

function vehicleName(index: CatalogueDatasetIndex, offer: CatalogueOffer): string {
  return deriveOfferFacts(index, offer).vehicleName;
}

function presentedFactCell(
  facts: readonly PresentedFact[],
  label: string,
): ComparisonCell {
  const fact = facts.find((candidate) => candidate.label === label);
  if (fact === undefined) {
    return unavailableCell("Oplysningen er ikke tilgængelig.");
  }
  return {
    content: fact.text,
    unavailable: fact.unavailable,
  };
}

function presentServiceCell(offer: CatalogueOffer): ComparisonCell {
  const fact = presentServiceFact(offer);
  return {
    content: fact.text,
    unavailable: fact.unavailable,
  };
}

function sourceCell(
  index: CatalogueDatasetIndex,
  offer: CatalogueOffer,
): ComparisonCell {
  const source = presentSourceFacts(index, offer);
  const name = vehicleName(index, offer);
  return {
    content: (
      <a
        aria-label={`Åbn den kanoniske tilbudskilde for ${name}`}
        href={source.canonicalOfferUrl}
        rel="noreferrer noopener"
        target="_blank"
      >
        {source.canonicalOfferUrl}
      </a>
    ),
  };
}

function textCell(content: string): ComparisonCell {
  return { content };
}

function unavailableCell(content: string): ComparisonCell {
  return { content, unavailable: true };
}

function comparisonCellClass(cell: ComparisonCell): string | undefined {
  if (cell.unavailable) return "comparison-unavailable";
  return undefined;
}

function scrollComparison(event: KeyboardEvent<HTMLDivElement>) {
  const region = event.currentTarget;
  const distance = Math.max(160, Math.round(region.clientWidth * 0.75));
  if (event.key === "ArrowRight" || event.key === "ArrowDown") {
    event.preventDefault();
    region.scrollBy({ left: distance, behavior: "auto" });
    return;
  }
  if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
    event.preventDefault();
    region.scrollBy({ left: -distance, behavior: "auto" });
    return;
  }
  if (event.key === "Home") {
    event.preventDefault();
    region.scrollTo({ left: 0, behavior: "auto" });
    return;
  }
  if (event.key === "End") {
    event.preventDefault();
    region.scrollTo({ left: region.scrollWidth, behavior: "auto" });
  }
}
