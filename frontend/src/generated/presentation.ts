/* Generated from Python presentation schema. Do not edit. */

export type Schemaversion = "catalogue-presentation/v1";
export type Generatedat = string;
export type Name = string;
export type Designatedsource = string;
export type Quarantinedcandidatecount = number;
export type Providers = PresentationCoverageProvider[];
export type Name1 = string;
export type Coverageendedat = string;
export type Coverageended = PresentationEndedProviderCoverage[];
export type Offeridentity = string;
export type Provider = string;
export type Providersourceurl = string;
export type Vehiclespecification = KnownPresentationValueFact | UnavailablePresentationFact;
export type State = "known";
export type Sourceurl = string;
export type Wording = string;
export type Value = string | number;
export type State1 = "not_stated" | "unclear" | "conflicting" | "not_applicable";
export type Supportedleasingform = KnownPresentationValueFact | UnavailablePresentationFact;
export type Providerformlabel = KnownPresentationValueFact | UnavailablePresentationFact;
export type Residualriskallocation = KnownPresentationValueFact | UnavailablePresentationFact;
export type Registrationtaxtreatment = KnownPresentationValueFact | UnavailablePresentationFact;
export type Servicearrangements = KnownPresentationServiceFact | UnavailablePresentationFact;
export type State2 = "known";
export type Category = string;
export type Treatment = "included" | "optional" | "required_external" | "excluded";
export type Scope = string;
export type Limits = string | null;
export type Value1 = ServiceArrangement[];
export type Exclusions = KnownPresentationServiceFact | UnavailablePresentationFact;
export type Exposurescenarios = KnownPresentationExposureFact | UnavailablePresentationFact;
export type State3 = "known";
export type Kind = string;
export type Trigger = string;
export type Requiredinputs = string[];
export type Inputkinds = string[] | null;
export type Formula = string | null;
export type Amountdkk = number | null;
export type Ratedkk = number | null;
export type Capdkk = number | null;
export type Value2 = ExposureScenario[];
export type Advertisedmonthlypayment = KnownPresentationMoneyFact | UnavailablePresentationFact;
export type State4 = "known";
export type Valuedkk = number;
export type Upfrontcashrequirement = KnownDerivedMoneyFact | UnavailableDerivedMoneyFact;
export type State5 = "known";
export type Method = "base_cash_flow_stream";
export type Inputevidence = Evidence[];
export type Valuedkk1 = number;
export type State6 = "not_stated";
export type Blockingfacts = string[];
export type Nominalbaseoutlay = KnownDerivedMoneyFact | UnavailableDerivedMoneyFact;
export type Nominalmonthlyequivalent = KnownDerivedMoneyFact | UnavailableDerivedMoneyFact;
export type State7 = "ready" | "blocked";
export type Blockingfacts1 = string[];
export type Status =
  "not_available" | "not_reconstructed" | "matching" | "within_ordinary_rounding_tolerance" | "mismatch";
export type Valuedkk2 = number;
export type Reconstructednominalbaseoutlaydkk = number | null;
export type Unexplaineddifferencedkk = number | null;
export type Tolerancedkk = number;
export type Termmonths = KnownPresentationValueFact | UnavailablePresentationFact;
export type Annualmileagekm = KnownPresentationValueFact | UnavailablePresentationFact;
export type Normalendmechanism = KnownPresentationValueFact | UnavailablePresentationFact;
export type Cashflowbreakdown = PresentationCashFlowEvent[] | null;
export type Meaning = string;
export type Direction = "payment" | "receipt";
export type Amountdkk1 = number | null;
export type Amountbasis = "including_vat" | "excluding_vat" | "not_stated";
export type Timing = "acceptance_to_handover" | "recurring" | "normal_completion_end";
export type Recurrencecount = number | null;
export type Refundability = "refundable" | "not_refundable" | "not_stated";
export type Blockingfacts2 = string[] | null;
export type Offers = PresentationOffer[];

