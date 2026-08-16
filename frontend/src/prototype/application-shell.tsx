// PROTOTYPE — three application-shell variants, switchable via ?shell=.
// The accepted page prototypes are deliberately embedded unchanged beneath the shell.
import { Link, useRouterState } from "@tanstack/react-router";
import {
  Building2,
  CalendarDays,
  CarFront,
  Home,
  Menu,
  Scale,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useState, type ReactNode } from "react";

import type { CatalogueDataset } from "@/catalogue-data";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import {
  type ApplicationShellVariant,
  applicationShellVariantSchema,
} from "@/prototype/application-shell-state";
import { PrototypeSwitcher } from "@/prototype/prototype-switcher";

const variants = [
  { key: "a", name: "Rolig toplinje" },
  { key: "b", name: "Registerrail" },
  { key: "c", name: "Kontekstbånd" },
] as const;

const date = new Intl.DateTimeFormat("da-DK", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

type ShellProps = {
  children: ReactNode;
  dataset: CatalogueDataset;
  selected: string[];
  variant: ApplicationShellVariant;
};

function activeProviderCount(dataset: CatalogueDataset) {
  return dataset.providers.filter((provider) => provider.status === "active")
    .length;
}

function isCurrent(pathname: string, destination: "landing" | "catalogue" | "compare" | "providers") {
  if (destination === "landing") return pathname === "/prototype/landing";
  if (destination === "catalogue") return pathname === "/catalogue";
  if (destination === "compare") return pathname === "/prototype/compare";
  return pathname === "/prototype/providers";
}

function NavLinks({
  compact = false,
  includeLanding = true,
  onNavigate,
  selected,
  variant,
}: {
  compact?: boolean;
  includeLanding?: boolean;
  onNavigate?: () => void;
  selected: string[];
  variant: ApplicationShellVariant;
}) {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });
  const linkClass = (current: boolean) =>
    cn(
      "flex items-center gap-2 rounded-lg font-semibold transition-colors",
      compact ? "px-3 py-2 text-xs" : "px-3 py-2.5 text-sm",
      current
        ? "bg-accent text-accent-foreground"
        : "text-muted-foreground hover:bg-secondary hover:text-foreground",
    );

  return (
    <>
      {includeLanding && (
        <Link
          aria-current={isCurrent(pathname, "landing") ? "page" : undefined}
          className={linkClass(isCurrent(pathname, "landing"))}
          onClick={onNavigate}
          search={{ selected, shell: variant, variant: "b" }}
          to="/prototype/landing"
        >
          <Home aria-hidden="true" className="size-4" /> Forside
        </Link>
      )}
      <Link
        aria-current={isCurrent(pathname, "catalogue") ? "page" : undefined}
        className={linkClass(isCurrent(pathname, "catalogue"))}
        onClick={onNavigate}
        search={{
          form: "all",
          power: "all",
          provider: "all",
          q: "",
          selected,
          shell: variant,
          sort: "source",
          variant: "d",
        }}
        to="/catalogue"
      >
        <Search aria-hidden="true" className="size-4" /> Tilbud
      </Link>
      <Link
        aria-current={isCurrent(pathname, "compare") ? "page" : undefined}
        className={linkClass(isCurrent(pathname, "compare"))}
        onClick={onNavigate}
        search={{ selected, shell: variant, variant: "a" }}
        to="/prototype/compare"
      >
        <Scale aria-hidden="true" className="size-4" /> Sammenlign
        {selected.length > 0 && (
          <span className="ml-auto grid size-5 place-content-center rounded-full bg-primary text-[0.65rem] text-primary-foreground">
            {selected.length}
          </span>
        )}
      </Link>
      <Link
        aria-current={isCurrent(pathname, "providers") ? "page" : undefined}
        className={linkClass(isCurrent(pathname, "providers"))}
        onClick={onNavigate}
        search={{
          provider: "fleasing",
          selected,
          shell: variant,
          variant: "a",
        }}
        to="/prototype/providers"
      >
        <Building2 aria-hidden="true" className="size-4" /> Udbydere
      </Link>
    </>
  );
}

