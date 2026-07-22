/*
 * PROTOTYPE — throwaway UI for issue #8.
 * Three variants of the private catalogue and comparison experience, switchable via
 * `?variant=`, on the new `/prototype/private-comparison/` route.
 */

const offers = [
  {
    id: "terminalen-ioniq5",
    provider: "Terminalen",
    car: "Hyundai IONIQ 5",
    trim: "Essential 84 kWh",
    year: "Ny bil",
    art: "#c8ddd5",
    form: "operationel",
    providerLabel: "Privatleasing",
    monthly: 3795,
    upfront: 15990,
    term: 36,
    km: 10000,
    nominal: 152610,
    equivalent: 4239,
    risk: "provider",
    riskLabel: "Udbyderen bærer restværdirisikoen",
    tax: "Fuld registreringsafgift",
    end: "Bilen afleveres ved normal udløb",
    obligation: "Du skal aflevere bilen og kan blive opkrævet for overkørte kilometer og skader ud over normalt slid.",
    service: "Service og obligatorisk inspektion er inkluderet",
    external: "Forsikring og periodisk afgift betales separat; beløb ikke oplyst",
    missing: ["Beløb for forsikring", "Pris pr. overkørt kilometer"],
    sourceUrl: "https://www.terminalen.dk/nye-biler/hyundai/hyundai-ioniq-5/pris-og-udstyr",
    source: "Terminalen · modelside",
    retrieved: "22. juli 2026 kl. 06.31",
    evidence: [
      ["Månedlig betaling", "“Månedlig ydelse 3.795 kr.”", "known"],
      ["Løbetid og kilometer", "“36 måneder · 10.000 km/år”", "known"],
      ["Forsikring", "Siden omtaler ikke forsikringsbeløbet.", "missing"],
    ],
    cashflows: [
      ["Ved start", "Førstegangsydelse og levering", -15990],
      ["Måned 1–36", "36 månedlige betalinger", -136620],
      ["Ved udløb", "Aflevering af bilen", 0],
    ],
  },
  {
    id: "clevr-bmw-i4",
    provider: "Clevr Car",
    car: "BMW i4 M50",
    trim: "Gran Coupé M Sport",
    year: "2022 · 48.000 km",
    art: "#d8d4c8",
    form: "finansiel",
    providerLabel: "Flexleasing",
    monthly: 5995,
    upfront: 54990,
    term: 12,
    km: null,
    nominal: 126930,
    equivalent: 10578,
    risk: "lessee",
    riskLabel: "Du bærer restværdirisikoen",
    tax: "Forholdsmæssig registreringsafgift (§ 3 b)",
    end: "Du skal anvise en tredjepartskøber til den aftalte restværdi",
    obligation: "Du hæfter for forskellen, hvis bilen realiserer mindre end restværdien, og du skal anvise en køber ved udløb.",
    service: "Service, reparationer og dæk er ikke inkluderet",
    external: "Kasko- og ansvarsforsikring kræves; personligt beløb ukendt",
    missing: ["Kilometergrundlag", "Maksimal restværdi-eksponering"],
    sourceUrl: "https://clevrcar.dk/vehicle/2022-bmw-i4-m50-gran-coupe-m-sport-44656/",
    source: "Clevr Car · tilbudsside",
    retrieved: "22. juli 2026 kl. 06.34",
    evidence: [
      ["Privat betaling", "“Privat pr. måned inkl. moms 5.995 kr.”", "known"],
      ["Restværdi", "“Restværdi 390.000 kr. ekskl. moms og afgift”", "known"],
      ["Kilometer", "Intet kilometergrundlag fundet i den udpegede kilde.", "missing"],
    ],
    cashflows: [
      ["Ved start", "Førstegangsydelse og etablering", -54990],
      ["Måned 1–12", "12 månedlige betalinger", -71940],
      ["Ved udløb", "Mulig restværdi-manko (ukendt)", null],
    ],
  },
  {
    id: "fleasing-polestar",
    provider: "Fleasing",
    car: "Polestar 2",
    trim: "Long Range Dual Motor",
    year: "2023 · 31.000 km",
    art: "#cdd4db",
    form: "finansiel",
    providerLabel: "Finansiel leasing",
    monthly: 4875,
    upfront: 42200,
    term: 12,
    km: 20000,
    nominal: null,
    equivalent: null,
    risk: "lessee",
    riskLabel: "Du bærer restværdirisikoen",
    tax: "Forholdsmæssig registreringsafgift (§ 3 b)",
    end: "Køberanvisning er oplyst; betalingsmekanismen er uklar",
    obligation: "Køberanvisning fremgår, men kilden gør det uklart, hvem der betaler et eventuelt restværdiunderskud.",
    service: "Servicebehandling ikke oplyst",
    external: "Forsikring kræves; øvrige eksterne omkostninger ikke fuldt oplyst",
    missing: ["Obligatoriske slutgebyrer", "Restværdi-mankoens betalingsmekanisme", "Servicebehandling"],
    sourceUrl: "https://fleasing.dk/biler/",
    source: "Fleasing · tilbudsside",
    retrieved: "22. juli 2026 kl. 06.36",
    evidence: [
      ["Privat betaling", "“Privatleasing fra 4.875 kr. inkl. moms”", "known"],
      ["Køberanvisning", "“Ved udløb anvises en køber”", "known"],
      ["Slutgebyrer", "Kilden oplyser ikke, om der er et obligatorisk slutgebyr.", "missing"],
    ],
    cashflows: [
      ["Ved start", "Førstegangsydelse og etablering", -42200],
      ["Måned 1–12", "12 månedlige betalinger", -58500],
      ["Ved udløb", "Obligatoriske slutbeløb ikke afklaret", null],
    ],
  },
  {
    id: "terminalen-yaris",
    provider: "Terminalen",
    car: "Toyota Yaris",
    trim: "1.5 Hybrid Active",
    year: "Ny bil",
    art: "#e7c8c0",
    form: "operationel",
    providerLabel: "Privatleasing",
    monthly: 2995,
    upfront: 9995,
    term: 36,
    km: 15000,
    nominal: 117815,
    equivalent: 3273,
    risk: "provider",
    riskLabel: "Udbyderen bærer restværdirisikoen",
    tax: "Fuld registreringsafgift",
    end: "Bilen afleveres; ingen køberpligt oplyst",
    obligation: "Du afleverer bilen ved udløb. Underkørte og overkørte kilometer afregnes med forskellige satser.",
    service: "Service er inkluderet med oplyste begrænsninger",
    external: "Forsikring, ejerafgift og ekstraudstyr er ikke inkluderet",
    missing: ["Beløb for påkrævet forsikring"],
    sourceUrl: "https://www.toyota.dk/kampagner/yaris-active-pl-jan26-ID-22-2026",
    source: "Toyota · kampagneside",
    retrieved: "22. juli 2026 kl. 06.39",
    evidence: [
      ["Månedlig betaling", "“Månedlig ydelse 2.995 kr.”", "known"],
      ["Samlet betaling", "“Samlet betaling i perioden 117.815 kr.”", "known"],
      ["Forsikring", "Forsikring er ekskluderet; beløbet er individuelt og ikke oplyst.", "missing"],
    ],
    cashflows: [
      ["Ved start", "Førstegangsydelse", -9995],
      ["Måned 1–36", "36 månedlige betalinger", -107820],
      ["Ved udløb", "Aflevering af bilen", 0],
    ],
  },
];

