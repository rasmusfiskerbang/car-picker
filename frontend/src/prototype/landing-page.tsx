// PROTOTYPE — three landing-page variants, switchable via ?variant=.
import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  CalendarDays,
  CarFront,
  Check,
  ChevronRight,
  CircleDot,
  ExternalLink,
  FileCheck2,
  ImageOff,
  Layers3,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useState, type ReactNode } from "react";

import {
  type CatalogueDataset,
  type CatalogueOffer,
  endMechanism,
  monthlyPayment,
  upfrontPayment,
  vehicleName,
} from "@/catalogue-data";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { PrototypeSwitcher } from "@/prototype/prototype-switcher";
import type { LandingSearch } from "@/routes/prototype.landing";

const date = new Intl.DateTimeFormat("da-DK", {
  day: "numeric",
  month: "long",
  year: "numeric",
});
const currency = new Intl.NumberFormat("da-DK", {
  currency: "DKK",
  maximumFractionDigits: 0,
  style: "currency",
});

const variants = [
  { key: "a", name: "Aftalen ved siden af" },
  { key: "b", name: "Sådan sammenligner du" },
  { key: "c", name: "Kataloget først" },
] as const;

const catalogueSearch = {
  form: "all" as const,
  power: "all" as const,
  provider: "all",
  q: "",
  selected: [] as string[],
  sort: "source" as const,
  variant: "d" as const,
};

function money(value: number | null) {
  return value === null ? "Ikke oplyst" : currency.format(value);
}

function activeProviderCount(dataset: CatalogueDataset) {
  return dataset.providers.filter((provider) => provider.status === "active")
    .length;
}

function LandingMasthead({ generatedAt }: { generatedAt: string }) {
  return (
    <header
      className="border-b border-border/75 bg-background/90 backdrop-blur"
      data-prototype-masthead
    >
      <div className="mx-auto flex max-w-[92rem] items-center justify-between gap-5 px-5 py-4 sm:px-8">
        <div className="flex items-center gap-3">
          <span className="grid size-10 place-content-center rounded-full bg-primary text-primary-foreground">
            <CarFront aria-hidden="true" className="size-5" />
          </span>
          <div>
            <p className="font-serif text-xl leading-none">Bilvalg</p>
            <p className="mt-1 text-[0.68rem] font-bold uppercase tracking-[0.16em] text-muted-foreground">
              Privatleasing
            </p>
          </div>
        </div>
        <p className="text-right text-[0.64rem] leading-4 text-muted-foreground sm:text-xs sm:leading-5">
          Katalogdata fra {date.format(new Date(generatedAt))}
          <br />
          Tilbud kan være ændret siden
        </p>
      </div>
    </header>
  );
}

function CatalogueLink({
  children,
  className,
  search,
  variant = "default",
}: {
  children: ReactNode;
  className?: string;
  search: LandingSearch;
  variant?: "default" | "outline";
}) {
  return (
    <Link
      className={cn(buttonVariants({ size: "lg", variant }), className)}
      search={{
        ...catalogueSearch,
        selected: search.selected,
        shell: search.shell,
      }}
      to="/catalogue"
    >
      {children}
      <ArrowRight aria-hidden="true" />
    </Link>
  );
}

function AgreementFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-t border-border py-3 first:border-t-0">
      <dt className="text-xs font-bold uppercase tracking-[0.11em] text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 font-semibold leading-5">{value}</dd>
    </div>
  );
}

function AgreementExample({ offer }: { offer: CatalogueOffer | undefined }) {
  if (offer === undefined) {
    return (
      <div className="rounded-2xl border bg-card p-6 text-sm text-muted-foreground">
        Ingen aftale er tilgængelig i dette katalogdatasæt.
      </div>
    );
  }

  return (
    <Card className="overflow-hidden shadow-lg shadow-primary/5">
      <div className="border-b border-border bg-secondary/55 px-5 py-4 sm:px-6">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary">
          Én aftale · flere afgørende fakta
        </p>
        <h2 className="mt-2 font-serif text-2xl">{vehicleName(offer)}</h2>
      </div>
      <dl className="grid px-5 sm:grid-cols-2 sm:px-6">
        <AgreementFact
          label="Oplyst månedsydelse"
          value={`${money(monthlyPayment(offer))}/md.`}
        />
        <AgreementFact label="Betaling ved start" value={money(upfrontPayment(offer))} />
        <AgreementFact label="Beregnet total" value={money(offer.totalDkk)} />
        <AgreementFact label="Ved aftalens udløb" value={endMechanism(offer)} />
      </dl>
      <p className="border-t border-border px-5 py-4 text-xs leading-5 text-muted-foreground sm:px-6">
        Eksemplet viser, hvorfor den annoncerede månedsydelse ikke kan stå alene.
      </p>
    </Card>
  );
}