function Brand({ selected, variant }: Pick<ShellProps, "selected" | "variant">) {
  return (
    <Link
      aria-label="Bilvalg — gå til forsiden"
      className="flex shrink-0 items-center gap-3 rounded-md"
      search={{ selected, shell: variant, variant: "b" }}
      to="/prototype/landing"
    >
      <span className="grid size-9 place-content-center rounded-full bg-primary text-primary-foreground">
        <CarFront aria-hidden="true" className="size-5" />
      </span>
      <span>
        <span className="block font-serif text-xl leading-none">Bilvalg</span>
        <span className="mt-1 block text-[0.64rem] font-bold uppercase tracking-[0.16em] text-muted-foreground">
          Privatleasing
        </span>
      </span>
    </Link>
  );
}

function CompareAction({
  selected,
  variant,
}: Pick<ShellProps, "selected" | "variant">) {
  return (
    <Link
      className={cn(
        buttonVariants({ size: "sm", variant: selected.length > 0 ? "default" : "outline" }),
        "shrink-0 gap-2",
      )}
      search={{ selected, shell: variant, variant: "a" }}
      to="/prototype/compare"
    >
      <Scale aria-hidden="true" className="size-4" />
      <span>{selected.length > 0 ? `${selected.length} valgt` : "Sammenlign"}</span>
    </Link>
  );
}

function DatasetContext({ dataset }: Pick<ShellProps, "dataset">) {
  return (
    <div className="flex items-center gap-2 text-xs leading-5 text-muted-foreground">
      <CalendarDays aria-hidden="true" className="size-4 shrink-0" />
      <span>
        Katalogdata fra {date.format(new Date(dataset.generatedAt))} ·{" "}
        {activeProviderCount(dataset)} aktive udbydere
      </span>
    </div>
  );
}

function ShellContent({ children }: { children: ReactNode }) {
  return <div className="application-shell-content min-w-0">{children}</div>;
}

function VariantA({ children, dataset, selected, variant }: ShellProps) {
  return (
    <div className="min-h-screen pb-16 md:pb-0">
      <header className="sticky top-0 z-30 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-[96rem] items-center justify-between gap-5 px-4 py-3 sm:px-6 lg:px-8">
          <Brand selected={selected} variant={variant} />
          <nav aria-label="Primær navigation" className="hidden items-center gap-1 md:flex">
            <NavLinks compact selected={selected} variant={variant} />
          </nav>
          <CompareAction selected={selected} variant={variant} />
        </div>
        <div className="border-t bg-secondary/45">
          <div className="mx-auto flex max-w-[96rem] items-center justify-between gap-4 px-4 py-2 sm:px-6 lg:px-8">
            <DatasetContext dataset={dataset} />
            <span className="hidden text-xs text-muted-foreground sm:inline">
              Afgrænset katalog · ingen rangering
            </span>
          </div>
        </div>
      </header>
      <ShellContent>{children}</ShellContent>
      <footer className="border-t bg-card">
        <div className="mx-auto flex max-w-[96rem] flex-col gap-3 px-5 py-8 text-xs leading-5 text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <p>Tilbud kan være ændret siden datasættet blev genereret. Tjek altid udbyderens original.</p>
          <p>Kataloget dækker navngivne udbydere, ikke nødvendigvis hele markedet.</p>
        </div>
      </footer>
      <nav
        aria-label="Mobil navigation"
        className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-4 border-t bg-background/97 px-1 py-1.5 backdrop-blur md:hidden"
      >
        <NavLinks compact selected={selected} variant={variant} />
      </nav>
    </div>
  );
}

