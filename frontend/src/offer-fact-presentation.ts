import {
  type CatalogueDatasetIndex,
  type CatalogueOffer,
  type CatalogueOfferFacts,
  deriveOfferFacts,
  findProviderById,
} from "@/catalogue-dataset";
import {
  currency,
  factText,
  isKnown,
  money,
  unavailableLabels,
  upfrontCashText,
  valueLabels,
} from "@/catalogue-ui";

type Service = CatalogueOffer["serviceArrangements"];
type ServiceArrangement = Extract<Service, { state: "known" }>["value"][number];
type Vehicle = CatalogueOffer["vehicleSpecification"];

export type PresentedFact = {
  label: string;
  text: string;
  unavailable: boolean;
};

export type PresentedServiceArrangement = {
  category: string;
  limits: string;
  summary: string;
  treatment: string;
};

export type ServicePresentation =
  | { kind: "unavailable"; text: string }
  | { kind: "empty"; text: string }
  | {
      kind: "known";
      arrangements: readonly PresentedServiceArrangement[];
    };

export type OfferFactPresentation = {
  contract: readonly PresentedFact[];
  service: ServicePresentation;
  source: {
    canonicalOfferUrl: string;
    providerName: string;
  };
  vehicle: readonly PresentedFact[];
};

type BodyStyle = Extract<Vehicle["bodyStyle"], { state: "known" }>["value"];

const bodyStyleLabels: Record<BodyStyle, string> = {
  hatchback: "Hatchback",
  saloon: "Sedan",
  estate: "Stationcar",
  suv: "SUV",
  coupe: "Coupé",
  convertible: "Cabriolet",
  mpv: "MPV",
  other: "Anden karrosseritype",
};

const fuelLabels: Record<
  Extract<Vehicle, { kind: "combustion" }>["fuelType"],
  string
> = {
  gasoline: "Benzin",
  diesel: "Diesel",
};

const treatmentLabels: Record<ServiceArrangement["treatment"], string> = {
  included: "Inkluderet",
  optional: "Valgfri",
  required_external: "Påkrævet eksternt",
  excluded: "Ikke omfattet af basisaftalen",
};

const serviceCategoryLabels: Record<ServiceArrangement["category"], string> = {
  service: "Service",
  maintenance: "Vedligeholdelse",
  insurance: "Forsikring",
  roadside_assistance: "Vejhjælp",
  tyres: "Dæk",
  other: "Andet",
};

export function presentOfferFacts(
  index: CatalogueDatasetIndex,
  offer: CatalogueOffer,
): OfferFactPresentation {
  const facts = deriveOfferFacts(index, offer);
  return {
    contract: presentContractFacts(offer, facts),
    service: presentService(offer.serviceArrangements),
    source: presentSourceFacts(index, offer),
    vehicle: presentVehicleFacts(offer),
  };
}

export function presentVehicleFacts(
  offer: CatalogueOffer,
  includeNotApplicable = false,
): PresentedFact[] {
  const vehicle = offer.vehicleSpecification;
  const facts: PresentedFact[] = [
    presentText("Mærke", vehicle.make),
    presentText("Model", vehicle.model),
    presentFact("Variant", vehicle.trim),
    presentFact("Modelår", vehicle.modelYear, String),
    presentFact("Førstegangsregistrering", vehicle.firstRegistrationYear, String),
    presentFact("Karrosseri", vehicle.bodyStyle, (value) => bodyStyleLabels[value]),
    presentFact("Kilometertal", vehicle.odometerKm, (value) => `${currency.format(value)} km`),
    presentText("Drivmiddel", vehicleKindText(vehicle)),
  ];

  if (vehicle.kind === "combustion") {
    facts.push(presentText("Brændstof", fuelLabels[vehicle.fuelType]));
    facts.push(
      presentFact(
        "Brændstoføkonomi",
        vehicle.fuelEfficiencyKmPerLiter,
        (value) => `${currency.format(value)} km/l`,
      ),
    );
    if (includeNotApplicable) {
      facts.push(notApplicableFact("Batterikapacitet"));
      facts.push(notApplicableFact("WLTP-rækkevidde"));
      facts.push(notApplicableFact("Maksimal ladeeffekt"));
      facts.push(notApplicableFact("Ladetid fra 10 til 80 %"));
    }
    return facts;
  }

  if (includeNotApplicable) {
    facts.push(notApplicableFact("Brændstof"));
    facts.push(notApplicableFact("Brændstoføkonomi"));
  }
  facts.push(presentFact("Batterikapacitet", vehicle.batteryCapacity, batteryText));
  facts.push(
    presentFact(
      "WLTP-rækkevidde",
      vehicle.wltpRangeKm,
      (value) => `${currency.format(value)} km`,
    ),
  );
  facts.push(
    presentFact("Maksimal ladeeffekt", vehicle.maxChargingPower, chargingPowerText),
  );
  facts.push(
    presentFact(
      "Ladetid fra 10 til 80 %",
      vehicle.chargingTime10To80Minutes,
      (value) => `${currency.format(value)} minutter`,
    ),
  );
  return facts;
}