function TrustStrip({ dataset }: { dataset: CatalogueDataset }) {
  const items = [
    {
      icon: FileCheck2,
      title: "Navngivne kilder",
      text: "Hvert tilbud peger tilbage på udbyderens offentlige tilbud.",
    },
    {
      icon: ShieldCheck,
      title: "Afgrænset katalog",
      text: `${activeProviderCount(dataset)} aktive udbydere — ikke en påstand om hele markedet.`,
    },
    {
      icon: Layers3,
      title: "Hele aftalen",
      text: "Betalinger, periode og afslutning vises som sammenhængende fakta.",
    },
  ];
  return (
    <section
      aria-label="Sådan afgrænses kataloget"
      className="grid border-y border-border md:grid-cols-3"
    >
      {items.map((item) => (
        <div
          className="flex gap-4 border-b border-border py-5 last:border-b-0 md:border-b-0 md:border-r md:px-6 md:first:pl-0 md:last:border-r-0 md:last:pr-0"
          key={item.title}
        >
          <item.icon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-primary" />
          <div>
            <h2 className="text-sm font-bold">{item.title}</h2>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              {item.text}
            </p>
          </div>
        </div>
      ))}
    </section>
  );
}

function VariantA({ dataset, search }: { dataset: CatalogueDataset; search: LandingSearch }) {
  const offer = dataset.offers.find((candidate) => candidate.totalDkk !== null);
  return (
    <div>
      <LandingMasthead generatedAt={dataset.generatedAt} />
      <main className="mx-auto max-w-[92rem] px-5 pb-36 pt-10 sm:px-8 lg:pt-16">
        <section className="grid items-center gap-10 lg:grid-cols-[minmax(0,1.05fr)_minmax(28rem,0.75fr)] lg:gap-16">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.19em] text-primary">
              Privatleasing i Danmark
            </p>
            <h1 className="mt-4 max-w-4xl font-serif text-5xl leading-[0.95] tracking-[-0.045em] sm:text-6xl lg:text-7xl">
              Sammenlign aftalen,
              <br />
              ikke kun månedsprisen.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg sm:leading-8">
              Se dokumenterede privatleasingtilbud på samme grundlag — fra
              første betaling til aftalens afslutning.
            </p>
            <div className="mt-8 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
              <CatalogueLink search={search}>
                Se alle {dataset.offers.length} tilbud
              </CatalogueLink>
              <p className="max-w-xs text-xs leading-5 text-muted-foreground">
                Kataloget dækker navngivne udbydere, ikke nødvendigvis hele
                markedet.
              </p>
            </div>
          </div>
          <AgreementExample offer={offer} />
        </section>
        <div className="mt-14 lg:mt-20">
          <TrustStrip dataset={dataset} />
        </div>
      </main>
    </div>
  );
}

type GuideStep = {
  description: string;
  icon: typeof Search;
  kicker: string;
  title: string;
};

const guideSteps: GuideStep[] = [
  {
    description:
      "Start i et dateret katalog fra navngivne udbydere — ikke i en påstand om at dække hele markedet.",
    icon: Search,
    kicker: "01 · Omfang",
    title: "Se, hvad der faktisk er med",
  },
  {
    description:
      "Sæt månedsydelse, startbetaling, beregnet total, løbetid og kilometer ved siden af hinanden.",
    icon: Layers3,
    kicker: "02 · Aftalen",
    title: "Sammenlign de samme fakta",
  },
  {
    description:
      "Læs hvordan aftalen slutter, og åbn altid det oprindelige tilbud hos udbyderen, før du går videre.",
    icon: ExternalLink,
    kicker: "03 · Kilden",
    title: "Kontrollér vilkårene selv",
  },
];

