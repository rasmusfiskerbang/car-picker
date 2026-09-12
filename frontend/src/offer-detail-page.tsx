import { Link } from "@tanstack/react-router";

import { CatalogueCashFlowDisplay } from "@/catalogue-cash-flow";
import {
  type CatalogueDataset,
  type CatalogueDatasetIndex,
  type CatalogueOffer,
  deriveOfferFacts,
  findProviderById,
} from "@/catalogue-dataset";
import { allowlistedOfferImageUrls } from "@/catalogue-image";
import { CatalogueOfferGallery } from "@/catalogue-offer-gallery";
import { MAX_SELECTED_OFFERS } from "@/catalogue-search";
import { derivedAmountText, generatedAtText } from "@/catalogue-ui";
import { OfferDetailContractSection } from "@/offer-detail-contract-section";
import { OfferDetailServiceSection } from "@/offer-detail-service-section";
import { OfferDetailSourceSection } from "@/offer-detail-source-section";
import { OfferDetailVehicleSection } from "@/offer-detail-vehicle-section";
import { offerSelectionSearch } from "@/offer-selection-search";

export function OfferDetailPage({
  dataset,
  index,
  offer,
  onSelectionChange,
  selectedOfferIdentities,
}: {
  dataset: CatalogueDataset;
  index: CatalogueDatasetIndex;
  offer: CatalogueOffer;
  onSelectionChange: (selected: boolean) => void;
  selectedOfferIdentities: readonly string[];
}) {
  const provider = findProviderById(index, offer.providerId);
  const facts = deriveOfferFacts(index, offer);
  const vehicleTitle = facts.vehicleName;
  const imageUrls = allowlistedOfferImageUrls(index, offer);
  const selected = selectedOfferIdentities.includes(offer.offerIdentity);

  return (
    <main className="page detail-page">
      <Link
        className="detail-back-link"
        search={offerSelectionSearch(selectedOfferIdentities)}
        to="/catalogue"
      >
        Tilbage til kataloget
      </Link>

      <section aria-labelledby="offer-title" className="detail-hero">
        <CatalogueOfferGallery
          alt={`${vehicleTitle} hos ${facts.providerName}`}
          urls={imageUrls}
        />
        <div className="detail-hero-copy">
          <p className="eyebrow">{facts.providerName}</p>
          <h1 id="offer-title">{vehicleTitle}</h1>
          <p className="detail-hero-context">
            {leasingFormLabel(offer.supportedLeasingForm)} · {offer.termMonths} måneder
          </p>
          <div className="detail-price-block">
            <span>Månedlig betaling</span>
            <strong>{derivedAmountText(facts.leasePayment)}</strong>
          </div>
          <DetailSelectionControl
            onSelectionChange={onSelectionChange}
            selected={selected}
            selectedOfferIdentities={selectedOfferIdentities}
            vehicleTitle={vehicleTitle}
          />
        </div>
      </section>

      <div className="detail-layout">
        <ContentsRail />
        <div className="detail-sections">
          <OfferDetailVehicleSection offer={offer} />
          <OfferDetailContractSection facts={facts} offer={offer} />
          <OfferDetailServiceSection offer={offer} />
          <section
            aria-label="Basiskontantstrøm"
            className="detail-section"
            id="cash-flow"
          >
            <h2 id="cash-flow-heading">Kontantstrøm</h2>
            <p className="section-lede">
              Alle dokumenterede betalinger og modtagne beløb ved normal afslutning,
              i kronologisk rækkefølge.
            </p>
            <CatalogueCashFlowDisplay
              offers={[offer]}
              referenceDate={new Date(dataset.generatedAt)}
            />
          </section>
          <OfferDetailSourceSection
            canonicalOfferUrl={offer.canonicalOfferUrl}
            provider={provider}
            providerId={offer.providerId}
          />
        </div>
      </div>

      <p className="source-note">
        Datasættet blev genereret {generatedAtText(dataset)}. Kontrollér altid de
        aktuelle vilkår hos udbyderen.
      </p>
    </main>
  );
}

function ContentsRail() {
  return (
    <nav aria-label="Indhold på siden" className="detail-contents">
      <p className="eyebrow">Indhold</p>
      <a href="#vehicle">Køretøj</a>
      <a href="#contract">Aftale</a>
      <a href="#service">Service</a>
      <a href="#cash-flow">Kontantstrøm</a>
      <a href="#source">Kilde</a>
    </nav>
  );
}

function DetailSelectionControl({
  onSelectionChange,
  selected,
  selectedOfferIdentities,
  vehicleTitle,
}: {
  onSelectionChange: (selected: boolean) => void;
  selected: boolean;
  selectedOfferIdentities: readonly string[];
  vehicleTitle: string;
}) {
  const selectionLimitReached =
    selectedOfferIdentities.length >= MAX_SELECTED_OFFERS && !selected;

  return (
    <div className="detail-selection-actions">
      <label className="detail-selection">
        <input
          aria-label={`Vælg ${vehicleTitle} til sammenligning`}
          checked={selected}
          disabled={selectionLimitReached}
          type="checkbox"
          onChange={(event) => onSelectionChange(event.target.checked)}
        />
        Vælg til sammenligning
      </label>
      {selectedOfferIdentities.length >= 2 && (
        <Link
          className="detail-comparison-link"
          search={offerSelectionSearch(selectedOfferIdentities)}
          to="/compare"
        >
          Sammenlign {selectedOfferIdentities.length} tilbud
        </Link>
      )}
      {selectionLimitReached && (
        <span className="detail-selection-note">
          Der kan højst vælges {MAX_SELECTED_OFFERS} tilbud.
        </span>
      )}
    </div>
  );
}

function leasingFormLabel(value: CatalogueOffer["supportedLeasingForm"]): string {
  const labels = {
    financial: "Finansiel leasing",
    flex: "Flexleasing",
    operational: "Operationel privatleasing",
    hybrid: "Hybrid leasingform",
  } as const;
  return labels[value];
}
