import { useSuspenseQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";

import { catalogueDatasetQuery } from "@/catalogue-data";
import { Skeleton } from "@/components/ui/skeleton";
import { ProviderOverviewPrototype } from "@/prototype/provider-overview";
import { optionalApplicationShellSearch } from "@/prototype/application-shell-state";

const providerSearchSchema = z.object({
  ...optionalApplicationShellSearch,
  variant: z.enum(["a", "b", "c"]).catch("a"),
  provider: z.string().catch("fleasing"),
  selected: z.array(z.string()).catch([]),
});

export type ProviderSearch = z.infer<typeof providerSearchSchema>;

function ProviderOverviewPage() {
  const { data } = useSuspenseQuery(catalogueDatasetQuery);
  const search = Route.useSearch();
  return (
    <ProviderOverviewPrototype
      dataset={data}
      search={search.shell === undefined ? search : { ...search, variant: "a" }}
    />
  );
}

function ProviderOverviewPending() {
  return (
    <main className="mx-auto max-w-[92rem] px-5 py-10 sm:px-8">
      <Skeleton className="h-5 w-52" />
      <Skeleton className="mt-6 h-16 max-w-2xl" />
      <div className="mt-10 grid gap-5 lg:grid-cols-3">
        <Skeleton className="h-80" />
        <Skeleton className="h-80" />
        <Skeleton className="h-80" />
      </div>
    </main>
  );
}

export const Route = createFileRoute("/prototype/providers")({
  component: ProviderOverviewPage,
  loader: ({ context }) =>
    context.queryClient.ensureQueryData(catalogueDatasetQuery),
  pendingComponent: ProviderOverviewPending,
  validateSearch: providerSearchSchema,
});
