// PROTOTYPE — three selected-offer comparison variants, switchable via
// ?variant=, on the throwaway /prototype/compare route.
import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  CalendarRange,
  CarFront,
  CircleAlert,
  ExternalLink,
  Plus,
  ReceiptText,
  Scale,
  ShieldQuestion,
} from "lucide-react";
import { type ReactNode, type UIEvent, useRef } from "react";

import {
  type CatalogueDataset,
  type CatalogueOffer,
  type OfferFact,
  endMechanism,
  monthlyPayment,
  riskAllocation,
  upfrontPayment,
  vehicleName,
} from "@/catalogue-data";
import { ComposedChart } from "@/components/charts/composed-chart";
import { Grid } from "@/components/charts/grid";
import { SeriesBar } from "@/components/charts/series-bar";
import { ChartTooltip } from "@/components/charts/tooltip/chart-tooltip";
import {
  TooltipContent as ChartTooltipContent,
  type TooltipRow,
} from "@/components/charts/tooltip/tooltip-content";
import { YAxis } from "@/components/charts/y-axis";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { PrototypeSwitcher } from "@/prototype/prototype-switcher";
import type { ComparisonSearch } from "@/routes/prototype.compare";

const currency = new Intl.NumberFormat("da-DK", {
  currency: "DKK",
  maximumFractionDigits: 0,
  style: "currency",
});
const decimal = new Intl.NumberFormat("da-DK", { maximumFractionDigits: 1 });
const integer = new Intl.NumberFormat("da-DK");
const chartDate = new Intl.DateTimeFormat("da-DK", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

const offerColors = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)"];
const receiptColors = offerColors.map(
  (color) => `color-mix(in oklch, ${color} 38%, var(--card))`,
);

const leasingLabels = {
  financial: "Finansiel leasing",
  flex: "Flexleasing",
  operational: "Operationel leasing",
  hybrid: "Hybrid leasingform",
} as const;

const bodyStyleLabels = {
  hatchback: "Hatchback",
  saloon: "Sedan",
  estate: "Stationcar",
  suv: "SUV",
  coupe: "Coupé",
  convertible: "Cabriolet",
  mpv: "MPV",
  other: "Anden",
} as const;

const cashFlowLabels = {
  initial_payment: "Førstegangsydelse",
  lease_payment: "Leasingydelse",
  establishment_fee: "Etableringsgebyr",
  delivery_fee: "Leveringsgebyr",
  deposit: "Depositum",
  deposit_refund: "Tilbagebetaling af depositum",
  mandatory_purchase_or_payoff: "Obligatorisk køb eller indfrielse",
  other: "Anden obligatorisk post",
} as const;

const serviceTreatmentLabels = {
  included: "Inkluderet",
  optional: "Valgfrit tilkøb",
  required_external: "Skal købes eksternt",
  excluded: "Ikke inkluderet",
} as const;

const variants = [
  { key: "a", name: "Kontrolmatrix" },
  { key: "b", name: "Aftalens faser" },
  { key: "c", name: "Afvigelsesregister" },
] as const;

type PatchSearch = (patch: Partial<ComparisonSearch>) => void;

type ComparisonValue = {
  detail?: ReactNode;
  key: string;
  muted?: boolean;
  text: string;
  unavailable?: boolean;
};

type ComparisonRow = {
  label: string;
  sharedDetail?: ReactNode;
  values: ComparisonValue[];
};

type ComparisonSection = {
  key: string;
  rows: ComparisonRow[];
  title: string;
};

function unavailableText(state: Exclude<OfferFact["state"], "known">) {
  const labels = {
    not_stated: "Ikke oplyst",
    unclear: "Uklart oplyst",
    conflicting: "Modstridende oplysninger",
    not_applicable: "Ikke relevant",
  } as const;
  return labels[state];
}

function money(value: number | null) {
  return value === null ? "Kan ikke beregnes" : currency.format(value);
}

function textValue(
  text: string,
  unavailable = false,
  muted = unavailable,
): ComparisonValue {
  return { key: text, muted, text, unavailable };
}

function factValue<T>(fact: OfferFact, format: (value: T) => string) {
  if (fact.state !== "known") {
    return textValue(
      unavailableText(fact.state),
      fact.state !== "not_applicable",
      true,
    );
  }
  return textValue(format(fact.value as T));
}

