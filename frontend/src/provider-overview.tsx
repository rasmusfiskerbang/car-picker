import {
  deriveCatalogueFacts,
  deriveProviderFacts,
  type CatalogueDataset,
  type ProviderFacts,
} from "@/catalogue-dataset";

const inactiveReasonLabels = {
  blocked: "Blokeret",
  deferred: "Udskudt",
  ineligible: "Ikke omfattet",
} as const;

type CatalogueView = "offers" | "quarantined";
type CatalogueHref = (providerId: string, view: CatalogueView) => string;
type ProviderCountKind = "offers" | "quarantined";

const providerCountLabels = {
  offers: {
    plural: "katalogtilbud",
    singular: "katalogtilbud",
  },
  quarantined: {
    plural: "karantænesatte kandidater",
    singular: "karantænesat kandidat",
  },
} as const satisfies Record<
  ProviderCountKind,
  { plural: string; singular: string }
>;

type ProviderCountView = {
  count: number;
  href: string | undefined;
};

type ProviderRowView = {
  provider: ProviderFacts["provider"];
  selected: boolean;
  hostname: string;
  explanation: string;
  counts: Record<ProviderCountKind, ProviderCountView>;
};

export interface ProviderOverviewProps {
  dataset: CatalogueDataset;
  selectedProviderId?: string;
  providerSelectionHref: (providerId: string) => string;
  catalogueHref: CatalogueHref;
}

export function ProviderOverview({
  dataset,
  selectedProviderId,
  providerSelectionHref,
  catalogueHref,
}: ProviderOverviewProps) {
  const facts = deriveProviderFacts(dataset);
  const catalogueFacts = deriveCatalogueFacts(dataset);
  const rows = providerRows(facts, selectedProviderId, catalogueHref);

  return (
    <main className="page provider-overview-page">
      <header className="provider-overview-header">
        <h1>Udbydere i det aktive katalog</h1>
        <dl className="provider-overview-counts">
          <div>
            <dt>Aktive udbydere</dt>
            <dd>{catalogueFacts.activeProviderCount}</dd>
          </div>
          <div>
            <dt>Registreret i alt</dt>
            <dd>{catalogueFacts.providerCount}</dd>
          </div>
        </dl>
      </header>

      <section
        aria-labelledby="provider-registry-heading"
        className="provider-registry"
      >
        <h2 id="provider-registry-heading">Udbyderregister</h2>
        <ProviderRegistryTable
          rows={rows}
          providerSelectionHref={providerSelectionHref}
        />
        <ProviderRegistryCards
          rows={rows}
          providerSelectionHref={providerSelectionHref}
        />
      </section>
    </main>
  );
}

