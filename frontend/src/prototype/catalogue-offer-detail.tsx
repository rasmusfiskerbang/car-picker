// PROTOTYPE — three Catalogue Offer detail variants, switchable via ?variant=,
// on the throwaway /prototype/offers/$offerIdentity route.
import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  ArrowUpRight,
  CalendarDays,
  CarFront,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  ExternalLink,
  ImageOff,
  Info,
  ReceiptText,
  Route as RouteIcon,
  ShieldCheck,
  WalletCards,
  X,
} from "lucide-react";
import { useState } from "react";

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
import { Area } from "@/components/charts/area";
import { AreaChart } from "@/components/charts/area-chart";
import { ComposedChart } from "@/components/charts/composed-chart";
import { Grid } from "@/components/charts/grid";
import { Line } from "@/components/charts/line";
import { SeriesBar } from "@/components/charts/series-bar";
import { ChartTooltip } from "@/components/charts/tooltip/chart-tooltip";
import {
  TooltipContent,
  type TooltipRow,
} from "@/components/charts/tooltip/tooltip-content";
import { YAxis } from "@/components/charts/y-axis";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { PrototypeSwitcher } from "@/prototype/prototype-switcher";
import type { OfferDetailSearch } from "@/routes/prototype.offers.$offerIdentity";

const currency = new Intl.NumberFormat("da-DK", {
  currency: "DKK",
  maximumFractionDigits: 0,
  style: "currency",
});
const decimal = new Intl.NumberFormat("da-DK", { maximumFractionDigits: 1 });
const integer = new Intl.NumberFormat("da-DK");
const date = new Intl.DateTimeFormat("da-DK", {
  day: "numeric",
  month: "long",
  year: "numeric",
});
const chartDate = new Intl.DateTimeFormat("da-DK", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

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

const serviceLabels = {
  included: "Inkluderet",
  optional: "Valgfrit tilkøb",
  required_external: "Skal købes eksternt",
  excluded: "Ikke inkluderet",
} as const;

const variants = [
  { key: "a", name: "Visuelt dossier" },
  { key: "b", name: "Aftalens forløb" },
  { key: "c", name: "Kompakt faktaark" },
] as const;

type PatchSearch = (patch: Partial<OfferDetailSearch>) => void;

function money(value: number | null) {
  return value === null ? "Kan ikke beregnes" : currency.format(value);
}

function unavailableText(state: Exclude<OfferFact["state"], "known">) {
  const labels = {
    not_stated: "Ikke oplyst",
    unclear: "Uklart oplyst",
    conflicting: "Modstridende oplysninger",
    not_applicable: "Ikke relevant",
  } as const;
  return labels[state];
}

function factText<T>(fact: OfferFact, format: (value: T) => string) {
  if (fact.state !== "known") return unavailableText(fact.state);
  return format(fact.value as T);
}

function providerFor(dataset: CatalogueDataset, offer: CatalogueOffer) {
  return dataset.providers.find((provider) => provider.id === offer.providerId);
}

function Masthead({
  generatedAt,
  selected,
}: {
  generatedAt: string;
  selected: string[];
}) {
  return (
    <header className="border-b border-border/80 bg-background/90 backdrop-blur">
      <div className="mx-auto flex max-w-[92rem] items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <Link
          className="flex items-center gap-3"
          search={{
            form: "all",
            power: "all",
            provider: "all",
            q: "",
            selected,
            sort: "source",
            variant: "d",
          }}
          to="/catalogue"
        >
          <span className="grid size-9 place-content-center rounded-full bg-primary text-primary-foreground">
            <CarFront aria-hidden="true" className="size-5" />
          </span>
          <span>
            <span className="block font-serif text-xl leading-none">Bilvalg</span>
            <span className="mt-1 block text-[0.68rem] font-bold uppercase tracking-[0.16em] text-muted-foreground">
              Tilbudsprototype
            </span>
          </span>
        </Link>
        <p className="hidden text-right text-xs text-muted-foreground sm:block">
          Katalog samlet {date.format(new Date(generatedAt))}
          <br />
          Tilbuddet kan være ændret siden
        </p>
      </div>
    </header>
  );
}

function BackToCatalogue({ selected }: { selected: string[] }) {
  return (
    <Link
      className="inline-flex items-center gap-2 text-sm font-bold text-primary underline-offset-4 hover:underline"
      search={{
        form: "all",
        power: "all",
        provider: "all",
        q: "",
        selected,
        sort: "source",
        variant: "d",
      }}
      to="/catalogue"
    >
      <ArrowLeft aria-hidden="true" className="size-4" />
      Tilbage til leasingtilbud
    </Link>
  );
}

function OfferGallery({
  compact = false,
  offer,
}: {
  compact?: boolean;
  offer: CatalogueOffer;
}) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [failed, setFailed] = useState<Set<string>>(() => new Set());
  const current = offer.imageUrls[selectedIndex];
  const currentFailed = current === undefined || failed.has(current);

  const markFailed = (source: string) => {
    setFailed((previous) => new Set(previous).add(source));
  };

  if (offer.imageUrls.length === 0) {
    return (
      <div
        className={cn(
          "grid place-content-center rounded-2xl bg-secondary text-muted-foreground",
          compact ? "aspect-[16/9]" : "aspect-[16/10]",
        )}
      >
        <div className="grid justify-items-center gap-3 text-sm font-semibold">
          <ImageOff aria-hidden="true" className="size-9" />
          Ingen billeder tilgængelige
        </div>
      </div>
    );
  }

  const move = (direction: -1 | 1) => {
    setSelectedIndex(
      (selectedIndex + direction + offer.imageUrls.length) %
        offer.imageUrls.length,
    );
  };

  return (
    <section aria-label="Billeder af bilen" className="grid gap-3">
      <div
        className={cn(
          "group relative overflow-hidden rounded-2xl bg-secondary",
          compact ? "aspect-[16/9]" : "aspect-[16/10]",
        )}
      >
        {currentFailed ? (
          <div className="grid size-full place-content-center text-muted-foreground">
            <div className="grid justify-items-center gap-2 text-sm font-semibold">
              <ImageOff aria-hidden="true" className="size-9" />
              Billedet kunne ikke vises
            </div>
          </div>
        ) : (
          <img
            alt=""
            className="size-full object-cover"
            onError={() => markFailed(current)}
            referrerPolicy="no-referrer"
            src={current}
          />
        )}
        <div className="absolute inset-x-3 bottom-3 flex items-center justify-between">
          <Button
            aria-label="Forrige billede"
            className="rounded-full bg-card/90 backdrop-blur hover:bg-card"
            onClick={() => move(-1)}
            size="icon"
            variant="outline"
          >
            <ChevronLeft aria-hidden="true" />
          </Button>
          <span className="rounded-full bg-foreground/85 px-3 py-1.5 text-xs font-bold text-background backdrop-blur">
            {selectedIndex + 1} / {offer.imageUrls.length}
          </span>
          <Button
            aria-label="Næste billede"
            className="rounded-full bg-card/90 backdrop-blur hover:bg-card"
            onClick={() => move(1)}
            size="icon"
            variant="outline"
          >
            <ChevronRight aria-hidden="true" />
          </Button>
        </div>
      </div>
      <div className="grid grid-cols-4 gap-2">
        {offer.imageUrls.map((source, index) => (
          <button
            aria-label={`Vis billede ${index + 1} af ${offer.imageUrls.length}`}
            className={cn(
              "aspect-[4/3] overflow-hidden rounded-lg border-2 bg-secondary",
              selectedIndex === index
                ? "border-primary"
                : "border-transparent opacity-75 hover:opacity-100",
            )}
            key={source}
            onClick={() => setSelectedIndex(index)}
            type="button"
          >
            {failed.has(source) ? (
              <ImageOff aria-hidden="true" className="m-auto size-5" />
            ) : (
              <img
                alt=""
                className="size-full object-cover"
                loading="lazy"
                onError={() => markFailed(source)}
                referrerPolicy="no-referrer"
                src={source}
              />
            )}
          </button>
        ))}
      </div>
      <p className="text-xs leading-5 text-muted-foreground">
        Billederne følger udbyderens rækkefølge og kan være vejledende. Tjek den
        præcise konfiguration hos udbyderen.
      </p>
    </section>
  );
}