export function presentContractFacts(
  offer: CatalogueOffer,
  facts: CatalogueOfferFacts,
  includeDerivedPayment = false,
): PresentedFact[] {
  const presentedFacts = [
    presentText(
      "Leasingform",
      valueLabels[offer.supportedLeasingForm] ?? offer.supportedLeasingForm,
    ),
    presentText("Udbyderens formbetegnelse", offer.providerFormLabel),
    presentText("Fuld løbetid", `${offer.termMonths} måneder`),
    presentFact("Kilometer om året", offer.annualMileageKm, (value) => `${currency.format(value)} km`),
    presentFact("Normal afslutning", offer.normalEndMechanism),
    presentFact("Restværdirisiko", offer.residualRiskAllocation),
    presentFact("Annonceret samlet betaling", offer.advertisedTotal, (value) => money(value.amountDkk)),
    presentResultFact("Nominelt basisudlæg", offer.calculatedTotal),
    presentResultFact("Nominelt månedligt gennemsnit", offer.calculatedMonthlyTotal),
  ];
  if (includeDerivedPayment) {
    presentedFacts.push(presentDerivedAmount("Månedlig betaling", facts.leasePayment));
  }
  presentedFacts.push(presentUpfrontCash(facts.upfrontCash));
  return presentedFacts;
}

export function presentServiceFact(offer: CatalogueOffer): PresentedFact {
  const service = presentService(offer.serviceArrangements);
  if (service.kind === "unavailable") {
    return unavailableFact("Serviceordninger", service.text);
  }
  if (service.kind === "empty") return presentText("Serviceordninger", service.text);
  return presentText(
    "Serviceordninger",
    service.arrangements
      .map(
        (arrangement) =>
          `${arrangement.category}: ${arrangement.treatment}. ${arrangement.summary}. Grænser: ${arrangement.limits}.`,
      )
      .join(" · "),
  );
}

export function presentSourceFacts(
  index: CatalogueDatasetIndex,
  offer: CatalogueOffer,
): OfferFactPresentation["source"] {
  const provider = findProviderById(index, offer.providerId);
  return {
    canonicalOfferUrl: offer.canonicalOfferUrl,
    providerName: provider?.name ?? offer.providerId,
  };
}

export function presentService(
  service: Service,
): ServicePresentation {
  if (!isKnown(service)) {
    return { kind: "unavailable", text: factText(service) };
  }
  if (service.value.length === 0) {
    return {
      kind: "empty",
      text: "Ingen serviceordning er registreret i datasættet.",
    };
  }
  return {
    kind: "known",
    arrangements: service.value.map((arrangement) => ({
      category: serviceCategoryLabels[arrangement.category],
      limits: factText(arrangement.limits),
      summary: arrangement.summary,
      treatment: treatmentLabels[arrangement.treatment],
    })),
  };
}

export function presentResultText(
  result: CatalogueOffer["calculatedTotal"],
): string {
  if (result.state === "available") return money(result.value.amountDkk);
  return result.reasons
    .map((reason) => {
      const label = unavailableLabels[reason.factState] ?? "Oplysningen er ikke tilgængelig";
      return `${label} (${reason.eventKey})`;
    })
    .join("; ");
}

function presentText(label: string, text: string): PresentedFact {
  return { label, text, unavailable: false };
}

function presentFact<Value>(
  label: string,
  fact: { state: "known"; value: Value } | { state: string },
  formatter?: (value: Value) => string,
): PresentedFact {
  if (fact.state !== "known") {
    return unavailableFact(label, unavailableLabels[fact.state] ?? "Oplysningen er ikke tilgængelig");
  }
  if (!("value" in fact)) {
    return unavailableFact(label, "Oplysningen er ikke tilgængelig");
  }
  let text = valueLabels[String(fact.value)] ?? String(fact.value);
  if (formatter !== undefined) text = formatter(fact.value);
  return presentText(label, text);
}

function presentDerivedAmount(
  label: string,
  result: CatalogueOfferFacts["leasePayment"],
): PresentedFact {
  if (result.state === "available") return presentText(label, money(result.amountDkk));
  return unavailableFact(label, unavailableLabels[result.factState]);
}

function presentUpfrontCash(
  result: CatalogueOfferFacts["upfrontCash"],
): PresentedFact {
  if (result.state === "available") return presentText("Kontant behov ved start", money(result.amountDkk));
  return unavailableFact("Kontant behov ved start", upfrontCashText(result));
}

function presentResultFact(
  label: string,
  result: CatalogueOffer["calculatedTotal"],
): PresentedFact {
  if (result.state === "available") return presentText(label, money(result.value.amountDkk));
  return unavailableFact(label, `Kan ikke beregnes: ${presentResultText(result)}`);
}

function unavailableFact(label: string, text: string): PresentedFact {
  return { label, text, unavailable: true };
}

function notApplicableFact(label: string): PresentedFact {
  return unavailableFact(label, unavailableLabels.not_applicable);
}

function vehicleKindText(vehicle: Vehicle): string {
  if (vehicle.kind === "battery_electric") return "Batterielektrisk";
  return "Forbrænding";
}

function batteryText(value: {
  valueKwh: number;
  basis: "gross" | "usable" | "not_stated";
}): string {
  const basisLabels = {
    gross: "brutto",
    usable: "brugbart",
    not_stated: "grundlag ikke oplyst",
  } as const;
  return `${currency.format(value.valueKwh)} kWh (${basisLabels[value.basis]})`;
}

function chargingPowerText(value: {
  valueKw: number;
  kind: "ac" | "dc" | "not_stated";
}): string {
  const kindLabels = { ac: "AC", dc: "DC", not_stated: "type ikke oplyst" } as const;
  return `${currency.format(value.valueKw)} kW (${kindLabels[value.kind]})`;
}
