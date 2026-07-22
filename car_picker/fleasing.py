from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Protocol
from urllib.parse import parse_qs, urljoin, urlparse


PARSER_VERSION = "fleasing-html-v2"


class TextHttpClient(Protocol):
    """The bounded HTTP boundary used by a source adapter."""

    def get_text(self, url: str) -> str: ...


class StructuralSourceError(ValueError):
    """The designated source changed shape and cannot be mapped safely."""


@dataclass(frozen=True)
class DiscoveredOffer:
    url: str
    source_fragment: str


class FleasingAdapter:
    """Map Fleasing's first-party vehicle page and its private-pricing tab."""

    def __init__(self, http_client: TextHttpClient, retrieved_at: str) -> None:
        self._http_client = http_client
        self._retrieved_at = retrieved_at

    def collect(self, catalogue_url: str = "https://fleasing.dk/biler/") -> list[dict[str, Any]]:
        catalogue_html = self._http_client.get_text(catalogue_url)
        offers = catalogue_detail_offers(catalogue_html, catalogue_url)
        if not offers:
            raise StructuralSourceError("Fleasing catalogue contains no designated detail links")

        candidates: list[dict[str, Any]] = []
        for offer in offers:
            detail_html = self._http_client.get_text(offer.url)
            candidates.append(
                map_detail_page(
                    catalogue_url=catalogue_url,
                    catalogue_html=catalogue_html,
                    discovered_offer=offer,
                    detail_html=detail_html,
                    retrieved_at=self._retrieved_at,
                )
            )
        return candidates


def catalogue_detail_offers(catalogue_html: str, catalogue_url: str) -> list[DiscoveredOffer]:
    parser = CatalogueLinkParser()
    parser.feed(catalogue_html)
    parser.close()
    catalogue_host = urlparse(catalogue_url).hostname
    catalogue_parts = urlparse(catalogue_url)
    offers: list[DiscoveredOffer] = []
    for href, text in parser.links:
        detail_url = urljoin(catalogue_url, href)
        parsed = urlparse(detail_url)
        if (
            parsed.hostname != catalogue_host
            or parsed.scheme != catalogue_parts.scheme
            or parsed.port != catalogue_parts.port
            or parsed.path != "/bil/"
            or not parse_qs(parsed.query).get("vid")
        ):
            continue
        if all(offer.url != detail_url for offer in offers):
            offers.append(DiscoveredOffer(detail_url, f'href="{href}" {text}'.strip()))
    return offers


def catalogue_detail_urls(catalogue_html: str, catalogue_url: str) -> list[str]:
    """Expose the bounded detail enumeration for the source-adapter test seam."""
    return [offer.url for offer in catalogue_detail_offers(catalogue_html, catalogue_url)]