function ComparisonControl({
  offer,
  search,
  toggleSelected,
}: {
  offer: CatalogueOffer;
  search: OfferDetailSearch;
  toggleSelected: () => void;
}) {
  const selected = search.selected.includes(offer.offerIdentity);
  return (
    <label className="flex cursor-pointer items-center gap-3 rounded-xl border bg-background px-4 py-3 text-sm font-bold">
      <Checkbox
        aria-label={`${selected ? "Fjern" : "Vælg"} ${vehicleName(offer)} til sammenligning`}
        checked={selected}
        onCheckedChange={toggleSelected}
      />
      <span className="flex-1">
        {selected ? "Valgt til sammenligning" : "Vælg til sammenligning"}
      </span>
      {selected && <Check aria-hidden="true" className="size-4 text-primary" />}
    </label>
  );
}

function UnavailableNotice() {
  return (
    <span className="inline-flex items-center gap-1.5 text-muted-foreground">
      <CircleHelp aria-hidden="true" className="size-3.5" />
      Oplysningen er ikke sikker
    </span>
  );
}

function Definition({
  label,
  unavailable = false,
  value,
}: {
  label: string;
  unavailable?: boolean;
  value: string;
}) {
  return (
    <div className="min-w-0 border-b border-border/70 py-3 last:border-b-0">
      <dt className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
        {label}
      </dt>
      <dd
        className={cn(
          "mt-1 text-sm font-semibold leading-5",
          unavailable && "text-muted-foreground",
        )}
      >
        {value}
      </dd>
    </div>
  );
}

