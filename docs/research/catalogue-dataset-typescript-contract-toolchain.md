# CatalogueDataset Python-to-TypeScript contract toolchain research

Research snapshot: 2026-08-02

This is a decision record for issue #52. It is research only: no production code, generated frontend artifacts, or GitHub issue state was changed.

## Executive recommendation

For this repository, keep the prototype's v1 seam:

1. Treat the Pydantic `CatalogueDataset.model_json_schema(mode="serialization", by_alias=True)` result as the only contract authority.
2. Generate a TypeScript schema constant and a `.d.ts` type from that same schema object.
3. Convert the schema to Zod with the repository's installed Zod 4.4.3 `z.fromJSONSchema()`.
4. Keep one small, named, audited cast from the converted `ZodType` to the generated type, then expose `z.infer` from that typed schema.

This is the best fit when Zod's parser/error API is part of the desired TypeScript experience. It was exercised against the repository's real schema and fixture. The cast is acceptable only at this generated boundary and only with build-time parity tests; it must not become a handwritten domain interface.

If exact JSON Schema semantics are more important than Zod ergonomics, the stronger runtime choice is Ajv 2020-12 against the original schema, paired with the same generated `.d.ts` type. Ajv avoids a JSON-Schema-to-Zod translation step and can emit standalone validation code. It needs a small compatibility decision for Pydantic's OpenAPI-style `discriminator.mapping` annotation.

Do not adopt `json-schema-to-zod` for production. Its upstream repository is archived, its README says it is no longer actively maintained, and it explicitly warns that conversion can lose schema details.

## Repository baseline

The relevant existing design is documented in [`03-python-to-typescript-seam.md`](../prototypes/catalogue-dataset-contract/03-python-to-typescript-seam.md). It already establishes the important boundaries:

- Pydantic serialization-mode JSON Schema is authoritative for the browser contract.
- There is no handwritten duplicate `CatalogueDataset` interface and no presentation/projection model.
- Whole-dataset identity, provider, and count invariants remain Python responsibilities; they are not shape constraints that the browser schema can reproduce.
- The proposed generated type plus one isolated Zod cast is intentionally a seam, not a second source of truth.

The current frontend dependency set is:

| Dependency | Manifest range | Locked/verified version | Role |
| --- | --- | --- | --- |
| `zod` | `^4.0.14` | 4.4.3 | Runtime schema/parser API |
| `json-schema-to-typescript` | `^15.0.4` | 15.0.4 | Build-time `.d.ts` generation |
| TypeScript | `^5.8.3` | 5.9.3 | Static checking |
| Pydantic | `>=2.12,<3` | 2.13.4 in the local Python environment | Schema authority |

The lockfile also already contains `@apidevtools/json-schema-ref-parser`, although it is not required by the recommended baseline.

## Shape of the actual Pydantic schema

The local schema was generated from the repository's real `CatalogueDataset` model using Pydantic 2.13.4. The emitted object has no root `$schema` member, so consumers must select Draft 2020-12 explicitly rather than relying on auto-detection. Its observed features are:

| Feature | Observed output |
| --- | --- |
| Reusable definitions | 26 `$defs` entries |
| Local references | `#/$defs/...` `$ref`s; 90 references in the serialized JSON representation |
| Closed objects | `additionalProperties: false` at the root and throughout the model because the shared base config uses `extra="forbid"` |
| Discriminated unions | `oneOf` branches plus OpenAPI-style `discriminator` objects and mappings; 30 of each in the serialized representation |
| Nullable/branching values | `anyOf` branches, including nullability |
| Numeric constraints | `minimum` and `exclusiveMinimum`, including constraints nested in nullable branches |
| Serialization aliases | camelCase properties such as `schemaVersion`, `generatedAt`, and `catalogueOffers` |

Pydantic documents its JSON Schema output as Draft 2020-12-compatible and OpenAPI 3.1-compatible, supports separate validation and serialization schema modes, emits `$defs`/local `$ref`s for submodels, and emits discriminator metadata for discriminated unions. The repository correctly uses serialization mode for data sent to the browser. Pydantic's `extra="forbid"` is the source of the closed-object behavior observed here.

