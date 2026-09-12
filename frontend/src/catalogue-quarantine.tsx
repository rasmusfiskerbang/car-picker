import {
  type CatalogueQuarantineCriterion,
  type CatalogueQuarantineFactState,
  findProviderById,
  type CatalogueDataset,
  type CatalogueDatasetIndex,
  type QuarantinedCandidate,
} from "@/catalogue-dataset";

const criterionLabels: Record<CatalogueQuarantineCriterion, string> = {
  offer_identity: "Tilbudsidentitet",
  private_consumer_eligibility: "Privatforbruger-egnethed",
  private_consumer_amount_admissibility: "Privatforbruger-beløb",
  passenger_car_scope: "Personbilafgrænsning",
  current_availability: "Aktuel tilgængelighed",
  supported_leasing_form: "Leasingform",
  advertised_monthly_payment: "Annonceret månedsbetaling",
  upfront_payment: "Førstegangsbetaling",
  term_months: "Løbetid",
  candidate_shape: "Kandidatens datastruktur",
};

const stateLabels: Record<CatalogueQuarantineFactState, string> = {
  not_stated: "Ikke oplyst af udbyderen",
  unclear: "Kan ikke afgøres ud fra kilden",
  conflicting: "Modstridende oplysninger i kilden",
};

export function CatalogueQuarantineOverview({
  dataset,
  index,
  providerId,
  offersHref,
}: {
  dataset: CatalogueDataset;
  index: CatalogueDatasetIndex;
  providerId: string | undefined;
  offersHref: string;
}) {
  const candidates = dataset.quarantinedCandidates.filter(
    (candidate) =>
      providerId === undefined || candidate.providerId === providerId,
  );
  const provider =
    providerId === undefined ? undefined : findProviderById(index, providerId);
  const providerLabel = provider === undefined ? undefined : provider.name;

  return (
    <main className="page catalogue-page quarantine-page">
      <header className="catalogue-overview-header">
        <p className="eyebrow">Aktivt katalog</p>
        <h1>Karantænesatte kandidater</h1>
      </header>

      <div className="quarantine-toolbar">
        <p aria-live="polite" className="catalogue-result-summary">
          {resultLabel(candidates.length, providerLabel)}
        </p>
        <a href={offersHref}>Tilbage til katalogtilbud</a>
      </div>

      <QuarantineResults candidates={candidates} index={index} />
    </main>
  );
}

function QuarantineResults({
  candidates,
  index,
}: {
  candidates: QuarantinedCandidate[];
  index: CatalogueDatasetIndex;
}) {
  if (candidates.length === 0) {
    return (
      <div className="empty-state quarantine-empty-state">
        <h2>Ingen karantænesatte kandidater i denne visning</h2>
        <p>
          Kandidater uden de nødvendige optagelsesfakta vises ikke som
          katalogtilbud.
        </p>
      </div>
    );
  }

  return (
    <div className="quarantine-list">
      {candidates.map((candidate) => (
        <QuarantineCard
          candidate={candidate}
          index={index}
          key={candidate.offerIdentity}
        />
      ))}
    </div>
  );
}

function QuarantineCard({
  candidate,
  index,
}: {
  candidate: QuarantinedCandidate;
  index: CatalogueDatasetIndex;
}) {
  const provider = findProviderById(index, candidate.providerId);
  return (
    <article className="card quarantine-card">
      <header className="quarantine-card-header">
        <div>
          <p className="eyebrow">{provider?.name ?? candidate.providerId}</p>
          <h2>{candidate.offerIdentity}</h2>
        </div>
        <span className="quarantine-status">Karantænesat</span>
      </header>
      <div className="quarantine-card-content">
        <h3>Årsager til karantæne</h3>
        <ul>
          {candidate.reasons.map((reason) => (
            <li key={`${reason.criterion}-${reason.code}`}>
              <strong>{criterionLabels[reason.criterion]}</strong>
              <span>{stateLabels[reason.state]}</span>
            </li>
          ))}
        </ul>
        <a href={candidate.canonicalSourceUrl} rel="noreferrer" target="_blank">
          Åbn kandidatens førstehåndskilde
        </a>
      </div>
    </article>
  );
}

function resultLabel(count: number, providerName: string | undefined): string {
  const suffix = providerName === undefined ? "" : ` fra ${providerName}`;
  return `${count} karantænesatte kandidater${suffix}`;
}