function PriceSummary({ offer }: { offer: CatalogueOffer }) {
  const advertised = factText<number>(offer.advertisedTotalDkk, money);
  return (
    <div className="grid gap-4">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
          Udbyderens månedsydelse
        </p>
        <p className="mt-1 font-serif text-4xl tracking-[-0.04em]">
          {money(monthlyPayment(offer))}
          {monthlyPayment(offer) !== null && (
            <span className="ml-1 font-sans text-sm tracking-normal text-muted-foreground">
              / md.
            </span>
          )}
        </p>
      </div>
      <dl className="grid grid-cols-2 gap-x-5 rounded-xl bg-secondary/60 px-4 py-2">
        <Definition label="Betaling ved start" value={money(upfrontPayment(offer))} />
        <Definition label="Beregnet i alt" value={money(offer.totalDkk)} />
        <Definition label="Udbyderens total" value={advertised} />
        <Definition label="Beregnet pr. måned" value={money(offer.totalDkkPerMonth)} />
      </dl>
      <p className="flex gap-2 text-xs leading-5 text-muted-foreground">
        <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        Beregnede beløb summerer kun den normale aftales betalingsstrøm.
        Betingede udgifter er ikke med og værdierne er derfor ikke en samlet
        ejeromkostning.
      </p>
    </div>
  );
}

function VehicleFacts({ offer }: { offer: CatalogueOffer }) {
  const spec = offer.vehicleSpecification;
  const shared = [
    { label: "Mærke", value: spec.make },
    { label: "Model", value: spec.model },
    {
      label: "Variant",
      value: factText<string>(spec.trim, String),
      unavailable: spec.trim.state !== "known",
    },
    {
      label: "Modelår",
      value: factText<number>(spec.modelYear, String),
      unavailable: spec.modelYear.state !== "known",
    },
    {
      label: "Første registrering",
      value: factText<number>(spec.firstRegistrationYear, String),
      unavailable: spec.firstRegistrationYear.state !== "known",
    },
    {
      label: "Karrosseri",
      value: factText<keyof typeof bodyStyleLabels>(
        spec.bodyStyle,
        (value) => bodyStyleLabels[value],
      ),
      unavailable: spec.bodyStyle.state !== "known",
    },
    {
      label: "Kilometerstand",
      value: factText<number>(
        spec.odometerKm,
        (value) => `${integer.format(value)} km`,
      ),
      unavailable: spec.odometerKm.state !== "known",
    },
  ];

  const powerFacts =
    spec.kind === "battery_electric"
      ? [
          { label: "Drivlinje", value: "Elbil" },
          {
            label: "Batteri",
            value: factText<{ valueKwh: number; basis: string }>(
              spec.batteryCapacity,
              ({ basis, valueKwh }) =>
                `${decimal.format(valueKwh)} kWh (${basis === "usable" ? "netto" : basis === "gross" ? "brutto" : "basis ikke oplyst"})`,
            ),
            unavailable: spec.batteryCapacity.state !== "known",
          },
          {
            label: "WLTP-rækkevidde",
            value: factText<number>(
              spec.wltpRangeKm,
              (value) => `${integer.format(value)} km`,
            ),
            unavailable: spec.wltpRangeKm.state !== "known",
          },
          {
            label: "Maks. ladeeffekt",
            value: factText<{ valueKw: number; kind: string }>(
              spec.maxChargingPower,
              ({ kind, valueKw }) =>
                `${decimal.format(valueKw)} kW${kind === "not_stated" ? "" : ` ${kind.toUpperCase()}`}`,
            ),
            unavailable: spec.maxChargingPower.state !== "known",
          },
          {
            label: "Ladetid 10–80 %",
            value: factText<number>(
              spec.chargingTime10To80Minutes,
              (value) => `${decimal.format(value)} min.`,
            ),
            unavailable: spec.chargingTime10To80Minutes.state !== "known",
          },
        ]
      : [
          {
            label: "Drivlinje",
            value: spec.fuelType === "diesel" ? "Diesel" : "Benzin",
          },
          {
            label: "Brændstoføkonomi",
            value: factText<number>(
              spec.fuelEfficiencyKmPerLiter,
              (value) => `${decimal.format(value)} km/l`,
            ),
            unavailable: spec.fuelEfficiencyKmPerLiter.state !== "known",
          },
        ];

  return (
    <dl className="grid grid-cols-2 gap-x-6 sm:grid-cols-3">
      {[...shared, ...powerFacts].map((fact) => (
        <Definition key={fact.label} {...fact} />
      ))}
    </dl>
  );
}

function ContractFacts({ offer }: { offer: CatalogueOffer }) {
  return (
    <dl className="grid grid-cols-2 gap-x-6 sm:grid-cols-3">
      <Definition label="Leasingform" value={leasingLabels[offer.leasingForm]} />
      <Definition label="Aftaleperiode" value={`${offer.termMonths} måneder`} />
      <Definition
        label="Årligt kilometertal"
        unavailable={offer.annualMileageKm.state !== "known"}
        value={factText<number>(
          offer.annualMileageKm,
          (value) => `${integer.format(value)} km/år`,
        )}
      />
      <Definition
        label="Ved normalt udløb"
        unavailable={offer.normalEndMechanism.state !== "known"}
        value={endMechanism(offer)}
      />
      <Definition
        label="Restværdirisiko"
        unavailable={offer.residualRiskAllocation.state !== "known"}
        value={riskAllocation(offer)}
      />
    </dl>
  );
}