export interface CataloguePresentation {
  schemaVersion: Schemaversion;
  generatedAt: Generatedat;
  coverage: PresentationCoverage;
  coverageEnded: Coverageended;
  offers: Offers;
}
export interface PresentationCoverage {
  providers: Providers;
}
export interface PresentationCoverageProvider {
  name: Name;
  designatedSource: Designatedsource;
  quarantinedCandidateCount: Quarantinedcandidatecount;
}
export interface PresentationEndedProviderCoverage {
  name: Name1;
  coverageEndedAt: Coverageendedat;
}
export interface PresentationOffer {
  offerIdentity: Offeridentity;
  provider: Provider;
  providerSourceUrl: Providersourceurl;
  vehicleSpecification: Vehiclespecification;
  supportedLeasingForm: Supportedleasingform;
  providerFormLabel: Providerformlabel;
  residualRiskAllocation: Residualriskallocation;
  registrationTaxTreatment: Registrationtaxtreatment;
  serviceArrangements: Servicearrangements;
  exclusions: Exclusions;
  exposureScenarios: Exposurescenarios;
  advertisedMonthlyPayment: Advertisedmonthlypayment;
  upfrontCashRequirement: Upfrontcashrequirement;
  nominalBaseOutlay: Nominalbaseoutlay;
  nominalMonthlyEquivalent: Nominalmonthlyequivalent;
  operationReadiness: ComparisonOperationReadiness;
  aggregateReconciliation: AggregateReconciliation;
  termMonths: Termmonths;
  annualMileageKm: Annualmileagekm;
  normalEndMechanism: Normalendmechanism;
  cashFlowBreakdown?: Cashflowbreakdown;
}
export interface KnownPresentationValueFact {
  state: State;
  evidence: Evidence;
  value: Value;
}
export interface Evidence {
  sourceUrl: Sourceurl;
  wording: Wording;
}
export interface UnavailablePresentationFact {
  state: State1;
  evidence: Evidence;
}
export interface KnownPresentationServiceFact {
  state: State2;
  evidence: Evidence;
  value: Value1;
}
export interface ServiceArrangement {
  category: Category;
  treatment: Treatment;
  scope: Scope;
  limits?: Limits;
}
export interface KnownPresentationExposureFact {
  state: State3;
  evidence: Evidence;
  value: Value2;
}
export interface ExposureScenario {
  kind: Kind;
  trigger: Trigger;
  requiredInputs: Requiredinputs;
  inputKinds?: Inputkinds;
  formula?: Formula;
  amountDkk?: Amountdkk;
  rateDkk?: Ratedkk;
  capDkk?: Capdkk;
}
export interface KnownPresentationMoneyFact {
  state: State4;
  evidence: Evidence;
  valueDkk: Valuedkk;
}
export interface KnownDerivedMoneyFact {
  state: State5;
  calculation: CalculationProvenance;
  valueDkk: Valuedkk1;
}
export interface CalculationProvenance {
  method: Method;
  inputEvidence: Inputevidence;
}
export interface UnavailableDerivedMoneyFact {
  state: State6;
  calculation: CalculationProvenance;
  blockingFacts: Blockingfacts;
}
export interface ComparisonOperationReadiness {
  upfrontCashRequirement: OperationReadiness;
  nominalBaseOutlay: OperationReadiness;
  nominalMonthlyEquivalent: OperationReadiness;
}
export interface OperationReadiness {
  state: State7;
  blockingFacts: Blockingfacts1;
}
export interface AggregateReconciliation {
  status: Status;
  providerAdvertisedAggregate: PresentationAggregateAssertion | null;
  reconstructedNominalBaseOutlayDkk: Reconstructednominalbaseoutlaydkk;
  unexplainedDifferenceDkk: Unexplaineddifferencedkk;
  toleranceDkk: Tolerancedkk;
}
export interface PresentationAggregateAssertion {
  valueDkk: Valuedkk2;
  evidence: Evidence;
}
export interface PresentationCashFlowEvent {
  meaning: Meaning;
  direction: Direction;
  amountDkk: Amountdkk1;
  amountBasis: Amountbasis;
  timing: Timing;
  recurrenceCount: Recurrencecount;
  refundability: Refundability;
  evidence: Evidence;
  blockingFacts?: Blockingfacts2;
}