function providerName(dataset: CatalogueDataset, offer: CatalogueOffer) {
  return (
    dataset.providers.find((provider) => provider.id === offer.providerId)
      ?.name ?? offer.providerId
  );
}

function mileage(offer: CatalogueOffer) {
  return factValue<number>(
    offer.annualMileageKm,
    (value) => `${integer.format(value)} km/år`,
  );
}

function advertisedTotal(offer: CatalogueOffer) {
  return factValue<number>(offer.advertisedTotalDkk, (value) =>
    currency.format(value),
  );
}

function serviceArrangement(offer: CatalogueOffer) {
  if (offer.serviceArrangements.state !== "known") {
    return textValue(unavailableText(offer.serviceArrangements.state), true);
  }
  const text = offer.serviceArrangements.value
    .map(
      (arrangement) =>
        `${serviceTreatmentLabels[arrangement.treatment]}: ${arrangement.summary} Begrænsninger: ${arrangement.limits.state === "known" ? arrangement.limits.value : unavailableText(arrangement.limits.state)}.`,
    )
    .join(" ");
  return textValue(text);
}

function drivetrain(offer: CatalogueOffer) {
  const spec = offer.vehicleSpecification;
  if (spec.kind === "combustion") {
    return textValue(spec.fuelType === "diesel" ? "Diesel" : "Benzin");
  }
  return textValue("Batterielektrisk");
}

function battery(offer: CatalogueOffer) {
  const spec = offer.vehicleSpecification;
  if (spec.kind === "combustion") return textValue("Ikke relevant", false, true);
  return factValue<{ basis: string; valueKwh: number }>(
    spec.batteryCapacity,
    ({ basis, valueKwh }) =>
      `${decimal.format(valueKwh)} kWh (${basis === "usable" ? "netto" : basis === "gross" ? "brutto" : "basis ikke oplyst"})`,
  );
}

function range(offer: CatalogueOffer) {
  const spec = offer.vehicleSpecification;
  if (spec.kind === "combustion") return textValue("Ikke relevant", false, true);
  return factValue<number>(
    spec.wltpRangeKm,
    (value) => `${integer.format(value)} km WLTP`,
  );
}

function fuelEfficiency(offer: CatalogueOffer) {
  const spec = offer.vehicleSpecification;
  if (spec.kind === "battery_electric")
    return textValue("Ikke relevant", false, true);
  return factValue<number>(
    spec.fuelEfficiencyKmPerLiter,
    (value) => `${decimal.format(value)} km/l`,
  );
}

function totalBlockers(offer: CatalogueOffer) {
  const blockers = offer.baseCashFlowStream
    .filter((event) => event.amount.state !== "known")
    .map(
      (event) =>
        `${cashFlowLabels[event.kind].toLocaleLowerCase("da-DK")} i måned ${event.occursAtMonth}: ${event.amount.state === "known" ? "" : unavailableText(event.amount.state).toLocaleLowerCase("da-DK")}`,
    );
  return blockers.length === 0
    ? "Ingen ukendte beløb i den normale betalingsstrøm."
    : `Blokeret af ${blockers.join("; ")}.`;
}

function cashFlowValue(offer: CatalogueOffer): ComparisonValue {
  const key = JSON.stringify(offer.baseCashFlowStream);
  const unavailable = offer.baseCashFlowStream.some(
    (event) => event.amount.state !== "known",
  );
  return {
    key,
    text: `${offer.baseCashFlowStream.length} kronologiske posteringer`,
    unavailable,
  };
}

type SharedCashFlowPoint = Record<string, unknown> & {
  date: Date;
  label: string;
  month: number;
};