function ServiceFacts({ offer }: { offer: CatalogueOffer }) {
  if (offer.serviceArrangements.state !== "known") {
    return (
      <div className="rounded-xl bg-secondary/55 p-4 text-sm">
        <p className="font-bold">
          {unavailableText(offer.serviceArrangements.state)}
        </p>
        <p className="mt-1 text-muted-foreground">
          Kataloget kan ikke fastslå, hvad aftalen inkluderer af service og
          øvrige ordninger.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-3">
      {offer.serviceArrangements.value.map((arrangement) => (
        <div className="rounded-xl border bg-background p-4" key={arrangement.category}>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{serviceLabels[arrangement.treatment]}</Badge>
            <p className="font-bold">{arrangement.summary}</p>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Begrænsninger: {factText<string>(arrangement.limits, String)}
          </p>
        </div>
      ))}
    </div>
  );
}

type CashFlowChartPoint = Record<string, unknown> & {
  cumulative?: number;
  date: Date;
  eventCount: number;
  label: string;
  month: number;
  payments: number;
  receipts: number;
  unavailableCount: number;
};

function cashFlowChartData(offer: CatalogueOffer): CashFlowChartPoint[] {
  let cumulative = 0;
  let cumulativeAvailable = true;
  const startDate = new Date();
  startDate.setHours(12, 0, 0, 0);

  return Array.from({ length: offer.termMonths + 1 }, (_, month) => {
    const events = offer.baseCashFlowStream.filter(
      (event) => event.occursAtMonth === month,
    );
    let payments = 0;
    let receipts = 0;
    let unavailableCount = 0;

    for (const event of events) {
      if (event.amount.state !== "known") {
        unavailableCount += 1;
        cumulativeAvailable = false;
        continue;
      }
      if (event.direction === "payment") payments += event.amount.value;
      if (event.direction === "receipt") receipts += event.amount.value;
    }

    if (cumulativeAvailable) cumulative += payments - receipts;
    const pointDate = new Date(
      startDate.getFullYear(),
      startDate.getMonth() + month + 1,
      0,
      12,
    );
    pointDate.setDate(Math.min(startDate.getDate(), pointDate.getDate()));
    const formattedDate = chartDate.format(pointDate);

    return {
      cumulative: cumulativeAvailable ? cumulative : undefined,
      date: pointDate,
      eventCount: events.length,
      label:
        month === 0
          ? `Ved start · ${formattedDate}`
          : month === offer.termMonths
            ? `Ved udløb · ${formattedDate}`
            : `${formattedDate} · måned ${month}`,
      month,
      payments,
      receipts,
      unavailableCount,
    };
  });
}

function cashFlowTooltipRows(point: Record<string, unknown>): TooltipRow[] {
  const rows: TooltipRow[] = [];
  const payments = point.payments;
  const receipts = point.receipts;
  const cumulative = point.cumulative;
  const unavailableCount = point.unavailableCount;

  if (typeof payments === "number" && payments > 0) {
    rows.push({
      color: "var(--chart-2)",
      label: "Betalinger",
      value: money(payments),
    });
  }
  if (typeof receipts === "number" && receipts > 0) {
    rows.push({
      color: "var(--chart-3)",
      label: "Modtagelser",
      value: money(receipts),
    });
  }
  if (typeof cumulative === "number") {
    rows.push({
      color: "var(--chart-1)",
      label: "Akkumuleret netto",
      value: money(cumulative),
    });
  }
  if (typeof unavailableCount === "number" && unavailableCount > 0) {
    rows.push({
      color: "var(--muted-foreground)",
      label: "Beløb ikke tilgængeligt",
      value: `${unavailableCount} ${unavailableCount === 1 ? "post" : "poster"}`,
    });
  }
  return rows;
}

function CashFlowTooltip({ point }: { point: Record<string, unknown> }) {
  return (
    <TooltipContent
      rows={cashFlowTooltipRows(point)}
      title={String(point.label)}
    />
  );
}

function dkkAxis(value: number) {
  if (value === 0) return "0";
  if (Math.abs(value) >= 1_000) {
    return `${decimal.format(value / 1_000)} t.`;
  }
  return integer.format(value);
}

function ContractDateAxis({
  data,
  leftMargin,
  rightMargin,
  termMonths,
}: {
  data: CashFlowChartPoint[];
  leftMargin: number;
  rightMargin: number;
  termMonths: number;
}) {
  const points = [
    0,
    Math.round(termMonths / 3),
    Math.round((termMonths * 2) / 3),
    termMonths,
  ].map((month) => data[month]);

  return (
    <div
      className="mt-2 grid grid-cols-2 gap-2 text-[0.68rem] font-semibold text-muted-foreground sm:grid-cols-4"
      style={{ paddingLeft: leftMargin, paddingRight: rightMargin }}
    >
      {points.map((point, index) => (
        <span
          className={cn(
            index > 0 &&
              index < points.length - 1 &&
              "hidden text-center sm:block",
            index === points.length - 1 && "text-right",
          )}
          key={point.month}
        >
          {chartDate.format(point.date)}
        </span>
      ))}
    </div>
  );
}

function CashFlowLegend({ showCumulative = true }: { showCumulative?: boolean }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs font-semibold text-muted-foreground">
      <span className="inline-flex items-center gap-2">
        <span className="size-2.5 rounded-sm bg-[var(--chart-2)]" /> Betalinger
      </span>
      <span className="inline-flex items-center gap-2">
        <span className="size-2.5 rounded-sm bg-[var(--chart-3)]" /> Modtagelser
      </span>
      {showCumulative && (
        <span className="inline-flex items-center gap-2">
          <span className="h-0.5 w-4 bg-[var(--chart-1)]" /> Akkumuleret netto
        </span>
      )}
    </div>
  );
}

