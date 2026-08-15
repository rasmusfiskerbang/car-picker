// PROTOTYPE — three provider-overview variants, switchable via ?variant=.
import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  Building2,
  CarFront,
  CheckCircle2,
  CircleOff,
  ExternalLink,
  FileWarning,
  Info,
} from "lucide-react";
import type { ReactNode } from "react";

import type { CatalogueDataset } from "@/catalogue-data";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { PrototypeSwitcher } from "@/prototype/prototype-switcher";
import type { ProviderSearch } from "@/routes/prototype.providers";

type Provider = CatalogueDataset["providers"][number];
type ProviderFacts = {
  provider: Provider;
  offerCount: number;
  quarantinedCount: number;
};

const date = new Intl.DateTimeFormat("da-DK", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

const inactiveReasonLabels = {
  blocked: "Blokeret",
  deferred: "Udskudt",
  ineligible: "Ikke omfattet",
} as const;

const variants = [
  { key: "a", name: "Offentligt register" },
  { key: "b", name: "Dækningskort" },
  { key: "c", name: "Udbydermapper" },
] as const;

function providerFacts(dataset: CatalogueDataset): ProviderFacts[] {
  return dataset.providers.map((provider) => ({
    provider,
    offerCount: dataset.offers.filter(
      (offer) => offer.providerId === provider.id,
    ).length,
    quarantinedCount: dataset.quarantinedCandidates.filter(
      (candidate) => candidate.providerId === provider.id,
    ).length,
  }));
}

function ProviderStatus({ provider }: { provider: Provider }) {
  if (provider.status === "active") {
    return (
      <Badge className="gap-1.5 border-primary/25 bg-accent text-accent-foreground hover:bg-accent">
        <CheckCircle2 aria-hidden="true" className="size-3.5" /> Aktiv
      </Badge>
    );
  }
  return (
    <Badge className="gap-1.5" variant="outline">
      <CircleOff aria-hidden="true" className="size-3.5" />
      {inactiveReasonLabels[provider.reason]}
    </Badge>
  );
}

function CatalogueLink({ facts }: { facts: ProviderFacts }) {
  if (facts.provider.status !== "active") return null;
  return (
    <Link
      className={buttonVariants({ variant: "default" })}
      search={{
        form: "all",
        power: "all",
        provider: facts.provider.id,
        q: "",
        selected: [],
        sort: "source",
        variant: "d",
      }}
      to="/catalogue"
    >
      Se {facts.offerCount} katalogtilbud
      <ArrowRight aria-hidden="true" />
    </Link>
  );
}

function ProviderWebsite({ provider }: { provider: Provider }) {
  return (
    <a
      className={buttonVariants({ variant: "outline" })}
      href={provider.url}
      rel="noreferrer"
      target="_blank"
    >
      Udbyderens website
      <ExternalLink aria-hidden="true" />
    </a>
  );
}

function RegistryMasthead({ generatedAt }: { generatedAt: string }) {
  return (
    <header className="border-b border-border/80 bg-background/90 backdrop-blur">
      <div className="mx-auto flex max-w-[92rem] items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <Link
          className="flex items-center gap-3 rounded-md"
          search={{
            form: "all",
            power: "all",
            provider: "all",
            q: "",
            selected: [],
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
              Udbyderregister
            </span>
          </span>
        </Link>
        <p className="hidden text-right text-xs text-muted-foreground sm:block">
          Katalogdatasæt fra {date.format(new Date(generatedAt))}
          <br />
          Tilbud og status kan være ændret siden
        </p>
      </div>
    </header>
  );
}

function ScopeNotice({ generatedAt }: { generatedAt: string }) {
  return (
    <aside
      aria-labelledby="scope-heading"
      className="rounded-2xl border border-border bg-secondary/55 p-5 sm:p-6"
    >
      <div className="flex gap-3">
        <Info aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-primary" />
        <div>
          <h2 className="font-semibold" id="scope-heading">
            Afgrænset kildegrundlag — ikke hele markedet
          </h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-muted-foreground">
            Visningen er en dateret kopi af udbyderregisteret i katalogdatasættet
            fra {date.format(new Date(generatedAt))}. Aktive udbydere indsamles kun
            fra de på forhånd valgte offentlige førstegangskilder. Inaktive
            udbydere deltager ikke. Tilbud uden den nødvendige dokumentation
            tælles som karantænesatte kandidater og vises ikke som katalogtilbud.
          </p>
        </div>
      </div>
    </aside>
  );
}

function Count({ children, label }: { children: number; label: string }) {
  return (
    <div>
      <p className="font-serif text-3xl tabular-nums">{children}</p>
      <p className="mt-1 text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function Intro({ dataset }: { dataset: CatalogueDataset }) {
  const active = dataset.providers.filter(
    (provider) => provider.status === "active",
  ).length;
  return (
    <div className="grid gap-6 border-b border-border pb-8 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary">
          Hvem kataloget omfatter
        </p>
        <h1 className="mt-3 max-w-4xl font-serif text-4xl leading-tight sm:text-6xl">
          Udbydere i det aktive katalog
        </h1>
        <p className="mt-4 max-w-3xl text-base leading-7 text-muted-foreground sm:text-lg">
          Se hvilke udbydere der deltager, hvilke der ikke gør, og hvor mange
          dokumenterede katalogtilbud der findes fra hver.
        </p>
      </div>
      <div className="flex gap-8 lg:pb-1">
        <Count label="aktive udbydere">{active}</Count>
        <Count label="registreret i alt">{dataset.providers.length}</Count>
      </div>
    </div>
  );
}

function MobileProviderRows({ facts }: { facts: ProviderFacts[] }) {
  return (
    <div className="grid gap-4 md:hidden">
      {facts.map((item) => (
        <Card key={item.provider.id}>
          <CardHeader className="flex-row items-start justify-between gap-3">
            <div>
              <h2 className="font-serif text-2xl">{item.provider.name}</h2>
              <a
                className="mt-1 inline-flex items-center gap-1 text-xs text-muted-foreground underline-offset-4 hover:underline"
                href={item.provider.url}
                rel="noreferrer"
                target="_blank"
              >
                {new URL(item.provider.url).hostname}
                <ExternalLink aria-hidden="true" className="size-3" />
              </a>
            </div>
            <ProviderStatus provider={item.provider} />
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 border-y border-border py-4">
              <Count label="katalogtilbud">{item.offerCount}</Count>
              <Count label="i karantæne">{item.quarantinedCount}</Count>
            </div>
            {item.provider.status === "inactive" && (
              <p className="mt-4 text-sm leading-6 text-muted-foreground">
                {item.provider.explanation}
              </p>
            )}
            <div className="mt-5 grid gap-2">
              <CatalogueLink facts={item} />
              <ProviderWebsite provider={item.provider} />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function VariantA({ dataset, facts }: VariantProps) {
  return (
    <PageFrame dataset={dataset}>
      <Intro dataset={dataset} />
      <section aria-labelledby="registry-table-heading" className="mt-8">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="font-serif text-3xl" id="registry-table-heading">
              Udbyderregister
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Alle registrerede udbydere, aktive og inaktive.
            </p>
          </div>
          <p className="text-xs text-muted-foreground">
            Status er gældende for dette katalogdatasæt
          </p>
        </div>

        <MobileProviderRows facts={facts} />
        <div className="hidden overflow-hidden rounded-2xl border border-border bg-card shadow-sm md:block">
          <table className="w-full border-collapse text-left text-sm">
            <thead className="bg-secondary/60 text-xs uppercase tracking-[0.12em] text-muted-foreground">
              <tr>
                <th className="px-5 py-4 font-bold">Udbyder</th>
                <th className="px-5 py-4 font-bold">Status</th>
                <th className="px-5 py-4 text-right font-bold">Tilbud</th>
                <th className="px-5 py-4 text-right font-bold">Karantæne</th>
                <th className="px-5 py-4 font-bold">Forklaring</th>
                <th className="px-5 py-4"><span className="sr-only">Handlinger</span></th>
              </tr>
            </thead>
            <tbody>
              {facts.map((item) => (
                <tr className="border-t border-border align-top" key={item.provider.id}>
                  <th className="px-5 py-5 font-semibold">
                    {item.provider.name}
                    <span className="mt-1 block text-xs font-normal text-muted-foreground">
                      {new URL(item.provider.url).hostname}
                    </span>
                  </th>
                  <td className="px-5 py-5"><ProviderStatus provider={item.provider} /></td>
                  <td className="px-5 py-5 text-right font-semibold tabular-nums">{item.offerCount}</td>
                  <td className="px-5 py-5 text-right font-semibold tabular-nums">{item.quarantinedCount}</td>
                  <td className="max-w-sm px-5 py-5 text-muted-foreground">
                    {item.provider.status === "active"
                      ? "Deltager via en afgrænset, forhåndsvalgt kilde."
                      : item.provider.explanation}
                  </td>
                  <td className="px-5 py-5 text-right">
                    {item.provider.status === "active" ? (
                      <Link
                        className="inline-flex items-center gap-1 font-semibold text-primary underline-offset-4 hover:underline"
                        search={{
                          form: "all",
                          power: "all",
                          provider: item.provider.id,
                          q: "",
                          selected: [],
                          sort: "source",
                          variant: "d",
                        }}
                        to="/catalogue"
                      >
                        Se tilbud <ArrowRight aria-hidden="true" className="size-4" />
                      </Link>
                    ) : (
                      <ProviderWebsite provider={item.provider} />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <div className="mt-8"><ScopeNotice generatedAt={dataset.generatedAt} /></div>
    </PageFrame>
  );
}

function ActiveProviderCard({ facts }: { facts: ProviderFacts }) {
  return (
    <Card className="flex min-h-80 flex-col">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <span className="grid size-11 place-content-center rounded-xl bg-accent text-accent-foreground">
            <Building2 aria-hidden="true" className="size-5" />
          </span>
          <ProviderStatus provider={facts.provider} />
        </div>
        <h3 className="mt-6 font-serif text-3xl">{facts.provider.name}</h3>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Tilbud hentes fra udbyderens afgrænsede offentlige kilde og optages
          kun, når katalogkravene er dokumenteret.
        </p>
      </CardHeader>
      <CardContent className="mt-auto">
        <div className="grid grid-cols-2 gap-4 border-y border-border py-4">
          <Count label="katalogtilbud">{facts.offerCount}</Count>
          <Count label="i karantæne">{facts.quarantinedCount}</Count>
        </div>
        <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
          <CatalogueLink facts={facts} />
          <ProviderWebsite provider={facts.provider} />
        </div>
      </CardContent>
    </Card>
  );
}

function VariantB({ dataset, facts }: VariantProps) {
  const active = facts.filter((item) => item.provider.status === "active");
  const inactive = facts.filter((item) => item.provider.status === "inactive");
  return (
    <PageFrame dataset={dataset}>
      <Intro dataset={dataset} />
      <div className="mt-8 grid gap-8 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <section aria-labelledby="participating-heading">
          <div className="flex items-center gap-3">
            <CheckCircle2 aria-hidden="true" className="size-5 text-primary" />
            <div>
              <h2 className="font-serif text-3xl" id="participating-heading">Deltager i kataloget</h2>
              <p className="mt-1 text-sm text-muted-foreground">Aktive udbydere med tilbud i den daterede udgivelse.</p>
            </div>
          </div>
          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            {active.map((item) => <ActiveProviderCard facts={item} key={item.provider.id} />)}
          </div>
        </section>

        <aside aria-labelledby="outside-heading" className="rounded-2xl border border-border bg-card p-5 shadow-sm sm:p-6">
          <CircleOff aria-hidden="true" className="size-5 text-muted-foreground" />
          <h2 className="mt-4 font-serif text-3xl" id="outside-heading">Deltager ikke</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Inaktiv betyder ikke, at udbyderen er dårligere. Den er blot ikke med i denne katalogudgivelse.
          </p>
          <div className="mt-6 grid gap-5">
            {inactive.map((item, index) => {
              if (item.provider.status === "active") return null;
              return (
                <div key={item.provider.id}>
                  {index > 0 && <Separator className="mb-5" />}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-semibold">{item.provider.name}</h3>
                    <ProviderStatus provider={item.provider} />
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.provider.explanation}</p>
                  <a className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-primary underline-offset-4 hover:underline" href={item.provider.url} rel="noreferrer" target="_blank">
                    Åbn website <ExternalLink aria-hidden="true" className="size-3.5" />
                  </a>
                </div>
              );
            })}
          </div>
        </aside>
      </div>
      <div className="mt-8"><ScopeNotice generatedAt={dataset.generatedAt} /></div>
    </PageFrame>
  );
}

function ProviderDetail({ facts }: { facts: ProviderFacts }) {
  const { provider } = facts;
  return (
    <Card className="overflow-hidden">
      <CardHeader className="border-b border-border bg-secondary/45 p-6 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <ProviderStatus provider={provider} />
          <span className="text-xs text-muted-foreground">ID: {provider.id}</span>
        </div>
        <h2 className="mt-6 font-serif text-4xl sm:text-5xl">{provider.name}</h2>
        <a className="mt-2 inline-flex items-center gap-1 text-sm text-muted-foreground underline-offset-4 hover:underline" href={provider.url} rel="noreferrer" target="_blank">
          {new URL(provider.url).hostname} <ExternalLink aria-hidden="true" className="size-3.5" />
        </a>
      </CardHeader>
      <CardContent className="p-6 sm:p-8">
        {provider.status === "active" ? (
          <>
            <div className="grid gap-6 sm:grid-cols-3">
              <Count label="katalogtilbud">{facts.offerCount}</Count>
              <Count label="karantænesatte kandidater">{facts.quarantinedCount}</Count>
              <div>
                <p className="font-serif text-3xl">Aktiv</p>
                <p className="mt-1 text-xs text-muted-foreground">i denne udgivelse</p>
              </div>
            </div>
            <Separator className="my-7" />
            <div className="grid gap-6 lg:grid-cols-2">
              <div>
                <h3 className="font-semibold">Kildeafgrænsning</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Kataloget bruger kun den adapterdefinerede, forhåndsvalgte offentlige kilde. Andre sider, annoncer og tredjepartskilder medregnes ikke.
                </p>
              </div>
              <div>
                <h3 className="font-semibold">Hvad karantæne betyder</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  En kandidat vises ikke som katalogtilbud, når et krævet forhold er manglende, uklart, modstridende eller ugyldigt.
                </p>
              </div>
            </div>
            <div className="mt-8 flex flex-col gap-2 sm:flex-row">
              <CatalogueLink facts={facts} />
              <ProviderWebsite provider={provider} />
            </div>
          </>
        ) : (
          <>
            <div className="flex gap-3 rounded-xl border border-border bg-muted/50 p-4">
              <FileWarning aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
              <div>
                <h3 className="font-semibold">Hvorfor udbyderen ikke deltager</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{provider.explanation}</p>
              </div>
            </div>
            <p className="mt-6 text-sm leading-6 text-muted-foreground">
              Der indsamles ingen katalogkandidater fra denne udbyder i den viste udgivelse. Status siger kun noget om katalogets afgrænsning — ikke om udbyderens kvalitet.
            </p>
            <div className="mt-8"><ProviderWebsite provider={provider} /></div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function VariantC({ dataset, facts, search, setProvider }: VariantProps) {
  const selected = facts.find((item) => item.provider.id === search.provider) ?? facts[0];
  return (
    <PageFrame dataset={dataset}>
      <Intro dataset={dataset} />
      <div className="mt-8 grid gap-6 lg:grid-cols-[18rem_minmax(0,1fr)] xl:grid-cols-[21rem_minmax(0,1fr)]">
        <nav aria-label="Vælg udbyder">
          <label className="grid gap-2 text-sm font-semibold lg:hidden">
            <span>Udbyder</span>
            <select className="h-11 rounded-md border border-input bg-card px-3" onChange={(event) => setProvider(event.target.value)} value={selected.provider.id}>
              {facts.map((item) => <option key={item.provider.id} value={item.provider.id}>{item.provider.name} — {item.provider.status === "active" ? "Aktiv" : inactiveReasonLabels[item.provider.reason]}</option>)}
            </select>
          </label>
          <div className="hidden overflow-hidden rounded-2xl border border-border bg-card shadow-sm lg:block">
            <p className="border-b border-border px-4 py-3 text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">Alle udbydere</p>
            {facts.map((item) => {
              const current = item.provider.id === selected.provider.id;
              return (
                <button
                  aria-current={current ? "page" : undefined}
                  className={cn("flex w-full items-center justify-between gap-3 border-b border-border px-4 py-4 text-left transition-colors last:border-b-0 hover:bg-accent/50", current && "bg-accent")}
                  key={item.provider.id}
                  onClick={() => setProvider(item.provider.id)}
                  type="button"
                >
                  <span>
                    <span className="block font-semibold">{item.provider.name}</span>
                    <span className="mt-1 block text-xs text-muted-foreground">{item.provider.status === "active" ? `${item.offerCount} katalogtilbud` : inactiveReasonLabels[item.provider.reason]}</span>
                  </span>
                  <ArrowRight aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
                </button>
              );
            })}
          </div>
        </nav>
        <ProviderDetail facts={selected} />
      </div>
      <div className="mt-8"><ScopeNotice generatedAt={dataset.generatedAt} /></div>
    </PageFrame>
  );
}

function PageFrame({ children, dataset }: { children: ReactNode; dataset: CatalogueDataset }) {
  return (
    <div className="min-h-screen pb-28">
      <RegistryMasthead generatedAt={dataset.generatedAt} />
      <main className="mx-auto max-w-[92rem] px-4 py-8 sm:px-6 sm:py-12 lg:px-8">{children}</main>
    </div>
  );
}

type VariantProps = {
  dataset: CatalogueDataset;
  facts: ProviderFacts[];
  search: ProviderSearch;
  setProvider: (provider: string) => void;
};

export function ProviderOverviewPrototype({ dataset, search }: { dataset: CatalogueDataset; search: ProviderSearch }) {
  const navigate = useNavigate({ from: "/prototype/providers" });
  const setVariant = (variant: ProviderSearch["variant"]) => {
    void navigate({ search: (previous) => ({ ...previous, variant }) });
  };
  const setProvider = (provider: string) => {
    void navigate({ search: (previous) => ({ ...previous, provider }) });
  };
  const props = { dataset, facts: providerFacts(dataset), search, setProvider };
  return (
    <>
      {search.variant === "a" && <VariantA {...props} />}
      {search.variant === "b" && <VariantB {...props} />}
      {search.variant === "c" && <VariantC {...props} />}
      <PrototypeSwitcher current={search.variant} onChange={setVariant} variants={variants} />
    </>
  );
}
