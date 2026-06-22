# Swedish Neuropsychological Test Scoring

Embedding-based graded scoring of paraphasic errors in Swedish neuropsychological
language tests. 

Repo for master's thesis *Embedding-Based Graded Scoring of Paraphasic Errors in Neuropsychological Language Tests* containing scoring pipelines, evaluation code, and synthetic data.

The pipelines score three tests:

- **BNT** — Boston Naming Test (confrontation naming), graded semantic scoring via
  embedding cosine similarity against a gold target.
- **SVF** — Semantic Verbal Fluency (animals), word counts plus embedding-based
  cluster/switch metrics.
- **FAS** — phonemic verbal fluency (F, A, S), count-based scoring plus
  Swedish-orthographic phonemic clustering.

All results are computed on **synthetic data**.

## Repository layout

```
src/thesis_project/      Core package
  embeddings/            Encoder wrappers (KB-BERT, sentence-transformers)
  preprocessing/         Data loaders, response normalisation
  scoring/               BNT graded scorer, SVF/FAS scorers, clustering rules
  evaluation/            SQ3 human-rater agreement, divergence, reliability
  lexical/               SALDO graph, word-frequency backends
bnt_pipeline.py          BNT scoring entry point
svf_pipeline.py          SVF scoring entry point
fas_pipeline.py          FAS scoring entry point
scripts/                 Analysis, calibration, SALDO build, SQ3 rating tools
configs/                 Default configuration (models, paths, thresholds)
data/xlsx/               Synthetic datasets (v3)
docs/                    Methodology write-ups per phase
tests/                   Unit tests and fixtures
notebooks/               Exploratory and results notebooks
```

## Installation

Requires Python 3.12.

```bash
git clone https://github.com/fboglind/swedish-neuropsych-scoring.git
cd swedish-neuropsych-scoring
python -m venv venv && source venv/bin/activate
pip install -e .
```

GPU is recommended for the transformer models but is not required; every pipeline accepts `--mock` to run with placeholder embeddings (no model download, no GPU), which is the quickest way to verify the pipeline end to end.

> **Note** `EmbeddingGemma-300M` is gated on Hugging Face and requires a
> token and license acknowledgement. The other models download without
> authentication. Models are selected via `configs/_default_configs.yaml`.

## Data

The synthetic datasets are in `data/xlsx/`:

| File                           | Test |
| ------------------------------ | ---- |
| `sweBNT-syntheticData_v3.xlsx` | BNT  |
| `sweSVF-syntheticData_v3.xlsx` | SVF  |
| `sweFAS-syntheticData_v3.xlsx` | FAS  |

These are committed here for convenience and reproducibility. The **canonical,
citable version** of the synthetic dataset is archived at Språkbanken Text
(Kokkinakis, 2026): `https://doi.org/10.23695/06j6-0j33.

Generated outputs (scored CSVs, figures, embedding caches) are written to `data/processed/` and are reproducible from the pipelines above.

Lexical resources (SALDO etc.) are **not** redistributed here due to their own licensing (`data/lexical/` is git-ignored), but are available from [Språkbanken Text](https://spraakbanken.gu.se/resurser) and build
the SALDO graph with:

```bash
python scripts/build_saldo_graph.py
```

Checksums for the expected resource files are committed
(`data/lexical/*.sha256`) so you can verify your downloads.

## Running the pipelines

Each pipeline reads its default data path from `configs/_default_configs.yaml`,
or accepts an explicit `--data` argument.

**BNT** — graded semantic scoring:

```bash
python bnt_pipeline.py --data data/xlsx/sweBNT-syntheticData_v3.xlsx
python bnt_pipeline.py --model sbert-swedish        # primary thesis model
python bnt_pipeline.py --mock                        # no GPU / no download
```

**SVF** — fluency counts and cluster metrics:

```bash
python svf_pipeline.py --data data/xlsx/sweSVF-syntheticData_v3.xlsx
python svf_pipeline.py --model sbert-swedish
```

**FAS** — phonemic fluency, count-based plus Troyer-style clustering:

```bash
python fas_pipeline.py --data data/xlsx/sweFAS-syntheticData_v3.xlsx
```

Available `--model` values: `kb-bert`, `sbert-swedish`, `e5-large`,
`e5-large-instruct`. The full multi-model comparison registry (including the
Qwen3, EmbeddingGemma, and Harrier variants used for model-sensitivity analysis)
is configured in `configs/_default_configs.yaml`.

## Mapping to the thesis

| Thesis question                     | Code                                                         |
| ----------------------------------- | ------------------------------------------------------------ |
| SQ1 — BNT graded vs. binary scoring | `bnt_pipeline.py`, `src/thesis_project/scoring/graded_scorer.py`, `binary_scorer.py` |
| SQ2 — SVF cluster metrics           | `svf_pipeline.py`, `src/thesis_project/scoring/svf_scorer.py` |
| SQ3 — human-rater alignment         | `scripts/sq3_analyze.py`, `src/thesis_project/evaluation/sq3_*.py` |

Per-phase methodology notes are in `docs/`.



## Tests

```bash
pip install -e ".[dev]"   # if a dev extra is defined; otherwise install pytest
pytest
```

SALDO-dependent tests use a small fixture (`tests/fixtures/saldo_mini.xml`) and do
not require the full lexical resources.

## License

See [LICENSE](LICENSE (MIT)).