function AccessibleCashFlow({ offer }: { offer: CatalogueOffer }) {
  return (
    <ol className="sr-only">
      {offer.baseCashFlowStream.map((event) => {
        const amount = factText<number>(event.amount, money);
        return (
          <li key={event.key}>
            {event.occursAtMonth === 0
              ? "Ved start"
              : `Måned ${event.occursAtMonth}`}
            : {cashFlowLabels[event.kind]}; {event.direction === "payment" ? "betaling" : "modtagelse"}; {amount}.
          </li>
        );
      })}
    </ol>
  );
}

function CashFlowSection({
  mode,
  offer,
}: {
  mode: "cumulative" | "composed" | "compact";
  offer: CatalogueOffer;
}) {
  const data = cashFlowChartData(offer);
  const unavailableCount = data.reduce(
    (total, point) => total + point.unavailableCount,
    0,
  );
  const totalReceipts = data.reduce(
    (total, point) => total + point.receipts,
    0,
  );
  const compact = mode === "compact";
  const chartDescription = compact
    ? "Søjlerne viser betalinger og modtagelser på deres faktiske datoer."
    : "Søjler viser månedens strøm. Kurven viser det akkumulerede nettoudlæg, hvor alle nødvendige beløb er tilgængelige.";
  const chartMargin = {
    bottom: 12,
    left: compact ? 66 : 64,
    right: mode === "composed" ? 66 : 24,
    top: 20,
  };

  return (
    <section aria-labelledby="cash-flow-heading">
      <div className="flex items-start justify-between gap-5">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary">
            Normal gennemførelse
          </p>
          <h2 id="cash-flow-heading" className="mt-1 font-serif text-3xl">
            {mode === "cumulative"
              ? "Sådan vokser nettoudlægget"
              : mode === "composed"
                ? "Aftalens betalingsforløb"
                : "Betalingsforløbet"}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            {chartDescription}
          </p>
        </div>
        <Badge className="hidden shrink-0 sm:inline-flex" variant="outline">
          {offer.baseCashFlowStream.length} poster
        </Badge>
      </div>

      <Card className="mt-5 overflow-hidden p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CashFlowLegend showCumulative={mode !== "compact"} />
          <p className="text-xs text-muted-foreground">
            Hold eller tryk på grafen for månedens beløb
          </p>
        </div>
        <div className="mt-3" data-testid={`bklit-cash-flow-${mode}`}>
          {mode === "cumulative" ? (
            <AreaChart
              aspectRatio={compact ? "3 / 2" : "2 / 1"}
              data={data}
              margin={chartMargin}
              xDataKey="date"
            >
              <Grid horizontal numTicksRows={4} />
              <Area
                dataKey="cumulative"
                fill="var(--chart-1)"
                fillOpacity={0.24}
                stroke="var(--chart-1)"
                strokeWidth={3}
              />
              <YAxis formatValue={dkkAxis} numTicks={compact ? 3 : 4} />
              <ChartTooltip
                content={({ point }) => <CashFlowTooltip point={point} />}
                showDatePill={false}
              />
            </AreaChart>
          ) : (
            <ComposedChart
              aspectRatio={compact ? "3 / 2" : "2 / 1"}
              barGap={2}
              data={data}
              margin={chartMargin}
              maxBarSize={compact ? 12 : 20}
              xDataKey="date"
            >
              <Grid horizontal numTicksRows={4} />
              <SeriesBar dataKey="receipts" fill="var(--chart-3)" radius={3} />
              <SeriesBar dataKey="payments" fill="var(--chart-2)" radius={3} />
              {mode === "composed" && (
                <Line
                  dataKey="cumulative"
                  fadeEdges={false}
                  stroke="var(--chart-1)"
                  strokeWidth={3}
                  yAxisId="cumulative"
                />
              )}
              <YAxis formatValue={dkkAxis} numTicks={compact ? 3 : 4} />
              {mode === "composed" && (
                <YAxis
                  formatValue={dkkAxis}
                  numTicks={4}
                  orientation="right"
                  yAxisId="cumulative"
                />
              )}
              <ChartTooltip
                content={({ point }) => <CashFlowTooltip point={point} />}
                showCrosshair={false}
                showDatePill={false}
              />
            </ComposedChart>
          )}
          <ContractDateAxis
            data={data}
            leftMargin={chartMargin.left}
            rightMargin={chartMargin.right}
            termMonths={offer.termMonths}
          />
        </div>
      </Card>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border bg-card p-4">
          <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
            Ved start
          </p>
          <p className="mt-1 font-serif text-xl">{money(upfrontPayment(offer))}</p>
        </div>
        <div className="rounded-xl border bg-card p-4">
          <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
            Modtagelser i strømmen
          </p>
          <p className="mt-1 font-serif text-xl">{money(totalReceipts)}</p>
        </div>
        <div className="rounded-xl border bg-card p-4">
          <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
            Beregnet ved udløb
          </p>
          <p className="mt-1 font-serif text-xl">{money(offer.totalDkk)}</p>
        </div>
      </div>

      {unavailableCount > 0 && (
        <p className="mt-4 flex gap-2 rounded-xl bg-secondary/60 p-4 text-sm text-muted-foreground">
          <CircleHelp aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {unavailableCount === 1
            ? "Ét beløb er ikke tilgængeligt."
            : `${unavailableCount} beløb er ikke tilgængelige.`}{" "}
          Den akkumulerede kurve stopper før det første ukendte beløb.
        </p>
      )}
      <AccessibleCashFlow offer={offer} />
    </section>
  );
}

