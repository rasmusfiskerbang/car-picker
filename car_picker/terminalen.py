from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

from car_picker.fleasing import StructuralSourceError, TextHttpClient


PARSER_VERSION = "terminalen-model-price-v1"


class TerminalenAdapter:
    """Collect Terminalen's bounded model-price pages and their paired page API data."""

    def __init__(self, http_client: TextHttpClient, retrieved_at: str) -> None:
        self._http_client = http_client
        self._retrieved_at = retrieved_at

    def collect(self, catalogue_url: str) -> list[dict[str, Any]]:
        catalogue_html = self._http_client.get_text(catalogue_url)
        price_urls = model_price_urls(catalogue_html, catalogue_url)
        if not price_urls:
            raise StructuralSourceError("Terminalen catalogue contains no model price pages")
        candidates: list[dict[str, Any]] = []
        for price_url in price_urls:
            page_html = self._http_client.get_text(price_url)
            api_url = model_page_api_url(price_url)
            api_text = self._http_client.get_text(api_url)
            candidates.extend(
                map_model_page(
                    catalogue_url=catalogue_url,
                    catalogue_html=catalogue_html,
                    page_url=price_url,
                    page_html=page_html,
                    api_url=api_url,
                    api_text=api_text,
                    retrieved_at=self._retrieved_at,
                )
            )
        return candidates


def model_price_urls(catalogue_html: str, catalogue_url: str) -> list[str]:
    parser = LinkParser()
    parser.feed(catalogue_html)
    parser.close()
    origin = urlparse(catalogue_url)
    scope_prefix = "/nye-biler/hyundai/" if origin.path == "/terminalen" else origin.path.rstrip("/") + "/"
    urls: list[str] = []
    for href in parser.hrefs:
        url = urljoin(catalogue_url, href)
        parsed = urlparse(url)
        if (
            parsed.scheme == origin.scheme
            and parsed.hostname == origin.hostname
            and parsed.port == origin.port
            and parsed.path.startswith(scope_prefix)
            and parsed.path.endswith("/pris-og-udstyr")
            and not parsed.query
            and not parsed.fragment
            and url not in urls
        ):
            urls.append(url)
    return urls


def model_page_api_url(page_url: str) -> str:
    parsed = urlparse(page_url)
    return f"{parsed.scheme}://{parsed.netloc}/api/page/url?url={parsed.path}&culture=da-DK"


def map_model_page(
    *,
    catalogue_url: str,
    catalogue_html: str,
    page_url: str,
    page_html: str,
    api_url: str,
    api_text: str,
    retrieved_at: str,
) -> list[dict[str, Any]]:
    try:
        payload = json.loads(api_text)
    except json.JSONDecodeError as error:
        raise StructuralSourceError(f"Terminalen page API at {api_url} did not return JSON") from error
    if not isinstance(payload, Mapping) or payload.get("url") != urlparse(page_url).path:
        raise StructuralSourceError("Terminalen page API does not match the same model-price path")
    if payload.get("template") != "modelSubpage":
        raise StructuralSourceError("Terminalen page API is not a model-price page")
    model_id = required_string(payload, "pimModelId")
    vehicle = object_value(payload.get("vehicleData"), "Terminalen vehicleData")
    brand = required_string(vehicle, "brand")
    model = required_string(vehicle, "model")
    vehicle_wording = json.dumps(vehicle, ensure_ascii=False, separators=(",", ":"))
    rows, private_eligibility_wording, legal_wording, end_wording = private_lease_rows(payload)
    if not rows:
        raise StructuralSourceError("Terminalen model-price API contains no private lease offers")
    documents = [
        source_document(catalogue_url, catalogue_html, retrieved_at),
        source_document(page_url, page_html, retrieved_at),
        source_document(api_url, api_text, retrieved_at),
    ]
    return [
        map_configuration(
            row,
            page_url=page_url,
            api_url=api_url,
            model_id=model_id,
            brand=brand,
            model=model,
            vehicle_wording=vehicle_wording,
            private_eligibility_wording=private_eligibility_wording,
            end_wording=end_wording,
            legal_wording=legal_wording,
            documents=documents,
        )
        for row in rows
    ]


