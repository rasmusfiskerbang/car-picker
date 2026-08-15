import { useSuspenseQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";

import { catalogueDatasetQuery } from "@/catalogue-data";
import { Skeleton } from "@/components/ui/skeleton";
import { SelectedOfferComparisonPrototype } from "@/prototype/selected-offer-comparison";

const defaultSelection = [
  "fleasing:prototype-00:config-0",
  "terminalen:prototype-01:config-1",
  "terminalen:prototype-05:config-2",
] as const;

const comparisonSearchSchema = z.object({
  variant: z.enum(["a", "b", "c"]).catch("a"),
  selected: z.array(z.string()).catch([...defaultSelection]),
});

export type ComparisonSearch = z.infer<typeof comparisonSearchSchema>;

function ComparisonPage() {
  const { data } = useSuspenseQuery(catalogueDatasetQuery);
  const search = Route.useSearch();
  return <SelectedOfferComparisonPrototype dataset={data} search={search} />;
}

function ComparisonPending() {
  return (
    <main className="mx-auto max-w-[96rem] px-4 py-10 sm:px-8">
      <Skeleton className="h-5 w-52" />
      <Skeleton className="mt-6 h-16 max-w-2xl" />
      <div className="mt-10 grid grid-cols-3 gap-4">
        <Skeleton className="h-[34rem]" />
        <Skeleton className="h-[34rem]" />
        <Skeleton className="h-[34rem]" />
      </div>
    </main>
  );
}

export const Route = createFileRoute("/prototype/compare")({
  component: ComparisonPage,
  loader: ({ context }) =>
    context.queryClient.ensureQueryData(catalogueDatasetQuery),
  pendingComponent: ComparisonPending,
  validateSearch: comparisonSearchSchema,
});
