import { useMemo, type ReactNode } from "react";

import { barY, defineChart, group } from "@tanstack/charts";
import { Chart } from "@tanstack/charts/react";
import { scaleBand } from "@tanstack/charts/scales/band";
import { scaleLinear } from "@tanstack/charts/scales/linear";
import { scaleOrdinal } from "@tanstack/charts/scales/ordinal";
import { tooltip } from "@tanstack/charts/tooltip";

import type { CatalogueOffer } from "@/catalogue-dataset";
import { factText, isKnown, money, unavailableLabels } from "@/catalogue-ui";

type CashFlowEvent = CatalogueOffer["baseCashFlowStream"][number];
type FactUnavailableState = Exclude<CashFlowEvent["amount"]["state"], "known">;

type DisplayEvent = {
  date: Date;
  dateLabel: string;
  directionLabel: string;
  event: CashFlowEvent;
  eventLabel: string;
  offer: CatalogueOffer;
  refundabilityLabel: string;
};

type ActiveChartPoint = {
  date: Date;
  dateLabel: string;
  events: readonly DisplayEvent[];
  kind: "active";
  month: number;
  payments: number;
  receipts: number;
  unavailablePayments: readonly FactUnavailableState[];
  unavailableReceipts: readonly FactUnavailableState[];
};

type ChartDatum = {
  amount: number;
  color: string;
  direction: CashFlowEvent["direction"];
  month: number;
  offerIdentity: string;
  pointKey: string;
  seriesKey: string;
  tooltip: string;
};

type TotalResult =
  | { amountDkk: number; state: "available" }
  | { state: "no_events" }
  | { reason: string; state: "unavailable" };

type OfferCashFlowModel = {
  events: readonly DisplayEvent[];
  offer: CatalogueOffer;
  points: ReadonlyMap<number, ActiveChartPoint>;
  totals: {
    calculated: TotalResult;
    payments: TotalResult;
    receipts: TotalResult;
    upfront: TotalResult;
  };
};

const eventLabels: Record<CashFlowEvent["kind"], string> = {
  initial_payment: "Førstegangsbetaling",
  lease_payment: "Månedlig betaling",
  establishment_fee: "Oprettelsesgebyr",
  delivery_fee: "Leveringsgebyr",
  deposit: "Depositum",
  deposit_refund: "Tilbagebetaling af depositum",
  mandatory_purchase_or_payoff: "Obligatorisk køb eller indfrielse",
  other: "Anden betaling",
};

const directionLabels: Record<CashFlowEvent["direction"], string> = {
  payment: "Betaling",
  receipt: "Modtaget beløb",
};

const refundabilityLabels: Record<
  Extract<CashFlowEvent["refundability"], { state: "known" }>["value"],
  string
> = {
  refundable: "Refunderbar",
  not_refundable: "Ikke refunderbar",
};

const chartColors = ["#35513c", "#7d5a3c", "#526b8f", "#76506e", "#68764a"];
const cashFlowDirections = ["payment", "receipt"] as const;