def map_configuration(
    row: Mapping[str, Any],
    *,
    page_url: str,
    api_url: str,
    model_id: str,
    brand: str,
    model: str,
    vehicle_wording: str,
    private_eligibility_wording: str,
    end_wording: str,
    legal_wording: str,
    documents: list[dict[str, str]],
) -> dict[str, Any]:
    configuration_id = required_string(row, "configurationId")
    wording = required_string(row, "sourceWording")
    monthly = required_int(row, "monthlyPaymentDkk")
    upfront = required_int(row, "upfrontPaymentDkk")
    term = required_int(row, "termMonths")
    aggregate = required_int(row, "aggregatePaymentDkk")
    card_evidence = {"sourceUrl": api_url, "wording": wording}
    vehicle_evidence = {"sourceUrl": api_url, "wording": vehicle_wording}
    vat_basis = amount_basis(legal_wording)
    payment_evidence = combined_evidence(api_url, wording, legal_wording)
    mileage = mileage_fact(api_url, legal_wording)
    end_fee = inspection_fee(legal_wording)
    events = [
        event("Udbetaling", upfront, "acceptance_to_handover", 1, vat_basis, payment_evidence),
        event("Månedlig ydelse", monthly, "recurring", term, vat_basis, payment_evidence),
    ]
    if end_fee is not None:
        events.append(
            event(
                "Inspektionsgebyr",
                end_fee,
                "normal_completion_end",
                1,
                vat_basis,
                {"sourceUrl": api_url, "wording": legal_wording},
            )
        )
    total = upfront + monthly * term + sum(item["amountDkk"] for item in events[2:])
    blockers = ["unreconciledProviderAggregate"] if total != aggregate else []
    candidate = {
        "offerIdentity": f"terminalen:{model_id}:{configuration_id}",
        "provider": "Terminalen",
        "providerSourceId": model_id,
        "canonicalOfferUrl": page_url,
        "sourceLocalConfigurationKey": configuration_id,
        "vehicleSpecification": known({"make": brand, "model": model}, vehicle_evidence),
        "privateConsumerEligibility": known(
            True,
            {"sourceUrl": api_url, "wording": private_eligibility_wording},
        ),
        "passengerCarScope": not_stated(api_url, wording),
        "currentAvailability": not_stated(api_url, wording),
        "supportedLeasingForm": operational_form_fact(api_url, end_wording),
        "advertisedMonthlyPayment": money(monthly, payment_evidence),
        "providerAdvertisedAggregate": money(aggregate, card_evidence),
        "termMonths": known(term, card_evidence),
        "annualMileageKm": mileage,
        "normalEndMechanism": normal_end_fact(api_url, end_wording),
        "residualRiskAllocation": residual_risk_fact(api_url, end_wording),
        "registrationTaxTreatment": not_stated(api_url, legal_wording),
        "baseCashFlowStream": events,
        "baseCashFlowBlockers": blockers,
        "serviceArrangements": service_arrangements_fact(api_url, legal_wording),
        "exclusions": exclusions_fact(api_url, legal_wording),
        "exposureScenarios": not_stated(api_url, legal_wording),
        "sourceMetadata": {"parserVersion": PARSER_VERSION, "documents": documents},
        "admissionStatus": "quarantined",
    }
    candidate["quarantineReasons"] = admission_reasons(candidate)
    return candidate


def event(
    meaning: str,
    amount: int,
    timing: str,
    recurrence_count: int,
    amount_basis: str,
    evidence: dict[str, str],
) -> dict[str, Any]:
    return {
        "meaning": meaning, "direction": "payment", "amountDkk": amount,
        "amountBasis": amount_basis, "timing": timing, "recurrenceCount": recurrence_count,
        "refundability": "not_refundable", "includedInBase": True, "evidence": evidence,
    }