function ProviderCard({
  dataset,
  offer,
}: {
  dataset: CatalogueDataset;
  offer: CatalogueOffer;
}) {
  const provider = providerFor(dataset, offer);
  return (
    <Card className="p-5">
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
        Udbyder og original kilde
      </p>
      <div className="mt-3 flex items-start justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl">{provider?.name ?? offer.providerId}</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Bilvalg viser normaliserede fakta. Den bindende og aktuelle
            beskrivelse findes altid hos udbyderen.
          </p>
        </div>
        <ShieldCheck aria-hidden="true" className="size-7 shrink-0 text-primary" />
      </div>
      <div className="mt-5 grid gap-2 sm:grid-cols-2">
        {provider !== undefined && (
          <a
            className={buttonVariants({ variant: "outline" })}
            href={provider.url}
            rel="noreferrer"
            target="_blank"
          >
            Udbyderens hjemmeside <ExternalLink aria-hidden="true" />
          </a>
        )}
        <a
          className={buttonVariants({ variant: "default" })}
          href={offer.canonicalOfferUrl}
          rel="noreferrer"
          target="_blank"
        >
          Se det præcise tilbud <ArrowUpRight aria-hidden="true" />
        </a>
      </div>
    </Card>
  );
}

function SectionHeading({
  eyebrow,
  id,
  title,
}: {
  eyebrow?: string;
  id?: string;
  title: string;
}) {
  return (
    <div>
      {eyebrow !== undefined && (
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary">
          {eyebrow}
        </p>
      )}
      <h2
        className={cn(eyebrow !== undefined && "mt-1", "font-serif text-3xl")}
        id={id}
      >
        {title}
      </h2>
    </div>
  );
}

type VariantProps = {
  dataset: CatalogueDataset;
  offer: CatalogueOffer;
  search: OfferDetailSearch;
  toggleSelected: () => void;
};

function VariantA({ dataset, offer, search, toggleSelected }: VariantProps) {
  return (
    <div>
      <Masthead generatedAt={dataset.generatedAt} selected={search.selected} />
      <main className="mx-auto max-w-[92rem] px-4 pb-36 pt-6 sm:px-6 lg:px-8 lg:pt-9">
        <BackToCatalogue selected={search.selected} />
        <div className="mt-6 grid items-start gap-8 lg:grid-cols-[minmax(0,1.35fr)_minmax(21rem,0.65fr)] xl:gap-12">
          <OfferGallery offer={offer} />
          <aside className="lg:sticky lg:top-6">
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">
                {providerFor(dataset, offer)?.name ?? offer.providerId}
              </Badge>
              <Badge variant="outline">{leasingLabels[offer.leasingForm]}</Badge>
            </div>
            <h1 className="mt-4 font-serif text-4xl leading-[0.98] tracking-[-0.04em] sm:text-5xl">
              {vehicleName(offer)}
            </h1>
            <p className="mt-4 text-sm leading-6 text-muted-foreground">
              Ét præcist katalogtilbud. Ukendte og uklare oplysninger vises i
              stedet for at blive gættet.
            </p>
            <Card className="mt-6 p-5">
              <PriceSummary offer={offer} />
              <Separator className="my-5" />
              <ComparisonControl
                offer={offer}
                search={search}
                toggleSelected={toggleSelected}
              />
            </Card>
          </aside>
        </div>

        <div className="mt-14 grid items-start gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(28rem,1.2fr)] xl:gap-14">
          <div className="grid gap-10">
            <section>
              <SectionHeading eyebrow="Bilen" title="Køretøjsspecifikation" />
              <div className="mt-5 rounded-2xl border bg-card px-5">
                <VehicleFacts offer={offer} />
              </div>
            </section>
            <section>
              <SectionHeading eyebrow="Aftalen" title="Leasing og kontrakt" />
              <div className="mt-5 rounded-2xl border bg-card px-5">
                <ContractFacts offer={offer} />
              </div>
              <div className="mt-5">
                <h3 className="mb-3 font-serif text-xl">Service og ordninger</h3>
                <ServiceFacts offer={offer} />
              </div>
            </section>
            <ProviderCard dataset={dataset} offer={offer} />
          </div>
          <CashFlowSection mode="cumulative" offer={offer} />
        </div>
      </main>
    </div>
  );
}

