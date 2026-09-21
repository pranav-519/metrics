# MetriCheck: Legal Metrology Packaged Commodities Compliance Scanner

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-v4-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)
[![Rules](https://img.shields.io/badge/Legal_Framework-LMR_2011_v2024.1-blue.svg)](#legal-framework)

> **Hackathon Prototype Assistance System:** An uncertainty-aware, explainable decision-support web application for manufacturers and compliance inspectors to verify packaged commodity declarations against Indian **Legal Metrology (Packaged Commodities) Rules, 2011**.

---

## 🏛️ Project Mission & Problem Statement

Packaged commodities in India must display mandatory statutory declarations under **Rule 6 of the Legal Metrology (Packaged Commodities) Rules, 2011**, including:
1. **Maximum Retail Price (MRP)** with statutory tax inclusion phrasing ("inclusive of all taxes").
2. **Net Quantity** in standardized metric units (strictly prohibiting misleading terms such as *"when packed"*).
3. **Unit Sale Price (USP)** where statutory packaging thresholds apply.
4. **Name and complete address** of the manufacturer, packer, or importer.
5. **Month and Year** of manufacture, packing, or import.
6. **Best Before / Expiry Date** for perishable commodities.
7. **Consumer Care Details** (toll-free telephone, electronic mail, physical address).
8. **Statutory Font Height** on the principal display panel.

Manual inspection is tedious and error-prone. **MetriCheck** provides an automated, explainable assistant that processes packaging photographs, evaluates category-specific versioned rules, measures font dimensions via calibration, and explicitly handles optical uncertainty.

> **Important Legal Disclaimer:** MetriCheck is a prototype compliance-assistance tool designed to identify verified issues, potential non-compliances, and uncertain fields. It does **not** make final statutory legal determinations.

---

## 🌟 Key Innovations & Critical Solutions

### 1. Optical Uncertainty & Clear Taxonomy
- Distinguishes reliably between **`NOT_FOUND`** (clean OCR confirms declaration is missing) and **`UNABLE_TO_VERIFY`** (image blur, glare, or confidence < 55%).
- Unreadable or low-confidence fields are **never** automatically penalized as statutory violations.
- Transparent per-token confidence indicators for all extracted declarations.

### 2. Multi-Panel Packaging Support
- Upload slots for **Front Panel** (Principal Display), **Back Panel** (Details & Consumer Care), **Side Panel** (Dates & Batch codes), and **Close-up Panel** (Stamps & fine print).
- Combined cross-panel OCR extraction that avoids duplicate declarations.

### 3. Computer Vision Quality Telemetry
- Automatic **Laplacian variance** sharpness measurement to flag out-of-focus photographs.
- **Specular glare detection** to identify washed-out text regions.
- Automatic **CLAHE (Contrast Limited Adaptive Histogram Equalization)** preprocessing and OCR retry.

### 4. Physical Font Height Calibration (No Pixels-as-Millimeters)
- Designed around real-world calibration standards (e.g. standard ID card width 85.6mm or ₹5 coin 23.0mm).
- Converts pixel heights into estimated physical millimeters ($mm$) and benchmarks against statutory minimum thresholds (1.0mm, 1.5mm, 2.0mm, 4.0mm).
- Explicitly flags values as `VERIFIED` (calibrated) vs. `ESTIMATED` (camera heuristic).

### 5. Versioned & Category-Specific Legal Rules
- Decoupled rule engine with version history (`LMR-2011-v2024.1`).
- Initial statutory categories:
  - `Food / Grocery`
  - `Cosmetics`
  - `Household Products`
  - `Other Packaged Commodities`
- Future amendments can be added to the database without altering frontend code.

### 6. Full Explainability
- No opaque binary "PASS/FAIL". Every check provides:
  - **Field** and **Detected Text**
  - **Expected Requirement**
  - **Compliance State**
  - **Statutory Reason**
  - **Applicable Legal Clause & Version**
  - **Suggested Inspector Action**

---

## 🏗️ System Architecture

```
MetriCheck/
├── frontend/                     # React 19 + Tailwind CSS v4 + Vite
│   ├── src/
│   │   ├── components/           # Navbar, StatusBadge, ConfidenceBar, QualityBadge
│   │   ├── pages/                # Dashboard, NewScan, Analysis, Results, RulesExplorer
│   │   ├── index.css             # Tailwind v4 theme & typography
│   │   ├── App.jsx               # Tab state management & router
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js            # Proxy to backend on :8000
│
├── backend/                      # Python 3.11 + FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/                  # REST routers: /dashboard, /scans, /rules, /categories
│   │   ├── core/                 # App settings & config
│   │   ├── database/             # SQLAlchemy session & seed script
│   │   ├── models/               # Scan, ScanImage, Declaration, Rule models
│   │   ├── schemas/              # Pydantic v2 schemas
│   │   ├── services/
│   │   │   ├── image_processing/ # Image quality (blur, glare, CLAHE)
│   │   │   ├── ocr/              # Pretrained OCR interface & engine
│   │   │   ├── extraction/       # Declaration regex & NER parsing
│   │   │   ├── rules/            # Versioned rule engine & evaluator
│   │   │   ├── measurement/      # Physical calibration & mm calculation
│   │   │   └── reporting/        # Explainable report synthesis
│   │   └── main.py               # FastAPI entry point
│   ├── tests/                    # Pytest automated test suite
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start Guide (Local Setup)

### Prerequisites
- **Node.js** v18+ and `npm`
- **Python** 3.11+ (or [uv](https://github.com/astral-sh/uv))

---

### Step 1: Backend Setup

#### On Windows (PowerShell):
```powershell
cd backend

# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Seed database with categories, versioned rules, and demo scans
python -m app.database.seed

# 4. Start the FastAPI server
uvicorn app.main:app --reload --port 8000
```

#### On Linux / macOS (Bash):
```bash
cd backend

# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Seed database
python3 -m app.database.seed

# 4. Start the FastAPI server
uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- **Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Step 2: Frontend Setup

Open a separate terminal window:

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Start Vite development server
npm run dev
```

Open your browser at:
👉 **[http://localhost:5173](http://localhost:5173)**

---

### Running Automated Tests

To execute the backend verification test suite:

```powershell
cd backend
.\.venv\Scripts\activate
pytest -v tests
```

---

## 🐳 Docker Deployment

To launch the complete stack with PostgreSQL and Nginx:

```bash
docker-compose up --build
```

---

## 📊 API Reference Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health, framework & version info |
| `GET` | `/api/dashboard/stats` | Aggregated compliance rates & recent audit scans |
| `GET` | `/api/categories` | Statutory commodity categories list |
| `GET` | `/api/rules` | Versioned legal rules (filter by category) |
| `GET` | `/api/scans` | Paginated packaging scan audit records |
| `POST` | `/api/scans` | Multi-image multipart upload & full pipeline execution |
| `GET` | `/api/scans/{id}` | Detailed audit report with declarations & rule checks |
| `DELETE` | `/api/scans/{id}` | Delete a scan record |

---

## ⚖️ Hackathon Development Principles Followed
- ✅ **No Fake AI Claims:** Explicitly documents heuristics, pre-trained OCR wrappers, and confidence metrics.
- ✅ **Zero Crash Resiliency:** Gracefully falls back if external weights are unavailable or if an image is degraded.
- ✅ **No Hard-coded Rules in UI:** Rules are loaded dynamically from the versioned database.
- ✅ **No Weight Bloat in Git:** Pre-trained model integration lives behind a clean service layer without committing weights.
- ✅ **Safe Data Handling:** Clear distinction between missing declarations and low-confidence unverified text.
