import { Outlet, createRootRouteWithContext } from "@tanstack/react-router";

import type { RouterContext } from "@/router";

function RootLayout() {
  return <Outlet />;
}

function InvalidApplication() {
  return (
    <main className="mx-auto grid min-h-screen max-w-2xl place-content-center px-6 text-center">
      <p className="text-sm font-bold uppercase tracking-[0.18em] text-destructive">
        Ugyldigt katalog
      </p>
      <h1 className="mt-3 font-serif text-4xl">Kataloget kan ikke vises</h1>
      <p className="mt-4 text-muted-foreground">
        Den publicerede fil følger ikke den forventede kontrakt. Ingen tilbud er
        vist.
      </p>
    </main>
  );
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootLayout,
  errorComponent: InvalidApplication,
});