function sharedCashFlowData(offers: CatalogueOffer[]): SharedCashFlowPoint[] {
  const lastMonth = Math.max(...offers.map((offer) => offer.termMonths));
  const startDate = new Date();
  startDate.setHours(12, 0, 0, 0);

  return Array.from({ length: lastMonth + 1 }, (_, month) => {
    const pointDate = new Date(
      startDate.getFullYear(),
      startDate.getMonth() + month + 1,
      0,
      12,
    );
    pointDate.setDate(Math.min(startDate.getDate(), pointDate.getDate()));
    const point: SharedCashFlowPoint = {
      date: pointDate,
      label:
        month === 0
          ? `Ved start · ${chartDate.format(pointDate)}`
          : `${chartDate.format(pointDate)} · måned ${month}`,
      month,
    };

    offers.forEach((offer, offerIndex) => {
      if (month > offer.termMonths) return;
      const events = offer.baseCashFlowStream.filter(
        (event) => event.occursAtMonth === month,
      );
      let payments = 0;
      let receipts = 0;
      let unavailable = 0;
      for (const event of events) {
        if (event.amount.state !== "known") {
          unavailable += 1;
        } else if (event.direction === "payment") {
          payments += event.amount.value;
        } else {
          receipts += event.amount.value;
        }
      }
      point[`offer-${offerIndex}-payments`] = payments;
      point[`offer-${offerIndex}-receipts`] = receipts;
      point[`offer-${offerIndex}-unavailable`] = unavailable;
    });

    return point;
  });
}

function dkkAxis(value: number) {
  if (value === 0) return "0";
  if (Math.abs(value) >= 1_000) return `${decimal.format(value / 1_000)} t.`;
  return integer.format(value);
}

function sharedCashFlowTooltipRows(
  point: Record<string, unknown>,
  offers: CatalogueOffer[],
): TooltipRow[] {
  return offers.flatMap((offer, offerIndex) => {
    const rows: TooltipRow[] = [];
    const payments = point[`offer-${offerIndex}-payments`];
    const receipts = point[`offer-${offerIndex}-receipts`];
    const unavailable = point[`offer-${offerIndex}-unavailable`];
    const label = vehicleName(offer);
    if (typeof payments === "number" && payments > 0) {
      rows.push({
        color: offerColors[offerIndex] ?? "var(--chart-1)",
        label: `${label} · betaling`,
        value: money(payments),
      });
    }
    if (typeof receipts === "number" && receipts > 0) {
      rows.push({
        color: receiptColors[offerIndex] ?? "var(--chart-4)",
        label: `${label} · modtagelse`,
        value: money(receipts),
      });
    }
    if (typeof unavailable === "number" && unavailable > 0) {
      rows.push({
        color: "var(--muted-foreground)",
        label: `${label} · beløb mangler`,
        value: unavailable,
      });
    }
    return rows;
  });
}