def known(value: Any, evidence: dict[str, str]) -> dict[str, Any]:
    return {"state": "known", "value": value, "evidence": evidence}


def money(value: int, evidence: dict[str, str]) -> dict[str, Any]:
    return {"state": "known", "valueDkk": value, "evidence": evidence}


def not_stated(source_url: str, wording: str) -> dict[str, Any]:
    return {"state": "not_stated", "evidence": {"sourceUrl": source_url, "wording": wording}}


def private_lease_rows(payload: Mapping[str, Any]) -> tuple[list[dict[str, Any]], str, str, str]:
    grid = list_value(payload.get("grid"), "Terminalen grid")
    rows: list[dict[str, Any]] = []
    private_eligibility_wording = ""
    legal_wording = ""
    end_wording = ""
    in_private_leasing = False
    price_block_found = False
    for section in grid:
        for content in list_value(object_value(section, "Terminalen grid section").get("content"), "Terminalen grid content"):
            block = object_value(content, "Terminalen content block")
            if block.get("alias") == "anchor":
                in_private_leasing = block.get("anchorId") == "privatleasing"
                if in_private_leasing:
                    private_eligibility_wording = json.dumps(
                        {"alias": "anchor", "anchorId": "privatleasing"},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                continue
            if not in_private_leasing:
                continue
            if block.get("alias") == "imagetextpicker":
                columns = block.get("columns")
                if not isinstance(columns, list):
                    raise StructuralSourceError("Terminalen private lease card block requires columns")
                if not price_block_found:
                    price_block_found = True
                    for column in columns:
                        value = object_value(column, "Terminalen leasing column")
                        rows.append(
                            lease_row(
                                required_string(value, "title"),
                                html_text(required_string(value, "text")),
                            )
                        )
                    continue
                for column in columns:
                    value = object_value(column, "Terminalen leasing column")
                    text = html_text(required_string(value, "text"))
                    if required_string(value, "title") == "Privatleasing":
                        end_wording = text
            if block.get("alias") == "richtext":
                text = html_text(required_string(block, "text"))
                if "Samlet betaling" in text:
                    legal_wording = text
    return rows, private_eligibility_wording, legal_wording, end_wording


def lease_row(title: str, text: str) -> dict[str, Any]:
    monthly = money_in(text, r"([\d.]+)\s*kr\.?/md")
    upfront = money_in(text, r"Udbetaling:\s*([\d.]+)\s*kr")
    term = integer_in(text, r"Periode:\s*(\d+)\s*mdr")
    aggregate = money_in(text, r"Samlet betaling i perioden:\s*([\d.]+)\s*kr")
    configuration_values = f"{title}\n{monthly}\n{upfront}\n{term}\n{aggregate}\n{text}"
    return {
        "configurationId": f"private-{hashlib.sha256(configuration_values.encode('utf-8')).hexdigest()[:12]}",
        "trim": title,
        "monthlyPaymentDkk": monthly,
        "upfrontPaymentDkk": upfront,
        "termMonths": term,
        "aggregatePaymentDkk": aggregate,
        "sourceWording": text,
    }


def html_text(value: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", value).replace("&nbsp;", " ").split())


def money_in(value: str, pattern: str) -> int:
    match = re.search(pattern, value, flags=re.IGNORECASE)
    if match is None:
        raise StructuralSourceError("Terminalen leasing card is missing an explicit DKK amount")
    return int(match.group(1).replace(".", ""))


def integer_in(value: str, pattern: str) -> int:
    match = re.search(pattern, value, flags=re.IGNORECASE)
    if match is None:
        raise StructuralSourceError("Terminalen leasing card is missing an explicit term")
    return int(match.group(1))


def amount_basis(legal_wording: str) -> str:
    return "including_vat" if re.search(r"inkl\.?\s*moms", legal_wording, flags=re.IGNORECASE) else "not_stated"


def combined_evidence(source_url: str, card_wording: str, legal_wording: str) -> dict[str, str]:
    wording = card_wording if not legal_wording else f"{card_wording}; {legal_wording}"
    return {"sourceUrl": source_url, "wording": wording}


def mileage_fact(source_url: str, legal_wording: str) -> dict[str, Any]:
    match = re.search(r"(\d{1,3}(?:\.\d{3})*)\s*km\s*/\s*år", legal_wording, flags=re.IGNORECASE)
    if match is None:
        return not_stated(source_url, legal_wording)
    return known(int(match.group(1).replace(".", "")), {"sourceUrl": source_url, "wording": match.group(0)})


def inspection_fee(legal_wording: str) -> int | None:
    amount = re.search(r"gebyr på\s*([\d.]+)\s*kr", legal_wording, flags=re.IGNORECASE)
    if amount is None or not re.search(r"Gebyret opkræves sammen med sidste ydelse", legal_wording, flags=re.IGNORECASE):
        return None
    return int(amount.group(1).replace(".", ""))


def normal_end_fact(source_url: str, end_wording: str) -> dict[str, Any]:
    if re.search(r"afleverer du bilen", end_wording, flags=re.IGNORECASE):
        return known("return_to_provider", {"sourceUrl": source_url, "wording": end_wording})
    return not_stated(source_url, end_wording)


def residual_risk_fact(source_url: str, end_wording: str) -> dict[str, Any]:
    if re.search(r"ikke .*værditab", end_wording, flags=re.IGNORECASE):
        return known("provider", {"sourceUrl": source_url, "wording": end_wording})
    return not_stated(source_url, end_wording)


def operational_form_fact(source_url: str, end_wording: str) -> dict[str, Any]:
    has_return = normal_end_fact(source_url, end_wording)["state"] == "known"
    has_provider_risk = residual_risk_fact(source_url, end_wording)["state"] == "known"
    if has_return and has_provider_risk:
        return known("operational", {"sourceUrl": source_url, "wording": end_wording})
    return not_stated(source_url, end_wording)


def service_arrangements_fact(source_url: str, legal_wording: str) -> dict[str, Any]:
    match = re.search(r"inkl\.\s*(alle fabriksanbefalede services)", legal_wording, flags=re.IGNORECASE)
    if match is None:
        return not_stated(source_url, legal_wording)
    return known(
        [{"category": "manufacturer_recommended_service", "treatment": "included", "scope": match.group(1)}],
        {"sourceUrl": source_url, "wording": match.group(0)},
    )


def exclusions_fact(source_url: str, legal_wording: str) -> dict[str, Any]:
    match = re.search(r"Prisen er ekskl\.\s*([^.]*)", legal_wording, flags=re.IGNORECASE)
    if match is None:
        return not_stated(source_url, legal_wording)
    categories = (
        ("co2_fee", "CO2-afgift"),
        ("insurance", "forsikring"),
        ("tyres", "ekstra dæk"),
    )
    return known(
        [
            {"category": category, "treatment": "excluded", "scope": source_term}
            for category, source_term in categories
            if source_term.casefold() in match.group(1).casefold()
        ],
        {"sourceUrl": source_url, "wording": match.group(0)},
    )


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
        {"fact": name, "state": candidate[name]["state"]}
        for name in required_facts
        if candidate[name]["state"] != "known"
    ]


def source_document(url: str, content: str, retrieved_at: str) -> dict[str, str]:
    return {"sourceUrl": url, "contentSha256": hashlib.sha256(content.encode()).hexdigest(), "retrievedAt": retrieved_at}


def required_string(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise StructuralSourceError(f"Terminalen API requires {key}")
    return item


def required_int(value: Mapping[str, Any], key: str) -> int:
    item = value.get(key)
    if not isinstance(item, int) or isinstance(item, bool) or item < 0:
        raise StructuralSourceError(f"Terminalen API requires a non-negative integer {key}")
    return item


def object_value(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise StructuralSourceError(f"{name} must be an object")
    return value


def list_value(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise StructuralSourceError(f"{name} must be an array")
    return value


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)
