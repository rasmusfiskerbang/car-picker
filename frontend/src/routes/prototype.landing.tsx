import { useSuspenseQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";

import { catalogueDatasetQuery } from "@/catalogue-data";
import { Skeleton } from "@/components/ui/skeleton";
import { LandingPagePrototype } from "@/prototype/landing-page";
import { optionalApplicationShellSearch } from "@/prototype/application-shell-state";

const landingSearchSchema = z.object({
  ...optionalApplicationShellSearch,
  variant: z.enum(["a", "b", "c"]).catch("a"),
  selected: z.array(z.string()).catch([]),
});

export type LandingSearch = z.infer<typeof landingSearchSchema>;

function LandingPage() {
  const { data } = useSuspenseQuery(catalogueDatasetQuery);
  const search = Route.useSearch();
  return (
    <LandingPagePrototype
      dataset={data}
      search={search.shell === undefined ? search : { ...search, variant: "b" }}
    />
  );
}

function LandingPending() {
  return (
    <main className="mx-auto max-w-[92rem] px-5 py-10 sm:px-8">
      <Skeleton className="h-10 w-36" />
      <Skeleton className="mt-16 h-28 max-w-3xl" />
      <div className="mt-10 grid gap-5 lg:grid-cols-3">
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
      </div>
    </main>
  );
}

export const Route = createFileRoute("/prototype/landing")({
  component: LandingPage,
  loader: ({ context }) =>
    context.queryClient.ensureQueryData(catalogueDatasetQuery),
  pendingComponent: LandingPending,
  validateSearch: landingSearchSchema,
});
