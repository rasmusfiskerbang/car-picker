import { z } from "zod";

import generatedCatalogueDatasetJsonSchema from "./generated/catalogue-dataset-schema";
import type { CatalogueDataset } from "./generated/catalogue-dataset";

export const catalogueDatasetJsonSchema = generatedCatalogueDatasetJsonSchema;
export const catalogueDatasetSchemaVersion =
  catalogueDatasetJsonSchema.properties.schemaVersion.const;

/**
 * Audited bridge from the generated JSON Schema to Zod.
 *
 * Zod 4 validates the JSON Schema at runtime, but its JSON-Schema helper cannot
 * infer the named TypeScript unions emitted by json-schema-to-typescript. Keep
 * that one broad assertion here so application code never needs a cast.
 */
export const catalogueDatasetValidator = z.fromJSONSchema(
  catalogueDatasetJsonSchema as never,
) as unknown as z.ZodType<CatalogueDataset>;
