import { z } from "zod";

export const applicationShellVariantSchema = z.enum(["a", "b", "c"]);

export type ApplicationShellVariant = z.infer<
  typeof applicationShellVariantSchema
>;

export const optionalApplicationShellSearch = {
  shell: applicationShellVariantSchema.optional(),
};