function VariantB({ dataset, search }: { dataset: CatalogueDataset; search: LandingSearch }) {
  return (
    <div>
      <LandingMasthead generatedAt={dataset.generatedAt} />
      <main className="mx-auto max-w-[92rem] px-5 pb-36 pt-10 sm:px-8 lg:pt-14">
        <section className="mx-auto max-w-5xl text-center">
          <p className="text-xs font-bold uppercase tracking-[0.19em] text-primary">
            Privatleasing i Danmark
          </p>
          <h1 className="mt-6 font-serif text-5xl leading-[0.98] tracking-[-0.04em] sm:text-6xl lg:text-7xl">
            Sammenlign aftalen,
            <br />
            ikke kun månedsprisen.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
            Se dokumenterede privatleasingtilbud på samme grundlag — fra første
            betaling til aftalens afslutning.
          </p>
        </section>

        <section
          aria-labelledby="guide-heading"
          className="relative mt-10 grid overflow-hidden rounded-3xl border border-border bg-card shadow-sm lg:grid-cols-3"
        >
          <h2 className="sr-only" id="guide-heading">
            Sådan bruges Bilvalg
          </h2>
          {guideSteps.map((step, index) => (
            <article
              className="relative border-b border-border p-6 last:border-b-0 sm:p-8 lg:border-b-0 lg:border-r lg:last:border-r-0"
              key={step.title}
            >
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary">
                  {step.kicker}
                </p>
                <step.icon aria-hidden="true" className="size-5 text-muted-foreground" />
              </div>
              <h3 className="mt-8 font-serif text-2xl leading-tight sm:text-3xl">
                {step.title}
              </h3>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                {step.description}
              </p>
              {index < guideSteps.length - 1 && (
                <span
                  aria-hidden="true"
                  className="absolute -bottom-3 left-8 z-10 hidden size-6 place-content-center rounded-full border bg-background lg:-right-3 lg:bottom-auto lg:left-auto lg:top-1/2 lg:grid lg:-translate-y-1/2"
                >
                  <ChevronRight className="size-3.5" />
                </span>
              )}
            </article>
          ))}
        </section>

        <section className="mt-8 flex flex-col items-start justify-between gap-6 rounded-2xl bg-primary px-6 py-6 text-primary-foreground sm:flex-row sm:items-center sm:px-8">
          <div>
            <p className="font-serif text-2xl sm:text-3xl">
              {dataset.offers.length} tilbud er klar til sammenligning
            </p>
            <p className="mt-2 text-sm leading-6 text-primary-foreground/75">
              Fra {activeProviderCount(dataset)} aktive udbydere · neutral
              kildeorden · ingen anbefalinger
            </p>
          </div>
          <CatalogueLink
            className="shrink-0 bg-primary-foreground text-primary hover:bg-primary-foreground/90"
            search={search}
          >
            Se alle {dataset.offers.length} tilbud
          </CatalogueLink>
        </section>
      </main>
    </div>
  );
}

function OfferImage({ offer }: { offer: CatalogueOffer }) {
  const [failed, setFailed] = useState(false);
  const source = offer.imageUrls[0];
  if (source === undefined || failed) {
    return (
      <div className="grid aspect-[16/9] place-content-center bg-secondary text-muted-foreground">
        <ImageOff aria-hidden="true" className="size-7" />
        <span className="sr-only">Intet billede</span>
      </div>
    );
  }
  return (
    <img
      alt=""
      className="aspect-[16/9] w-full object-cover"
      onError={() => setFailed(true)}
      referrerPolicy="no-referrer"
      src={source}
    />
  );
}

function providerName(dataset: CatalogueDataset, providerId: string) {
  return (
    dataset.providers.find((provider) => provider.id === providerId)?.name ??
    providerId
  );
}

function OfferPreview({
  dataset,
  offer,
}: {
  dataset: CatalogueDataset;
  offer: CatalogueOffer;
}) {
  return (
    <Card className="overflow-hidden">
      <OfferImage offer={offer} />
      <div className="p-4">
        <p className="text-xs text-muted-foreground">
          {providerName(dataset, offer.providerId)}
        </p>
        <h3 className="mt-1 font-serif text-xl leading-tight">
          {vehicleName(offer)}
        </h3>
        <dl className="mt-4 grid grid-cols-2 gap-3 border-t border-border pt-4">
          <div>
            <dt className="text-[0.68rem] font-bold uppercase tracking-[0.1em] text-muted-foreground">
              Månedsydelse
            </dt>
            <dd className="mt-1 font-semibold">
              {money(monthlyPayment(offer))}/md.
            </dd>
          </div>
          <div>
            <dt className="text-[0.68rem] font-bold uppercase tracking-[0.1em] text-muted-foreground">
              Beregnet total
            </dt>
            <dd className="mt-1 font-semibold">{money(offer.totalDkk)}</dd>
          </div>
        </dl>
      </div>
    </Card>
  );
}

