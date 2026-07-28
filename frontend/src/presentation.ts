import { z } from "zod";

import presentationJsonSchema from "@/generated/presentation-schema.json";
import type { CataloguePresentation } from "@/generated/presentation";

export type { CataloguePresentation } from "@/generated/presentation";
export const presentationValidator: z.ZodType<CataloguePresentation> =
  z.fromJSONSchema(presentationJsonSchema as never) as z.ZodType<CataloguePresentation>;

export async function loadPresentation(): Promise<CataloguePresentation> {
  const response = await fetch("./projection.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Katalogdata kunne ikke hentes.");
  }
  return presentationValidator.parse(await response.json());
}