function TimelineSummary({ offer }: { offer: CatalogueOffer }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <div className="rounded-xl bg-secondary/60 p-4">
        <WalletCards aria-hidden="true" className="size-5 text-primary" />
        <p className="mt-3 text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
          Ved start
        </p>
        <p className="mt-1 font-serif text-2xl">{money(upfrontPayment(offer))}</p>
      </div>
      <div className="rounded-xl bg-secondary/60 p-4">
        <CalendarDays aria-hidden="true" className="size-5 text-primary" />
        <p className="mt-3 text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
          Undervejs
        </p>
        <p className="mt-1 font-serif text-2xl">
          {money(monthlyPayment(offer))} / md.
        </p>
      </div>
      <div className="rounded-xl bg-secondary/60 p-4">
        <ReceiptText aria-hidden="true" className="size-5 text-primary" />
        <p className="mt-3 text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
          Beregnet total
        </p>
        <p className="mt-1 font-serif text-2xl">{money(offer.totalDkk)}</p>
      </div>
      <div className="rounded-xl bg-secondary/60 p-4">
        <RouteIcon aria-hidden="true" className="size-5 text-primary" />
        <p className="mt-3 text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
          Ved udløb
        </p>
        <p className="mt-1 text-sm font-bold leading-5">{endMechanism(offer)}</p>
      </div>
    </div>
  );
}

