"""Declared provider scope shared by the catalogue contract and collection."""

from typing import Literal, get_args


CoveredProvider = Literal["Fleasing", "Terminalen"]

FLEASING_CATALOGUE_URL = "https://fleasing.dk/biler/"
FLEASING_DESIGNATED_SOURCE = "Fleasing passenger-car catalogue and linked detail pages"
TERMINALEN_CATALOGUE_URL = "https://www.terminalen.dk/nye-biler/hyundai"
TERMINALEN_DESIGNATED_SOURCE = (
    "Terminalen Hyundai model price pages and paired page API responses"
)
PROVIDER_DESIGNATED_SOURCES: dict[CoveredProvider, str] = {
    "Fleasing": FLEASING_DESIGNATED_SOURCE,
    "Terminalen": TERMINALEN_DESIGNATED_SOURCE,
}
PROVIDER_NAMES: tuple[CoveredProvider, ...] = get_args(CoveredProvider)
