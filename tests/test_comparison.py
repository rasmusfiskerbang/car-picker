from __future__ import annotations

import unittest

from car_picker.comparison import calculate_comparison_values


class ComparisonCalculationTest(unittest.TestCase):
    def test_calculates_normal_completion_values_with_refunds_without_exposures_in_the_base_stream(self) -> None:
        offer = {
            "termMonths": {"state": "known", "value": 12},
            "baseCashFlowStream": [
                event("extraordinary_payment", "payment", 12000, "acceptance_to_handover", "not_refundable"),
                event("security_deposit", "payment", 4000, "acceptance_to_handover", "refundable"),
                event("monthly_payment", "payment", 1000, "recurring", "not_refundable", recurrence_count=12),
                event("deposit_return", "receipt", 4000, "normal_completion_end", "refundable"),
                event("mandatory_end_payment", "payment", 6000, "normal_completion_end", "not_refundable"),
            ],
            "exposureScenarios": ["third_party_sale_proceeds", "residual_shortfall"],
        }

        values = calculate_comparison_values(offer)

        self.assertEqual(values["upfrontCashRequirement"], {"state": "known", "valueDkk": 16000})
        self.assertEqual(values["nominalBaseOutlay"], {"state": "known", "valueDkk": 30000})
        self.assertEqual(values["nominalMonthlyEquivalent"], {"state": "known", "valueDkk": 2500})

    def test_keeps_independent_values_when_the_term_blocks_only_the_monthly_equivalent(self) -> None:
        offer = {
            "termMonths": {"state": "not_stated"},
            "baseCashFlowStream": [
                event("extraordinary_payment", "payment", 12000, "acceptance_to_handover", "not_refundable"),
            ],
        }

        values = calculate_comparison_values(offer)

        self.assertEqual(values["upfrontCashRequirement"], {"state": "known", "valueDkk": 12000})
        self.assertEqual(values["nominalBaseOutlay"], {"state": "known", "valueDkk": 12000})
        self.assertEqual(
            values["nominalMonthlyEquivalent"],
            {"state": "not_stated", "blockingFacts": ["termMonths"]},
        )

    def test_monthly_equivalent_rounds_the_full_term_division_to_a_whole_dkk(self) -> None:
        offer = {
            "termMonths": {"state": "known", "value": 3},
            "baseCashFlowStream": [
                event("upfront_payment", "payment", 11, "acceptance_to_handover", "not_refundable"),
            ],
        }

        values = calculate_comparison_values(offer)

        self.assertEqual(values["nominalMonthlyEquivalent"], {"state": "known", "valueDkk": 4})

    def test_monthly_equivalent_names_both_missing_stream_and_term(self) -> None:
        values = calculate_comparison_values({"termMonths": {"state": "not_stated"}})

        self.assertEqual(
            values["nominalMonthlyEquivalent"],
            {"state": "not_stated", "blockingFacts": ["baseCashFlowStream", "termMonths"]},
        )

    def test_rejects_non_base_or_out_of_order_events_from_the_base_cash_flow_stream(self) -> None:
        excluded_event = event("third_party_sale", "receipt", 80000, "normal_completion_end", "not_refundable")
        excluded_event["includedInBase"] = False
        out_of_order_offer = {
            "termMonths": {"state": "known", "value": 12},
            "baseCashFlowStream": [
                event("monthly_payment", "payment", 1000, "recurring", "not_refundable", recurrence_count=12),
                event("upfront_payment", "payment", 12000, "acceptance_to_handover", "not_refundable"),
            ],
        }

        excluded_values = calculate_comparison_values({
            "termMonths": {"state": "known", "value": 12},
            "baseCashFlowStream": [excluded_event],
        })
        out_of_order_values = calculate_comparison_values(out_of_order_offer)

        self.assertEqual(excluded_values["nominalBaseOutlay"], {"state": "not_stated", "blockingFacts": ["baseCashFlowStream"]})
        self.assertEqual(out_of_order_values["upfrontCashRequirement"], {"state": "not_stated", "blockingFacts": ["baseCashFlowStream"]})

    def test_keeps_the_known_upfront_requirement_when_a_later_mandatory_payment_is_missing(self) -> None:
        offer = {
            "termMonths": {"state": "known", "value": 12},
            "baseCashFlowStream": [
                event("upfront_payment", "payment", 12000, "acceptance_to_handover", "not_refundable"),
                event(
                    "monthly_payment",
                    "payment",
                    None,
                    "recurring",
                    "not_refundable",
                    recurrence_count=12,
                    blocking_facts=["advertisedMonthlyPayment"],
                ),
            ],
        }

        values = calculate_comparison_values(offer)

        self.assertEqual(values["upfrontCashRequirement"], {"state": "known", "valueDkk": 12000})
        self.assertEqual(
            values["nominalBaseOutlay"],
            {"state": "not_stated", "blockingFacts": ["advertisedMonthlyPayment"]},
        )
        self.assertEqual(
            values["nominalMonthlyEquivalent"],
            {"state": "not_stated", "blockingFacts": ["advertisedMonthlyPayment"]},
        )


def event(
    kind: str,
    direction: str,
    amount_dkk: int | None,
    timing: str,
    refundability: str,
    recurrence_count: int = 1,
    included_in_base: bool = True,
    blocking_facts: list[str] | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "kind": kind,
        "direction": direction,
        "amountDkk": amount_dkk,
        "timing": timing,
        "refundability": refundability,
        "amountBasis": "including_vat",
        "recurrenceCount": recurrence_count,
        "includedInBase": included_in_base,
        "evidence": {
            "sourceUrl": "https://example.test/cash-flow",
            "wording": f"{kind}: {amount_dkk} kr.",
        },
    }
    if blocking_facts is not None:
        value["blockingFacts"] = blocking_facts
    return value


if __name__ == "__main__":
    unittest.main()
