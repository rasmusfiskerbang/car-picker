// PROTOTYPE — three catalogue-overview variants, switchable via ?variant=.
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useNavigate } from "@tanstack/react-router";
import {
  ArrowDownUp,
  ArrowLeft,
  ArrowRight,
  CarFront,
  Check,
  ChevronRight,
  ImageOff,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";

import {
  type CatalogueDataset,
  type CatalogueOffer,
  endMechanism,
  knownValue,
  monthlyPayment,
  riskAllocation,
  upfrontPayment,
  vehicleName,
} from "@/catalogue-data";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import type { CatalogueSearch } from "@/routes/catalogue";

type SearchPatch = Partial<CatalogueSearch>;
type PatchSearch = (patch: SearchPatch, options?: { replace?: boolean }) => void;

const currency = new Intl.NumberFormat("da-DK", {
  maximumFractionDigits: 0,
  style: "currency",
  currency: "DKK",
});
const integer = new Intl.NumberFormat("da-DK");
const date = new Intl.DateTimeFormat("da-DK", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

const leasingLabels = {
  financial: "Finansiel",
  flex: "Flexleasing",
  operational: "Operationel",
  hybrid: "Hybrid",
} as const;

function money(value: number | null) {
  return value === null ? "Kan ikke beregnes" : currency.format(value);
}

function mileage(offer: CatalogueOffer) {
  const value = knownValue<number>(offer.annualMileageKm);
  return value === null ? "Ikke oplyst" : `${integer.format(value)} km/år`;
}

function monthly(offer: CatalogueOffer) {
  const value = monthlyPayment(offer);
  return value === null ? "Ikke oplyst" : `${currency.format(value)}/md.`;
}

function providerName(dataset: CatalogueDataset, providerId: string) {
  return (
    dataset.providers.find((provider) => provider.id === providerId)?.name ??
    providerId
  );
}

function FilterFields({
  activeProviders,
  search,
  patchSearch,
}: {
  activeProviders: CatalogueDataset["providers"];
  search: CatalogueSearch;
  patchSearch: PatchSearch;
}) {
  return (
    <div className="grid gap-5">
      <label className="grid gap-2 text-sm font-semibold">
        <span>Søg efter bil eller udbyder</span>
        <span className="relative">
          <Search
            aria-hidden="true"
            className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            className="h-11 bg-card pl-9"
          onChange={(event) =>
            patchSearch({ q: event.target.value }, { replace: true })
          }
            placeholder="Fx Volvo, elbil eller Fleasing"
            type="search"
            value={search.q}
          />
        </span>
      </label>

      <label className="grid gap-2 text-sm font-semibold">
        <span>Udbyder</span>
        <select
          className="h-11 rounded-md border border-input bg-card px-3"
          onChange={(event) => patchSearch({ provider: event.target.value })}
          value={search.provider}
        >
          <option value="all">Alle aktive udbydere</option>
          {activeProviders.map((provider) => (
            <option key={provider.id} value={provider.id}>
              {provider.name}
            </option>
          ))}
        </select>
      </label>

      <label className="grid gap-2 text-sm font-semibold">
        <span>Leasingform</span>
        <select
          className="h-11 rounded-md border border-input bg-card px-3"
          onChange={(event) =>
            patchSearch({ form: event.target.value as CatalogueSearch["form"] })
          }
          value={search.form}
        >
          <option value="all">Alle leasingformer</option>
          <option value="operational">Operationel</option>
          <option value="financial">Finansiel</option>
          <option value="flex">Flexleasing</option>
          <option value="hybrid">Hybrid</option>
        </select>
      </label>

      <label className="grid gap-2 text-sm font-semibold">
        <span>Drivlinje</span>
        <select
          className="h-11 rounded-md border border-input bg-card px-3"
          onChange={(event) =>
            patchSearch({ power: event.target.value as CatalogueSearch["power"] })
          }
          value={search.power}
        >
          <option value="all">Alle drivlinjer</option>
          <option value="battery_electric">Elbil</option>
          <option value="combustion">Benzin eller diesel</option>
        </select>
      </label>

      <label className="grid gap-2 text-sm font-semibold">
        <span>Sortering</span>
        <select
          className="h-11 rounded-md border border-input bg-card px-3"
          onChange={(event) =>
            patchSearch({ sort: event.target.value as CatalogueSearch["sort"] })
          }
          value={search.sort}
        >
          <option value="source">Neutral kildeorden</option>
          <option value="monthly">Laveste månedsydelse</option>
          <option value="upfront">Laveste betaling ved start</option>
          <option value="total">Laveste beregnede total</option>
        </select>
      </label>

      <Button
        className="justify-start px-0"
        onClick={() =>
          patchSearch({
            q: "",
            provider: "all",
            form: "all",
            power: "all",
            sort: "source",
          })
        }
        variant="link"
      >
        Nulstil søgning og filtre
      </Button>
    </div>
  );
}

function MobileFilters(props: Parameters<typeof FilterFields>[0]) {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button className="gap-2 md:hidden" variant="outline">
          <SlidersHorizontal className="size-4" /> Filtre
        </Button>
      </SheetTrigger>
      <SheetContent className="overflow-y-auto bg-background">
        <SheetHeader className="mb-6 text-left">
          <SheetTitle>Tilpas kataloget</SheetTitle>
        </SheetHeader>
        <FilterFields {...props} />
      </SheetContent>
    </Sheet>
  );
}

function PrototypeMasthead({ generatedAt }: { generatedAt: string }) {
  return (
    <header className="border-b border-border/80 bg-background/85 backdrop-blur">
      <div className="mx-auto flex max-w-[92rem] items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <span className="grid size-9 place-content-center rounded-full bg-primary text-primary-foreground">
            <CarFront className="size-5" aria-hidden="true" />
          </span>
          <div>
            <p className="font-serif text-xl leading-none">Bilvalg</p>
            <p className="mt-1 text-[0.68rem] font-bold uppercase tracking-[0.16em] text-muted-foreground">
              Katalogprototype
            </p>
          </div>
        </div>
        <p className="hidden text-right text-xs text-muted-foreground sm:block">
          Samlet {date.format(new Date(generatedAt))}
          <br />
          Tilbud kan være ændret siden
        </p>
      </div>
    </header>
  );
}

function OfferImage({
  offer,
  className,
}: {
  offer: CatalogueOffer;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const source = offer.imageUrls[0];

  if (source === undefined || failed) {
    return (
      <div
        className={cn(
          "grid place-content-center bg-secondary text-muted-foreground",
          className,
        )}
      >
        <div className="grid justify-items-center gap-2 text-xs font-semibold">
          <ImageOff aria-hidden="true" className="size-7" />
          Intet billede
        </div>
      </div>
    );
  }

  return (
    <img
      alt=""
      className={cn("object-cover", className)}
      loading="lazy"
      onError={() => setFailed(true)}
      referrerPolicy="no-referrer"
      src={source}
    />
  );
}

function SelectionControl({
  offer,
  selected,
  toggle,
  compact = false,
}: {
  offer: CatalogueOffer;
  selected: boolean;
  toggle: () => void;
  compact?: boolean;
}) {
  const name = vehicleName(offer);
  return (
    <label
      className={cn(
        "inline-flex cursor-pointer items-center gap-2 font-semibold",
        compact ? "text-xs" : "text-sm",
      )}
    >
      <Checkbox
        aria-label={`${selected ? "Fjern" : "Vælg"} ${name} til sammenligning`}
        checked={selected}
        onCheckedChange={toggle}
      />
      {selected ? "Valgt" : "Sammenlign"}
    </label>
  );
}

function OfferLink({ offer, label = "Se hos udbyderen" }: { offer: CatalogueOffer; label?: string }) {
  return (
    <a
      className="inline-flex items-center gap-1 text-sm font-bold text-primary underline-offset-4 hover:underline"
      href={offer.canonicalOfferUrl}
      rel="noreferrer"
      target="_blank"
    >
      {label} <ChevronRight className="size-4" aria-hidden="true" />
    </a>
  );
}

function Metric({
  label,
  value,
  quiet = false,
}: {
  label: string;
  value: string;
  quiet?: boolean;
}) {
  return (
    <div>
      <dt className="text-[0.68rem] font-bold uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </dt>
      <dd className={cn("mt-1 font-semibold", quiet ? "text-sm" : "text-base")}>
        {value}
      </dd>
    </div>
  );
}

function OverviewHeading({ count }: { count: number }) {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary">
        Privatleasing i Danmark
      </p>
      <h1 className="mt-2 max-w-3xl font-serif text-4xl leading-[0.98] tracking-[-0.035em] sm:text-5xl lg:text-6xl">
        Sammenlign aftalen,
        <br />
        ikke kun månedsprisen.
      </h1>
      <p className="mt-4 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
        {count} aktuelle konfigurationer fra navngivne udbydere. Kataloget
        rangerer ikke tilbud og dækker ikke nødvendigvis hele markedet.
      </p>
    </div>
  );
}

function VariantA({
  dataset,
  offers,
  search,
  patchSearch,
  toggleSelected,
}: VariantProps) {
  const activeProviders = dataset.providers.filter(
    (provider) => provider.status === "active",
  );
  return (
    <div>
      <PrototypeMasthead generatedAt={dataset.generatedAt} />
      <main className="mx-auto max-w-[92rem] px-4 pb-36 pt-8 sm:px-6 lg:px-8 lg:pt-12">
        <div className="flex items-end justify-between gap-6">
          <OverviewHeading count={offers.length} />
          <MobileFilters
            activeProviders={activeProviders}
            patchSearch={patchSearch}
            search={search}
          />
        </div>

        <div className="mt-10 grid items-start gap-8 md:grid-cols-[17rem_minmax(0,1fr)] lg:grid-cols-[19rem_minmax(0,1fr)]">
          <aside className="sticky top-5 hidden rounded-2xl border bg-card p-5 md:block">
            <div className="mb-5 flex items-center gap-2">
              <SlidersHorizontal className="size-4" />
              <h2 className="font-serif text-xl">Afgræns kataloget</h2>
            </div>
            <FilterFields
              activeProviders={activeProviders}
              patchSearch={patchSearch}
              search={search}
            />
          </aside>

          <section aria-label="Katalogtilbud" className="grid gap-4">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>{offers.length} tilbud i neutral kildeorden</span>
              <span className="hidden sm:inline">Variant A · Rolige rækker</span>
            </div>
            {offers.map((offer) => {
              const selected = search.selected.includes(offer.offerIdentity);
              return (
                <Card
                  className="group overflow-hidden transition-shadow hover:shadow-md"
                  key={offer.offerIdentity}
                >
                  <div className="grid sm:grid-cols-[12rem_minmax(0,1fr)] lg:grid-cols-[15rem_minmax(0,1fr)]">
                    <OfferImage
                      className="aspect-[16/9] h-full min-h-44 w-full sm:aspect-auto"
                      offer={offer}
                    />
                    <div className="grid gap-5 p-5 lg:grid-cols-[minmax(13rem,1.2fr)_minmax(19rem,1.8fr)]">
                      <div>
                        <div className="flex flex-wrap gap-2">
                          <Badge variant="secondary">
                            {providerName(dataset, offer.providerId)}
                          </Badge>
                          <Badge variant="outline">
                            {leasingLabels[offer.leasingForm]}
                          </Badge>
                        </div>
                        <h2 className="mt-3 font-serif text-2xl leading-tight lg:text-3xl">
                          {vehicleName(offer)}
                        </h2>
                        <p className="mt-3 text-sm font-semibold text-primary">
                          {endMechanism(offer)}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {riskAllocation(offer)}
                        </p>
                      </div>
                      <div className="grid content-between gap-5">
                        <dl className="grid grid-cols-2 gap-x-5 gap-y-4 lg:grid-cols-4">
                          <Metric label="Månedsydelse" value={monthly(offer)} />
                          <Metric label="Ved start" value={money(upfrontPayment(offer))} />
                          <Metric label="Beregnet total" value={money(offer.totalDkk)} />
                          <Metric label="Per måned" value={money(offer.totalDkkPerMonth)} />
                        </dl>
                        <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
                          <div className="flex items-center gap-4">
                            <SelectionControl
                              offer={offer}
                              selected={selected}
                              toggle={() => toggleSelected(offer.offerIdentity)}
                            />
                            <span className="text-xs text-muted-foreground">
                              {offer.termMonths} mdr. · {mileage(offer)}
                            </span>
                          </div>
                          <OfferLink offer={offer} />
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>
              );
            })}
          </section>
        </div>
      </main>
    </div>
  );
}

function VariantB({
  dataset,
  offers,
  search,
  patchSearch,
  toggleSelected,
}: VariantProps) {
  const activeProviders = dataset.providers.filter(
    (provider) => provider.status === "active",
  );
  return (
    <div>
      <PrototypeMasthead generatedAt={dataset.generatedAt} />
      <main className="mx-auto max-w-[92rem] px-4 pb-36 pt-8 sm:px-6 lg:px-8 lg:pt-12">
        <div className="grid items-end gap-8 lg:grid-cols-[1fr_34rem]">
          <OverviewHeading count={offers.length} />
          <div className="rounded-2xl border bg-card p-4 shadow-sm">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="relative sm:col-span-2">
                <span className="sr-only">Søg</span>
                <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  className="h-12 pl-9"
                  onChange={(event) =>
                    patchSearch({ q: event.target.value }, { replace: true })
                  }
                  placeholder="Søg i 24 konfigurationer"
                  type="search"
                  value={search.q}
                />
              </label>
              <select
                aria-label="Udbyder"
                className="h-10 rounded-md border bg-background px-3 text-sm font-semibold"
                onChange={(event) => patchSearch({ provider: event.target.value })}
                value={search.provider}
              >
                <option value="all">Alle udbydere</option>
                {activeProviders.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.name}
                  </option>
                ))}
              </select>
              <select
                aria-label="Sortering"
                className="h-10 rounded-md border bg-background px-3 text-sm font-semibold"
                onChange={(event) =>
                  patchSearch({ sort: event.target.value as CatalogueSearch["sort"] })
                }
                value={search.sort}
              >
                <option value="source">Neutral rækkefølge</option>
                <option value="monthly">Månedsydelse</option>
                <option value="upfront">Betaling ved start</option>
                <option value="total">Beregnet total</option>
              </select>
            </div>
          </div>
        </div>

        <div className="mt-8 flex items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {(["all", "battery_electric", "combustion"] as const).map((power) => (
              <Button
                key={power}
                onClick={() => patchSearch({ power })}
                size="sm"
                variant={search.power === power ? "default" : "outline"}
              >
                {power === "all" ? "Alle biler" : power === "battery_electric" ? "Elbiler" : "Benzin & diesel"}
              </Button>
            ))}
          </div>
          <MobileFilters
            activeProviders={activeProviders}
            patchSearch={patchSearch}
            search={search}
          />
          <span className="hidden text-xs text-muted-foreground sm:inline">
            Variant B · Visuelt katalog
          </span>
        </div>

        <section
          aria-label="Katalogtilbud"
          className="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-3"
        >
          {offers.map((offer, index) => {
            const selected = search.selected.includes(offer.offerIdentity);
            return (
              <Card
                className={cn(
                  "relative overflow-hidden",
                  index === 0 && "sm:col-span-2 xl:col-span-2",
                )}
                key={offer.offerIdentity}
              >
                <OfferImage
                  className={cn(
                    "aspect-[4/3] w-full",
                    index === 0 && "sm:aspect-[2/1]",
                  )}
                  offer={offer}
                />
                <div className="absolute left-4 top-4 flex gap-2">
                  <Badge className="bg-card/90 text-card-foreground backdrop-blur" variant="secondary">
                    {providerName(dataset, offer.providerId)}
                  </Badge>
                  <Badge className="bg-card/90 backdrop-blur" variant="outline">
                    {leasingLabels[offer.leasingForm]}
                  </Badge>
                </div>
                <div className="grid gap-5 p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h2 className="font-serif text-2xl leading-tight">
                        {vehicleName(offer)}
                      </h2>
                      <p className="mt-2 text-sm text-muted-foreground">
                        {endMechanism(offer)}
                      </p>
                    </div>
                    <SelectionControl
                      compact
                      offer={offer}
                      selected={selected}
                      toggle={() => toggleSelected(offer.offerIdentity)}
                    />
                  </div>
                  <div className="rounded-xl bg-secondary/55 p-4">
                    <p className="text-[0.68rem] font-bold uppercase tracking-[0.12em] text-muted-foreground">
                      Oplyst månedsydelse
                    </p>
                    <p className="mt-1 font-serif text-3xl">{monthly(offer)}</p>
                    <Separator className="my-3" />
                    <dl className="grid grid-cols-2 gap-3">
                      <Metric label="Ved start" quiet value={money(upfrontPayment(offer))} />
                      <Metric label="Beregnet total" quiet value={money(offer.totalDkk)} />
                    </dl>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs text-muted-foreground">
                      {offer.termMonths} mdr. · {mileage(offer)}
                    </span>
                    <OfferLink label="Åbn tilbud" offer={offer} />
                  </div>
                </div>
              </Card>
            );
          })}
        </section>
      </main>
    </div>
  );
}