function MobileRailMenu({ dataset, selected, variant }: Omit<ShellProps, "children">) {
  const [open, setOpen] = useState(false);
  return (
    <Sheet onOpenChange={setOpen} open={open}>
      <SheetTrigger asChild>
        <Button aria-label="Åbn navigation" size="icon" variant="outline">
          <Menu aria-hidden="true" className="size-4" />
        </Button>
      </SheetTrigger>
      <SheetContent className="flex flex-col" side="left">
        <SheetHeader className="text-left">
          <SheetTitle>Bilvalg</SheetTitle>
        </SheetHeader>
        <nav aria-label="Primær navigation" className="mt-8 grid gap-1">
          <NavLinks
            onNavigate={() => setOpen(false)}
            selected={selected}
            variant={variant}
          />
        </nav>
        <div className="mt-auto border-t pt-5">
          <DatasetContext dataset={dataset} />
          <p className="mt-3 text-xs leading-5 text-muted-foreground">
            Navngivne udbydere · ikke nødvendigvis hele markedet.
          </p>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function VariantB({ children, dataset, selected, variant }: ShellProps) {
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[15.5rem_minmax(0,1fr)]">
      <aside className="sticky top-0 hidden h-screen flex-col border-r bg-card p-5 lg:flex">
        <Brand selected={selected} variant={variant} />
        <nav aria-label="Primær navigation" className="mt-10 grid gap-1">
          <NavLinks selected={selected} variant={variant} />
        </nav>
        <div className="mt-auto border-t pt-5">
          <DatasetContext dataset={dataset} />
          <div className="mt-5">
            <CompareAction selected={selected} variant={variant} />
          </div>
          <p className="mt-4 text-[0.7rem] leading-5 text-muted-foreground">
            Afgrænset katalog uden rangering. Tjek altid originalkilden.
          </p>
        </div>
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-30 flex items-center justify-between border-b bg-background/95 px-4 py-3 backdrop-blur lg:hidden">
          <MobileRailMenu dataset={dataset} selected={selected} variant={variant} />
          <Brand selected={selected} variant={variant} />
          <CompareAction selected={selected} variant={variant} />
        </header>
        <ShellContent>{children}</ShellContent>
      </div>
    </div>
  );
}

function VariantC({ children, dataset, selected, variant }: ShellProps) {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const pageTitle = pathname === "/catalogue"
    ? "Tilbud"
    : pathname === "/prototype/compare"
      ? "Sammenligning"
      : pathname === "/prototype/providers"
        ? "Udbyderregister"
        : pathname.startsWith("/prototype/offers/")
          ? "Tilbuddet"
          : "Forside";

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b bg-background/95 backdrop-blur">
        <div className="bg-primary text-primary-foreground">
          <div className="mx-auto flex max-w-[96rem] items-center justify-between gap-4 px-4 py-1.5 text-[0.68rem] sm:px-6 lg:px-8">
            <span className="flex items-center gap-2">
              <ShieldCheck aria-hidden="true" className="size-3.5" />
              Afgrænset, neutralt katalog
            </span>
            <span>Data fra {date.format(new Date(dataset.generatedAt))}</span>
          </div>
        </div>
        <div className="mx-auto flex max-w-[96rem] items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
          <Brand selected={selected} variant={variant} />
          <div className="hidden h-7 w-px bg-border sm:block" />
          <p className="hidden font-serif text-lg sm:block">{pageTitle}</p>
          <nav aria-label="Primær navigation" className="ml-auto hidden items-center gap-1 lg:flex">
            <NavLinks
              compact
              includeLanding={false}
              selected={selected}
              variant={variant}
            />
          </nav>
        </div>
        <nav
          aria-label="Mobil navigation"
          className="flex gap-1 overflow-x-auto border-t px-3 py-1.5 lg:hidden"
        >
          <NavLinks
            compact
            includeLanding={false}
            selected={selected}
            variant={variant}
          />
        </nav>
      </header>
      <ShellContent>{children}</ShellContent>
    </div>
  );
}

export function ApplicationShellPrototype({
  children,
  dataset,
}: {
  children: ReactNode;
  dataset: CatalogueDataset;
}) {
  const search = useRouterState({ select: (state) => state.location.search });
  const variantResult = applicationShellVariantSchema.safeParse(search.shell);
  if (!variantResult.success) return children;

  const selected = Array.isArray(search.selected)
    ? search.selected.filter((value): value is string => typeof value === "string")
    : [];
  const variant = variantResult.data;
  const props = { dataset, selected, variant };
  const changeVariant = (next: ApplicationShellVariant) => {
    const [pathname, query = ""] = window.location.hash.slice(1).split("?");
    const params = new URLSearchParams(query);
    params.set("shell", next);
    window.location.hash = `${pathname}?${params.toString()}`;
  };

  return (
    <div className="application-shell-prototype">
      {variant === "a" && <VariantA {...props}>{children}</VariantA>}
      {variant === "b" && <VariantB {...props}>{children}</VariantB>}
      {variant === "c" && <VariantC {...props}>{children}</VariantC>}
      <div className="application-shell-switcher">
        <PrototypeSwitcher
          current={variant}
          onChange={changeVariant}
          variants={variants}
        />
      </div>
    </div>
  );
}
