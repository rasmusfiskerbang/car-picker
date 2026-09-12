import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ExternalLink, FileText } from "lucide-react";
import {
  type CatalogueDatasetIndex,
  type CatalogueOffer,
  deriveOfferFacts,
} from "@/catalogue-dataset";
import { allowlistedOfferImageUrls } from "@/catalogue-image";
import { CatalogueOfferImage } from "@/catalogue-offer-image";
import {
  currency,
  derivedAmountText,
  factText,
  money,
  upfrontCashText,
  valueLabels,
} from "@/catalogue-ui";

export function CatalogueOfferCard({
  detailHref,
  index,
  offer,
  selected,
  selectionDisabled,
  onSelectionChange,
}: {
  detailHref: string;
  index: CatalogueDatasetIndex;
  offer: CatalogueOffer;
  selected: boolean;
  selectionDisabled: boolean;
  onSelectionChange: (selected: boolean) => void;
}) {
  const facts = deriveOfferFacts(index, offer);
  const vehicle = facts.vehicleName;
  const imageUrls = allowlistedOfferImageUrls(index, offer);

  return (
    <Card className="offer-card">
      <CatalogueOfferImage
        alt={`${vehicle} hos ${facts.providerName}`}
        className="offer-card-image"
        urls={imageUrls}
      />
      <CardHeader className="offer-card-header">
        <p className="eyebrow">{facts.providerName}</p>
        <h2>{vehicle}</h2>
        <p className="offer-card-context">
          {valueLabels[offer.supportedLeasingForm] ?? offer.supportedLeasingForm} · {vehicleKind(offer)}
        </p>
      </CardHeader>
      <CardContent>
        <dl className="facts offer-card-facts">
          <FactRow
            label="Månedlig betaling"
            value={derivedAmountText(facts.leasePayment)}
          />
          <FactRow
            label="Annonceret samlet betaling"
            value={factText(offer.advertisedTotal, (value) => money(value.amountDkk))}
          />
          <FactRow
            label="Kontant behov ved start"
            value={upfrontCashText(facts.upfrontCash)}
          />
          <FactRow
            label="Nominelt basisudlæg"
            value={
              facts.calculatedTotalDkk === undefined
                ? "Kan ikke beregnes"
                : money(facts.calculatedTotalDkk)
            }
          />
          <FactRow label="Fuld løbetid" value={`${offer.termMonths} måneder`} />
          <FactRow
            label="Kilometer om året"
            value={factText(offer.annualMileageKm, (value) => `${currency.format(value)} km`)}
          />
        </dl>
        <footer className="offer-card-footer">
          <label className="offer-selection">
            <input
              aria-label={`Vælg ${vehicle} til sammenligning`}
              checked={selected}
              disabled={selectionDisabled && !selected}
              type="checkbox"
              onChange={(event) => onSelectionChange(event.target.checked)}
            />
            Vælg til sammenligning
          </label>
          <div className="offer-card-links">
            <a
              aria-label={`Åbn hos ${facts.providerName}`}
              className="offer-source-link"
              href={offer.canonicalOfferUrl}
              rel="noreferrer"
              target="_blank"
            >
              <ExternalLink aria-hidden="true" />
            </a>
            <a aria-label={`Se detaljer for ${vehicle}`} href={detailHref}>
              <FileText aria-hidden="true" />
            </a>
          </div>
        </footer>
      </CardContent>
    </Card>
  );
}

function vehicleKind(offer: CatalogueOffer): string {
  return offer.vehicleSpecification.kind === "battery_electric"
    ? "Batterielektrisk"
    : `Forbrænding · ${offer.vehicleSpecification.fuelType === "diesel" ? "diesel" : "benzin"}`;
}

function FactRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="fact-row">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
