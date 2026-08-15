import { useSuspenseQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";

import { catalogueDatasetQuery } from "@/catalogue-data";
import { Skeleton } from "@/components/ui/skeleton";
import { CatalogueOverviewPrototype } from "@/prototype/catalogue-overview";

const catalogueSearchSchema = z.object({
  variant: z.enum(["a", "b", "c", "d"]).catch("a"),
  q: z.string().catch(""),
  provider: z.string().catch("all"),
  form: z
    .enum(["all", "financial", "flex", "operational", "hybrid"])
    .catch("all"),
  power: z.enum(["all", "battery_electric", "combustion"]).catch("all"),
  sort: z.enum(["source", "monthly", "upfront", "total"]).catch("source"),
  selected: z.array(z.string()).catch([]),
});

export type CatalogueSearch = z.infer<typeof catalogueSearchSchema>;

function CataloguePage() {
  const { data } = useSuspenseQuery(catalogueDatasetQuery);
  const search = Route.useSearch();
  return <CatalogueOverviewPrototype dataset={data} search={search} />;
}

function CataloguePending() {
  return (
    <main className="mx-auto max-w-[92rem] px-6 py-16">
      <Skeleton className="h-5 w-36" />
      <Skeleton className="mt-4 h-20 max-w-2xl" />
      <div className="mt-10 grid gap-5 md:grid-cols-3">
        <Skeleton className="h-96" />
        <Skeleton className="h-96" />
        <Skeleton className="h-96" />
      </div>
    </main>
  );
}

export const Route = createFileRoute("/catalogue")({
  component: CataloguePage,
  loader: ({ context }) =>
    context.queryClient.ensureQueryData(catalogueDatasetQuery),
  pendingComponent: CataloguePending,
  validateSearch: catalogueSearchSchema,
});