const longDate = new Intl.DateTimeFormat("da-DK", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

export function normalizedViewingDate(now = new Date()): Date {
  const viewingDate = new Date(now);
  viewingDate.setHours(12, 0, 0, 0);
  return viewingDate;
}

export function CatalogueCashFlowDisplay({
  offers,
  referenceDate,
}: {
  offers: readonly CatalogueOffer[];
  referenceDate: Date;
}) {
  const models = deriveCashFlowDisplayModels(offers, referenceDate);

  return (
    <div className="cash-flow-display">
      <CashFlowDateNote referenceDate={referenceDate} />
      {models.length > 0 && (
        <CatalogueCashFlowChart models={models} referenceDate={referenceDate} />
      )}
      {models.map((model) => (
        <CashFlowOfferDetails
          key={model.offer.offerIdentity}
          model={model}
          multipleOffers={models.length > 1}
        />
      ))}
    </div>
  );
}

export function CatalogueCashFlowSharedChart({
  offers,
  referenceDate,
}: {
  offers: readonly CatalogueOffer[];
  referenceDate: Date;
}) {
  const models = deriveCashFlowDisplayModels(offers, referenceDate);
  if (models.length === 0) return null;
  return <CatalogueCashFlowChart models={models} referenceDate={referenceDate} />;
}

export function CatalogueCashFlowColumn({
  offer,
  referenceDate,
}: {
  offer: CatalogueOffer;
  referenceDate: Date;
}) {
  const model = deriveCashFlowDisplayModels([offer], referenceDate)[0];
  if (model === undefined) return null;

  return (
    <section
      aria-label={`Kontantstrøm for ${offerName(offer)}`}
      className="cash-flow-column"
    >
      <CashFlowTotals model={model} />
      <CashFlowVisual model={model} />
      <CashFlowTable model={model} multipleOffers />
      <AccessibleCashFlow model={model} includeOfferName />
    </section>
  );
}

function CashFlowDateNote({ referenceDate }: { referenceDate: Date }) {
  return (
    <p className="cash-flow-date-note">
      Kalenderdatoerne er en visning beregnet fra {longDate.format(referenceDate)}.
      Datasættet angiver aftalemåneder, ikke en startdato.
    </p>
  );
}

function deriveCashFlowDisplayModels(
  offers: readonly CatalogueOffer[],
  referenceDate: Date,
): OfferCashFlowModel[] {
  return offers.map((offer) => {
    const events = offer.baseCashFlowStream.map((event) =>
      displayEvent(offer, event, referenceDate),
    );
    const points = new Map<number, ActiveChartPoint>();
    for (let month = 0; month <= offer.termMonths; month += 1) {
      const monthEvents = events.filter(
        (candidate) => candidate.event.month === month,
      );
      points.set(month, activeChartPoint(month, monthEvents, referenceDate));
    }

    return {
      events,
      offer,
      points,
      totals: {
        calculated: calculatedTotal(offer),
        payments: totalForEvents(
          events.filter((candidate) => candidate.event.direction === "payment"),
        ),
        receipts: totalForEvents(
          events.filter((candidate) => candidate.event.direction === "receipt"),
        ),
        upfront: totalForEvents(
          events.filter(
            (candidate) =>
              candidate.event.month === 0 &&
              candidate.event.direction === "payment",
          ),
        ),
      },
    };
  });
}

function displayEvent(
  offer: CatalogueOffer,
  event: CashFlowEvent,
  referenceDate: Date,
): DisplayEvent {
  const date = calendarDateForMonth(referenceDate, event.month);
  return {
    date,
    dateLabel: eventDateLabel(event.month, date),
    directionLabel: directionLabels[event.direction],
    event,
    eventLabel: eventLabels[event.kind],
    offer,
    refundabilityLabel: factText(
      event.refundability,
      (value) => refundabilityLabels[value],
    ),
  };
}

function activeChartPoint(
  month: number,
  events: readonly DisplayEvent[],
  referenceDate: Date,
): ActiveChartPoint {
  let payments = 0;
  let receipts = 0;
  const unavailablePayments: FactUnavailableState[] = [];
  const unavailableReceipts: FactUnavailableState[] = [];

  for (const displayEvent of events) {
    const amount = displayEvent.event.amount;
    if (!isKnown(amount)) {
      appendUnavailableAmount(
        displayEvent.event.direction,
        amount.state,
        unavailablePayments,
        unavailableReceipts,
      );
      continue;
    }
    if (displayEvent.event.direction === "payment") payments += amount.value;
    if (displayEvent.event.direction === "receipt") receipts += amount.value;
  }

  const date = calendarDateForMonth(referenceDate, month);
  return {
    date,
    dateLabel: eventDateLabel(month, date),
    events,
    kind: "active",
    month,
    payments,
    receipts,
    unavailablePayments,
    unavailableReceipts,
  };
}

function appendUnavailableAmount(
  direction: CashFlowEvent["direction"],
  state: FactUnavailableState,
  unavailablePayments: FactUnavailableState[],
  unavailableReceipts: FactUnavailableState[],
) {
  if (direction === "payment") {
    unavailablePayments.push(state);
    return;
  }
  unavailableReceipts.push(state);
}

function chartRows(
  models: readonly OfferCashFlowModel[],
): ChartDatum[] {
  const rows: ChartDatum[] = [];
  const lastMonth = Math.max(
    ...models.map((model) => model.offer.termMonths),
  );
  for (let month = 0; month <= lastMonth; month += 1) {
    for (const [offerIndex, model] of models.entries()) {
      const point = model.points.get(month);
      if (point === undefined) continue;
      for (const direction of cashFlowDirections) {
        const events = point.events.filter(
          (displayEvent) => displayEvent.event.direction === direction,
        );
        const amount = knownAmountTotal(events);
        if (amount === undefined) continue;
        const seriesKey = `${model.offer.offerIdentity}-${direction}`;
        rows.push({
          amount,
          color: chartColors[offerIndex] ?? chartColors[0],
          direction,
          month,
          offerIdentity: model.offer.offerIdentity,
          pointKey: `${seriesKey}-${month}`,
          seriesKey,
          tooltip: chartTooltip(model.offer, point, direction),
        });
      }
    }
  }
  return rows;
}

function knownAmountTotal(events: readonly DisplayEvent[]): number | undefined {
  let total = 0;
  let hasKnownAmount = false;
  for (const displayEvent of events) {
    if (!isKnown(displayEvent.event.amount)) continue;
    hasKnownAmount = true;
    total += displayEvent.event.amount.value;
  }
  return hasKnownAmount ? total : undefined;
}

function totalForEvents(events: readonly DisplayEvent[]): TotalResult {
  if (events.length === 0) return { state: "no_events" };

  let total = 0;
  const unavailableStates: FactUnavailableState[] = [];
  for (const displayEvent of events) {
    const amount = displayEvent.event.amount;
    if (!isKnown(amount)) {
      unavailableStates.push(amount.state);
      continue;
    }
    total += amount.value;
  }
  if (unavailableStates.length > 0) {
    const reasons = [...new Set(unavailableStates)].map(
      (state) => unavailableLabels[state],
    );
    return { reason: reasons.join("; "), state: "unavailable" };
  }
  return { amountDkk: total, state: "available" };
}

function calculatedTotal(offer: CatalogueOffer): TotalResult {
  if (offer.calculatedTotal.state === "available") {
    return {
      amountDkk: offer.calculatedTotal.value.amountDkk,
      state: "available",
    };
  }
  const reason = offer.calculatedTotal.reasons
    .map((item) => {
      const label = unavailableLabels[item.factState] ?? "Oplysningen er ikke tilgængelig";
      return `${label} (${item.eventKey})`;
    })
    .join("; ");
  return { reason, state: "unavailable" };
}

function CatalogueCashFlowChart({
  models,
  referenceDate,
}: {
  models: readonly OfferCashFlowModel[];
  referenceDate: Date;
}) {
  const chartRowsAndDefinition = useMemo(() => {
    const rows = chartRows(models);
    const lastMonth = Math.max(
      ...models.map((model) => model.offer.termMonths),
    );
    const months = Array.from({ length: lastMonth + 1 }, (_, month) => month);
    const offerIdentities = models.map((model) => model.offer.offerIdentity);
    const offerColors = models.map(
      (_, offerIndex) => chartColors[offerIndex] ?? chartColors[0],
    );
    const colorScale = scaleOrdinal<string, string>()
      .domain(offerIdentities)
      .range(offerColors);
    const definition = defineChart({
      marks: [
        barY(rows, {
          id: "cash-flow-amounts",
          x: "month",
          y: "amount",
          z: "seriesKey",
          color: "offerIdentity",
          key: "pointKey",
          fill: (row) => row.color,
          stroke: (row) => row.color,
          strokeDasharray: (row) =>
            row.direction === "receipt" ? "4 3" : "none",
          strokeWidth: 1.5,
          radius: 4,
          layout: group({ padding: 0.16 }),
        }),
      ],
      scales: {
        x: {
          scale: scaleBand<number>().domain(months).padding(0.14),
          axis: {
            label: "Kalenderdato",
            ticks: {
              values: months,
              format: (month) => monthAxisLabel(month, referenceDate),
            },
            tickLabels: { thin: { minGap: 8, priority: "ends" } },
          },
        },
        y: {
          scale: scaleLinear,
          nice: true,
          grid: true,
          axis: {
            label: "Beløb (DKK)",
            ticks: { format: money },
          },
        },
      },
      color: { scale: colorScale },
      focus: "nearest",
      keyboard: true,
      tooltip: {
        use: tooltip,
        format: (point) => point.datum.tooltip,
        sticky: true,
      },
      theme: {
        foreground: "#20221f",
        muted: "#65705f",
        grid: "#e4e1d9",
        background: "transparent",
        palette: chartColors,
      },
    });
    return {
      definition,
      minimumWidthRem: Math.max(56, months.length * 4.4),
    };
  }, [models, referenceDate]);
  const unavailableCount = chartUnavailableCount(models);
  const chartLabel = `Fælles søjlediagram for ${models.length} tilbud`;

  return (
    <figure
      aria-label={chartLabel}
      className="cash-flow-chart"
      data-testid="shared-cash-flow-chart"
    >
      <figcaption>
        <strong>Fælles betalingsforløb i DKK</strong>
        <span>
          Kalenderdatoerne er en visning beregnet fra {longDate.format(referenceDate)}.
          Ukendte beløb vises ikke som nul.
        </span>
      </figcaption>
      <div
        aria-label="Rul for at se alle kalenderdatoer"
        className="cash-flow-chart-scroll"
        tabIndex={0}
      >
        <div
          className="cash-flow-chart-surface"
          style={{ minWidth: `${chartRowsAndDefinition.minimumWidthRem}rem` }}
        >
          <Chart
            ariaDescription="Kendte betalinger og modtagne beløb vises i kronologisk rækkefølge. Se tabellen nedenfor for alle hændelser, inklusive beløb der ikke er oplyst."
            ariaLabel="Visuel kontantstrøm i DKK"
            className="cash-flow-chart-tanstack"
            definition={chartRowsAndDefinition.definition}
            height={320}
            initialWidth={chartRowsAndDefinition.minimumWidthRem * 16}
          />
        </div>
      </div>
      <div className="cash-flow-chart-legend">
        {legendItems(models)}
        <span>
          <i className="unknown" /> Beløb ikke oplyst
        </span>
      </div>
      {unavailableCount > 0 && (
        <p className="cash-flow-chart-unavailable" data-testid="cash-flow-unavailable-note">
          {unavailableNote(unavailableCount)}
        </p>
      )}
    </figure>
  );
}

function chartTooltip(
  offer: CatalogueOffer,
  point: ActiveChartPoint,
  direction: CashFlowEvent["direction"],
): string {
  const events = point.events.filter(
    (displayEvent) => displayEvent.event.direction === direction,
  );
  const directionText = directionLabels[direction];
  if (events.length === 0) {
    return `${point.dateLabel} · ${offerName(offer)} · ${directionText}: Ingen post.`;
  }
  const details = events
    .map((displayEvent) => `${displayEvent.eventLabel}: ${cashFlowAmount(displayEvent.event)}`)
    .join("; ");
  return `${point.dateLabel} · ${offerName(offer)} · ${directionText}: ${details}.`;
}

function legendItems(models: readonly OfferCashFlowModel[]): ReactNode[] {
  const items: ReactNode[] = [];
  models.forEach((model, offerIndex) => {
    const color = chartColors[offerIndex] ?? chartColors[0];
    items.push(
      <span key={`${model.offer.offerIdentity}-payment`}>
        <i className="payment" style={{ backgroundColor: color }} />
        {offerName(model.offer)} · betaling
      </span>,
    );
    items.push(
      <span key={`${model.offer.offerIdentity}-receipt`}>
        <i
          className="receipt"
          style={{
            backgroundColor: color,
            backgroundImage:
              "repeating-linear-gradient(135deg, transparent 0, transparent 3px, rgb(255 255 255 / 58%) 3px, rgb(255 255 255 / 58%) 5px)",
          }}
        />
        {offerName(model.offer)} · modtaget beløb
      </span>,
    );
  });
  return items;
}

function chartUnavailableCount(models: readonly OfferCashFlowModel[]): number {
  let count = 0;
  for (const model of models) {
    for (const point of model.points.values()) {
      count +=
        point.unavailablePayments.length + point.unavailableReceipts.length;
    }
  }
  return count;
}

function unavailableNote(count: number): string {
  if (count === 1) return "Ét beløb er ikke tilgængeligt og vises ikke som nul.";
  return `${count} beløb er ikke tilgængelige og vises ikke som nul.`;
}

function CashFlowOfferDetails({
  model,
  multipleOffers,
}: {
  model: OfferCashFlowModel;
  multipleOffers: boolean;
}) {
  return (
    <section
      aria-label={`Kontantstrøm for ${offerName(model.offer)}`}
      className="cash-flow-offer"
    >
      {multipleOffers && <h3>{offerName(model.offer)}</h3>}
      <CashFlowTotals model={model} />
      <CashFlowVisual model={model} />
      <CashFlowTable model={model} multipleOffers={multipleOffers} />
      <AccessibleCashFlow model={model} includeOfferName={multipleOffers} />
    </section>
  );
}

function CashFlowTotals({ model }: { model: OfferCashFlowModel }) {
  return (
    <div className="cash-flow-totals">
      <CashFlowTotal label="Ved start" result={model.totals.upfront} />
      <CashFlowTotal label="Betalinger i strømmen" result={model.totals.payments} />
      <CashFlowTotal label="Modtagne beløb i strømmen" result={model.totals.receipts} />
      <CashFlowTotal label="Beregnet ved udløb" result={model.totals.calculated} />
    </div>
  );
}

function CashFlowTotal({
  label,
  result,
}: {
  label: string;
  result: TotalResult;
}) {
  return (
    <div className="cash-flow-total">
      <span>{label}</span>
      <strong>{totalText(result)}</strong>
    </div>
  );
}

function CashFlowVisual({ model }: { model: OfferCashFlowModel }) {
  return (
    <div
      aria-label="Kronologisk visning af basiskontantstrøm"
      className="cash-flow-visual"
    >
      <ol
        aria-label={`Kronologisk kontantstrøm for ${offerName(model.offer)}`}
        className="cash-flow-timeline"
      >
        {model.events.map((displayEvent) => (
          <li
            className={`cash-flow-event ${displayEvent.event.direction}`}
            key={displayEvent.event.key}
          >
            <div className="cash-flow-event-heading">
              <span>{displayEvent.dateLabel}</span>
              <strong>{displayEvent.eventLabel}</strong>
            </div>
            <p>
              <span>{displayEvent.directionLabel}</span>
              <span>{cashFlowAmount(displayEvent.event)}</span>
            </p>
            <small>{displayEvent.refundabilityLabel}</small>
          </li>
        ))}
      </ol>
    </div>
  );
}

function CashFlowTable({
  model,
  multipleOffers,
}: {
  model: OfferCashFlowModel;
  multipleOffers: boolean;
}) {
  const label = cashFlowTableLabel(model.offer, multipleOffers);
  return (
    <div className="cash-flow-table-scroll">
      <table aria-label={label} className="cash-flow-table">
        <caption>{label}</caption>
        <thead>
          <tr>
            <th aria-label="Tidspunkt" scope="col">
              <span className="cash-flow-header-full">Tidspunkt</span>
              <span aria-hidden="true" className="cash-flow-header-short">Tid</span>
            </th>
            <th aria-label="Hændelse" scope="col">
              <span className="cash-flow-header-full">Hændelse</span>
              <span aria-hidden="true" className="cash-flow-header-short">Hænd.</span>
            </th>
            <th aria-label="Retning" scope="col">
              <span className="cash-flow-header-full">Retning</span>
              <span aria-hidden="true" className="cash-flow-header-short">Retn.</span>
            </th>
            <th aria-label="Beløb" scope="col">
              <span className="cash-flow-header-full">Beløb</span>
              <span aria-hidden="true" className="cash-flow-header-short">Beløb</span>
            </th>
            <th aria-label="Refundering" scope="col">
              <span className="cash-flow-header-full">Refundering</span>
              <span aria-hidden="true" className="cash-flow-header-short">Ref.</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {model.events.map((displayEvent) => (
            <tr key={displayEvent.event.key}>
              <td>{displayEvent.dateLabel}</td>
              <td>{displayEvent.eventLabel}</td>
              <td>{displayEvent.directionLabel}</td>
              <td>{factText(displayEvent.event.amount, money)}</td>
              <td>{displayEvent.refundabilityLabel}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function cashFlowTableLabel(
  offer: CatalogueOffer,
  multipleOffers: boolean,
): string {
  if (!multipleOffers) return "Basiskontantstrøm i DKK";
  return `Basiskontantstrøm i DKK for ${offerName(offer)}`;
}

function AccessibleCashFlow({
  includeOfferName,
  model,
}: {
  includeOfferName: boolean;
  model: OfferCashFlowModel;
}) {
  const label = accessibleCashFlowLabel(model.offer, includeOfferName);
  return (
    <ol aria-label={label} className="visually-hidden">
      {model.events.map((displayEvent) => (
        <li key={displayEvent.event.key}>
          {displayEvent.dateLabel}: {displayEvent.eventLabel}; {displayEvent.directionLabel};{" "}
          {factText(displayEvent.event.amount, money)}; {displayEvent.refundabilityLabel}.
        </li>
      ))}
    </ol>
  );
}

function accessibleCashFlowLabel(
  offer: CatalogueOffer,
  includeOfferName: boolean,
): string {
  if (!includeOfferName) return "Tilgængelig kontantstrøm";
  return `Tilgængelig kontantstrøm for ${offerName(offer)}`;
}

function totalText(result: TotalResult): string {
  if (result.state === "available") return money(result.amountDkk);
  if (result.state === "no_events") return "Ingen post er registreret i strømmen.";
  return `Kan ikke opgøres: ${result.reason}`;
}

function cashFlowAmount(event: CashFlowEvent): string {
  if (!isKnown(event.amount)) return factText(event.amount);
  const sign = eventSign(event.direction);
  return `${sign} ${money(event.amount.value)}`;
}

function eventSign(direction: CashFlowEvent["direction"]): string {
  if (direction === "payment") return "−";
  return "+";
}

function calendarDateForMonth(referenceDate: Date, month: number): Date {
  const anchor = new Date(referenceDate);
  anchor.setHours(12, 0, 0, 0);
  const target = new Date(anchor.getFullYear(), anchor.getMonth() + month, 1, 12);
  const lastDay = new Date(
    target.getFullYear(),
    target.getMonth() + 1,
    0,
    12,
  ).getDate();
  target.setDate(Math.min(anchor.getDate(), lastDay));
  return target;
}

function eventDateLabel(month: number, date: Date): string {
  if (month === 0) return `Måned 0 · ved start · ${longDate.format(date)}`;
  return `Måned ${month} · ${longDate.format(date)}`;
}

function monthAxisLabel(month: number, referenceDate: Date): string {
  return eventDateLabel(month, calendarDateForMonth(referenceDate, month));
}

function offerName(offer: CatalogueOffer): string {
  const { vehicleSpecification: vehicle } = offer;
  if (!isKnown(vehicle.trim)) return `${vehicle.make} ${vehicle.model}`;
  return `${vehicle.make} ${vehicle.model} ${vehicle.trim.value}`;
}
