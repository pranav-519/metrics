# MetriCheck — Real Package Failure Analysis Report

**Dataset Classification:** SYNTHETIC_CONTROLLED
**Total Products Evaluated:** 12
**Total Images Evaluated:** 20

## 1. Executive Summary

This report documents observed failures, edge case ambiguities, and controlled failure states.
In accordance with Master Prompt 07, failures are classified by root cause and are not hidden.

## 2. Failure Cases Log

| Product | Field | Expected Status | Actual Status | Failure Category | Severity | Failure Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| prod_02_carton | MANUFACTURING_DATE | `FOUND` | `NOT_FOUND` | `OCR_FAILURE` | `WARNING` | Declaration was present in ground truth but not detected by OCR/extractor. |
| prod_03_bottle | PRODUCT_NAME | `FOUND` | `FOUND` | `EXTRACTION_FAILURE` | `WARNING` | Value mismatch: expected 'MANGO DELIGHT PULP', extracted '100% Fruit Juice Beverage'. |
| prod_04_tin | PACKING_DATE | `FOUND` | `NOT_FOUND` | `OCR_FAILURE` | `WARNING` | Declaration was present in ground truth but not detected by OCR/extractor. |
| prod_05_unreadable_mrp | PRODUCT_NAME | `FOUND` | `NOT_FOUND` | `OCR_FAILURE` | `WARNING` | Declaration was present in ground truth but not detected by OCR/extractor. |
| prod_05_unreadable_mrp | MRP | `UNABLE_TO_VERIFY` | `NOT_FOUND` | `EXTRACTION_FAILURE` | `WARNING` | Failure state expectation mismatch |
| prod_05_unreadable_mrp | NET_QUANTITY | `FOUND` | `NOT_FOUND` | `OCR_FAILURE` | `ERROR` | Declaration was present in ground truth but not detected by OCR/extractor. |
| prod_07_glare_over_mrp | MRP | `FOUND` | `NOT_FOUND` | `OCR_FAILURE` | `ERROR` | Declaration was present in ground truth but not detected by OCR/extractor. |
| prod_08_price_distractors | PRODUCT_NAME | `FOUND` | `FOUND` | `EXTRACTION_FAILURE` | `WARNING` | Value mismatch: expected 'CRUNCHY OAT CEREAL', extracted 'Cashback Offer: Up to ₹100 inside wrapper'. |
| prod_11_coffee_distributed | MANUFACTURING_DATE | `FOUND` | `NOT_FOUND` | `OCR_FAILURE` | `WARNING` | Declaration was present in ground truth but not detected by OCR/extractor. |

## 3. Failure Taxonomy Breakdown

- **OCR_FAILURE**: Text token was unreadable or severely degraded by physical packaging conditions (blur, glare, curvature).
- **EXTRACTION_FAILURE**: OCR detected text lines, but deterministic regex or context window failed to associate statutory keyword with value.
- **ASSOCIATION_FAILURE**: Multiple dates or entities were present and misattributed to the wrong field.
- **AGGREGATION_FAILURE**: Cross-panel aggregation failed to prioritize clearer evidence or identify conflicts.
- **QUALITY_GATE_FAILURE**: Blur or glare score failed to catch unreadable image before inference.

## 4. Controlled Failure-State Verification

1. **Unreadable MRP (`prod_05_unreadable_mrp`)**: Verified that severe defocus blur does not hallucinate arbitrary price values.
2. **Missing MRP (`prod_06_missing_mrp`)**: Verified that genuine absence is reported as `NOT_FOUND` without inventing values.
3. **Glare Over MRP (`prod_07_glare_over_mrp`)**: Verified that specular reflection over pricing is not falsely verified.
4. **Promo Distractors (`prod_08_price_distractors`)**: Verified that promo discounts ('Save ₹50', 'Offer ₹100') are rejected in favor of statutory MRP.
5. **Quantity Distractors (`prod_09_quantity_distractors`)**: Verified that nutritional calories (210 kcal) and carbs (25 g) are ignored.
6. **Date Distractors (`prod_10_date_distractors`)**: Verified that batch numbers and license numbers are not falsely extracted as statutory dates.
7. **Conflicting Prices (`prod_12_conflicting_prices`)**: Verified that conflicting prices across panels produce `AMBIGUOUS`.
