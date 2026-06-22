# Data Directory README

Synthetic Swedish neuropsychological language assessment data for embedding-based
paraphasia scoring research.

## Overview

| File | Test | Participants | Items/Rows | Description |
|------|------|--------------|------------|-------------|
| `sweBNT-syntheticData_v3.xlsx` | Boston Naming Test | 100 | 30 items | Confrontation naming |
| `sweSVF-syntheticData_v3.xlsx` | Semantic Verbal Fluency | 100 | up to ~25 responses | Animal naming |
| `sweFAS-syntheticData_v3.xlsx` | Phonemic Verbal Fluency | 100 | up to ~15 rows | F-A-S letter fluency |

**Encoding:** UTF-8
**Language:** Swedish
**Data type:** Synthetic (LLM-generated)
**Version:** v3 — adds an `MMSE` metadata row to every test (see below).

---

## File Schemas

> **Note on columns.** Participant responses start at the **third column**
> (spreadsheet column C, header `User-1`) in BNT, and at the **second column**
> (column B, header `User-1`) in SVF and FAS. The intervening/leading empty
> column is an export artifact. There are 100 unique participants; some `User-*`
> headers carry an Excel `.1` suffix (e.g. `User-2.1`) from the export.

### sweBNT-syntheticData_v3.xlsx — Boston Naming Test

Sheet: `Blad1`. Participants name pictures; responses are compared against the
target word in column `Gold`.

| Column | Type | Description |
|--------|------|-------------|
| `Gold` | string | Target word (correct answer), rows 2–31 |
| `User-1` ... `User-100` | string | Participant responses (from column C) |

**Metadata rows:**
| Row | Field | Values |
|-----|-------|--------|
| 34 | `Gender:` | `M`, `F` |
| 35 | `Age:` | numeric (years) |
| 36 | `Kategori:` | `HC`, `MCI`, `AD`, `non-AD` |
| 37 | `MMSE` | numeric (0–30) |

**Target words (Gold), rows 2–31:**
säng, penna, visselpipa, kam, såg, helikopter, bläckfisk, galge, kamel, kringla,
racket, vulkan, pil, jordglob, bäver, noshörning, iglo, domino, rulltrappa,
hängmatta, pelikan, pyramid, passare, dragspel, sparris, lås, ok, sfinx, spalje,
gradskiva

---

### sweSVF-syntheticData_v3.xlsx — Semantic Verbal Fluency

Sheet: `SVF_djur_60s`. Participants name animals within the time limit; one word
per row.

| Column | Type | Description |
|--------|------|-------------|
| (col A) | — | Empty leading column |
| `User-1` ... `User-100` | string | Animal names or empty (from column B) |

**Metadata rows:**
| Row | Field | Values |
|-----|-------|--------|
| 28 | `Gender:` | `M`, `F` |
| 29 | `Age:` | numeric (years) |
| 30 | `Category:` | `HC`, `MCI`, `AD`, `non-AD` |
| 31 | `MMSE` | numeric (0–30) |

---

### sweFAS-syntheticData_v3.xlsx — Phonemic/Letter Verbal Fluency

Sheet: `FAS_simulation`. Participants produce words starting with F, A, S; each
row stores one comma-separated triplet (F-word, A-word, S-word).

| Column | Type | Description |
|--------|------|-------------|
| (col A) | — | Empty leading column |
| `User-1` ... `User-100` | string | Triplet: `"F-word, A-word, S-word"` (from column B) |

**Example:** `"fisk, artikel, snö"`

**Metadata rows:**
| Row | Field | Values |
|-----|-------|--------|
| 19 | `Gender:` | `M`, `F` |
| 20 | `Age:` | numeric (years) |
| 21 | `Category:` | `HC`, `MCI`, `AD`, `non-AD` |
| 22 | `MMSE` | numeric (0–30) |

**Proper nouns / named entities** are marked with angle brackets and should be
excluded from F/A/S scoring: `<Stockholm>`, `<Anna>`, `<Fredrik>`.

---

## Diagnostic Categories

| Code | Description |
|------|-------------|
| `HC` | Healthy Control |
| `MCI` | Mild Cognitive Impairment |
| `AD` | Alzheimer's Disease |
| `non-AD` | Non-Alzheimer's Dementia |

> The diagnostic-group label is stored under the header `Kategori:` in BNT and
> `Category:` in SVF/FAS. The data loader normalises both to a single
> `Category` field.

---

## Missing / Special Values

| Value | Meaning |
|-------|---------|
| *(empty)* | No response / end of list |
| `pass` | Participant skipped item |
| `hhhm jag vet inte`, `vet inte` | "I don't know" non-responses |

**FAS empty positions** appear as missing elements within a triplet, with or
without surrounding spaces: `", ansvar, sol"`, `"fisk, , stol"`, `",,sparv"`.
The loader treats each empty slot as an absent word for that letter.

---

## MMSE (new in v3)

Every test file now carries an `MMSE` metadata row (Mini-Mental State
Examination, 0–30). Values are aligned per participant across the three tests and
were used for the MMSE-prediction analyses in the pipeline. MMSE is synthetic and
inherits all caveats of LLM-generated data; it is **not** a validated cognitive
score.

---

## Directory Structure

```
data/
├── xlsx/          # Source synthetic datasets (v3)
├── lexical/       # Lexical resources (git-ignored; not redistributed)
├── processed/     # Pipeline outputs (git-ignored; regenerable)
└── README.md
```

---

## Notes

- Column-naming quirks: some `User-*` headers carry an Excel `.1` suffix
  (`User-2.1`, `User-34.1`) from export; there are 100 unique participants.
- Response data includes realistic errors: semantic paraphasias, circumlocutions,
  and superordinate substitutions.
- Earlier versions (`v1`, `v2`) used different filenames and lacked the MMSE row;
  they are superseded by v3 and are not included.

---

## Source and Citation

Synthetic data generated January 2026 for the thesis *Embedding-Based Graded
Scoring of Paraphasic Errors in Neuropsychological Language Tests*.

The canonical, citable version of this dataset is archived at Språkbanken Text
(Kokkinakis, 2026): `https://doi.org/10.23695/06j6-0j33. Please cite that DOI when
referring to the data.

Contact: Dimitrios Kokkinakis (dimitrios.kokkinakis@svenska.gu.se)