const variantMeta = {
  A: "Roligt overblik",
  B: "Kontroltabel",
  C: "Beslutningsnotat",
};

const state = {
  variant: getVariant(),
  view: "catalogue",
  detailId: null,
  selected: new Set(["terminalen-ioniq5", "clevr-bmw-i4", "fleasing-polestar"]),
  filters: { search: "", form: "all", risk: "all", maxMonthly: 12000 },
};

function getVariant() {
  const value = new URLSearchParams(window.location.search).get("variant")?.toUpperCase();
  return Object.hasOwn(variantMeta, value) ? value : "A";
}

function money(value) {
  if (value == null) return "Kan ikke beregnes";
  return `${new Intl.NumberFormat("da-DK").format(value)} kr.`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function filteredOffers() {
  const query = state.filters.search.trim().toLowerCase();
  return offers.filter((offer) => {
    const matchesQuery = !query || `${offer.car} ${offer.trim} ${offer.provider}`.toLowerCase().includes(query);
    const matchesForm = state.filters.form === "all" || offer.form === state.filters.form;
    const matchesRisk = state.filters.risk === "all" || offer.risk === state.filters.risk;
    return matchesQuery && matchesForm && matchesRisk && offer.monthly <= state.filters.maxMonthly;
  });
}

function selectedOffers() {
  return offers.filter((offer) => state.selected.has(offer.id));
}

function datasetStamp() {
  return `
    <div class="dataset-stamp" title="Alle tilbud i dette demo-datasæt har samme generationstidspunkt">
      <span class="dataset-stamp__dot"></span>
      <span>Demo-datasæt genereret 22. jul. 2026 kl. 06.40 · 18 sek.</span>
    </div>`;
}

function header() {
  const count = state.selected.size;
  return `
    <header class="site-header">
      <button class="brand" data-action="catalogue" aria-label="Gå til kataloget">
        <span class="brand-mark">B</span>
        <span class="brand-word">Bilvalg</span>
      </button>
      ${datasetStamp()}
      <div class="site-header__actions">
        <button class="btn btn--ghost" data-action="catalogue">Katalog</button>
        <button class="btn btn--primary" data-action="compare" ${count < 2 ? "disabled" : ""}>
          Sammenlign <span class="count">${count}</span>
        </button>
      </div>
    </header>`;
}

function filters(extraClass = "") {
  return `
    <div class="filters ${extraClass}">
      <div class="filter-heading">
        <h2>Filtre</h2>
        <button class="text-button" data-action="clear-filters">Nulstil</button>
      </div>
      <label>
        Søg i bil eller udbyder
        <input type="search" data-filter="search" value="${escapeHtml(state.filters.search)}" placeholder="fx BMW eller Terminalen" />
      </label>
      <label>
        Leasingform
        <select data-filter="form">
          <option value="all" ${state.filters.form === "all" ? "selected" : ""}>Alle former</option>
          <option value="operationel" ${state.filters.form === "operationel" ? "selected" : ""}>Operationel</option>
          <option value="finansiel" ${state.filters.form === "finansiel" ? "selected" : ""}>Finansiel / flex</option>
        </select>
      </label>
      <label>
        Restværdirisiko
        <select data-filter="risk">
          <option value="all" ${state.filters.risk === "all" ? "selected" : ""}>Alle fordelinger</option>
          <option value="provider" ${state.filters.risk === "provider" ? "selected" : ""}>Udbyderen bærer risikoen</option>
          <option value="lessee" ${state.filters.risk === "lessee" ? "selected" : ""}>Du bærer risikoen</option>
        </select>
      </label>
      <label>
        Maks. annonceret ydelse: <strong class="value" data-max-value>${money(state.filters.maxMonthly)}</strong>
        <input type="range" min="3000" max="12000" step="500" data-filter="maxMonthly" value="${state.filters.maxMonthly}" />
      </label>
    </div>`;
}

function prototypeSwitcher() {
  const local = ["127.0.0.1", "localhost", ""].includes(window.location.hostname);
  const forced = new URLSearchParams(window.location.search).get("prototype") === "1";
  if (!local && !forced) return "";
  const viewLabel = state.view === "catalogue" ? `${filteredOffers().length} vist` : state.view === "compare" ? `${state.selected.size} valgt` : "Tilbudsdetaljer";
  return `
    <nav class="prototype-switcher" aria-label="Skift prototypevariant">
      <button data-action="previous-variant" aria-label="Forrige variant">←</button>
      <div class="prototype-switcher__state" aria-live="polite">
        <strong>${state.variant} — ${variantMeta[state.variant]}</strong>
        <small>${state.view} · ${viewLabel} · ${state.selected.size} til sammenligning</small>
      </div>
      <button data-action="next-variant" aria-label="Næste variant">→</button>
    </nav>`;
}

function rankingNote() {
  return `
    <div class="annotation">
      <span aria-hidden="true">◎</span>
      <span><strong>Ingen personlig rangering.</strong> Filtre indsnævrer kun kataloget. Den faste rækkefølge er ikke en anbefaling, og ukendte beløb regnes aldrig som 0 kr.</span>
    </div>`;
}

function riskPill(offer) {
  const className = offer.risk === "lessee" ? "status-pill--risk" : "status-pill--known";
  return `<span class="status-pill ${className}">${offer.risk === "lessee" ? "Din restværdirisiko" : "Udbyders restværdirisiko"}</span>`;
}

function compareControl(offer) {
  const checked = state.selected.has(offer.id);
  return `
    <label class="compare-checkbox">
      <input type="checkbox" data-action="toggle-compare" data-id="${offer.id}" ${checked ? "checked" : ""} />
      ${checked ? "Valgt" : "Vælg til sammenligning"}
    </label>`;
}

function emptyState() {
  return `
    <div class="empty-state">
      <div>
        <h2>Ingen tilbud matcher</h2>
        <p class="muted">Prøv at hæve den månedlige grænse eller nulstil filtrene.</p>
        <button class="btn" data-action="clear-filters">Nulstil filtre</button>
      </div>
    </div>`;
}

function offerCardA(offer) {
  return `
    <article class="offer-card">
      <div class="offer-art" style="--art:${offer.art}">
        <span class="offer-art__label">Illustration · ingen foto-licens</span>
      </div>
      <div class="offer-card__body">
        <div class="offer-card__head">
          <div>
            <h3>${offer.car}</h3>
            <span class="muted">${offer.trim} · ${offer.provider}</span>
          </div>
          ${riskPill(offer)}
        </div>
        <div class="price-line"><strong class="value">${money(offer.monthly)}</strong><span class="muted">/ md.</span></div>
        <div class="fact-strip">
          <div><span>Ved start</span><strong class="value">${money(offer.upfront)}</strong></div>
          <div><span>Nom. basisudgift</span><strong class="value">${money(offer.nominal)}</strong></div>
          <div><span>Periode</span><strong>${offer.term} mdr. · ${offer.km ? `${offer.km.toLocaleString("da-DK")} km/år` : "km ikke oplyst"}</strong></div>
        </div>
        <div class="obligation" style="--accent:${offer.risk === "lessee" ? "var(--red)" : "var(--forest)"}">
          <strong>Ved udløb:</strong><span>${offer.end}</span>
        </div>
        ${offer.missing.length ? `<span class="status-pill status-pill--missing">${offer.missing.length} oplysning${offer.missing.length > 1 ? "er" : ""} mangler</span>` : ""}
        <div class="card-footer">
          ${compareControl(offer)}
          <button class="btn btn--compact" data-action="details" data-id="${offer.id}">Se vilkår og kilder →</button>
        </div>
      </div>
    </article>`;
}

function catalogueA() {
  const list = filteredOffers();
  return `
    <main>
      <section class="hero">
        <p class="eyebrow">Privatleasing med vilkårene fremme</p>
        <h1 class="hero-title">Se hele betalingen.<br />Og det, der kan komme bagefter.</h1>
        <div class="hero__meta">
          <p class="lead">Sammenlign dokumenterede pengestrømme, pligter ved udløb og det, udbyderen ikke har oplyst.</p>
          <div class="hero__note">${rankingNote()}</div>
        </div>
      </section>
      <section class="catalogue-layout">
        <aside class="filter-rail">${filters()}</aside>
        <div>
          <div class="result-heading">
            <h2>${list.length} leasingtilbud</h2>
            <span class="muted">4 illustrative tilbud · 3 dækkede udbyderkilder · 1 kandidat i karantæne</span>
          </div>
          ${list.length ? `<div class="offer-grid">${list.map(offerCardA).join("")}</div>` : emptyState()}
        </div>
      </section>
    </main>`;
}

function rowB(offer) {
  const missingKm = offer.km == null;
  return `
    <tr>
      <td>${compareControl(offer)}</td>
      <td>
        <button class="text-button offer-table__car" data-action="details" data-id="${offer.id}">
          <span class="car-swatch" style="--art:${offer.art}"></span>
          <span><strong>${offer.car}</strong><small>${offer.trim}<br />${offer.provider}</small></span>
        </button>
      </td>
      <td><strong class="value">${money(offer.monthly)}</strong><small>${offer.providerLabel}</small></td>
      <td><strong class="value">${money(offer.upfront)}</strong><small>brutto til levering</small></td>
      <td class="${offer.nominal == null ? "missing-cell" : ""}"><strong class="value">${money(offer.nominal)}</strong><small>${offer.nominal == null ? "blokeret af manglende slutgebyrer" : `${money(offer.equivalent)} / md. ækvivalent`}</small></td>
      <td class="${missingKm ? "missing-cell" : ""}"><strong>${offer.term} mdr.</strong><small>${missingKm ? "Ikke oplyst" : `${offer.km.toLocaleString("da-DK")} km/år`}</small></td>
      <td>${riskPill(offer)}<small>${offer.end}</small></td>
      <td><div class="obligation-code">${offer.obligation}</div></td>
      <td><span class="status-pill status-pill--missing">${offer.missing.length} mangler</span><small>${offer.missing.join(" · ")}</small></td>
      <td><button class="btn btn--compact" data-action="details" data-id="${offer.id}">Kilder →</button></td>
    </tr>`;
}

function mobileRowB(offer) {
  return `
    <article class="mobile-row-card">
      <div class="mobile-row-card__head">
        <div><strong>${offer.car}</strong><div class="muted">${offer.provider} · ${offer.trim}</div></div>
        ${riskPill(offer)}
      </div>
      <div class="mobile-row-card__facts">
        <div><span>Ydelse</span><strong class="value">${money(offer.monthly)}</strong></div>
        <div><span>Ved start</span><strong class="value">${money(offer.upfront)}</strong></div>
        <div><span>Basisudgift</span><strong class="value">${money(offer.nominal)}</strong></div>
      </div>
      <p class="obligation-code">${offer.obligation}</p>
      <div class="button-row">${compareControl(offer)}<button class="btn btn--compact" data-action="details" data-id="${offer.id}">Detaljer</button></div>
    </article>`;
}

function catalogueB() {
  const list = filteredOffers();
  return `
    <main>
      <section class="control-header">
        <div class="control-header__top">
          <div>
            <p class="eyebrow">Kontroltabel · ${list.length} af ${offers.length}</p>
            <h1>Sammenlign vilkår uden pynt</h1>
            <p class="lead">Alle beløb er inkl. moms. Ukendte felter er markeret og udelukkes fra beregninger.</p>
          </div>
          ${rankingNote()}
        </div>
        ${filters()}
      </section>
      <section class="table-section">
        <div class="table-meta">
          <span>Fast rækkefølge: udbyderens kildesekvens · ikke pris eller relevans</span>
          <span>Demo-data · genereret samlet på 18 sek.</span>
        </div>
        ${list.length ? `
          <div class="offer-table-wrap">
            <table class="offer-table">
              <thead><tr><th>Vælg</th><th>Tilbud</th><th>Annonceret ydelse</th><th>Ved start</th><th>Nom. basisudgift</th><th>Periode</th><th>Restværdi</th><th>Din pligt</th><th>Datamangler</th><th>Dokumentation</th></tr></thead>
              <tbody>${list.map(rowB).join("")}</tbody>
            </table>
          </div>
          <div class="mobile-offer-list">${list.map(mobileRowB).join("")}</div>
        ` : emptyState()}
      </section>
    </main>`;
}

function memoOfferC(offer, index) {
  return `
    <article class="memo-offer">
      <div class="memo-offer__identity">
        <span class="memo-offer__index">0${index + 1} / ${offer.provider}</span>
        <h3>${offer.car}</h3>
        <span class="muted">${offer.trim} · ${offer.year}</span>
        <div class="memo-offer__price"><strong class="value">${money(offer.monthly)} / md.</strong><span class="muted">${money(offer.upfront)} ved start</span></div>
      </div>
      <div>
        <p class="memo-offer__difference">${offer.obligation}</p>
        <dl class="memo-facts">
          <div><dt>Normal afslutning</dt><dd>${offer.end}</dd></div>
          <div><dt>Nom. basisudgift</dt><dd class="value">${money(offer.nominal)}</dd></div>
          <div><dt>Grundlag</dt><dd>${offer.term} mdr. · ${offer.km ? `${offer.km.toLocaleString("da-DK")} km/år` : "km ikke oplyst"}</dd></div>
          <div><dt>Service</dt><dd>${offer.service}</dd></div>
          <div><dt>Eksternt</dt><dd>${offer.external}</dd></div>
          <div><dt>Dokumentation</dt><dd>${offer.missing.length} kendte datamangler</dd></div>
        </dl>
        <div class="memo-actions">
          ${compareControl(offer)}
          <button class="btn btn--compact" data-action="details" data-id="${offer.id}">Læs dokumentationen</button>
        </div>
      </div>
    </article>`;
}

function catalogueC() {
  const list = filteredOffers();
  return `
    <main class="memo-layout">
      <aside class="memo-rail">
        <p class="eyebrow">Beslutningsnotat</p>
        <h1>Hvad forpligter du dig til?</h1>
        <p>En læseoplevelse, der begynder med forskellen ved udløb — ikke med laveste månedstal.</p>
        ${filters()}
      </aside>
      <section class="memo-main">
        <div class="memo-intro">
          <h2>Fire tilbud.<br />Tre forskellige slutninger.</h2>
          <div class="memo-number"><strong>${list.length}</strong><span>matcher dine filtre</span></div>
        </div>
        <div style="margin:24px 0">${rankingNote()}</div>
        ${list.length ? `<div class="memo-offers">${list.map(memoOfferC).join("")}</div>` : emptyState()}
      </section>
    </main>`;
}

function evidenceItem(item, sourceUrl) {
  const [name, quote, status] = item;
  return `
    <li class="evidence-item">
      <div class="evidence-item__top"><strong>${name}</strong><span class="fact-state fact-state--${status}">${status === "known" ? "Dokumenteret" : "Ikke oplyst"}</span></div>
      <blockquote>${quote}</blockquote>
      <small><a href="${sourceUrl}" target="_blank" rel="noreferrer">Åbn den udpegede førstehåndskilde ↗</a></small>
    </li>`;
}

function detailView(offer) {
  return `
    <main class="detail-wrap">
      <button class="back-link" data-action="catalogue">← Tilbage til kataloget</button>
      <section class="detail-hero">
        <div>
          <p class="eyebrow">${offer.provider} · ${offer.providerLabel}</p>
          <h1>${offer.car}</h1>
          <p class="lead">${offer.trim} · ${offer.year}</p>
          <div class="button-row">${riskPill(offer)}<span class="tag">${offer.tax}</span></div>
        </div>
        <div class="detail-price">
          <small>Annonceret månedlig betaling</small>
          <strong class="detail-price__big value">${money(offer.monthly)}</strong>
          <span>${money(offer.upfront)} kræves fra aftale til levering</span>
        </div>
      </section>
      <div class="detail-grid">
        <div style="display:grid;gap:28px">
          <section class="panel">
            <h2>Pengestrøm ved normal gennemførelse</h2>
            <div class="cashflow-timeline">
              ${offer.cashflows.map(([when, label, amount]) => `<div class="cashflow-event"><span>${when}</span><strong>${label}</strong><strong>${amount == null ? "Ukendt" : amount === 0 ? "0 kr." : money(amount)}</strong></div>`).join("")}
            </div>
            <div class="annotation" style="margin-top:18px"><span>Σ</span><span><strong>Nominal basisudgift: ${money(offer.nominal)}.</strong> Betingede eksponeringer og eksterne omkostninger er ikke lagt ind som gæt.</span></div>
          </section>
          <section class="panel">
            <h2>Dokumentation pr. oplysning</h2>
            <ul class="evidence-list">${offer.evidence.map((item) => evidenceItem(item, offer.sourceUrl)).join("")}</ul>
          </section>
        </div>
        <div style="display:grid;gap:28px;align-content:start">
          <section class="panel">
            <h2>Dine pligter og eksponeringer</h2>
            <ul class="obligation-list">
              <li><span class="list-icon">1</span><span><strong>Ved udløb</strong><br />${offer.end}</span></li>
              <li><span class="list-icon">2</span><span><strong>Restværdi</strong><br />${offer.riskLabel}</span></li>
              <li><span class="list-icon">3</span><span><strong>Service</strong><br />${offer.service}</span></li>
              <li><span class="list-icon">4</span><span><strong>Påkrævet udenfor aftalen</strong><br />${offer.external}</span></li>
            </ul>
          </section>
          <section class="panel">
            <h2>Det ved vi ikke endnu</h2>
            <ul class="plain-list">${offer.missing.map((item) => `<li><span class="status-pill status-pill--missing">Ikke oplyst</span><span>${item}</span></li>`).join("")}</ul>
          </section>
          <section class="panel">
            <h2>Kilde og aktualitet</h2>
            <p><strong>${offer.source}</strong></p>
            <p class="muted">Hentet ${offer.retrieved}. Indgår i demo-datasættet genereret 22. juli 2026 kl. 06.40.</p>
            <a class="btn" href="${offer.sourceUrl}" target="_blank" rel="noreferrer">Åbn original kilde ↗</a>
          </section>
        </div>
      </div>
    </main>`;
}

const comparisonRows = [
  ["Pengestrøm", "Ved start", (o) => money(o.upfront)],
  [null, "Annonceret ydelse", (o) => `${money(o.monthly)} / md.`],
  [null, "Nominal basisudgift", (o) => o.nominal == null ? `Kan ikke beregnes|Mangler: ${o.missing[0]}` : money(o.nominal)],
  [null, "Nom. månedsækvivalent", (o) => o.equivalent == null ? "Kan ikke beregnes" : `${money(o.equivalent)} / md.`],
  ["Aftale", "Løbetid og kilometer", (o) => `${o.term} mdr.|${o.km ? `${o.km.toLocaleString("da-DK")} km/år` : "Ikke oplyst"}`],
  [null, "Providerens label", (o) => o.providerLabel],
  [null, "Registreringsafgift", (o) => o.tax],
  ["Udløb og risiko", "Normal afslutning", (o) => o.end],
  [null, "Restværdirisiko", (o) => o.riskLabel],
  [null, "Væsentlig pligt", (o) => o.obligation],
  ["Drift", "Service", (o) => o.service],
  [null, "Påkrævet eksternt", (o) => o.external],
  ["Dokumentation", "Ikke oplyst / uklart", (o) => o.missing.join("|• ")],
  [null, "Kilde hentet", (o) => `${o.source}|${o.retrieved}`],
];

function comparisonValue(value, offer) {
  const parts = value.split("|");
  return `${parts.map((part, index) => `${index ? "<br><small class=\"muted\">" : ""}${part}${index ? "</small>" : ""}`).join("")}<a class="source-ref" href="${offer.sourceUrl}" target="_blank" rel="noreferrer">Se kilde ↗</a>`;
}

function compareView() {
  const selected = selectedOffers();
  if (selected.length < 2) {
    state.view = "catalogue";
    return state.variant === "A" ? catalogueA() : state.variant === "B" ? catalogueB() : catalogueC();
  }
  let cells = `<div class="comparison-cell comparison-cell--label comparison-cell--head">Tilbud</div>`;
  cells += selected.map((offer) => `<div class="comparison-cell comparison-cell--head"><span class="muted">${offer.provider}</span><strong>${offer.car}</strong><span>${offer.trim}</span><button class="text-button" data-action="remove-compare" data-id="${offer.id}" style="margin-top:12px">Fjern</button></div>`).join("");
  for (const [section, label, getter] of comparisonRows) {
    if (section) cells += `<div class="comparison-section">${section}</div>`;
    const values = selected.map(getter);
    const differs = new Set(values).size > 1;
    cells += `<div class="comparison-cell comparison-cell--label">${label}</div>`;
    cells += selected.map((offer, index) => `<div class="comparison-cell ${differs ? "difference" : ""}">${comparisonValue(values[index], offer)}</div>`).join("");
  }
  return `
    <main class="compare-wrap">
      <button class="back-link" data-action="catalogue">← Tilbage til kataloget</button>
      <div class="compare-topline" style="margin-top:34px">
        <div><p class="eyebrow">Side om side · ${selected.length} tilbud</p><h1>Sammenlign forskellene</h1></div>
        <p class="compare-note">Gule felter er forskellige. Samme række betyder ikke samme køretøjskonfiguration. Ingen kolonne er fremhævet som vinder, og ukendte værdier er ikke regnet som 0.</p>
      </div>
      <div class="comparison-scroll" role="region" aria-label="Sammenligning af leasingtilbud" tabindex="0">
        <div class="comparison-grid" style="--compare-count:${selected.length}">${cells}</div>
      </div>
    </main>`;
}

function render() {
  let content;
  if (state.view === "detail") {
    content = detailView(offers.find((offer) => offer.id === state.detailId) ?? offers[0]);
  } else if (state.view === "compare") {
    content = compareView();
  } else if (state.variant === "A") {
    content = catalogueA();
  } else if (state.variant === "B") {
    content = catalogueB();
  } else {
    content = catalogueC();
  }

  document.getElementById("app").innerHTML = `
    <div class="shell variant-${state.variant.toLowerCase()}">
      ${header()}
      ${content}
      ${prototypeSwitcher()}
    </div>`;
}

function cycleVariant(direction) {
  const variants = Object.keys(variantMeta);
  const current = variants.indexOf(state.variant);
  state.variant = variants[(current + direction + variants.length) % variants.length];
  const url = new URL(window.location.href);
  url.searchParams.set("variant", state.variant);
  window.history.replaceState({}, "", url);
  render();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action]");
  if (!target) return;
  const action = target.dataset.action;
  const id = target.dataset.id;
  if (action === "catalogue") {
    state.view = "catalogue";
    state.detailId = null;
  } else if (action === "compare" && state.selected.size >= 2) {
    state.view = "compare";
  } else if (action === "details") {
    state.view = "detail";
    state.detailId = id;
  } else if (action === "toggle-compare") {
    target.checked ? state.selected.add(id) : state.selected.delete(id);
  } else if (action === "remove-compare") {
    state.selected.delete(id);
    if (state.selected.size < 2) state.view = "catalogue";
  } else if (action === "clear-filters") {
    state.filters = { search: "", form: "all", risk: "all", maxMonthly: 12000 };
  } else if (action === "previous-variant") {
    cycleVariant(-1);
    return;
  } else if (action === "next-variant") {
    cycleVariant(1);
    return;
  } else {
    return;
  }
  render();
  if (["catalogue", "compare", "details"].includes(action)) window.scrollTo({ top: 0, behavior: "smooth" });
});