Primary references: [Pydantic JSON Schema](https://pydantic.dev/docs/validation/latest/concepts/json_schema/), [`BaseModel.model_json_schema`](https://pydantic.dev/docs/validation/latest/api/pydantic/base_model/), [Pydantic model config](https://pydantic.dev/docs/validation/latest/api/pydantic/config/), and [Pydantic unions](https://pydantic.dev/docs/validation/latest/concepts/unions/).

The absent root `$schema` matters. JSON Schema says that `$schema` identifies the dialect and that behavior without it is implementation-defined. The consumer boundary should therefore pin Draft 2020-12 in code and tests. See the [2020-12 core specification](https://json-schema.org/draft/2020-12/json-schema-core) and [validation specification](https://json-schema.org/draft/2020-12/json-schema-validation).

## Capability comparison

| Option | Runtime validation | Static type | Current-schema fit | Main trade-off |
| --- | --- | --- | --- | --- |
| Zod `fromJSONSchema` + `json-schema-to-typescript` + isolated cast | Zod 4 conversion at module initialization, then `parse`/`safeParse` | Readable generated `.d.ts`; one cast connects it to Zod and `z.infer` | Good for the observed local `$defs`, local refs, unions, closed objects, nullability, strings, and numeric bounds | `fromJSONSchema` is experimental and non-generic; translation is not a guaranteed 1:1 round trip; static TS cannot encode numeric/regex refinements |
| `json-schema-to-zod` source generator | Generated Zod source | Generated `z.infer` type | Partial; requires separate ref resolution and has known factored-`oneOf`/recursion limitations | Archived/deprecated, explicitly lossy, ISC; generated source quality is not a sufficient answer to semantic loss |
| `json-schema-to-ts` `FromSchema` | None; type-only | Type inferred directly from an `as const` schema value | Promising smoke-test result, but its declared `JSONSchema` surface names `definitions`, not `$defs`; oneOf is modeled like anyOf | No runtime guard, no numeric refinement, no recursive schemas currently; direct `$defs` use is not a documented compatibility contract |
| Ajv `Ajv2020` + generated `.d.ts` | Validates the original JSON Schema; can emit standalone validator code | Same generated `.d.ts`, or a separately tested type-level approach | Highest semantic fidelity; preserves oneOf, `$defs`/`$ref`, closed objects, and numeric constraints | Not Zod; Pydantic's OpenAPI discriminator annotation needs to be ignored/registered or removed while retaining oneOf validation |
| quicktype | Can generate runtime checks and has TypeScript/Zod targets | Generated TypeScript | Viable candidate, but this repository's exact Pydantic feature combination needs fixture-based proof | More code-generation policy and less direct evidence for this schema; not selected without a prototype |

### Zod 4 `fromJSONSchema`

The installed Zod 4.4.3 converter accepts Draft 2020-12, Draft 7, Draft 4, and OpenAPI 3.0 targets. Its current source handles local `$defs`/`$ref`, `oneOf`, `anyOf`, `allOf`, object properties and `additionalProperties`, array bounds, string constraints, and numeric constraints such as `minimum`, `exclusiveMinimum`, and `multipleOf`. It maps `additionalProperties: false` to a strict Zod object and numeric bounds to Zod checks.

There are two important limitations:

- The public function returns a bare `ZodType`, not a schema-specific generic. `z.infer<typeof z.fromJSONSchema(schema)>` therefore does not recover the generated domain type. The isolated cast is the bridge.
- `discriminator` is not used as a Zod dispatch mechanism by the converter. The current dataset remains safe because its `oneOf` branches have disjoint literal state values; the `oneOf` validation still runs.

Zod labels this API experimental and says its behavior may change. It also does not promise a 1:1 round trip between JSON Schema and Zod. See the [official JSON Schema docs](https://zod.dev/json-schema) and the [converter source](https://github.com/colinhacks/zod/blob/main/packages/zod/src/v4/classic/from-json-schema.ts).

### `json-schema-to-typescript`

The actual Pydantic schema compiled successfully with `json2ts` 15.0.4. The resulting declaration was 341 lines. The public `CatalogueDataset` shape was readable; internal aliases derived from Pydantic's generic titles were verbose, but that does not create a second hand-maintained model. The output correctly represented aliases, literal unions, nullable values, references, required properties, and non-empty arrays.

Its static output is necessarily weaker than runtime JSON Schema validation. The project documents that `minimum`, `maximum`, `multipleOf`, `pattern`, `format`, `uniqueItems`, and exclusive `oneOf` semantics are not expressible in ordinary TypeScript. It also documents that `oneOf` is treated like `anyOf`. The generated type should therefore be described as structurally precise within TypeScript's type system, while Zod or Ajv remains responsible for value-level constraints.

The project is MIT-licensed and non-archived. Its [README](https://github.com/bcherny/json-schema-to-typescript) documents the compiler/API, feature set, and TypeScript expressivity limits.

### `json-schema-to-zod`

The current package can generate Zod v3 or v4 source and optionally emit a `z.infer` type. That removes the isolated cast and avoids shipping `fromJSONSchema` as a runtime converter. However, the current upstream README says it is no longer actively maintained; the GitHub repository is archived. Its documented limitations include separate `$ref` resolution, partial support for factored schemas/`oneOf`, recursion depth fallbacks that can become `z.any()`, and possible loss of details during translation. The README recommends Ajv when runtime JSON Schema fidelity is required.

It is ISC-licensed. These maintenance and semantic risks outweigh the convenience of generated Zod source for this contract. See the [upstream README](https://github.com/StefanTerdell/json-schema-to-zod) and [npm package](https://www.npmjs.com/package/json-schema-to-zod).

### Type-level JSON Schema inference: `json-schema-to-ts`

`json-schema-to-ts` is the most attractive type-only alternative. `FromSchema<typeof schema>` infers a type from an `as const` schema value with no emitted runtime code. The real CatalogueDataset schema was tested this way with TypeScript 5.9.3: the schema-version literal, provider literals, admission-outcome literals, discriminator-state narrowing, and invalid literal negative tests all typechecked as expected.

There is a compatibility caveat. The current library's declared JSON Schema type exposes `definitions` but not `$defs`. The actual generated constant happened to infer correctly in the smoke test because the schema's literal structure was traversable, but using `satisfies JSONSchema` or relying on `$defs` as a formally supported surface would require a library fix, type augmentation, or a schema adapter. The library also has no runtime validation, cannot express numeric ranges, treats `oneOf` like `anyOf`, and documents that recursive schemas are not currently supported.

It is MIT-licensed and active. See the [official README](https://github.com/ThomasAribart/json-schema-to-ts), the [current JSON Schema type definition](https://github.com/ThomasAribart/json-schema-to-ts/blob/main/src/definitions/jsonSchema.ts), and the [reference handling source](https://github.com/ThomasAribart/json-schema-to-ts/blob/main/src/parse-schema/references/utils.ts).

### Ajv as the higher-fidelity runtime

Ajv 8.20.0 with its `Ajv2020` export compiled the original Pydantic schema after one compatibility adjustment: Pydantic includes an OpenAPI-style `discriminator` object with a `mapping`, while Ajv's discriminator support does not support that mapping form and strict mode rejects the unknown keyword. Registering `discriminator` as a validated no-op annotation, or removing only that known annotation before compilation, allowed strict compilation while leaving the JSON Schema `oneOf` branches authoritative.

The resulting validator accepted the real fixture, rejected an unknown root property through `additionalProperties: false`, and rejected a `termMonths` value of zero through `exclusiveMinimum`. This is the most faithful runtime path because the original schema is what Ajv evaluates. Ajv also supports generated standalone validation code, which is useful if the browser should not ship a schema compiler.

Ajv is MIT-licensed and active. The relevant primary sources are [Ajv JSON Schema support](https://ajv.js.org/json-schema.html), [strict mode](https://ajv.js.org/strict-mode.html), [TypeScript guidance](https://ajv.js.org/guide/typescript.html), and [standalone code generation](https://ajv.js.org/standalone.html).

The cost is a different runtime API and error model from Zod. Ajv's `JSONSchemaType<T>` helper also assumes that `T` already exists, so it does not by itself solve the Python-authoritative type-generation problem; pair it with generated declarations or a separately verified type-level strategy.

### Other generators

[quicktype](https://github.com/glideapps/quicktype) is active, Apache-2.0-licensed, accepts JSON Schema, and can target TypeScript, Zod, and runtime type checks. It is a reasonable follow-up prototype, but its official material does not establish exact preservation of this repository's combination of Pydantic `$defs`, discriminator mappings, disjoint `oneOf` branches, and nested numeric constraints. It should not replace the baseline without fixture-by-fixture comparison.

`openapi-typescript` is a good active, MIT-licensed type generator for OpenAPI documents, but it is runtime-free and expects an OpenAPI document rather than a standalone Pydantic JSON Schema. Introducing an OpenAPI wrapper solely to use it would add a translation boundary without solving runtime validation.

## Concrete recommended pipeline

Generate all artifacts from one Python dictionary during the build or release step:

```text
CatalogueDataset.model_json_schema(
    mode="serialization",
    by_alias=True,
)
        |
        +--> catalogue-dataset.schema.json
        +--> catalogue-dataset.schema.ts       (the same object, `as const`)
        +--> catalogue-dataset.generated.d.ts  (json-schema-to-typescript)
```

The TypeScript seam remains deliberately small:

```ts
import { z } from "zod";
import schema from "./catalogue-dataset.schema";
import type { CatalogueDataset as GeneratedCatalogueDataset } from "./catalogue-dataset.generated";

const convertedCatalogueDatasetSchema = z.fromJSONSchema(schema);

export const CatalogueDatasetSchema =
  convertedCatalogueDatasetSchema as z.ZodType<GeneratedCatalogueDataset>;

export type CatalogueDataset = z.infer<typeof CatalogueDatasetSchema>;

export const parseCatalogueDataset = (input: unknown): CatalogueDataset =>
  CatalogueDatasetSchema.parse(input);
```

The cast should live in one generated-contract module and carry a comment explaining that it is checked by the build. It should not be repeated at call sites. The converter should run once when the module is initialized, not once per dataset fetch. If bundle size or startup cost becomes material, switch the runtime half to Ajv standalone output or evaluate a maintained source generator after fixture testing.

Required build gates:

- Generate the JSON file, schema constant, and declaration from the same serialized Python dictionary; do not hand-edit any of them.
- Parse representative fixtures through Pydantic and the TypeScript validator, including every discriminated-union state that is present in the catalogue.
- Assert rejection of unknown fields, incorrect discriminator values, missing required fields, invalid nullability, and every important numeric boundary.
- Add TypeScript negative tests for schema-version and enum literals, plus narrowing of representative discriminator branches.
- Fail the build if the schema feature inventory grows into a converter-supported gap, such as external refs, conditionals, `unevaluatedProperties`, or a union whose branches are not disjoint.
- Keep whole-dataset invariants in Python. A successful TypeScript parse proves shape and value-level schema constraints, not cross-record consistency.
- Pin and smoke-test the Zod minor line because `fromJSONSchema` is experimental; a dependency update should regenerate and re-run the fixtures before merge.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Zod converter behavior changes or is not 1:1 | Keep one adapter module, pin versions, test the real schema and fixtures, and maintain an explicit feature inventory |
| Generated TypeScript accepts values that violate numeric or regex constraints | Treat the declaration as a static structural view; always validate untrusted data at runtime |
| `oneOf` becomes a broad union in the declaration | Test each branch and keep discriminator literals disjoint; use Ajv if exclusive branch semantics become central to the runtime decision |
| Pydantic's `discriminator.mapping` is ignored by Zod or rejected by Ajv | Rely on the actual `oneOf` branches for validation; add a focused test for every branch; register/remove only the known OpenAPI annotation for strict Ajv |
| Pydantic emits a future unsupported keyword or external ref | Make generation fail closed and review the feature inventory before upgrading Pydantic |
| Root dialect is inferred inconsistently | Select Draft 2020-12 explicitly in the consumer and test harness because the emitted root currently omits `$schema` |
| Generated aliases are noisy | Accept verbose internal aliases while keeping the public top-level type generated; improve Python schema titles only if readability becomes a real maintenance problem |
| Browser bundle includes a schema converter | Convert once at module initialization for v1; use Ajv standalone or generated source if measured bundle/startup costs justify the added toolchain |
| Python whole-model validators are mistaken for browser validation | Document the boundary: Python remains authoritative for cross-record/domain invariants |

## Maintenance and licensing snapshot

Checked against package/repository metadata on 2026-08-02:

| Project | Version checked | License | Activity signal |
| --- | --- | --- | --- |
| Zod | 4.4.3 | MIT | Non-archived; repository updated in the current snapshot |
| json-schema-to-typescript | 15.0.4 | MIT | Non-archived; repository pushed in the current snapshot |
| json-schema-to-ts | 3.1.1 | MIT | Non-archived; recent upstream activity |
| Ajv | 8.20.0 | MIT | Non-archived; recent upstream activity |
| json-schema-to-zod | 2.8.1 | ISC | Archived; README says no longer actively maintained |
| quicktype | 26.0.0 | Apache-2.0 | Non-archived; recent upstream activity |

Activity is only a maintenance signal, not a correctness guarantee. The recommendation is based on the observed schema compatibility and the repository's preference for Zod, with Ajv retained as the fidelity-oriented alternative.

## Primary sources

- [Pydantic JSON Schema documentation](https://pydantic.dev/docs/validation/latest/concepts/json_schema/)
- [JSON Schema 2020-12 core](https://json-schema.org/draft/2020-12/json-schema-core) and [validation](https://json-schema.org/draft/2020-12/json-schema-validation)
- [Zod JSON Schema documentation](https://zod.dev/json-schema) and [Zod converter source](https://github.com/colinhacks/zod/blob/main/packages/zod/src/v4/classic/from-json-schema.ts)
- [`json-schema-to-typescript` README](https://github.com/bcherny/json-schema-to-typescript)
- [`json-schema-to-zod` README](https://github.com/StefanTerdell/json-schema-to-zod)
- [`json-schema-to-ts` README](https://github.com/ThomasAribart/json-schema-to-ts)
- [Ajv JSON Schema support](https://ajv.js.org/json-schema.html), [strict mode](https://ajv.js.org/strict-mode.html), and [standalone code](https://ajv.js.org/standalone.html)
- [quicktype repository](https://github.com/glideapps/quicktype)
- [openapi-typescript documentation](https://openapi-ts.dev/introduction)
