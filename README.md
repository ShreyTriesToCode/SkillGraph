# SkillGraph

A local career-exploration application that compares a student's skills with occupation requirements, explains matching and missing skills, and builds a prerequisite-aware learning roadmap.

## Features

- Student profiles with recognized skill aliases and self-reported proficiency
- Ranked career matches, comparisons and component-level explanations
- Essential and optional skill-gap analysis
- RDF knowledge graph with relationship provenance, local SPARQL queries and Turtle export
- TF-IDF/SVD occupation representations and cosine similarity
- Learning roadmaps with prerequisites, persistent completion and acquired-skill updates
- CSV inspection, explicit column mapping and normalized exports
- Responsive interface with keyboard graph inspection and reduced-motion support

The six pages are Overview, Profile, Careers, Skill gaps, Knowledge graph and Learning roadmap. Expand the sections on Knowledge graph to access technical data, queries and CSV import.

## Requirements

- Python 3.11 or newer
- Node.js 22.12 or newer, with npm
- macOS for the provided setup and launch scripts
- Internet access for the first dependency installation

## Quick start

Clone the repository and open a terminal in its root folder:

```bash
git clone https://github.com/ShreyTriesToCode/SkillGraph.git
cd SkillGraph
bash scripts/setup_mac.sh
bash scripts/run_demo.sh
```

Open http://127.0.0.1:5173/ . The API documentation is at http://127.0.0.1:8000/docs and health is at http://127.0.0.1:8000/api/health . Keep the terminal open. Press Ctrl+C to stop both services. Later launches need only `bash scripts/run_demo.sh`.

Setup creates a virtual environment, installs Python and locked frontend dependencies, builds the occupation model and compiles the frontend. Startup creates a local SQLite database and seeds three fictional example profiles. No external database server, paid service or dataset download is needed for the bundled examples. If port 8000 or 5173 is occupied, stop the existing application you recognize before launching.

For manual launch on another platform, create and activate a Python virtual environment, install `backend/requirements.txt`, run `npm ci --prefix frontend` and `python scripts/train_model.py`. Then run these in separate terminals from the repository root:

```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
npm run dev --prefix frontend
```

The shell scripts target macOS; Windows and Linux setup have not been validated.

## Matching method

```text
matching index = 100 * (0.50 * coverage + 0.20 * graph + 0.30 * similarity)
```

- Coverage weights essential requirements by 2 and optional requirements by 1.
- Graph matching adds 0.35 partial credit for a missing requirement related to a known skill. Partial credit does not remove the requirement from the gap.
- Similarity compares a student's skill vector with occupation vectors using TF-IDF, up to eight TruncatedSVD dimensions and cosine similarity.

Configuration is in `data/scoring.json`. The learned representation fits occupation requirements. Student skill changes update the query vector rather than retraining the occupation catalog. A catalog hash controls model reload/refitting.

Skill presence affects matching. Proficiency, interests, academic details and project descriptions are stored or displayed but do not currently affect the score. Matching indices support exploration and do not measure the probability of career success. Prerequisites and effort estimates are curated planning assumptions.

## Data

`data/demo.json` contains three fictional students, 36 curated skills and ten teaching occupations. `data/esco_snapshot.json` contains an official ESCO API subset with two occupations, 106 skills and 117 requirement links, including source URLs and provenance. The subset is not the full ESCO release. ESCO identifiers remain distinct from curated identifiers; label similarity does not establish equivalence.

Source: [ESCO, European Commission](https://esco.ec.europa.eu/en/use-esco/download). Original survey spreadsheets, processed student surveys and personal databases are not part of this repository. The combined starter catalog supplies 12 occupation documents and 142 concept features. Generated databases, models and exports stay local.

## Try the workflow

1. On Profile, create an anonymous profile and save it. Add Python, SQL, Pandas, Basic Statistics and Git at 3/5.
2. On Careers, filter for Data Engineer and open its skill gaps.
3. Record the matching index, then add ETL on Skill gaps. With the bundled catalog, the index changes from about 46.77 to 61.01.
4. Inspect a relationship and its source on Knowledge graph.
5. On Learning roadmap, mark a task complete. Reload and reselect the profile to inspect saved progress. Recording a skill as acquired also updates the inventory and matching results.

To repeat, remove ETL from Profile and clear any completed roadmap tasks, or create a new anonymous profile.

## Verification

After setup:

```bash
.venv/bin/python -m pytest backend/tests -q
npm run build --prefix frontend
.venv/bin/python scripts/validate_project.py --application-only
```

For browser tests, start the application first, then run:

```bash
cd frontend
npx playwright install chromium
npm test
```

Use `PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/to/chromium npm test` to select an existing compatible browser on macOS/Linux. Browser tests create example profiles and update local progress. Backend tests isolate their test database but can write generated model/export files. Run tests in a disposable checkout when local records must remain unchanged; regenerate the starter model with `scripts/train_model.py` afterward.

To reproduce the catalog retrieval diagnostic:

```bash
MPLCONFIGDIR="$PWD/.build/matplotlib" .venv/bin/python scripts/evaluate.py
```

This generates evaluation JSON, CSV and a chart under `results/`. The experiment hides one essential skill from occupation-derived queries and reports recall@3. It is a catalog retrieval proxy, not independent career-outcome accuracy. Timings include a shared pipeline and do not establish per-method speed differences.

## Structure

```text
backend/app/       API, storage, imports, graph, ranking and roadmap logic
backend/tests/     Backend tests
frontend/src/      React views and lazy graph/chart components
frontend/public/   Local interface fonts and their license
frontend/tests/    Browser workflow and responsive tests
data/              Starter catalogs and scoring configuration
models/            Generated occupation model, ignored by Git
results/           Generated test and evaluation outputs, ignored by Git
scripts/           Setup, launch, training, evaluation and validation
```

## Scope

The application binds to loopback and has no authentication or multi-user access control. It does not assess competency, parse resumes, perform general ontology reasoning or provide validated career-outcome predictions. Keep it local unless you add a suitable deployment and security design.

Interface fonts retain their license under `frontend/public/fonts/`.