def map_detail_page(
    *,
    catalogue_url: str,
    catalogue_html: str,
    discovered_offer: DiscoveredOffer,
    detail_html: str,
    retrieved_at: str,
) -> dict[str, Any]:
    detail = FleasingDetailParser()
    detail.feed(detail_html)
    detail.close()
    if not detail.found_vehicle_info or not detail.found_private_tab:
        raise StructuralSourceError(
            f"Fleasing detail {discovered_offer.url} no longer contains vehicle information and a private-pricing tab"
        )

    source_id = source_id_from_url(discovered_offer.url)
    source_metadata = {
        "parserVersion": PARSER_VERSION,
        "documents": [
            source_document(catalogue_url, catalogue_html, retrieved_at),
            source_document(discovered_offer.url, detail_html, retrieved_at),
        ],
    }
    vehicle = vehicle_specification(detail, discovered_offer.url)
    monthly_payment = money_fact(detail.private_terms, "Ydelse pr. måned", discovered_offer.url)
    term_months = months_fact(detail.private_terms, "Leasingperiode", discovered_offer.url)
    configuration_key = configuration_key_from_private_terms(detail.private_terms)
    candidate = {
        "offerIdentity": f"fleasing:{source_id}:{configuration_key}",
        "provider": "Fleasing",
        "providerSourceId": source_id,
        "canonicalOfferUrl": discovered_offer.url,
        "sourceLocalConfigurationKey": configuration_key,
        "vehicleSpecification": vehicle,
        "privateConsumerEligibility": known_fact(True, discovered_offer.url, 'id="privat"'),
        "passengerCarScope": passenger_car_fact(detail, discovered_offer.url),
        "currentAvailability": known_fact(True, catalogue_url, discovered_offer.source_fragment),
        "supportedLeasingForm": financial_leasing_fact(detail.private_terms, discovered_offer.url),
        "advertisedMonthlyPayment": monthly_payment,
        "termMonths": term_months,
        "upfrontCashRequirement": not_stated_fact(discovered_offer.url, detail.private_tab_fragment),
        "nominalBaseOutlay": not_stated_fact(discovered_offer.url, detail.private_tab_fragment),
        "nominalMonthlyEquivalent": not_stated_fact(discovered_offer.url, detail.private_tab_fragment),
        "annualMileageKm": not_stated_fact(discovered_offer.url, detail.private_tab_fragment),
        "normalEndMechanism": not_stated_fact(discovered_offer.url, detail.private_tab_fragment),
        "sourceMetadata": source_metadata,
    }
    reasons = admission_reasons(candidate)
    candidate["admissionStatus"] = "quarantined" if reasons else "admitted"
    if reasons:
        candidate["quarantineReasons"] = reasons
    return candidate


def vehicle_specification(detail: "FleasingDetailParser", source_url: str) -> dict[str, Any]:
    if not detail.make or not detail.trim:
        return not_stated_fact(source_url, detail.private_tab_fragment)
    return known_fact(
        {"make": detail.make, "model": detail.model, "trim": detail.trim},
        source_url,
        f"{detail.make} {detail.model} {detail.trim}",
    )


def passenger_car_fact(detail: "FleasingDetailParser", source_url: str) -> dict[str, Any]:
    return not_stated_fact(source_url, detail.private_tab_fragment)


def financial_leasing_fact(private_terms: Mapping[str, str], source_url: str) -> dict[str, Any]:
    residual_value = private_terms.get("Restværdi")
    if residual_value is None:
        return not_stated_fact(source_url, 'id="privat"')
    return unclear_fact(source_url, f"Restværdi {residual_value}")


def admission_reasons(candidate: Mapping[str, Any]) -> list[dict[str, str]]:
    required_facts = (
        "vehicleSpecification",
        "privateConsumerEligibility",
        "passengerCarScope",
        "currentAvailability",
        "supportedLeasingForm",
        "advertisedMonthlyPayment",
        "termMonths",
    )
    return [
        {"fact": fact_name, "state": candidate[fact_name]["state"]}
        for fact_name in required_facts
        if candidate[fact_name]["state"] != "known"
    ]


def configuration_key_from_private_terms(private_terms: Mapping[str, str]) -> str:
    selected_values = "\n".join(f"{label}:{value}" for label, value in sorted(private_terms.items()))
    return f"private-{hashlib.sha256(selected_values.encode('utf-8')).hexdigest()[:12]}"


def source_id_from_url(detail_url: str) -> str:
    source_ids = parse_qs(urlparse(detail_url).query).get("vid")
    if not source_ids:
        raise StructuralSourceError(f"Fleasing detail URL has no vid identity: {detail_url}")
    return source_ids[0]


def source_document(url: str, content: str, retrieved_at: str) -> dict[str, str]:
    return {
        "sourceUrl": url,
        "contentSha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "retrievedAt": retrieved_at,
    }


def known_fact(value: Any, source_url: str, wording: str) -> dict[str, Any]:
    return {"state": "known", "value": value, "evidence": evidence(source_url, wording)}


def not_stated_fact(source_url: str, wording: str) -> dict[str, Any]:
    return {"state": "not_stated", "evidence": evidence(source_url, wording)}