function ProviderRegistryTable({ rows, providerSelectionHref }: RegistryProps) {
  return (
    <div className="provider-registry-table-wrap">
      <table className="provider-registry-table">
        <caption className="visually-hidden">
          Publication-safe Provider Registry in Dataset order
        </caption>
        <thead>
          <tr>
            <th scope="col">Udbyder</th>
            <th scope="col">Status</th>
            <th scope="col">Tilbud</th>
            <th scope="col">Karantænesatte kandidater</th>
            <th scope="col">Forklaring</th>
            <th scope="col">
              <span className="visually-hidden">Website</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <ProviderTableRow
              key={row.provider.id}
              row={row}
              providerSelectionHref={providerSelectionHref}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ProviderTableRow({
  row,
  providerSelectionHref,
}: {
  row: ProviderRowView;
  providerSelectionHref: (providerId: string) => string;
}) {
  const { provider } = row;
  return (
    <tr data-selected={row.selected}>
      <th scope="row">
        <ProviderSelectionLink
          provider={provider}
          providerSelectionHref={providerSelectionHref}
          selected={row.selected}
        />
        <span className="provider-hostname">{row.hostname}</span>
      </th>
      <td>
        <ProviderStatus provider={provider} />
      </td>
      <td>
        <CatalogueCountLink
          count={row.counts.offers.count}
          kind="offers"
          provider={provider}
          href={row.counts.offers.href}
        />
      </td>
      <td>
        <CatalogueCountLink
          count={row.counts.quarantined.count}
          kind="quarantined"
          provider={provider}
          href={row.counts.quarantined.href}
        />
      </td>
      <td className="provider-explanation">
        <ProviderExplanation text={row.explanation} />
      </td>
      <td>
        <ProviderWebsite provider={provider} />
      </td>
    </tr>
  );
}

function ProviderRegistryCards({ rows, providerSelectionHref }: RegistryProps) {
  return (
    <div className="provider-card-list">
      {rows.map((row) => (
        <article
          className="card provider-card"
          data-selected={row.selected}
          key={row.provider.id}
        >
          <header className="provider-card-header">
            <div>
              <ProviderSelectionLink
                provider={row.provider}
                providerSelectionHref={providerSelectionHref}
                selected={row.selected}
              />
              <span className="provider-hostname">{row.hostname}</span>
            </div>
            <ProviderStatus provider={row.provider} />
          </header>
          <dl className="provider-card-counts">
            <div>
              <dt>Tilbud</dt>
              <dd>
                <CatalogueCountLink
                  count={row.counts.offers.count}
                  kind="offers"
                  provider={row.provider}
                  href={row.counts.offers.href}
                />
              </dd>
            </div>
            <div>
              <dt>Karantænesatte kandidater</dt>
              <dd>
                <CatalogueCountLink
                  count={row.counts.quarantined.count}
                  kind="quarantined"
                  provider={row.provider}
                  href={row.counts.quarantined.href}
                />
              </dd>
            </div>
          </dl>
          <p className="provider-explanation">
            <ProviderExplanation text={row.explanation} />
          </p>
          <div className="provider-card-actions">
            <ProviderWebsite provider={row.provider} />
          </div>
        </article>
      ))}
    </div>
  );
}

type RegistryProps = {
  rows: readonly ProviderRowView[];
  providerSelectionHref: (providerId: string) => string;
};

function providerRows(
  facts: readonly ProviderFacts[],
  selectedProviderId: string | undefined,
  catalogueHref: CatalogueHref,
): ProviderRowView[] {
  return facts.map((factsForProvider) => {
    const provider = factsForProvider.provider;
    return {
      provider,
      selected: provider.id === selectedProviderId,
      hostname: hostname(provider.url),
      explanation:
        provider.status === "active"
          ? "Aktiv i denne udgivelse."
          : provider.explanation,
      counts: {
        offers: {
          count: factsForProvider.offerCount,
          href: catalogueHrefForProvider(provider, "offers", catalogueHref),
        },
        quarantined: {
          count: factsForProvider.quarantinedCandidateCount,
          href: catalogueHrefForProvider(
            provider,
            "quarantined",
            catalogueHref,
          ),
        },
      },
    };
  });
}

function ProviderSelectionLink({
  provider,
  selected,
  providerSelectionHref,
}: {
  provider: ProviderFacts["provider"];
  selected: boolean;
  providerSelectionHref: (providerId: string) => string;
}) {
  return (
    <a
      aria-current={selected ? "page" : undefined}
      className="provider-selection-link"
      data-selected={selected}
      href={providerSelectionHref(provider.id)}
    >
      <span className="visually-hidden">Vælg </span>
      {provider.name}
    </a>
  );
}

function ProviderStatus({ provider }: { provider: ProviderFacts["provider"] }) {
  if (provider.status === "active") {
    return (
      <span className="provider-status provider-status-active">Aktiv</span>
    );
  }

  return (
    <span className="provider-status provider-status-inactive">
      Inaktiv · {inactiveReasonLabels[provider.reason]}
    </span>
  );
}

function CatalogueCountLink({
  count,
  kind,
  provider,
  href,
}: {
  count: number;
  kind: ProviderCountKind;
  provider: ProviderFacts["provider"];
  href: string | undefined;
}) {
  if (href === undefined)
    return <span className="provider-count">{count}</span>;
  const accessibleLabel = providerCountLabel(kind, count);
  return (
    <a
      aria-label={`Se ${count} ${accessibleLabel} fra ${provider.name}`}
      className="provider-count-link"
      href={href}
    >
      {count}
    </a>
  );
}

function providerCountLabel(kind: ProviderCountKind, count: number): string {
  const labels = providerCountLabels[kind];
  return count === 1 ? labels.singular : labels.plural;
}

function ProviderExplanation({ text }: { text: string }) {
  return text;
}

function catalogueHrefForProvider(
  provider: ProviderFacts["provider"],
  view: CatalogueView,
  catalogueHref: CatalogueHref,
): string | undefined {
  if (provider.status !== "active") return undefined;
  return catalogueHref(provider.id, view);
}

function ProviderWebsite({
  provider,
}: {
  provider: ProviderFacts["provider"];
}) {
  return (
    <a
      className="provider-website-link"
      href={provider.url}
      rel="noreferrer"
      target="_blank"
    >
      Åbn website
      <span className="visually-hidden"> hos {provider.name}</span>
    </a>
  );
}

function hostname(url: string): string {
  return new URL(url).hostname;
}
