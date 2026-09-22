# MetriCheck — Real Package Validation Dataset Framework

This directory houses the evaluation datasets and ground-truth annotations for **MetriCheck** (SIH26034 — Legal Metrology Packaged Commodities Compliance Scanner for India).

---

## 1. Directory Structure

```text
datasets/real_package_validation/
├── README.md
├── dataset_generator.py          # Generator for controlled synthetic test sets
├── images/
│   ├── real/                     # Directory for genuine real-world package photographs
│   └── synthetic/                # Directory for controlled synthetic test packages
├── annotations/
│   ├── real/                     # Ground-truth annotations for real photographs
│   └── synthetic/                # Ground-truth annotations for synthetic test sets
└── metadata/
    └── dataset_manifest.json     # Metadata and dataset index
```

---

## 2. Mandatory Dataset Classification

Every dataset and annotation file MUST declare an explicit `dataset_type`:

| Dataset Type | Description |
| :--- | :--- |
| `REAL_PHOTO` | Genuine photographs taken of physical retail packaged commodities. |
| `SYNTHETIC_CONTROLLED` | Programmatically generated or rendered package imagery used for controlled stress testing and perturbation benchmarks. |
| `MIXED` | A dataset containing both real photographs and synthetic packages (metrics are strictly reported separately). |

> **IMPORTANT RULE**: Controlled synthetic packages MUST NEVER be labeled or reported as real-world photographs. Real-photo accuracy and synthetic controlled accuracy are always calculated and presented independently.

---

## 3. Ground-Truth Annotation Format

Each product has a JSON annotation file in `annotations/real/` or `annotations/synthetic/`:

```json
{
  "product_id": "product_001",
  "dataset_type": "REAL_PHOTO",
  "package_material": "Plastic Pouch",
  "category": "Food & Grocery",
  "images": [
    {
      "image_id": "product_001_front",
      "file_name": "product_001_front.jpg",
      "role": "front"
    },
    {
      "image_id": "product_001_back",
      "file_name": "product_001_back.jpg",
      "role": "back"
    }
  ],
  "ground_truth": {
    "PRODUCT_NAME": "Royal Basmati Rice",
    "MRP": "₹299.00",
    "NET_QUANTITY": "5 kg",
    "MANUFACTURER": "Himalayan Agro Foods Ltd, Sector 18, Gurugram, Haryana - 122015",
    "PACKER": null,
    "IMPORTER": null,
    "MANUFACTURING_DATE": "01/2026",
    "PACKING_DATE": null,
    "EXPIRY_DATE": "12/2027",
    "BEST_BEFORE": "24 Months from Packaging",
    "CONSUMER_CARE": "care@himalayanagro.in, 1800-111-222",
    "COUNTRY_OF_ORIGIN": "India"
  }
}
```

### Absence Semantics:
- Use `null` when a declaration genuinely does not exist or is not legally required for that product (e.g. an indigenous domestic product has `IMPORTER: null`).
- A genuinely absent declaration (`null`) is evaluated as `NOT_APPLICABLE` or confirmed absence, NEVER as an OCR error.

---

## 4. How to Provide Real-World Package Photographs

Real photographs of commercial packaged commodities do not need to be committed to Git. You can supply an external dataset directory using either:

### Method 1: CLI Argument
```bash
uv run python tests/run_real_validation_benchmark.py --dataset-dir "/path/to/my_real_packages"
```

### Method 2: Environment Variable
```bash
$env:METRICHECK_REAL_DATASET_DIR = "/path/to/my_real_packages"
uv run python tests/run_real_validation_benchmark.py
```

The external directory should have the same structure:
```text
my_real_packages/
├── images/
│   └── product_001_front.jpg
└── annotations/
    └── product_001.json
```

If no external real dataset is supplied, the benchmark runner executes the `SYNTHETIC_CONTROLLED` dataset and explicitly reports:
```text
Real Photograph Validation:
NOT EXECUTED — no genuine real-photo dataset supplied.
```

---

## 5. Benchmark Output Locations

All benchmark results and diagnostic failure analyses are written to:
- **Metrics JSON**: `backend/tests/benchmark_results_real.json`
- **Failure Analysis**: `backend/tests/real_world_failure_analysis.md`
