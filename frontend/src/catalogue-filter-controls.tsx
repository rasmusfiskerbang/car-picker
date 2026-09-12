import type { CatalogueDataset } from "@/catalogue-dataset";
import { RotateCcw } from "lucide-react";
import type {
  CatalogueSearch,
  CatalogueSort,
  LeasingForm,
  VehicleKind,
} from "@/catalogue-search";

export interface CatalogueFilterControlsProps {
  dataset: CatalogueDataset;
  search: CatalogueSearch;
  heading?: boolean;
  onSearchChange: (value: string | undefined) => void;
  onProviderChange: (value: string | undefined) => void;
  onLeasingFormChange: (value: LeasingForm | undefined) => void;
  onVehicleKindChange: (value: VehicleKind | undefined) => void;
  onSortChange: (value: CatalogueSort | undefined) => void;
  onReset: () => void;
}

const leasingForms: readonly LeasingForm[] = [
  "operational",
  "financial",
  "flex",
  "hybrid",
];
const vehicleKinds: readonly VehicleKind[] = ["combustion", "battery_electric"];
const sortOptions: readonly CatalogueSort[] = [
  "source",
  "monthly",
  "total",
  "term",
  "mileage",
];

export function CatalogueFilterControls({
  dataset,
  search,
  heading = true,
  onSearchChange,
  onProviderChange,
  onLeasingFormChange,
  onVehicleKindChange,
  onSortChange,
  onReset,
}: CatalogueFilterControlsProps) {
  return (
    <form className="filters" onSubmit={(event) => event.preventDefault()}>
      <div className="search-filter-control">
        <div className="search-filter-label">
          <span>Søg</span>
          {heading && (
            <button
              aria-label="Nulstil filtre"
              title="Nulstil filtre"
              type="button"
              onClick={onReset}
            >
              <RotateCcw aria-hidden="true" />
            </button>
          )}
        </div>
        <input
          aria-label="Søg i køretøjsspecifikation eller dækket udbyder"
          placeholder="Fx BMW, i4 eller Terminalen"
          type="search"
          value={search.search ?? ""}
          onChange={(event) => onSearchChange(emptyToUndefined(event.target.value))}
        />
      </div>
      <label>
        Udbyder
        <select
          aria-label="Udbyder"
          value={search.provider ?? "all"}
          onChange={(event) => onProviderChange(allToUndefined(event.target.value))}
        >
          <option value="all">Alle udbydere</option>
          {dataset.providers.map((provider) => (
            <option key={provider.id} value={provider.id}>
              {provider.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Leasingform
        <select
          aria-label="Leasingform"
          value={search.leasingForm ?? "all"}
          onChange={(event) =>
            onLeasingFormChange(optionOrUndefined(leasingForms, event.target.value))
          }
        >
          <option value="all">Alle former</option>
          <option value="operational">Operationel</option>
          <option value="financial">Finansiel</option>
          <option value="flex">Flex</option>
          <option value="hybrid">Hybrid</option>
        </select>
      </label>
      <label>
        Køretøjstype
        <select
          aria-label="Køretøjstype"
          value={search.vehicleKind ?? "all"}
          onChange={(event) =>
            onVehicleKindChange(optionOrUndefined(vehicleKinds, event.target.value))
          }
        >
          <option value="all">Alle køretøjstyper</option>
          <option value="combustion">Forbrænding</option>
          <option value="battery_electric">Batterielektrisk</option>
        </select>
      </label>
      <label>
        Sortér tilbud
        <select
          aria-label="Sortér tilbud"
          value={search.sort ?? "source"}
          onChange={(event) => onSortChange(optionOrUndefined(sortOptions, event.target.value))}
        >
          <option value="source">Kilderækkefølge</option>
          <option value="monthly">Månedlig betaling · lavest først</option>
          <option value="total">Beregnet total · lavest først</option>
          <option value="term">Løbetid · kortest først</option>
          <option value="mileage">Kilometer · lavest først</option>
        </select>
      </label>
    </form>
  );
}

function emptyToUndefined(value: string): string | undefined {
  return value === "" ? undefined : value;
}

function allToUndefined(value: string): string | undefined {
  return value === "all" ? undefined : value;
}

function optionOrUndefined<T extends string>(
  options: readonly T[],
  value: string,
): T | undefined {
  return value === "all" ? undefined : options.find((option) => option === value);
}