document.addEventListener("input", (event) => {
  const key = event.target.dataset.filter;
  if (!key) return;
  if (key === "maxMonthly") {
    state.filters.maxMonthly = Number(event.target.value);
    document.querySelector("[data-max-value]").textContent = money(state.filters.maxMonthly);
    return;
  }
  if (key !== "search") return;
  state.filters.search = event.target.value;
  const cursor = event.target.selectionStart;
  render();
  const nextSearch = document.querySelector('[data-filter="search"]');
  nextSearch?.focus();
  nextSearch?.setSelectionRange(cursor, cursor);
});

document.addEventListener("change", (event) => {
  const key = event.target.dataset.filter;
  if (!key || key === "search") return;
  state.filters[key] = key === "maxMonthly" ? Number(event.target.value) : event.target.value;
  render();
});

document.addEventListener("keydown", (event) => {
  const active = document.activeElement;
  const typing = active && (active.matches("input, textarea, select") || active.isContentEditable);
  if (!typing && event.key === "ArrowLeft") cycleVariant(-1);
  if (!typing && event.key === "ArrowRight") cycleVariant(1);
  if (!typing && event.key === "Escape" && state.view !== "catalogue") {
    state.view = "catalogue";
    render();
  }
});

window.addEventListener("popstate", () => {
  state.variant = getVariant();
  render();
});

render();