function VariantB({ dataset, offer, search, toggleSelected }: VariantProps) {
  return (
    <div>
      <Masthead generatedAt={dataset.generatedAt} selected={search.selected} />
      <main className="mx-auto max-w-[100rem] px-4 pb-36 pt-6 sm:px-6 lg:px-8 lg:pt-9">
        <BackToCatalogue selected={search.selected} />
        <header className="mt-6 grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary">
              Aftalens forløb · {leasingLabels[offer.leasingForm]}
            </p>
            <h1 className="mt-2 font-serif text-4xl tracking-[-0.04em] sm:text-5xl">
              {vehicleName(offer)}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {providerFor(dataset, offer)?.name ?? offer.providerId} · {offer.termMonths} måneder
            </p>
          </div>
          <div className="min-w-72">
            <ComparisonControl
              offer={offer}
              search={search}
              toggleSelected={toggleSelected}
            />
          </div>
        </header>
        <div className="mt-7">
          <TimelineSummary offer={offer} />
        </div>

        <div className="mt-10 grid items-start gap-10 lg:grid-cols-[minmax(19rem,0.65fr)_minmax(34rem,1.35fr)] xl:gap-14">
          <aside className="grid gap-7 lg:sticky lg:top-6">
            <OfferGallery compact offer={offer} />
            <Card className="p-5">
              <h2 className="font-serif text-2xl">Aftalens nøglefakta</h2>
              <ContractFacts offer={offer} />
              <Separator className="my-5" />
              {offer.residualRiskAllocation.state !== "known" && (
                <UnavailableNotice />
              )}
            </Card>
            <ProviderCard dataset={dataset} offer={offer} />
          </aside>

          <div className="grid gap-12">
            <CashFlowSection mode="composed" offer={offer} />
            <section>
              <SectionHeading eyebrow="Bilen bag aftalen" title="Køretøjsspecifikation" />
              <div className="mt-5 rounded-2xl border bg-card px-5">
                <VehicleFacts offer={offer} />
              </div>
            </section>
            <section>
              <SectionHeading eyebrow="Inkluderet eller ej" title="Service og ordninger" />
              <div className="mt-5">
                <ServiceFacts offer={offer} />
              </div>
            </section>
            <section className="rounded-2xl border bg-card p-5">
              <SectionHeading eyebrow="Beløbsgrundlag" title="Udbyderens og beregnede totaler" />
              <div className="mt-5 max-w-xl">
                <PriceSummary offer={offer} />
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}

function VariantC({ dataset, offer, search, toggleSelected }: VariantProps) {
  return (
    <div>
      <Masthead generatedAt={dataset.generatedAt} selected={search.selected} />
      <main className="mx-auto max-w-[82rem] px-4 pb-36 pt-6 sm:px-6 lg:px-8 lg:pt-9">
        <BackToCatalogue selected={search.selected} />
        <Card className="mt-6 overflow-hidden">
          <div className="grid lg:grid-cols-[0.9fr_1.1fr]">
            <div className="bg-secondary p-4 sm:p-6">
              <OfferGallery compact offer={offer} />
            </div>
            <div className="grid content-between gap-7 p-5 sm:p-8">
              <div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="secondary">
                    {providerFor(dataset, offer)?.name ?? offer.providerId}
                  </Badge>
                  <Badge variant="outline">{leasingLabels[offer.leasingForm]}</Badge>
                </div>
                <h1 className="mt-4 font-serif text-4xl leading-none tracking-[-0.04em] sm:text-5xl">
                  {vehicleName(offer)}
                </h1>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  Faktaarket samler hele katalogposten uden vurdering eller
                  anbefaling.
                </p>
              </div>
              <PriceSummary offer={offer} />
              <ComparisonControl
                offer={offer}
                search={search}
                toggleSelected={toggleSelected}
              />
            </div>
          </div>
        </Card>

        <div className="mt-8 grid grid-cols-[minmax(0,1fr)] items-start gap-10 lg:grid-cols-[13rem_minmax(0,1fr)]">
          <nav className="hidden rounded-2xl border bg-card p-4 lg:sticky lg:top-6 lg:block" aria-label="Indhold">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">Indhold</p>
            <div className="mt-3 grid text-sm font-bold">
              <a className="border-b py-3 hover:text-primary" href="#vehicle">Bilen</a>
              <a className="border-b py-3 hover:text-primary" href="#contract">Aftalen</a>
              <a className="border-b py-3 hover:text-primary" href="#payments">Betalinger</a>
              <a className="py-3 hover:text-primary" href="#source">Udbyder og kilde</a>
            </div>
          </nav>

          <div className="grid grid-cols-[minmax(0,1fr)] gap-8">
            <section className="rounded-2xl border bg-card p-5 sm:p-7" id="vehicle">
              <SectionHeading title="Bilen" />
              <div className="mt-5"><VehicleFacts offer={offer} /></div>
            </section>
            <section className="rounded-2xl border bg-card p-5 sm:p-7" id="contract">
              <SectionHeading title="Aftalen" />
              <div className="mt-5"><ContractFacts offer={offer} /></div>
              <Separator className="my-6" />
              <h3 className="mb-3 font-serif text-xl">Service og ordninger</h3>
              <ServiceFacts offer={offer} />
            </section>
            <section className="rounded-2xl border bg-card p-5 sm:p-7" id="payments">
              <CashFlowSection mode="compact" offer={offer} />
            </section>
            <div id="source"><ProviderCard dataset={dataset} offer={offer} /></div>
          </div>
        </div>
      </main>
    </div>
  );
}

function SelectionStatus({
  patchSearch,
  search,
}: {
  patchSearch: PatchSearch;
  search: OfferDetailSearch;
}) {
  if (search.selected.length === 0) return null;

  return (
    <aside className="fixed bottom-20 right-4 z-40 flex max-w-[calc(100%-2rem)] items-center gap-3 rounded-2xl border border-primary/25 bg-card/95 p-3 shadow-xl backdrop-blur sm:right-6">
      <span className="grid size-9 place-content-center rounded-full bg-primary text-primary-foreground">
        <Check aria-hidden="true" className="size-4" />
      </span>
      <div>
        <p className="text-sm font-bold">{search.selected.length} tilbud valgt</p>
        <p className="text-xs text-muted-foreground">Valget følger med i URL’en</p>
      </div>
      <Button
        aria-label="Ryd valgte tilbud"
        onClick={() => patchSearch({ selected: [] })}
        size="icon"
        variant="ghost"
      >
        <X aria-hidden="true" />
      </Button>
    </aside>
  );
}

export function CatalogueOfferDetailPrototype({
  dataset,
  offer,
  search,
}: {
  dataset: CatalogueDataset;
  offer: CatalogueOffer;
  search: OfferDetailSearch;
}) {
  const navigate = useNavigate({ from: "/prototype/offers/$offerIdentity" });
  const patchSearch: PatchSearch = (patch) => {
    void navigate({ search: (previous) => ({ ...previous, ...patch }) });
  };
  const toggleSelected = () => {
    patchSearch({
      selected: search.selected.includes(offer.offerIdentity)
        ? search.selected.filter((identity) => identity !== offer.offerIdentity)
        : [...search.selected, offer.offerIdentity],
    });
  };
  const props = { dataset, offer, search, toggleSelected };

  return (
    <>
      {search.variant === "a" && <VariantA {...props} />}
      {search.variant === "b" && <VariantB {...props} />}
      {search.variant === "c" && <VariantC {...props} />}
      <SelectionStatus patchSearch={patchSearch} search={search} />
      <PrototypeSwitcher
        current={search.variant}
        onChange={(variant) => patchSearch({ variant })}
        variants={variants}
      />
    </>
  );
}
