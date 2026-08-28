import { createContext, useContext, type ReactNode } from "react";

import {
  type CatalogueDataset,
  type CatalogueDatasetIndex,
  loadCatalogueDataset,
} from "@/catalogue-dataset";

export const catalogueDatasetQueryOptions = {
  queryKey: ["catalogue-dataset"] as const,
  queryFn: () => loadCatalogueDataset(),
  retry: false,
  staleTime: Infinity,
};

type CatalogueDatasetContextValue = {
  dataset: CatalogueDataset;
  index: CatalogueDatasetIndex;
};

const CatalogueDatasetContext = createContext<
  CatalogueDatasetContextValue | undefined
>(undefined);

export function CatalogueDatasetProvider({
  children,
  dataset,
  index,
}: CatalogueDatasetContextValue & { children: ReactNode }) {
  return (
    <CatalogueDatasetContext.Provider value={{ dataset, index }}>
      {children}
    </CatalogueDatasetContext.Provider>
  );
}

export function useCatalogueDataset(): CatalogueDatasetContextValue {
  const value = useContext(CatalogueDatasetContext);
  if (value === undefined) {
    throw new Error(
      "useCatalogueDataset must be used inside CatalogueDatasetProvider",
    );
  }
  return value;
}
