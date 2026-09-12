import type {
  CatalogueDataset,
  DerivedAmount,
  UpfrontCashResult,
} from "@/catalogue-dataset";

export const currency = new Intl.NumberFormat("da-DK");

export const unavailableLabels: Record<string, string> = {
  not_stated: "Ikke oplyst af udbyderen",
  unclear: "Kan ikke afgøres ud fra kilden",
  conflicting: "Modstridende oplysninger i kilden",
  not_applicable: "Ikke relevant for denne aftale",
};

export const valueLabels: Record<string, string> = {
  operational: "Operationel privatleasing",
  financial: "Finansiel leasing",
  flex: "Flexleasing",
  hybrid: "Hybrid leasingform",
  provider: "Udbyderen bærer restværdirisikoen",
  lessee: "Den potentielle leasingtager bærer restværdirisikoen",
  shared: "Restværdirisikoen er delt",
  return_to_provider: "Bilen afleveres til udbyderen ved normalt udløb",
  designate_third_party_buyer:
    "Den potentielle leasingtager skal anvise en tredjepartskøber ved normalt udløb",
  mandatory_purchase_or_payoff:
    "Den potentielle leasingtager skal købe bilen eller betale restforpligtelsen ved normalt udløb",
  other: "Den normale afslutning er ikke klassificeret",
};

type KnownValue<T extends { state: string }> = Extract<
  T,
  { state: "known" }
> extends { value: infer Value }
  ? Value
  : never;
type KnownState<T extends { state: string }> = Extract<
  T,
  { state: "known" }
> & { value: KnownValue<T> };

export function isKnown<T extends { state: string }>(
  fact: T,
): fact is KnownState<T> {
  return fact.state === "known";
}

export function factText<T extends { state: string }>(
  fact: T,
  formatter: (value: KnownValue<T>) => string = (value) =>
    valueLabels[String(value)] ?? String(value),
): string {
  return isKnown(fact)
    ? formatter(fact.value)
    : unavailableLabels[fact.state] ?? "Oplysningen er ikke tilgængelig";
}

export function money(value: number): string {
  return `${currency.format(value)} kr.`;
}

export function derivedAmountText(amount: DerivedAmount): string {
  return amount.state === "available"
    ? money(amount.amountDkk)
    : unavailableLabels[amount.factState];
}

const upfrontCashUnavailableLabels = {
  no_payment_documented: "Ingen betaling ved start er dokumenteret i datasættet.",
  not_stated: "Beløbet ved start er ikke oplyst af udbyderen.",
  unclear: "Beløbet ved start kan ikke afgøres ud fra kilden.",
  conflicting: "Kilden indeholder modstridende oplysninger om beløbet ved start.",
  not_applicable:
    "Betaling ved start er ikke relevant for denne aftale ifølge datasættet.",
} as const;

export function upfrontCashText(result: UpfrontCashResult): string {
  return result.state === "available"
    ? money(result.amountDkk)
    : result.reasons.map((reason) => upfrontCashUnavailableLabels[reason]).join(" ");
}

export function generatedAtText(dataset: CatalogueDataset): string {
  return new Intl.DateTimeFormat("da-DK", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(dataset.generatedAt));
}
