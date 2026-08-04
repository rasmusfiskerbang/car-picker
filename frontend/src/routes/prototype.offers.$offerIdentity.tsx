import { useSuspenseQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";

import { catalogueDatasetQuery } from "@/catalogue-data";
import { Skeleton } from "@/components/ui/skeleton";
import { CatalogueOfferDetailPrototype } from "@/prototype/catalogue-offer-detail";

const detailSearchSchema = z.object({
  variant: z.enum(["a", "b", "c"]).catch("a"),
  selected: z.array(z.string()).catch([]),
});

export type OfferDetailSearch = z.infer<typeof detailSearchSchema>;

function OfferDetailPage() {
  const { data } = useSuspenseQuery(catalogueDatasetQuery);
  const { offerIdentity } = Route.useParams();
  const search = Route.useSearch();
  const offer = data.offers.find(
    (candidate) => candidate.offerIdentity === offerIdentity,
  );

  if (offer === undefined) {
    return (
      <main className="mx-auto grid min-h-screen max-w-xl place-content-center px-6 text-center">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-destructive">
          Tilbuddet findes ikke
        </p>
        <h1 className="mt-3 font-serif text-4xl">Ingen katalogpost matcher</h1>
        <p className="mt-4 text-muted-foreground">
          Tilbuddet er ikke med i dette genererede katalogdatasæt.
        </p>
      </main>
    );
  }

  return (
    <CatalogueOfferDetailPrototype
      dataset={data}
      key={offer.offerIdentity}
      offer={offer}
      search={search}
    />
  );
}

function OfferDetailPending() {
  return (
    <main className="mx-auto max-w-[92rem] px-5 py-10 sm:px-8">
      <Skeleton className="h-5 w-52" />
      <div className="mt-8 grid gap-8 lg:grid-cols-[1.4fr_0.8fr]">
        <Skeleton className="aspect-[16/10]" />
        <Skeleton className="min-h-96" />
      </div>
    </main>
  );
}

export const Route = createFileRoute("/prototype/offers/$offerIdentity")({
  component: OfferDetailPage,
  loader: ({ context }) =>
    context.queryClient.ensureQueryData(catalogueDatasetQuery),
  pendingComponent: OfferDetailPending,
  validateSearch: detailSearchSchema,
});