type LedgerRow = {
  offer: CatalogueOffer;
  provider: string;
  selected: boolean;
  toggle: () => void;
};

const ledgerColumns: ColumnDef<LedgerRow>[] = [
  {
    id: "select",
    header: "Vælg",
    cell: ({ row }) => (
      <SelectionControl
        compact
        offer={row.original.offer}
        selected={row.original.selected}
        toggle={row.original.toggle}
      />
    ),
  },
  {
    id: "vehicle",
    header: "Bil og aftale",
    cell: ({ row }) => (
      <div className="flex min-w-56 items-center gap-3">
        <OfferImage className="size-16 shrink-0 rounded-lg" offer={row.original.offer} />
        <div>
          <p className="font-serif text-lg leading-tight">{vehicleName(row.original.offer)}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {row.original.provider} · {leasingLabels[row.original.offer.leasingForm]}
          </p>
        </div>
      </div>
    ),
  },
  {
    id: "end",
    header: "Ved aftalens udløb",
    cell: ({ row }) => (
      <div className="max-w-52 text-sm">
        <p className="font-semibold">{endMechanism(row.original.offer)}</p>
        <p className="mt-1 text-xs text-muted-foreground">{riskAllocation(row.original.offer)}</p>
      </div>
    ),
  },
  {
    id: "monthly",
    header: "Månedsydelse",
    cell: ({ row }) => <span className="font-semibold">{monthly(row.original.offer)}</span>,
  },
  {
    id: "upfront",
    header: "Ved start",
    cell: ({ row }) => <span className="font-semibold">{money(upfrontPayment(row.original.offer))}</span>,
  },
  {
    id: "total",
    header: "Beregnet total",
    cell: ({ row }) => <span className="font-semibold">{money(row.original.offer.totalDkk)}</span>,
  },
  {
    id: "terms",
    header: "Periode og kilometer",
    cell: ({ row }) => (
      <span className="text-sm">
        {row.original.offer.termMonths} mdr.
        <br />
        <span className="text-xs text-muted-foreground">{mileage(row.original.offer)}</span>
      </span>
    ),
  },
  {
    id: "source",
    header: "Kilde",
    cell: ({ row }) => <OfferLink label="Åbn" offer={row.original.offer} />,
  },
];