function VariantC({ dataset, search }: { dataset: CatalogueDataset; search: LandingSearch }) {
  const previews = dataset.offers.slice(0, 3);
  return (
    <div>
      <LandingMasthead generatedAt={dataset.generatedAt} />
      <main className="mx-auto max-w-[92rem] px-5 pb-36 pt-8 sm:px-8 lg:pt-10">
        <section className="grid gap-8 lg:grid-cols-[19rem_minmax(0,1fr)] xl:grid-cols-[22rem_minmax(0,1fr)]">
          <div className="lg:sticky lg:top-8 lg:self-start">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary">
              Katalog over privatleasing
            </p>
            <h1 className="mt-3 font-serif text-4xl leading-[1.02] tracking-[-0.035em] sm:text-5xl">
              Se aftalerne på samme grundlag
            </h1>
            <p className="mt-5 text-sm leading-6 text-muted-foreground sm:text-base sm:leading-7">
              Gå direkte til tilbuddene. Bilvalg viser månedsydelsen sammen med
              startbetalingen, den beregnede total og aftalens afslutning.
            </p>
            <CatalogueLink
              className="mt-7 w-full sm:w-auto lg:w-full"
              search={search}
            >
              Se hele kataloget
            </CatalogueLink>

            <dl className="mt-8 grid grid-cols-2 gap-5 border-y border-border py-5">
              <div>
                <dt className="text-xs text-muted-foreground">Aktuelle tilbud</dt>
                <dd className="mt-1 font-serif text-3xl tabular-nums">
                  {dataset.offers.length}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Aktive udbydere</dt>
                <dd className="mt-1 font-serif text-3xl tabular-nums">
                  {activeProviderCount(dataset)}
                </dd>
              </div>
            </dl>
            <ul className="mt-5 grid gap-3 text-sm leading-5 text-muted-foreground">
              <li className="flex gap-2">
                <Check aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
                Dateret og afgrænset — ikke nødvendigvis hele markedet
              </li>
              <li className="flex gap-2">
                <Check aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
                Neutral kildeorden uden rangering
              </li>
              <li className="flex gap-2">
                <Check aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
                Direkte vej til udbyderens offentlige tilbud
              </li>
            </ul>
          </div>

          <div>
            <div className="flex flex-col gap-3 border-b border-border pb-5 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
                  <CircleDot aria-hidden="true" className="size-3 text-primary" />
                  Udsnit i neutral kildeorden
                </p>
                <h2 className="mt-2 font-serif text-3xl">Leasingtilbud</h2>
              </div>
              <p className="flex items-center gap-2 text-xs text-muted-foreground">
                <CalendarDays aria-hidden="true" className="size-4" />
                Data fra {date.format(new Date(dataset.generatedAt))}
              </p>
            </div>
            <div className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {previews.map((offer) => (
                <OfferPreview dataset={dataset} key={offer.offerIdentity} offer={offer} />
              ))}
            </div>
            <div className="mt-6 flex flex-col items-start justify-between gap-4 rounded-2xl border border-border bg-secondary/55 p-5 sm:flex-row sm:items-center">
              <div>
                <h2 className="font-semibold">Månedsydelsen er kun én linje</h2>
                <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
                  I kataloget får hvert tilbud én samlet faktavisning af betalinger,
                  periode, kilometer og afslutning.
                </p>
              </div>
              <CatalogueLink
                className="shrink-0"
                search={search}
                variant="outline"
              >
                Se alle {dataset.offers.length}
              </CatalogueLink>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export function LandingPagePrototype({
  dataset,
  search,
}: {
  dataset: CatalogueDataset;
  search: LandingSearch;
}) {
  const navigate = useNavigate({ from: "/prototype/landing" });
  const changeVariant = (variant: LandingSearch["variant"]) => {
    void navigate({ search: (previous) => ({ ...previous, variant }) });
  };

  return (
    <>
      {search.variant === "a" && <VariantA dataset={dataset} search={search} />}
      {search.variant === "b" && <VariantB dataset={dataset} search={search} />}
      {search.variant === "c" && <VariantC dataset={dataset} search={search} />}
      <PrototypeSwitcher
        current={search.variant}
        onChange={changeVariant}
        variants={variants}
      />
    </>
  );
}