def unclear_fact(source_url: str, wording: str) -> dict[str, Any]:
    return {"state": "unclear", "evidence": evidence(source_url, wording)}


def money_fact(private_terms: Mapping[str, str], label: str, source_url: str) -> dict[str, Any]:
    wording = private_terms.get(label)
    if wording is None:
        return not_stated_fact(source_url, 'id="privat"')
    amount = dkk_amount(wording)
    if amount is None or "inkl. moms" not in wording.lower():
        return {"state": "unclear", "evidence": evidence(source_url, f"{label} {wording}")}
    return {"state": "known", "valueDkk": amount, "evidence": evidence(source_url, f"{label} {wording}")}


def months_fact(private_terms: Mapping[str, str], label: str, source_url: str) -> dict[str, Any]:
    wording = private_terms.get(label)
    if wording is None:
        return not_stated_fact(source_url, 'id="privat"')
    match = re.search(r"\b(\d+)\b", wording)
    if match is None:
        return {"state": "unclear", "evidence": evidence(source_url, f"{label} {wording}")}
    return {"state": "known", "value": int(match.group(1)), "evidence": evidence(source_url, f"{label} {wording}")}


def dkk_amount(wording: str) -> int | None:
    match = re.search(r"\b([\d.]+)\s*kr\.?", wording, flags=re.IGNORECASE)
    if match is None:
        return None
    return int(match.group(1).replace(".", ""))


def evidence(source_url: str, wording: str) -> dict[str, str]:
    return {"sourceUrl": source_url, "wording": wording}


class CatalogueLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text_parts).split())))
            self._href = None
            self._text_parts = []


class FleasingDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.found_vehicle_info = False
        self.found_private_tab = False
        self.make = ""
        self.model = ""
        self.trim = ""
        self.private_terms: dict[str, str] = {}
        self.private_tab_fragment = 'id="privat"'
        self._vehicle_info_depth: int | None = None
        self._private_tab_depth: int | None = None
        self._depth = 0
        self._capturing_tag: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._depth += 1
        attributes = {name: value for name, value in attrs if value is not None}
        if tag == "div" and "vehicle-page-info" in attributes.get("class", "").split():
            self.found_vehicle_info = True
            self._vehicle_info_depth = self._depth
        if tag == "div" and attributes.get("id") == "privat":
            self.found_private_tab = True
            self._private_tab_depth = self._depth
        if self._in_vehicle_info() and tag in {"h1", "h3"}:
            self._capturing_tag = tag
            self._text_parts = []
        if self._in_private_tab() and tag == "li":
            self._capturing_tag = tag
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._capturing_tag is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self._capturing_tag:
            text = " ".join("".join(self._text_parts).split())
            if tag == "h1" and not self.make:
                self.make, self.model = split_make_and_model(text)
            elif tag == "h3" and not self.trim:
                self.trim = text
            elif tag == "li":
                label, value = split_private_term(text)
                if label and value:
                    self.private_terms[label] = value
            self._capturing_tag = None
            self._text_parts = []
        if self._vehicle_info_depth == self._depth:
            self._vehicle_info_depth = None
        if self._private_tab_depth == self._depth:
            self._private_tab_depth = None
        self._depth -= 1

    def _in_vehicle_info(self) -> bool:
        return self._vehicle_info_depth is not None

    def _in_private_tab(self) -> bool:
        return self._private_tab_depth is not None


def split_make_and_model(value: str) -> tuple[str, str]:
    for make in ("Aston Martin", "Alfa Romeo", "Land Rover", "Mercedes-Benz"):
        if value.startswith(f"{make} "):
            return make, value.removeprefix(make).strip()
    pieces = value.split(maxsplit=1)
    if len(pieces) != 2:
        return value, ""
    return pieces[0], pieces[1]


def split_private_term(value: str) -> tuple[str | None, str | None]:
    labels = ("Ydelse pr. måned", "Udbetaling", "Restværdi", "Leasingperiode")
    for label in labels:
        if value.startswith(label):
            return label, value.removeprefix(label).strip()
    return None, None