function VariantC({
  dataset,
  offers,
  search,
  patchSearch,
  toggleSelected,
}: VariantProps) {
  const activeProviders = dataset.providers.filter(
    (provider) => provider.status === "active",
  );
  const table = useReactTable({
    columns: ledgerColumns,
    data: offers.map((offer) => ({
      offer,
      provider: providerName(dataset, offer.providerId),
      selected: search.selected.includes(offer.offerIdentity),
      toggle: () => toggleSelected(offer.offerIdentity),
    })),
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div>
      <PrototypeMasthead generatedAt={dataset.generatedAt} />
      <main className="mx-auto max-w-[100rem] px-4 pb-36 pt-8 sm:px-6 lg:px-8">
        <div className="grid items-end gap-6 lg:grid-cols-[1fr_auto]">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary">
              Variant C · Analytisk register
            </p>
            <h1 className="mt-2 font-serif text-4xl tracking-[-0.03em] sm:text-5xl">
              Katalog over leasingaftaler
            </h1>
            <p className="mt-3 max-w-2xl text-sm text-muted-foreground">
              Sammenlign vilkår i neutral kildeorden. Ingen score, anbefaling
              eller personlig rangering.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative w-full min-w-64 sm:w-80">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="h-11 bg-card pl-9"
                onChange={(event) =>
                  patchSearch({ q: event.target.value }, { replace: true })
                }
                placeholder="Søg i registeret"
                type="search"
                value={search.q}
              />
            </div>
            <MobileFilters
              activeProviders={activeProviders}
              patchSearch={patchSearch}
              search={search}
            />
          </div>
        </div>

        <div className="mt-7 hidden items-center justify-between gap-4 rounded-xl border bg-card p-3 md:flex">
          <div className="flex flex-wrap gap-3">
            <select
              aria-label="Udbyder"
              className="h-9 rounded-md border bg-background px-3 text-sm"
              onChange={(event) => patchSearch({ provider: event.target.value })}
              value={search.provider}
            >
              <option value="all">Alle udbydere</option>
              {activeProviders.map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.name}
                </option>
              ))}
            </select>
            <select
              aria-label="Leasingform"
              className="h-9 rounded-md border bg-background px-3 text-sm"
              onChange={(event) =>
                patchSearch({ form: event.target.value as CatalogueSearch["form"] })
              }
              value={search.form}
            >
              <option value="all">Alle leasingformer</option>
              <option value="operational">Operationel</option>
              <option value="financial">Finansiel</option>
              <option value="flex">Flexleasing</option>
            </select>
            <select
              aria-label="Drivlinje"
              className="h-9 rounded-md border bg-background px-3 text-sm"
              onChange={(event) =>
                patchSearch({ power: event.target.value as CatalogueSearch["power"] })
              }
              value={search.power}
            >
              <option value="all">Alle drivlinjer</option>
              <option value="battery_electric">Elbil</option>
              <option value="combustion">Benzin eller diesel</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm font-semibold">
            <ArrowDownUp className="size-4" />
            <span className="sr-only">Sortering</span>
            <select
              className="bg-transparent"
              onChange={(event) =>
                patchSearch({ sort: event.target.value as CatalogueSearch["sort"] })
              }
              value={search.sort}
            >
              <option value="source">Neutral kildeorden</option>
              <option value="monthly">Månedsydelse</option>
              <option value="upfront">Betaling ved start</option>
              <option value="total">Beregnet total</option>
            </select>
          </label>
        </div>

        <div className="mt-5 overflow-hidden rounded-2xl border bg-card shadow-sm" role="table">
          {table.getHeaderGroups().map((headerGroup) => (
            <div
              className="hidden grid-cols-[7rem_minmax(17rem,1.5fr)_minmax(14rem,1.2fr)_10rem_9rem_10rem_10rem_6rem] border-b bg-secondary/60 px-4 py-3 md:grid"
              key={headerGroup.id}
              role="row"
            >
              {headerGroup.headers.map((header) => (
                <div
                  className="pr-4 text-[0.65rem] font-bold uppercase tracking-[0.12em] text-muted-foreground"
                  key={header.id}
                  role="columnheader"
                >
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                </div>
              ))}
            </div>
          ))}
          <div role="rowgroup">
            {table.getRowModel().rows.map((row) => (
              <div
                className="grid gap-4 border-b p-4 last:border-b-0 md:grid-cols-[7rem_minmax(17rem,1.5fr)_minmax(14rem,1.2fr)_10rem_9rem_10rem_10rem_6rem] md:items-center md:gap-0"
                key={row.id}
                role="row"
              >
                {row.getVisibleCells().map((cell) => (
                  <div className="pr-4" key={cell.id} role="cell">
                    <span className="mb-1 block text-[0.65rem] font-bold uppercase tracking-[0.12em] text-muted-foreground md:hidden">
                      {typeof cell.column.columnDef.header === "string"
                        ? cell.column.columnDef.header
                        : cell.column.id}
                    </span>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}

type VariantProps = {
  dataset: CatalogueDataset;
  offers: CatalogueOffer[];
  search: CatalogueSearch;
  patchSearch: PatchSearch;
  toggleSelected: (offerIdentity: string) => void;
};

function SelectionTray({ search, patchSearch }: { search: CatalogueSearch; patchSearch: PatchSearch }) {
  if (search.selected.length === 0) return null;
  return (
    <aside className="fixed bottom-20 left-1/2 z-40 flex w-[min(calc(100%-2rem),34rem)] -translate-x-1/2 items-center justify-between gap-4 rounded-2xl border border-primary/25 bg-card/95 p-3 shadow-xl backdrop-blur">
      <div className="flex items-center gap-3">
        <span className="grid size-9 place-content-center rounded-full bg-primary text-primary-foreground">
          <Check className="size-4" />
        </span>
        <div>
          <p className="text-sm font-bold">{search.selected.length} tilbud valgt</p>
          <p className="text-xs text-muted-foreground">Sammenligningen prototypes senere</p>
        </div>
      </div>
      <Button
        aria-label="Ryd valgte tilbud"
        onClick={() => patchSearch({ selected: [] })}
        size="icon"
        variant="ghost"
      >
        <X className="size-4" />
      </Button>
    </aside>
  );
}

const variants = [
  { key: "a", name: "Rolige rækker" },
  { key: "b", name: "Visuelt katalog" },
  { key: "c", name: "Analytisk register" },
] as const;

function PrototypeSwitcher({ search, patchSearch }: { search: CatalogueSearch; patchSearch: PatchSearch }) {
  const navigate = useNavigate({ from: "/catalogue" });
  const currentIndex = variants.findIndex((variant) => variant.key === search.variant);

  const cycle = (direction: -1 | 1) => {
    const next = variants[(currentIndex + direction + variants.length) % variants.length];
    void navigate({
      search: (previous) => ({ ...previous, variant: next.key }),
    });
  };

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      const target = event.target;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        (target instanceof HTMLElement && target.isContentEditable)
      ) {
        return;
      }
      if (event.key === "ArrowLeft") cycle(-1);
      if (event.key === "ArrowRight") cycle(1);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  });

  if (!import.meta.env.DEV) return null;
  const current = variants[currentIndex];
  return (
    <nav
      aria-label="Skift prototypevariant"
      className="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 items-center rounded-full bg-foreground p-1.5 text-background shadow-2xl"
    >
      <Button
        aria-label="Forrige variant"
        className="rounded-full text-background hover:bg-background/15 hover:text-background"
        onClick={() => cycle(-1)}
        size="icon"
        variant="ghost"
      >
        <ArrowLeft className="size-4" />
      </Button>
      <span className="min-w-44 px-3 text-center text-xs font-bold">
        {current.key.toUpperCase()} · {current.name}
      </span>
      <Button
        aria-label="Næste variant"
        className="rounded-full text-background hover:bg-background/15 hover:text-background"
        onClick={() => cycle(1)}
        size="icon"
        variant="ghost"
      >
        <ArrowRight className="size-4" />
      </Button>
    </nav>
  );
}

function filteredOffers(dataset: CatalogueDataset, search: CatalogueSearch) {
  const query = search.q.trim().toLocaleLowerCase("da-DK");
  const offers = dataset.offers.filter((offer) => {
    const provider = providerName(dataset, offer.providerId);
    const text = `${vehicleName(offer)} ${provider} ${offer.leasingForm}`.toLocaleLowerCase("da-DK");
    return (
      (query === "" || text.includes(query)) &&
      (search.provider === "all" || offer.providerId === search.provider) &&
      (search.form === "all" || offer.leasingForm === search.form) &&
      (search.power === "all" || offer.vehicleSpecification.kind === search.power)
    );
  });

  if (search.sort === "source") return offers;
  const value = (offer: CatalogueOffer) => {
    if (search.sort === "monthly") return monthlyPayment(offer);
    if (search.sort === "upfront") return upfrontPayment(offer);
    return offer.totalDkk;
  };
  return [...offers].sort((left, right) => {
    const leftValue = value(left);
    const rightValue = value(right);
    if (leftValue === null) return 1;
    if (rightValue === null) return -1;
    return leftValue - rightValue;
  });
}

export function CatalogueOverviewPrototype({
  dataset,
  search,
}: {
  dataset: CatalogueDataset;
  search: CatalogueSearch;
}) {
  const navigate = useNavigate({ from: "/catalogue" });
  const patchSearch: PatchSearch = (patch, options) => {
    void navigate({
      replace: options?.replace ?? false,
      search: (previous) => ({ ...previous, ...patch }),
    });
  };
  const toggleSelected = (offerIdentity: string) => {
    const selected = search.selected.includes(offerIdentity)
      ? search.selected.filter((identity) => identity !== offerIdentity)
      : [...search.selected, offerIdentity];
    patchSearch({ selected });
  };
  const offers = filteredOffers(dataset, search);
  const props = { dataset, offers, search, patchSearch, toggleSelected };

  return (
    <>
      {search.variant === "a" && <VariantA {...props} />}
      {search.variant === "b" && <VariantB {...props} />}
      {search.variant === "c" && <VariantC {...props} />}
      <SelectionTray patchSearch={patchSearch} search={search} />
      <PrototypeSwitcher patchSearch={patchSearch} search={search} />
    </>
  );
}