function SharedCashFlowChart({ offers }: { offers: CatalogueOffer[] }) {
  const data = sharedCashFlowData(offers);
  const chartMargin = { bottom: 12, left: 62, right: 14, top: 16 };
  const unavailable = offers.flatMap((offer) =>
    offer.baseCashFlowStream.filter((event) => event.amount.state !== "known"),
  );

  return (
    <div className="p-3 sm:p-4" data-testid="bklit-shared-cash-flow">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs font-semibold text-muted-foreground">
          {offers.map((offer, index) => (
            <span
              className="inline-flex items-center gap-2"
              key={offer.offerIdentity}
            >
              <span
                className="size-2.5 rounded-sm"
                style={{
                  backgroundColor: offerColors[index] ?? "var(--chart-1)",
                }}
              />
              {vehicleName(offer)}
            </span>
          ))}
        </div>
        <span className="text-xs text-muted-foreground">
          Mørk = betaling · lys = modtagelse
        </span>
      </div>

      <div className="mt-3">
        <ComposedChart
          aspectRatio="3 / 1"
          barGap={1}
          data={data}
          margin={chartMargin}
          maxBarSize={9}
          xDataKey="date"
        >
          <Grid horizontal numTicksRows={3} />
          {offers.flatMap((offer, index) => [
            <SeriesBar
              dataKey={`offer-${index}-payments`}
              fill={offerColors[index] ?? "var(--chart-1)"}
              key={`${offer.offerIdentity}-payments`}
              radius={2}
            />,
            <SeriesBar
              dataKey={`offer-${index}-receipts`}
              fill={receiptColors[index] ?? "var(--chart-4)"}
              key={`${offer.offerIdentity}-receipts`}
              radius={2}
            />,
          ])}
          <YAxis formatValue={dkkAxis} numTicks={3} />
          <ChartTooltip
            content={({ point }) => (
              <ChartTooltipContent
                rows={sharedCashFlowTooltipRows(point, offers)}
                title={String(point.label)}
              />
            )}
            showCrosshair={false}
            showDatePill={false}
          />
        </ComposedChart>
        <div
          className="mt-2 grid grid-cols-2 text-[0.68rem] font-semibold text-muted-foreground"
          style={{
            paddingLeft: chartMargin.left,
            paddingRight: chartMargin.right,
          }}
        >
          <span>{chartDate.format(data[0].date)}</span>
          <span className="text-right">
            {chartDate.format(data[data.length - 1].date)}
          </span>
        </div>
      </div>

      {unavailable.length > 0 && (
        <p className="mt-3 flex gap-2 rounded-lg bg-secondary/65 p-3 text-xs leading-5 text-muted-foreground">
          <CircleAlert aria-hidden="true" className="mt-0.5 size-3.5 shrink-0" />
          {unavailable.length === 1
            ? "Ét beløb er ikke tilgængeligt og vises ikke som nul."
            : `${unavailable.length} beløb er ikke tilgængelige og vises ikke som nul.`}
        </p>
      )}

      <div className="sr-only">
        {offers.map((offer) => (
          <section key={offer.offerIdentity}>
            <h3>{vehicleName(offer)}</h3>
            <ol>
              {offer.baseCashFlowStream.map((event) => (
                <li key={event.key}>
                  {event.occursAtMonth === 0
                    ? "Ved start"
                    : `Måned ${event.occursAtMonth}`}
                  : {cashFlowLabels[event.kind]};{" "}
                  {event.direction === "payment" ? "betaling" : "modtagelse"};{" "}
                  {event.amount.state === "known"
                    ? money(event.amount.value)
                    : unavailableText(event.amount.state)}
                  .
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>
    </div>
  );
}

function comparisonSections(
  dataset: CatalogueDataset,
  offers: CatalogueOffer[],
): ComparisonSection[] {
  const row = (
    label: string,
    value: (offer: CatalogueOffer) => ComparisonValue,
  ): ComparisonRow => ({ label, values: offers.map(value) });

  return [
    {
      key: "money",
      title: "Beløb og totaler",
      rows: [
        row("Udbyderens månedsydelse", (offer) =>
          textValue(
            monthlyPayment(offer) === null
              ? "Ikke oplyst"
              : `${currency.format(monthlyPayment(offer) ?? 0)}/md.`,
            monthlyPayment(offer) === null,
          ),
        ),
        row("Betaling ved start", (offer) =>
          textValue(money(upfrontPayment(offer)), upfrontPayment(offer) === null),
        ),
        row("Udbyderens annoncerede total", advertisedTotal),
        row("Beregnet total", (offer) => ({
          detail: (
            <div>
              <p className="font-bold">{money(offer.totalDkk)}</p>
              {offer.totalDkk === null && (
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  {totalBlockers(offer)}
                </p>
              )}
            </div>
          ),
          key: String(offer.totalDkk),
          text: money(offer.totalDkk),
          unavailable: offer.totalDkk === null,
        })),
        row("Beregnet pr. måned", (offer) =>
          textValue(money(offer.totalDkkPerMonth), offer.totalDkkPerMonth === null),
        ),
      ],
    },
    {
      key: "end",
      title: "Udløb og forpligtelser",
      rows: [
        row("Ved normalt udløb", (offer) =>
          textValue(
            endMechanism(offer),
            offer.normalEndMechanism.state !== "known",
          ),
        ),
        row("Restværdirisiko", (offer) =>
          textValue(
            riskAllocation(offer),
            offer.residualRiskAllocation.state !== "known",
          ),
        ),
        row("Service og ordninger", serviceArrangement),
      ],
    },
    {
      key: "agreement",
      title: "Aftalens rammer",
      rows: [
        row("Leasingform", (offer) => textValue(leasingLabels[offer.leasingForm])),
        row("Løbetid", (offer) => textValue(`${offer.termMonths} måneder`)),
        row("Årligt kilometertal", mileage),
      ],
    },
    {
      key: "cashflow",
      title: "Betalingsstrøm",
      rows: [
        {
          label: "Alle posteringer",
          sharedDetail: <SharedCashFlowChart offers={offers} />,
          values: offers.map(cashFlowValue),
        },
      ],
    },
    {
      key: "vehicle",
      title: "Køretøjet",
      rows: [
        row("Mærke og model", (offer) =>
          textValue(
            `${offer.vehicleSpecification.make} ${offer.vehicleSpecification.model}`,
          ),
        ),
        row("Variant", (offer) =>
          factValue<string>(offer.vehicleSpecification.trim, String),
        ),
        row("Drivlinje", drivetrain),
        row("Modelår", (offer) =>
          factValue<number>(offer.vehicleSpecification.modelYear, String),
        ),
        row("Første registrering", (offer) =>
          factValue<number>(
            offer.vehicleSpecification.firstRegistrationYear,
            String,
          ),
        ),
        row("Karrosseri", (offer) =>
          factValue<keyof typeof bodyStyleLabels>(
            offer.vehicleSpecification.bodyStyle,
            (value) => bodyStyleLabels[value],
          ),
        ),
        row("Kilometerstand", (offer) =>
          factValue<number>(
            offer.vehicleSpecification.odometerKm,
            (value) => `${integer.format(value)} km`,
          ),
        ),
        row("Batteri", battery),
        row("WLTP-rækkevidde", range),
        row("Brændstoføkonomi", fuelEfficiency),
      ],
    },
    {
      key: "source",
      title: "Udbyder og kilde",
      rows: [
        row("Udbyder", (offer) => textValue(providerName(dataset, offer))),
        row("Aktuel kilde", (offer) => ({
          detail: (
            <a
              className="inline-flex items-center gap-1.5 font-bold text-primary underline-offset-4 hover:underline"
              href={offer.canonicalOfferUrl}
              rel="noreferrer"
              target="_blank"
            >
              Tjek pris og vilkår
              <ExternalLink aria-hidden="true" className="size-3.5" />
            </a>
          ),
          key: offer.canonicalOfferUrl,
          text: offer.canonicalOfferUrl,
        })),
      ],
    },
  ];
}

function rowDiffers(row: ComparisonRow) {
  return new Set(row.values.map((value) => value.key)).size > 1;
}

function rowNeedsAttention(row: ComparisonRow) {
  return rowDiffers(row) || row.values.some((value) => value.unavailable);
}

function OfferHeader({
  offer,
  search,
}: {
  offer: CatalogueOffer;
  search: ComparisonSearch;
}) {
  return (
    <Link
      className="block h-full bg-card p-3 font-serif text-lg leading-tight underline-offset-4 hover:bg-accent hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring sm:p-4"
      params={{ offerIdentity: offer.offerIdentity }}
      search={{
        selected: search.selected,
        shell: search.shell,
        variant: "c",
      }}
      to="/prototype/offers/$offerIdentity"
    >
      {vehicleName(offer)}
    </Link>
  );
}

function ComparisonHeader({
  offers,
  search,
}: {
  offers: CatalogueOffer[];
  search: ComparisonSearch;
}) {
  const gridTemplateColumns = `clamp(8.5rem, 14vw, 12rem) repeat(${offers.length}, minmax(15rem, 1fr))`;
  return (
    <div
      className="grid w-full border-b bg-card shadow-[0_8px_18px_-18px_rgba(0,0,0,0.8)]"
      style={{ gridTemplateColumns }}
    >
      <div
        aria-hidden="true"
        className="sticky left-0 z-40 border-r bg-secondary"
      />
      {offers.map((offer) => (
        <div className="border-r last:border-r-0" key={offer.offerIdentity}>
          <OfferHeader offer={offer} search={search} />
        </div>
      ))}
    </div>
  );
}

function ComparisonRowView({
  offers,
  row,
  quiet = false,
}: {
  offers: CatalogueOffer[];
  quiet?: boolean;
  row: ComparisonRow;
}) {
  const differs = rowDiffers(row);
  const gridTemplateColumns = `clamp(8.5rem, 14vw, 12rem) repeat(${offers.length}, minmax(15rem, 1fr))`;
  return (
    <div
      className="grid w-full border-b last:border-b-0"
      style={{ gridTemplateColumns }}
    >
      <div className="sticky left-0 z-10 border-r bg-card p-3 text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground sm:p-4">
        {row.label}
      </div>
      {row.sharedDetail !== undefined ? (
        <div
          className={cn(
            "min-w-0",
            differs && !quiet && "bg-secondary/35",
          )}
          style={{ gridColumn: `2 / span ${offers.length}` }}
        >
          {row.sharedDetail}
        </div>
      ) : (
        row.values.map((value, index) => (
          <div
            className={cn(
              "min-w-0 border-r p-3 text-sm leading-6 last:border-r-0 sm:p-4",
              differs && !quiet && "bg-secondary/35",
              value.muted && "text-muted-foreground",
            )}
            key={offers[index].offerIdentity}
          >
            {value.detail ?? value.text}
          </div>
        ))
      )}
    </div>
  );
}

function SectionBlock({
  offers,
  section,
  quiet,
}: {
  offers: CatalogueOffer[];
  quiet?: boolean;
  section: ComparisonSection;
}) {
  return (
    <section aria-labelledby={`section-${section.key}`}>
      <div className="sticky left-0 z-10 border-b bg-foreground px-4 py-3 text-background">
        <h2 className="font-serif text-lg" id={`section-${section.key}`}>
          {section.title}
        </h2>
      </div>
      {section.rows.map((row) => (
        <ComparisonRowView
          key={row.label}
          offers={offers}
          quiet={quiet}
          row={row}
        />
      ))}
    </section>
  );
}

function ComparisonViewport({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div
      className="min-w-0 max-w-full overflow-hidden rounded-2xl border bg-card shadow-sm"
      style={{ contain: "layout paint" }}
    >
      <div
        aria-label="Side om side-sammenligning af leasingtilbud"
        className="overflow-x-auto"
        role="region"
        tabIndex={0}
      >
        {children}
      </div>
    </div>
  );
}

function PageComparisonViewport({
  children,
  header,
}: {
  children: ReactNode;
  header: ReactNode;
}) {
  const headerScrollRef = useRef<HTMLDivElement>(null);
  const syncHeaderScroll = (event: UIEvent<HTMLDivElement>) => {
    if (headerScrollRef.current === null) return;
    headerScrollRef.current.scrollLeft = event.currentTarget.scrollLeft;
  };

  return (
    <section
      aria-label="Side om side-sammenligning af leasingtilbud"
      className="min-w-0 max-w-full rounded-2xl border bg-card shadow-sm"
    >
      <div
        className="sticky top-0 z-30 overflow-hidden rounded-t-2xl bg-card"
        ref={headerScrollRef}
      >
        {header}
      </div>
      <div
        aria-label="Sammenligningsfakta"
        className="overflow-x-auto rounded-b-2xl"
        onScroll={syncHeaderScroll}
        role="region"
        tabIndex={0}
      >
        {children}
      </div>
    </section>
  );
}

function AddOfferControl({
  addOffer,
  dataset,
  selected,
}: {
  addOffer: (offerIdentity: string) => void;
  dataset: CatalogueDataset;
  selected: string[];
}) {
  const available = dataset.offers.filter(
    (offer) => !selected.includes(offer.offerIdentity),
  );
  return (
    <label className="flex min-w-0 items-center gap-2 rounded-xl border bg-card p-1.5 pl-3 text-sm font-bold shadow-sm">
      <Plus aria-hidden="true" className="size-4 shrink-0 text-primary" />
      <span className="sr-only">Tilføj tilbud</span>
      <select
        className="h-9 min-w-0 flex-1 bg-transparent pr-2 outline-none"
        onChange={(event) => {
          if (event.target.value !== "") addOffer(event.target.value);
          event.target.value = "";
        }}
        value=""
      >
        <option value="">Tilføj et tilbud…</option>
        {available.map((offer) => (
          <option key={offer.offerIdentity} value={offer.offerIdentity}>
            {vehicleName(offer)} · {providerName(dataset, offer)} ·{" "}
            {leasingLabels[offer.leasingForm]} · {offer.termMonths} mdr.
          </option>
        ))}
      </select>
    </label>
  );
}

function PageFrame({
  addOffer,
  children,
  dataset,
  search,
}: {
  addOffer: (offerIdentity: string) => void;
  children: ReactNode;
  dataset: CatalogueDataset;
  search: ComparisonSearch;
}) {
  return (
    <div className="min-h-screen pb-32">
      <header className="border-b bg-background">
        <div className="mx-auto grid max-w-[96rem] items-center gap-3 px-3 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(18rem,28rem)] sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <Link
              aria-label="Tilbage til leasingtilbud"
              className="grid size-9 shrink-0 place-content-center rounded-full border bg-card text-primary shadow-sm hover:bg-accent"
              search={{
                form: "all",
                power: "all",
                provider: "all",
                q: "",
                selected: search.selected,
                shell: search.shell,
                sort: "source",
                variant: "d",
              }}
              to="/catalogue"
            >
              <ArrowLeft aria-hidden="true" className="size-4" />
            </Link>
            <h1 className="font-serif text-2xl leading-none sm:text-3xl">
              Sammenlign tilbud
            </h1>
          </div>
          <AddOfferControl
            addOffer={addOffer}
            dataset={dataset}
            selected={search.selected}
          />
        </div>
      </header>

      <main className="mx-auto max-w-[96rem] px-3 py-3 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  );
}

type VariantProps = {
  addOffer: (offerIdentity: string) => void;
  dataset: CatalogueDataset;
  offers: CatalogueOffer[];
  search: ComparisonSearch;
  sections: ComparisonSection[];
};

function VariantA({
  addOffer,
  dataset,
  offers,
  search,
  sections,
}: VariantProps) {
  return (
    <PageFrame
      addOffer={addOffer}
      dataset={dataset}
      search={search}
    >
      <PageComparisonViewport
        header={
          <ComparisonHeader
            offers={offers}
            search={search}
          />
        }
      >
        {sections.map((section) => (
          <SectionBlock key={section.key} offers={offers} section={section} />
        ))}
      </PageComparisonViewport>
    </PageFrame>
  );
}

function VariantB({
  addOffer,
  dataset,
  offers,
  search,
  sections,
}: VariantProps) {
  const byKey = new Map(sections.map((section) => [section.key, section]));
  const order = ["end", "money", "cashflow", "agreement", "vehicle", "source"];
  return (
    <PageFrame
      addOffer={addOffer}
      dataset={dataset}
      search={search}
    >
      <div className="grid gap-6">
        <ComparisonViewport>
          <ComparisonHeader
            offers={offers}
            search={search}
          />
        </ComparisonViewport>
        {order.map((key, index) => {
          const section = byKey.get(key);
          if (section === undefined) return null;
          const icons = [
            ShieldQuestion,
            ReceiptText,
            CalendarRange,
            Scale,
            CarFront,
            ExternalLink,
          ];
          const Icon = icons[index];
          return (
            <div className="rounded-2xl border bg-card/55 p-2 shadow-sm sm:p-3" key={key}>
              <div className="flex items-center gap-3 px-2 py-3 sm:px-3">
                <span className="grid size-9 place-content-center rounded-full bg-primary text-primary-foreground">
                  <Icon aria-hidden="true" className="size-4" />
                </span>
                <div>
                  <p className="text-[0.65rem] font-bold uppercase tracking-[0.14em] text-muted-foreground">
                    Fase {index + 1}
                  </p>
                  <h2 className="font-serif text-2xl">{section.title}</h2>
                </div>
              </div>
              <ComparisonViewport>
                {section.rows.map((row) => (
                  <ComparisonRowView key={row.label} offers={offers} row={row} />
                ))}
              </ComparisonViewport>
            </div>
          );
        })}
      </div>
    </PageFrame>
  );
}

function VariantC({
  addOffer,
  dataset,
  offers,
  search,
  sections,
}: VariantProps) {
  const rows = sections.flatMap((section) =>
    section.rows.map((row) => ({ ...row, section: section.title })),
  );
  const attention = rows.filter(rowNeedsAttention);
  const common = rows.filter((row) => !rowNeedsAttention(row));
  return (
    <PageFrame
      addOffer={addOffer}
      dataset={dataset}
      search={search}
    >
      <div className="grid items-start gap-6 lg:grid-cols-[15rem_minmax(0,1fr)]">
        <aside className="rounded-2xl border bg-card p-5 lg:sticky lg:top-5">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Registerstatus
          </p>
          <p className="mt-2 font-serif text-4xl">{attention.length}</p>
          <p className="text-sm text-muted-foreground">
            rækker med forskelle eller usikkerhed
          </p>
          <div className="mt-5 grid gap-2 text-xs">
            <p className="flex items-center gap-2 font-bold">
              <CircleAlert aria-hidden="true" className="size-4 text-primary" />
              {rows.filter((row) => row.values.some((value) => value.unavailable)).length} med ukendte fakta
            </p>
            <p className="flex items-center gap-2 font-bold">
              <Scale aria-hidden="true" className="size-4 text-primary" />
              {common.length} ens rækker
            </p>
          </div>
          <p className="mt-5 border-t pt-4 text-xs leading-5 text-muted-foreground">
            “Ikke relevant” er en faktatilstand, ikke en mangel og aldrig et nul.
          </p>
        </aside>

        <div className="grid gap-6">
          <ComparisonViewport>
            <ComparisonHeader
              offers={offers}
              search={search}
            />
          </ComparisonViewport>

          <section>
            <div className="mb-3 flex items-center gap-2">
              <CircleAlert aria-hidden="true" className="size-5 text-primary" />
              <h2 className="font-serif text-2xl">Forskelle og usikkerhed</h2>
            </div>
            <ComparisonViewport>
              {attention.map((row) => (
                <ComparisonRowView key={`${row.section}-${row.label}`} offers={offers} row={row} />
              ))}
            </ComparisonViewport>
          </section>

          {common.length > 0 && (
            <section>
              <div className="mb-3 flex items-center gap-2">
                <Badge variant="secondary">Fælles</Badge>
                <h2 className="font-serif text-2xl">Samme på tværs</h2>
              </div>
              <ComparisonViewport>
                {common.map((row) => (
                  <ComparisonRowView
                    key={`${row.section}-${row.label}`}
                    offers={offers}
                    quiet
                    row={row}
                  />
                ))}
              </ComparisonViewport>
            </section>
          )}
        </div>
      </div>
    </PageFrame>
  );
}

function EmptyComparison({
  addOffer,
  dataset,
  search,
}: {
  addOffer: (offerIdentity: string) => void;
  dataset: CatalogueDataset;
  search: ComparisonSearch;
}) {
  return (
    <PageFrame
      addOffer={addOffer}
      dataset={dataset}
      search={search}
    >
      <div className="grid min-h-72 place-content-center rounded-2xl border border-dashed bg-card text-center">
        <Plus aria-hidden="true" className="mx-auto size-8 text-primary" />
        <p className="mt-3 font-serif text-2xl">Sammenligningen er tom</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Brug feltet ovenfor eller gå tilbage til kataloget.
        </p>
      </div>
    </PageFrame>
  );
}

export function SelectedOfferComparisonPrototype({
  dataset,
  search,
}: {
  dataset: CatalogueDataset;
  search: ComparisonSearch;
}) {
  const navigate = useNavigate({ from: "/prototype/compare" });
  const patchSearch: PatchSearch = (patch) => {
    void navigate({ search: (previous) => ({ ...previous, ...patch }) });
  };
  const selected = [...new Set(search.selected)];
  const offers = selected
    .map((offerIdentity) =>
      dataset.offers.find((offer) => offer.offerIdentity === offerIdentity),
    )
    .filter((offer): offer is CatalogueOffer => offer !== undefined);
  const addOffer = (offerIdentity: string) => {
    if (selected.includes(offerIdentity)) return;
    patchSearch({ selected: [...selected, offerIdentity] });
  };
  if (offers.length === 0) {
    return (
      <>
        <EmptyComparison
          addOffer={addOffer}
          dataset={dataset}
          search={search}
        />
        <PrototypeSwitcher
          current={search.variant}
          onChange={(variant) => patchSearch({ variant })}
          variants={variants}
        />
      </>
    );
  }

  const sections = comparisonSections(dataset, offers);
  const props = {
    addOffer,
    dataset,
    offers,
    search,
    sections,
  };

  return (
    <>
      {search.variant === "a" && <VariantA {...props} />}
      {search.variant === "b" && <VariantB {...props} />}
      {search.variant === "c" && <VariantC {...props} />}
      <PrototypeSwitcher
        current={search.variant}
        onChange={(variant) => patchSearch({ variant })}
        variants={variants}
      />
    </>
  );
}
