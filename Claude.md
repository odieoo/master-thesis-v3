# Claude.md — Technical Context for the SQL→Cassandra Migration Thesis Project

This file is the persistent technical reference for future Claude sessions working on this
repository. It was produced by direct inspection of the source code, configuration, and
generated output files in this repo (as of 2026-09-05). Wherever something could not be
verified from the repository, this is stated explicitly rather than guessed.

---

## Project Overview

This repository is the code companion to a Master's thesis on **migrating relational
(SQL) database schemas to Apache Cassandra**, a wide-column / column-oriented NoSQL
database. The repo implements and compares **two different, independently-coded
approaches** for suggesting a Cassandra table design from a relational schema:

1. A **clustering-based approach** using sentence embeddings + unsupervised clustering
   over `table.column` name strings.
2. An **LLM-based approach** using Google's Gemini API, prompted directly with the list
   of `table.column` names.

The repository is experimental/exploratory in nature (single-file scripts, hardcoded
paths, hardcoded API keys, no test suite, no CLI framework) rather than a productized
tool. It is best understood as a lab notebook that produced concrete output artifacts
(JSON, CQL, PNG visualizations) which are then compared against each other.

## Thesis Context

The thesis question is about the transformation of relational schemas into
Cassandra's denormalized, query-driven data model. The repo contains supporting research
material in `documents/` (papers on RDBMS→NoSQL migration, a DVD Store benchmark paper
analysis, Cassandra reference material) and two experimental pipelines that operationalize
different strategies for making this transformation:

- Automatic/statistical (embedding similarity + clustering — no external model).
- AI-assisted (delegating schema-design judgment to an LLM via prompting).

The comparison of these two is the empirical contribution the code in this repo supports.

**Important discrepancy to flag:** `documents/Implementation1.md` describes a *third*,
more sophisticated pipeline ("Hybrid Query Discovery": `schema_extractor.py`,
`candidate_query_generator.py`, `query_log_generator.py`, `query_prioritizer.py`,
producing `output/candidate_queries.json`, `output/query_log.json`,
`output/prioritized_queries.json`). **None of these files exist anywhere in this
repository** (verified via repo-wide search). This appears to be documentation for a
planned/future phase of the methodology (query-log-driven, frequency-based
prioritization) that has not yet been implemented in code. Do not assume this pipeline
exists — only the clustering-based and Gemini-based approaches described below are
actually implemented.

---

## Repository Structure

```
utils/                              Core Python scripts (the actual migration logic)
  db_service.py                     DB connector — extracts table.column names
  clustering.py                     Clustering-only approach (Agglomerative, script form)
  gemini_migration_analyzer.py      Combined Gemini + embedding-clustering pipeline (main script)
  comparison_analyzer.py            Compares Gemini output vs embedding-clustering output
  embaddings-generator.py           Standalone embedding-generation demo/debug script
  test-google-models.py             Standalone Gemini API smoke-test / model-listing script
  dummy.py                          Scratch/experiment file (Colab-style, HF sentiment pipeline)
  __pycache__/                      Compiled bytecode (not source)

db/                                 Input databases and DB source material
  chinook.db                        SQLite sample DB (earlier experiment subject)
  ds2/                               DVD Store 2 (DS2) benchmark: docs, Perl installers, schema docs
    ds2_schema.txt                   Human-readable schema doc for DS2 (8 tables)
    mysqlds2/build/mysqlds2_create_db.sql   Actual CREATE TABLE DDL used to build the MySQL DS2 DB
  ds21.tar.gz, ds21_mysql.tar.gz     DS2 distribution archives
  extractor-tar-gz.py                Safe tar-extraction helper for the above archives

documents/                          Research material (papers, notes) — not executable code
  Implementation1.md                Describes an UNIMPLEMENTED "Phase 2" query-log-driven pipeline
  dataset-installation.md            Notes on how DS2 was obtained/installed and how query logs
                                     are conventionally captured (MySQL general_log)
  cassandra-course.md, useful-links.md   Reference links
  *.pdf                              Source papers (migration methodology, Cassandra reference)

output/                             All generated artifacts from running the utils/ scripts
  ds2_json.json                     Flat list of "table.COLUMN" strings extracted from DS2 (MySQL)
  ds2_Fixed.json                    Manually-shaped nested {table: {column: null}} view of the same
  gemini_suggested_tables.json      Gemini's structured JSON table-grouping suggestion (DS2 run)
  gemini_migration_suggestions.txt  Gemini's free-text detailed migration strategy (DS2 run)
  embedding_suggested_tables.json   Embedding+KMeans clustering table-grouping output (DS2 run)
  cassandra_schema.cql              CQL generated FROM THE EMBEDDING CLUSTERS (not from Gemini)
  cassandra_migration_visualization.png   PCA scatter plot of KMeans clusters (Gemini script's clustering half)
  clustering_visualization.png      PCA scatter plot of AgglomerativeClustering clusters (clustering.py)
  comparison_visualization.png      Side-by-side scatter plots: embedding clusters vs Gemini table membership
  comparison_results.json           Jaccard-similarity comparison metrics between the two approaches
  DELL-DVD-ERD-diagram.svg          ER diagram of the DS2 schema (reference image)
  chinbook_content/                 Earlier full run of the SAME pipeline against chinook.db (SQLite)
```

Note the plumbing: `output/ds2_json.json` (produced by `db_service.get_table_columns()`)
is the **single shared input artifact** consumed by `gemini_migration_analyzer.py`,
`comparison_analyzer.py`, and (via `db_service.get_table_columns()`, called live) by
`clustering.py`.

---

## Migration Architecture

Both approaches share the *same* input-extraction step and the *same* representation of
the schema: **a flat list of `"table.COLUMN"` strings**, with no types, no keys, and no
foreign-key metadata carried along. This is the most consequential architectural fact in
the repo — see [Important Technical Concepts](#important-technical-concepts).

```
MySQL DS2 database
   │
   ▼
utils/db_service.py :: get_table_columns()
   │  (SHOW TABLES, then SHOW COLUMNS FROM <table> for each)
   ▼
list["table.COLUMN", ...]  ──────►  saved to output/ds2_json.json
   │
   ├──────────────────────────────────────────────┐
   ▼                                               ▼
utils/clustering.py                    utils/gemini_migration_analyzer.py
(embedding + AgglomerativeClustering)  (Gemini prompting  +  embedding + KMeans clustering)
   │                                               │
   ▼                                               ▼
clustering_visualization.png          gemini_suggested_tables.json, gemini_migration_suggestions.txt,
(console-printed clusters only —                embedding_suggested_tables.json, cassandra_schema.cql,
no JSON/CQL saved by this script)               cassandra_migration_visualization.png
                                                    │
                                                    ▼
                                    utils/comparison_analyzer.py
                                    (Jaccard similarity between Gemini tables and embedding clusters)
                                                    │
                                                    ▼
                                    comparison_results.json, comparison_visualization.png
```

---

## Method 1: Clustering-Based Migration

### Purpose
Group semantically-similar columns (by name) into clusters intended to become Cassandra
tables, using no external AI model — purely local embeddings + unsupervised clustering.

### Input
`table_columns = get_table_columns()` from [utils/db_service.py](utils/db_service.py) —
a live call to the MySQL DS2 database (`host=localhost, user=web, password=web,
database=ds2`), returning a flat Python list of strings like `"customers.CUSTOMERID"`.
There is **no SQL parsing** of `CREATE TABLE`/DDL text; the schema is discovered purely
through MySQL's `SHOW TABLES` / `SHOW COLUMNS FROM <table>` introspection commands (see
`get_table_columns()` in [utils/db_service.py:94-126](utils/db_service.py)). No data
values, no column types, no PK/FK constraints are read or used anywhere downstream.

### Processing pipeline (file: [utils/clustering.py](utils/clustering.py))

`utils/clustering.py` (module-level script, executes top-to-bottom, no `main()` / no
function decomposition):

1. `get_table_columns()` (imported from `db_service.py`) → flat list of `table.column` strings.
2. `SentenceTransformer('all-MiniLM-L6-v2').encode(table_columns)` → 384-dimensional
   embedding vector per column-name string (line 20-21). This is the **only feature
   extracted** — a semantic embedding of the literal string `"table.COLUMN"` (dots and
   underscores included, not stripped).
3. `cosine_similarity(embeddings)` → full pairwise similarity matrix (line 26).
4. `distance_matrix = 1 - similarity_matrix` → converts similarity to a distance metric
   for use by a distance-based clustering algorithm (line 42).
5. **Number of clusters is forced to equal the number of tables**:
   `n_clusters = len(set(col.split('.')[0] for col in table_columns))` (line 45-46).
   This means the algorithm is *not* discovering a natural number of clusters — it is
   told in advance "produce exactly as many groups as there are original SQL tables."
6. `AgglomerativeClustering(n_clusters=n_clusters, metric='precomputed', linkage='average')`
   `.fit_predict(distance_matrix)` (lines 51-56) — hierarchical agglomerative clustering
   using average linkage over the precomputed cosine-distance matrix.
7. Columns are grouped by resulting cluster label (`defaultdict(list)`), printed to
   console (not saved as JSON in this script).
8. Cross-table high-similarity pairs (`similarity >= 0.7`, only pairs from *different*
   source tables) are computed and printed as a diagnostic (lines 82-105) — this is
   informational only; it does not feed back into the clustering or the schema output.
9. Visualization: embeddings reduced to 2D via `PCA(n_components=2)` (line 124-125),
   plotted with `matplotlib`, colored by cluster label, saved to
   `../output/clustering_visualization.png` (line 168-169).

### Algorithm
- **Embedding model**: `sentence-transformers` `all-MiniLM-L6-v2` (384-dim).
- **Similarity metric**: cosine similarity (`sklearn.metrics.pairwise.cosine_similarity`).
- **Clustering algorithm**: `sklearn.cluster.AgglomerativeClustering`, `linkage='average'`,
  `metric='precomputed'` (i.e., operates directly on the 1-minus-cosine-similarity
  distance matrix rather than raw embedding vectors).
- **Dimensionality reduction for viz only**: `sklearn.decomposition.PCA` to 2 components.

### Cassandra table / key generation
**`clustering.py` does not generate any Cassandra schema (no CQL, no partition-key or
clustering-key selection logic exists in this file at all).** It only prints cluster
membership to the console and saves a PNG plot. There is no `CREATE TABLE`, no primary
key selection, and no output JSON produced by this specific script.

The actual **CQL generation** for the clustering-based approach lives in a *different*
file — `generate_cassandra_schema()` inside
[utils/gemini_migration_analyzer.py:292-332](utils/gemini_migration_analyzer.py) — which
operates on the **KMeans**-based clusters computed later in that same file (see Method 2
below), not on `clustering.py`'s AgglomerativeClustering output. This is an important
implementation detail: the file named `cassandra_schema.cql` in `output/` was generated
from KMeans clusters (produced inside the Gemini script), not from the
AgglomerativeClustering clusters in `clustering.py`. The two clustering algorithms are
never reconciled or run through the same code path.

### Partition key / clustering key selection (as actually implemented)
In `generate_cassandra_schema()` ([utils/gemini_migration_analyzer.py:292-332](utils/gemini_migration_analyzer.py)):
- Table name = underscore-joined sorted set of source table names + `_data` suffix
  (e.g. cluster containing columns from `reorder`, `orderlines`, `orders` becomes
  `orderlines_orders_reorder_data`, per [output/cassandra_schema.cql:18](output/cassandra_schema.cql)).
- **Every column is typed as `text`** — no type inference or mapping from the original
  SQL column types (INT, DATE, NUMERIC, etc.) is performed anywhere in this pipeline.
- **Partition key = the first column in the cluster's list, unconditionally**
  (`PRIMARY KEY ({first_col})`, [utils/gemini_migration_analyzer.py:327-328](utils/gemini_migration_analyzer.py)).
  There is no ranking, scoring, or cardinality analysis to choose a "good" partition key
  — it is purely positional (whatever order the columns happened to be grouped in).
- **No clustering columns are ever generated** — every generated table has a
  single-column `PRIMARY KEY`, confirmed in every table of
  [output/cassandra_schema.cql](output/cassandra_schema.cql) (e.g.
  `PRIMARY KEY (customers_CREDITCARDTYPE)`, `PRIMARY KEY (orders_ORDERID)`).
- Column names are flattened by replacing `.` with `_` (e.g. `customers.CUSTOMERID` →
  `customers_CUSTOMERID`), so the table-of-origin remains encoded in each column name.

### Relationship handling
No explicit relationship/FK model is used or needed, because none exists in the source:
the DS2 MySQL DDL ([db/ds2/mysqlds2/build/mysqlds2_create_db.sql](db/ds2/mysqlds2/build/mysqlds2_create_db.sql))
declares **no `FOREIGN KEY` constraints** at all — only `AUTO_INCREMENT PRIMARY KEY` on
`CUSTOMERS.CUSTOMERID`, `ORDERS.ORDERID`, `PRODUCTS.PROD_ID`, `INVENTORY.PROD_ID`, and
`CATEGORIES.CATEGORY`. "Relationships" in the clustering approach are therefore entirely
implicit — they emerge only if two columns from different tables happen to have similar
embeddings (e.g., `reorder.PROD_ID` and `products.PROD_ID` both containing "PROD_ID").
There is no explicit foreign-key traversal, no join-graph construction, and no
1:N / M:N distinction anywhere in the code.

### Heuristics/rules used
- Cluster count == table count (heuristic, hardcoded assumption that source tables are
  a reasonable proxy for target table count).
- 0.7 cosine-similarity threshold for reporting "high similarity" cross-table pairs
  (diagnostic-only, not used for schema decisions).
- First-column-as-partition-key (positional heuristic, no semantic justification in code).
- All columns as `text` type (default/no-op heuristic).

### Output
- Console-printed cluster groupings (no file).
- [output/clustering_visualization.png](output/clustering_visualization.png) — PCA 2D
  scatter of the Agglomerative clusters (labeled "Cassandra Table 1..8" in the legend
  even though this script does not itself produce Cassandra tables).
- (Indirectly, via the Gemini script's KMeans clustering + `generate_cassandra_schema()`):
  [output/embedding_suggested_tables.json](output/embedding_suggested_tables.json) and
  [output/cassandra_schema.cql](output/cassandra_schema.cql).

### Limitations (observed)
- No type mapping, no clustering-column selection, positional (not analytical) partition
  key choice, no use of PK/FK metadata (because DS2 has almost none), no query-pattern
  awareness, no validation that generated tables actually serve any real query.
- `clustering.py` and the clustering logic inside `gemini_migration_analyzer.py` use two
  *different* algorithms (Agglomerative vs KMeans) and are not unified — the file
  producing the final `.cql` output is not `clustering.py` itself.
- Requires a live MySQL connection with hardcoded credentials (`web`/`web`) to run.

---

## Method 2: Gemini/LLM-Based Migration

### Purpose
Delegate schema-design reasoning (grouping columns, choosing partition/clustering keys,
denormalization strategy) to Google's Gemini LLM via natural-language + JSON-structured
prompting, instead of relying on unsupervised clustering.

### File
[utils/gemini_migration_analyzer.py](utils/gemini_migration_analyzer.py) — this single
file implements **both** the Gemini calls **and** its own independent embedding+KMeans
clustering pipeline, run one after the other in `main()`. (`utils/test-google-models.py`
is a separate, standalone smoke-test script that lists available Gemini models and is not
part of the executed pipeline.)

### Input
`JSON_FILE_PATH = "../output/ds2_json.json"` — the **same** flat
`["table.COLUMN", ...]` list produced by `db_service.get_table_columns()`, loaded via
`load_json_schema()` ([utils/gemini_migration_analyzer.py:52-70](utils/gemini_migration_analyzer.py)).
So the Gemini approach receives an identical schema representation to the clustering
approach — a flat list of qualified column names, no types, no keys, no FK info.

### Gemini API call mechanics
`call_gemini_api()` ([utils/gemini_migration_analyzer.py:73-132](utils/gemini_migration_analyzer.py)):
- Uses the `google.genai` package (`from google import genai`), **not** the older
  `google.generativeai` package.
- `client = genai.Client(api_key=api_key)` — API key is **hardcoded in source**
  (`GEMINI_API_KEY = "AIzaSyCr9llWTEZ_LYHE_oazT2oLwLC-xgYNJww"`, line 37) — a live
  secret committed to the repo. (`test-google-models.py` and
  `embaddings-generator.py`/`dummy.py`'s neighbor `utils/test-google-models.py` also
  hardcode a *different* key: `AIzaSyAXprsvJy44V14AsnqoGRQOtMEaEdEZAdU`.) **Both should
  be treated as compromised/exposed and rotated — flagged here as a security concern,
  not fixed automatically per Rule 6 (preserve the repository).**
- **Model**: `gemini-2.5-flash` (hardcoded, line 111).
- **No explicit temperature, top_p, or max_output_tokens configuration is set** — the
  call is `client.models.generate_content(model="gemini-2.5-flash", contents=full_prompt)`
  with no `generation_config`/`config` argument at all. Generation settings are therefore
  whatever Gemini's API defaults are for that model; **not determined from the available
  source code**.
- **No structured-output / JSON-mode / response-schema constraint is used** — the API is
  called with a plain text prompt and returns plain text; JSON-ness of the response is
  requested only via prompt instructions ("Return ONLY a valid JSON object..."), not via
  any `response_mime_type` or schema parameter.
- **Retry logic**: up to `max_retries=5` attempts, only retrying on
  `ClientError` containing `"RESOURCE_EXHAUSTED"` or `"429"` (rate limiting), with linear
  backoff `wait_time = (attempt + 1) * 10` seconds (10s, 20s, 30s, 40s, 50s). Any other
  exception type is caught, logged, and returns `None` (no retry). If retries are
  exhausted, returns `None` and prints an error — callers must handle a `None` response.
- A system-style instruction is prepended to every prompt in-line (not via a dedicated
  `system_instruction` API field):
  `"You are an expert database architect specializing in migrating relational databases
  to NoSQL column-oriented databases like Cassandra. Provide practical, detailed
  migration suggestions."` ([utils/gemini_migration_analyzer.py:100-104](utils/gemini_migration_analyzer.py)).

### Two sequential Gemini calls are made (non-deterministic pipeline, two different prompts)

**Call 1 — structured JSON table suggestion** ([utils/gemini_migration_analyzer.py:357-378](utils/gemini_migration_analyzer.py)):
- Prompt: dumps the full `columns` list as pretty-printed JSON, asks Gemini to "Analyze
  this schema and suggest how to migrate to Cassandra," explicitly instructs it to
  "Group columns that are frequently queried together," "Consider denormalization for
  query optimization," and to "Return ONLY a valid JSON object" mapping
  `cassandra_table_name -> [columns]`.
- **Note the input given here is the flat list, but Gemini's response uses bare column
  names without the table prefix** (e.g. `"CUSTOMERID"` not `"customers.CUSTOMERID"`),
  as seen in [output/gemini_suggested_tables.json](output/gemini_suggested_tables.json).
  This is a self-directed choice by the model, not something the code enforces.

**Response parsing** ([utils/gemini_migration_analyzer.py:380-412](utils/gemini_migration_analyzer.py)):
- Strips markdown code fences manually: if response starts with ` ``` `, splits on
  ` ``` ` and takes segment `[1]`, then strips a leading `json` tag if present.
- `json.loads(clean_response)` — a **bare `try/except json.JSONDecodeError`**; on
  failure it only prints a warning and continues (no retry-with-different-prompt, no
  schema validation of the parsed structure, no check that referenced columns actually
  exist in the original schema).
- On success, saves the parsed dict verbatim to
  [output/gemini_suggested_tables.json](output/gemini_suggested_tables.json).

- 10-second fixed `time.sleep(10)` between the two calls to avoid rate limiting
  ([utils/gemini_migration_analyzer.py:414-417](utils/gemini_migration_analyzer.py)).

**Call 2 — free-text detailed migration strategy** ([utils/gemini_migration_analyzer.py:420-434](utils/gemini_migration_analyzer.py)):
- Same column list, but a different prompt asking for prose covering: (1) migration
  approach, (2) partition/clustering key suggestions, (3) denormalization strategies,
  (4) query patterns optimized for, (5) example CQL.
- Response is **not parsed at all** — saved verbatim as plain text to
  [output/gemini_migration_suggestions.txt](output/gemini_migration_suggestions.txt).
  This is where the actual partition-key/clustering-key reasoning is visible (in prose +
  example CQL), but it is never programmatically extracted back into a structured schema
  or validated — it is documentation-only output.

### Independent embedding/KMeans clustering (same file, runs regardless of Gemini success)
After (or instead of, if no API key) the Gemini calls, `main()` proceeds to run its own
clustering pipeline on the same `columns` list:
- `generate_embeddings()` → `SentenceTransformer('all-MiniLM-L6-v2')` (line 158-172,
  identical model to `clustering.py`).
- `n_clusters` auto-detected as `len(unique_tables)` if `N_CLUSTERS is None` (default;
  line 458-462) — same heuristic as `clustering.py`.
- `cluster_columns()` → **`sklearn.cluster.KMeans(n_clusters=n_clusters, random_state=42,
  n_init='auto')`** ([utils/gemini_migration_analyzer.py:175-190](utils/gemini_migration_analyzer.py))
  — note this is **KMeans**, a different algorithm from `clustering.py`'s
  AgglomerativeClustering, despite both scripts conceptually implementing "the clustering
  approach." `random_state=42` makes this half deterministic given fixed input.
- Cluster→table naming and JSON export identical in spirit to describe above:
  `embedding_suggested_tables.json`.
- `reduce_dimensions()` (PCA to 2D) + `create_visualization()` →
  `cassandra_migration_visualization.png`.
- `generate_cassandra_schema(clusters, gemini_response)` — **this is the actual function
  that writes [output/cassandra_schema.cql](output/cassandra_schema.cql)**, and it uses
  only the `clusters` dict (KMeans output); the `chatgpt_suggestion`/`gemini_response`
  parameter is accepted but **never used inside the function body** (dead parameter —
  the CQL text does not reference or embed anything from Gemini's text response).

### Error / invalid-response handling
- Missing/placeholder API key (`"your-gemini-api-key-here"`) → skips both Gemini calls
  entirely, prints a warning, and proceeds straight to the embedding/KMeans path (line
  355, 448-451). The script is therefore designed to degrade gracefully to the clustering
  approach if no key is present, but a real (if possibly expired/invalid) key is
  hardcoded in the committed source, so this fallback path would not normally trigger.
- Invalid JSON from Gemini → warning printed, `suggested_tables` stays `None`, no
  retry, execution continues (the JSON-based table suggestion file is simply not written).
- Non-rate-limit API exceptions → printed, function returns `None`, caller does not crash
  but downstream `if gemini_response:` guards skip writing outputs.

### Determinism
- **Gemini calls are not deterministic** — no `seed`/`temperature=0` is set, and Gemini
  is a hosted model that can return different groupings/prose across runs.
- **The KMeans clustering half is deterministic** given the same embeddings, because
  `random_state=42` is fixed; the embedding model itself (`all-MiniLM-L6-v2`) is also
  deterministic at inference time for identical input strings.

### Output (Gemini approach specifically)
- [output/gemini_suggested_tables.json](output/gemini_suggested_tables.json) — 6 tables,
  79 total column references (with duplication across tables — denormalized).
- [output/gemini_migration_suggestions.txt](output/gemini_migration_suggestions.txt) —
  free-text strategy, including explicit partition-key / clustering-key / CQL guidance
  (this is the only place in the whole repo where clustering columns are actually
  proposed, and it is prose, not machine-parsed).

### Limitations (observed)
- Two Gemini prompts are independent — the structured JSON table names
  (`customers_by_id`, etc.) and the prose response's table names
  (`customers_by_id`, `order_details_by_order_id`, etc.) are **not cross-validated**
  against each other by the code; they happen to be similar in this run because the same
  model produced both from similar prompts, but nothing enforces consistency.
  Comparing [output/gemini_suggested_tables.json](output/gemini_suggested_tables.json)
  against the tables described in
  [output/gemini_migration_suggestions.txt](output/gemini_migration_suggestions.txt)
  shows the JSON output has table `order_details_by_order` while the text has
  `order_details_by_order_id` — same concept, different derived name, never reconciled.
- No validation that suggested column names actually exist in the source schema (Gemini
  returns bare names like `"FIRSTNAME"` without table qualification, so there's no
  programmatic way to check for typos/hallucinated columns).
- The `cassandra_schema.cql` file's name and header comment
  ("-- Generated based on semantic clustering analysis") could mislead a reader into
  thinking it reflects Gemini's suggestions; **it is actually generated solely from the
  KMeans clustering output**, not from Gemini.
- Hardcoded, exposed API key committed to source control (see above).

---

## Output Analysis

### Input schema (both approaches, DS2 run)
DS2 "DVD Store" benchmark schema, MySQL, **8 tables, 52 columns total**
([output/ds2_json.json](output/ds2_json.json)): `categories` (2 cols), `cust_hist`
(3 cols), `customers` (19 cols), `inventory` (3 cols), `orderlines` (5 cols), `orders`
(6 cols), `products` (7 cols), `reorder` (6 cols). Confirmed against the actual DDL in
[db/ds2/mysqlds2/build/mysqlds2_create_db.sql](db/ds2/mysqlds2/build/mysqlds2_create_db.sql):
only `CUSTOMERS.CUSTOMERID`, `ORDERS.ORDERID`, `PRODUCTS.PROD_ID`,
`INVENTORY.PROD_ID`, and `CATEGORIES.CATEGORY` are declared as primary keys; **no
`FOREIGN KEY` constraints exist in the schema at all** — relationships are implicit
(same column name convention, e.g. `PROD_ID` appears in `products`, `inventory`,
`orderlines`, `cust_hist`, `reorder`).

### Clustering approach output ([output/cassandra_schema.cql](output/cassandra_schema.cql), built from KMeans clusters)
8 tables generated, each named by joining its source table names alphabetically + `_data`:
- `customers_data` (appears **twice** — cluster 0 has 3 columns
  `CREDITCARDTYPE/CREDITCARD/CREDITCARDEXPIRATION`, cluster 4 has 10 different customer
  columns; both KMeans clusters independently produced the exact table name
  `customers_data`, silently colliding — `output/embedding_suggested_tables.json` avoids
  this only because its dict keys overwrite each other, ending up with a **single**
  merged `customers_data` entry of 10 columns, i.e. the 3-column cluster's content is
  lost in the JSON but both appear in the printed/](output/cassandra_schema.cql) CQL text
  as two separate `CREATE TABLE IF NOT EXISTS customers_data` statements — a real bug:
  the second `CREATE TABLE... customers_data` would fail in Cassandra due to the
  `IF NOT EXISTS` guard silently no-op'ing, silently dropping the credit-card columns).
- `orderlines_orders_reorder_data`, `cust_hist_customers_data`,
  `categories_inventory_products_data`, `cust_hist_orderlines_data`,
  `cust_hist_inventory_products_reorder_data`, `orders_data`.
- Every table: all columns typed `text`, single-column `PRIMARY KEY` = first column in
  cluster (positional, e.g. `PRIMARY KEY (customers_CREDITCARDTYPE)`,
  `PRIMARY KEY (cust_hist_CUSTOMERID)`) — **no clustering columns anywhere**.
- Denormalization is incidental (a side effect of which columns happened to embed
  closely), not driven by any declared query pattern.
- Relationships: implicit only, via shared substrings like `PROD_ID`/`CUSTOMERID`
  landing in the same cluster.

### Gemini approach output ([output/gemini_suggested_tables.json](output/gemini_suggested_tables.json) + [output/gemini_migration_suggestions.txt](output/gemini_migration_suggestions.txt))
6 tables, deliberately denormalized and named after query intent:
- `customers_by_id` (20 cols) — full customer profile lookup by ID.
- `orders_by_customer` (8 cols, includes denormalized `FIRSTNAME`/`LASTNAME`) — customer
  order history.
- `order_details_by_order` (25 cols — the most denormalized table, embeds customer,
  product, category, and order-line data together) — full order view in one read.
- `products_by_id` (10 cols, merges `products` + `inventory` fields) — product detail lookup.
- `products_by_category` (10 cols, duplicates most product fields) — category listing.
- `product_reorder_status` (6 cols, maps 1:1 to `reorder` table) — restock status.

The prose file ([output/gemini_migration_suggestions.txt](output/gemini_migration_suggestions.txt))
additionally proposes a **6th/7th** table, `customer_product_history` (mapping
`cust_hist`), and gives concrete partition-key / clustering-column choices absent from
the JSON, e.g.:
- `products_by_category`: partition key `category`, clustering columns `title, prod_id`.
- `orders_by_customer`: partition key `customerid`, clustering columns
  `orderdate DESC, orderid`.
- `order_details_by_order_id`: partition key `orderid`, clustering column `orderlineid`.
- `customer_product_history`: partition key `customerid`, clustering column `prod_id`.
- Recommends `UUID` types for IDs and flags credit-card/password fields as needing
  encryption/hashing — a data-governance consideration entirely absent from the
  clustering approach's output (which stores everything, including
  `customers_CREDITCARD`/`customers_PASSWORD`, as plain `text`).

**Key discrepancy**: the *only structured, machine-usable* Gemini output
(`gemini_suggested_tables.json`) contains **no partition-key/clustering-key
information at all** — that reasoning exists solely in the unstructured text file. So
in practice, "Gemini's schema" as consumed by [comparison_analyzer.py](utils/comparison_analyzer.py)
is just as key-less as the clustering approach's JSON; the richer key design only exists
as prose for a human reader, never fed back into any generated CQL for the Gemini path
specifically (there is no `gemini_cassandra_schema.cql` file anywhere in `output/`).

### Comparison of outputs ([output/comparison_results.json](output/comparison_results.json), via [utils/comparison_analyzer.py](utils/comparison_analyzer.py))
- Gemini: 6 tables / 79 total column-slots (denormalized, columns repeated across tables).
- Embedding/KMeans: 7 tables / 49 total column-slots (closer to a partition of the
  original 52 columns, i.e., much less denormalization).
- Jaccard similarity computed per Gemini table against its best-matching embedding table
  (after normalizing names: strip table prefix, lowercase, remove underscores).
  Average similarity across matched pairs: **58.15%**. 4 of 6 pairs exceed 50%
  similarity; **0 pairs exceed 90%** (`perfect_matches: 0`) — the two approaches never
  fully agree on any single table's column membership.
  Best alignment: `product_reorder_status` ↔ `orderlines_orders_reorder_data` (71.4%).
  Worst alignment: `order_details_by_order` ↔ `customers_data` (25%) — Gemini's most
  denormalized, cross-entity table has no good embedding-based counterpart, because the
  clustering approach never produces a single table spanning that many source tables.

---

## Comparison

| Aspect | Clustering Approach | Gemini/LLM Approach |
|---|---|---|
| Input | Flat `table.COLUMN` string list from live MySQL introspection (`db_service.get_table_columns()`) | Same flat list, loaded from the saved `ds2_json.json` file |
| Processing | Sentence embeddings (`all-MiniLM-L6-v2`) → cosine similarity → AgglomerativeClustering (`clustering.py`) or KMeans (`gemini_migration_analyzer.py`'s own clustering half) | Two prompt/response round-trips to Gemini `gemini-2.5-flash`, plus (separately, same file) its own embedding+KMeans clustering |
| Schema understanding | None beyond string similarity of column names; no types, no keys, no FK read | Model reasons in natural language about entities/relationships from column names alone (no types/keys given either) |
| Table generation | Cluster ⇒ table; table name = sorted source-table names + `_data` | Model freely proposes table names reflecting query intent (`_by_id`, `_by_customer`, etc.) |
| Partition-key selection | Positional: always the first column in the cluster list (no scoring) | Explicit reasoning in prose (cardinality/access-pattern justification given for each table); **not present in the structured JSON output** |
| Clustering-key selection | **None implemented** — every generated table is single-column PK | Present only in prose output (e.g. `orderdate DESC, orderid`); never encoded in JSON or a `.cql` file |
| Relationship handling | Implicit, via embedding similarity of shared substrings (e.g. `PROD_ID`) | Implicit too (same flat input), but the LLM narrates inferred 1:1 / 1:N relationships explicitly in prose (e.g. "inventory 1:1 with products") |
| Denormalization | Incidental / unintentional — a side effect of clustering, not a designed strategy; embedding output is closer to a partition (49 of 52 original columns, minimal duplication) | Deliberate and explicit strategy, explicitly reasoned about in the prompt and response; heavy duplication (79 column-slots from 52 source columns) |
| Determinism | Embeddings deterministic; AgglomerativeClustering fully deterministic given fixed input; KMeans deterministic here due to `random_state=42` | Two Gemini calls are non-deterministic (no seed/temperature=0 set); the file's own KMeans half is deterministic |
| Explainability | Low — cluster membership has no stated rationale beyond "high cosine similarity"; console-only diagnostic of cross-table pairs | High in the prose output — every table/key choice comes with a written justification; low in the structured JSON output (no rationale, just column lists) |
| Dependence on heuristics | High — cluster count = table count, first-column-as-PK, `_data` suffix naming, all-`text` typing, are all hardcoded rules | Low for the LLM call itself, but the file's *own* clustering half shares the same heuristics as the clustering approach |
| Dependence on external model | None (fully local: `sentence-transformers` + `scikit-learn`) | High — requires network access, a valid Gemini API key, and Gemini API availability/quotas |
| Computational cost | Local CPU/GPU inference only (one embedding batch of 52 short strings + agglomerative/KMeans clustering — cheap) | Two network round-trips to a hosted LLM, plus a fixed 10s sleep between them, plus the same local embedding+clustering cost as the other approach (this file does both) |
| Scalability | Embedding + clustering cost grows with column count but stays cheap for realistic schemas; forcing `n_clusters == n_tables` does not scale conceptually to schemas needing very different Cassandra table counts | Prompt size grows with schema size (all columns dumped into the prompt text); large schemas risk exceeding context/token limits or costing more; retry logic only covers rate limiting, not general robustness at scale |
| Error handling | None needed/implemented (no external call); assumes DB connection succeeds | Retry with backoff for rate limits only (5 attempts, 10s/20s/.../50s); bare `try/except` around JSON parsing with only a printed warning on failure; other exceptions caught and return `None` |
| Adaptability | Low — same fixed heuristics regardless of domain; would need code changes to adapt naming/PK-selection rules | Higher in principle (prompt text could be changed to steer behavior without code changes), but current prompts are hardcoded and not parameterized by e.g. known query patterns |
| Potential weaknesses | No PK/clustering-key rationale, single-column PKs only, table-name collisions overwrite data silently (`customers_data` collision, see Output Analysis), all columns typed as `text`, no validation of output against source schema | Non-deterministic and unverifiable without re-running; structured JSON output lacks the very key-design detail (partition/clustering keys) that is the whole point of Cassandra modeling; two prompts can produce mutually inconsistent table names/counts; hardcoded exposed API key; no schema/column-existence validation of the model's response |

---

## Trace the Implementation (pipeline diagrams)

### Clustering-based pipeline (as actually wired, using files that produce output/)
```
MySQL DS2 database
  → utils/db_service.py :: get_table_columns()          [SHOW TABLES / SHOW COLUMNS FROM]
  → output/ds2_json.json  (flat "table.COLUMN" list)
  → utils/clustering.py (standalone script, re-fetches via get_table_columns()):
        SentenceTransformer('all-MiniLM-L6-v2').encode()
      → cosine_similarity()
      → 1 - similarity  (distance matrix)
      → n_clusters = len(unique source tables)
      → AgglomerativeClustering(metric='precomputed', linkage='average').fit_predict()
      → console-printed clusters + high-similarity-pair diagnostic
      → PCA(n_components=2) → matplotlib scatter
      → output/clustering_visualization.png
```

### KMeans/CQL-producing half of the "Gemini" file (the path that actually writes cassandra_schema.cql)
```
output/ds2_json.json
  → utils/gemini_migration_analyzer.py :: load_json_schema()
  → generate_embeddings()                [SentenceTransformer('all-MiniLM-L6-v2')]
  → cluster_columns()                    [sklearn.cluster.KMeans, random_state=42]
  → output/embedding_suggested_tables.json
  → reduce_dimensions()                  [PCA 2D]
  → create_visualization()               → output/cassandra_migration_visualization.png
  → generate_cassandra_schema(clusters)  → output/cassandra_schema.cql
```

### Gemini LLM pipeline
```
output/ds2_json.json
  → utils/gemini_migration_analyzer.py :: load_json_schema()
  → json_prompt built (schema dump + structured-JSON instructions)
  → call_gemini_api(json_prompt, GEMINI_API_KEY)     [model="gemini-2.5-flash", retry x5 on 429]
  → manual markdown-fence stripping → json.loads()
  → output/gemini_suggested_tables.json
  → time.sleep(10)
  → detail_prompt built (partition/clustering/denorm/CQL-example instructions)
  → call_gemini_api(detail_prompt, GEMINI_API_KEY)
  → output/gemini_migration_suggestions.txt          (saved verbatim, unparsed)
```

### Comparison pipeline
```
output/gemini_suggested_tables.json, output/embedding_suggested_tables.json, output/ds2_json.json
  → utils/comparison_analyzer.py :: compare_migration_approaches()
  → SentenceTransformer('all-MiniLM-L6-v2').encode(original_columns)  [for visualization only]
  → PCA(n_components=2)
  → normalize_column() [strip table prefix, lowercase, remove underscores]
  → Jaccard similarity per Gemini-table vs every Embedding-table → best match kept
  → output/comparison_results.json
  → output/comparison_visualization.png (two side-by-side scatter plots)
```

---

## Important Technical Concepts

- **Schema representation is name-only.** Across both approaches, the SQL schema is
  reduced to a flat list of `"table.COLUMN"` strings. No column data types, no
  PRIMARY KEY/FOREIGN KEY metadata, no row-count/cardinality statistics, and no query
  logs are used as input anywhere in the executed code. This is consistent with the fact
  that the DS2 MySQL DDL itself declares almost no FK constraints
  ([db/ds2/mysqlds2/build/mysqlds2_create_db.sql](db/ds2/mysqlds2/build/mysqlds2_create_db.sql)).
- **Embedding model**: `sentence-transformers/all-MiniLM-L6-v2`, 384-dim, used
  identically (same model string) in `clustering.py`, `gemini_migration_analyzer.py`,
  `comparison_analyzer.py`, and `embaddings-generator.py`.
- **Two different clustering algorithms exist under the "clustering approach" umbrella**:
  `AgglomerativeClustering` (average linkage, precomputed cosine distance) in
  `clustering.py`, versus `KMeans` (`random_state=42`) inside
  `gemini_migration_analyzer.py`. Only the KMeans path's clusters are ever turned into a
  `.cql` file.
- **Cluster count heuristic**: both clustering paths set `n_clusters` equal to the number
  of distinct source SQL tables — an assumption baked into the code, not a discovered or
  tuned value (e.g. via silhouette score or elbow method — neither is implemented).
- **`generate_cassandra_schema()`'s dead parameter**: accepts a `chatgpt_suggestion`
  (aliased in the call site as `gemini_response`) argument that is never referenced in
  the function body — Gemini's output has zero influence on the generated `.cql` file's
  content despite being passed in.
- **Table-name collision bug**: KMeans producing two clusters whose sorted source-table
  set is identical (both are pure `customers` clusters here) causes both
  `generate_cassandra_schema()` (two `CREATE TABLE IF NOT EXISTS customers_data`
  statements in the same file — the second is a silent no-op in real Cassandra) and the
  JSON export (`embedding_suggested_tables.json`, a Python dict — second write overwrites
  the first key) to silently lose one cluster's data. Confirmed by diffing
  [output/cassandra_schema.cql](output/cassandra_schema.cql) (which shows both
  `customers_data` tables, 3 cols and 10 cols) against
  [output/embedding_suggested_tables.json](output/embedding_suggested_tables.json)
  (which shows only one `customers_data` entry, with 10 columns — the 3-column
  credit-card cluster is missing).
- **Structured output is prompt-engineered, not API-enforced.** Gemini's JSON response is
  requested purely through prompt wording ("Return ONLY a valid JSON object... Return
  ONLY the JSON, no other text") and parsed with manual string-splitting on triple
  backticks plus `json.loads()` — no `response_mime_type="application/json"` or
  schema/tool-based structured output feature of the Gemini API is used.
- **Hardcoded secrets**: two different Gemini API keys are committed in plaintext in
  `utils/gemini_migration_analyzer.py:37` and `utils/test-google-models.py:9`. Treat as
  exposed; do not reuse, and flag to the user for rotation/removal — do not silently
  "fix" this without telling the user, per the instruction to preserve the repository
  and report findings faithfully.
- **Two independent database subjects were used across the project's history**:
  `chinook.db` (SQLite, Chinook sample DB — outputs preserved under
  `output/chinbook_content/`) was the earlier experiment; the current/active run is
  against the DS2 "DVD Store" MySQL benchmark database (outputs directly in `output/`).
  `db_service.py`'s current code only supports MySQL/DS2; the SQLite/chinook logic is
  present but fully commented out in the same file (two commented-out prior versions:
  a script-level version and a `get_table_columns()` function version).

---

## How to Run

Only commands/behavior directly inferable from the source are listed; nothing here is invented.

- **Clustering approach**: from inside `utils/`, run `python clustering.py`. Requires a
  live MySQL server reachable at `localhost` with database `ds2`, user `web`,
  password `web` (hardcoded in `db_service.py`), and the packages imported at the top of
  the file (`sentence-transformers`, `scikit-learn`, `matplotlib`, `numpy`). Produces
  console output and `../output/clustering_visualization.png`; does not write any JSON/CQL.

- **Gemini + embedding pipeline**: from inside `utils/`, run
  `python gemini_migration_analyzer.py`. The file's own docstring
  ([utils/gemini_migration_analyzer.py:1-17](utils/gemini_migration_analyzer.py)) states:
  ```
  pip install google-genai sentence-transformers scikit-learn matplotlib numpy
  python chatgpt_migration_analyzer.py   # (docstring is stale — actual filename differs)
  ```
  Note the docstring's own usage line references a filename
  (`chatgpt_migration_analyzer.py`) that does not match the actual file
  (`gemini_migration_analyzer.py`) — a leftover from an earlier ChatGPT-based version of
  the script (consistent with the commented-out `call_chatgpt_api()` function still
  present in the file, lines 135-155). The correct invocation based on the file's actual
  name is `python gemini_migration_analyzer.py`. Reads `../output/ds2_json.json` (must
  already exist — produced by a prior run of `db_service.get_table_columns()`); requires
  network access to Google's Gemini API and the hardcoded API key to still be valid.
  Writes `gemini_suggested_tables.json`, `gemini_migration_suggestions.txt`,
  `embedding_suggested_tables.json`, `cassandra_migration_visualization.png`,
  `cassandra_schema.cql` into `../output/`.

- **Comparison**: from inside `utils/`, run `python comparison_analyzer.py`. Requires
  `../output/gemini_suggested_tables.json`, `../output/embedding_suggested_tables.json`,
  and `../output/ds2_json.json` to already exist (i.e., must run after the Gemini script).
  Writes `../output/comparison_visualization.png` and `../output/comparison_results.json`.

- **Generating `ds2_json.json` from scratch**: calling
  `db_service.get_table_columns()` (e.g. via `python -c "from db_service import
  get_table_columns; get_table_columns()"` from inside `utils/`, or implicitly via
  `clustering.py`'s import) connects to the MySQL `ds2` database and (re)writes
  `../output/ds2_json.json`.

- **Not determined from the available source code**: how the MySQL `ds2` database itself
  was populated in this environment (the `db/ds2/mysqlds2/` Perl/SQL scripts are present
  as the DS2 distribution's own installer, but no repo script here automates running
  them against a local MySQL instance for this project specifically), and what Python/
  package version constraints apply (no `requirements.txt` or `pyproject.toml` exists
  anywhere in the repo).

---

## Known Issues / Limitations

1. **`Implementation1.md` describes an unimplemented pipeline.** Phase-2 "Hybrid Query
   Discovery" files (`schema_extractor.py`, `candidate_query_generator.py`,
   `query_log_generator.py`, `query_prioritizer.py`) and their outputs
   (`candidate_queries.json`, `query_log.json`, `prioritized_queries.json`) do not exist
   in the repository. Do not treat this document as reflecting current code.
2. **Table-name collision silently drops data** in the KMeans/embedding path — see
   `customers_data` discrepancy above.
3. **`generate_cassandra_schema()` ignores its `chatgpt_suggestion`/`gemini_response`
   argument** — the file `cassandra_schema.cql`, despite living in the same script as
   the Gemini calls and being generated right after them in `main()`, has zero Gemini
   influence; it is purely a KMeans-clusters-to-CQL dump.
4. **No partition/clustering-key selection logic exists in code for either approach** —
   the only concrete PK/clustering-key proposals in the whole repo are the Gemini
   free-text output (`gemini_migration_suggestions.txt`), which is never parsed back into
   a machine-usable schema.
5. **All generated CQL columns are typed `text`**, with no type inference from the
   original SQL column types, even though those types (INT, DATE, NUMERIC, VARCHAR) are
   readily available from `SHOW COLUMNS` (but not captured by
   `db_service.get_table_columns()`, which only keeps column *names*).
2. **Hardcoded, exposed Gemini API keys** in two files.
6. **`clustering.py` and the KMeans half of `gemini_migration_analyzer.py` are not the
   same algorithm**, despite both being labeled/thought-of as "the clustering approach";
   only the latter's output is materialized into the committed `.cql`/`.json` artifacts.
7. **No automated tests** exist anywhere in the repository (no `tests/` directory, no
   `pytest`/`unittest` usage found).
8. **Docstring/filename mismatch** in `gemini_migration_analyzer.py`'s module docstring
   (references a non-existent `chatgpt_migration_analyzer.py`), and a fully commented-out
   `call_chatgpt_api()` function, both remnants of an earlier ChatGPT-based version of
   this same script.
9. **`db_service.py` hardcodes MySQL credentials** (`user="web", password="web"`) and a
   fixed `host="localhost"` — not configurable via environment variables or CLI args.
10. **DS2 schema's near-total absence of FK constraints** (only 5 PKs, zero FKs across 8
    tables) means neither approach is actually tested against a schema with rich,
    explicit relational metadata it could have exploited — an important caveat for any
    thesis claim about "relationship handling," since the input data itself under-tests
    that capability.

---

## Research-Relevant Observations

**Observed facts** (directly supported by code/output inspected above):
- The clustering approach (embedding-only KMeans/Agglomerative path) produced output
  closer to a *partition* of the original columns (49 of 52 columns placed, minimal
  duplication, 7 tables), while the Gemini approach produced a heavily *denormalized*
  schema (79 column-slots from 52 source columns across 6 tables, i.e. ~52% column
  duplication) — a directly measurable, code-computed difference
  ([output/comparison_results.json](output/comparison_results.json)).
- Average Jaccard similarity between the two approaches' table groupings was 58.15%,
  with zero pairs above 90% similarity — i.e., by this repo's own metric, the two methods
  never converge on the same table design for any entity, even where they agree
  reasonably well (e.g., reorder-related data at 71.4%).
- Only the Gemini (prose) output contains any partition-key/clustering-key rationale;
  the clustering approach never produces clustering columns at all (single-column PK
  only), and Gemini's own *structured* JSON output likewise omits key information —
  key-design reasoning exists in this repo exclusively as unstructured natural-language
  text, not as parseable/executable schema metadata.
- The clustering approach's decisions (partition key = first column, cluster count =
  table count) are purely positional/structural heuristics with no data- or
  query-pattern justification recorded anywhere in code or output. The Gemini approach's
  decisions come with explicit, human-readable justifications (e.g., "high cardinality
  and matches your most common access pattern's filter criteria") but these
  justifications are Gemini's own inferred/assumed query patterns, not patterns derived
  from real application logs (no query log exists in this repo — `Implementation1.md`
  proposes but does not implement query-log-driven prioritization).

**Interpretation** (author's synthesis, for thesis framing — not directly "in" the code):
- This repo's two approaches sit at different points on an
  explainability/determinism-vs-semantic-reasoning trade-off: the clustering approach is
  fully deterministic and reproducible offline but is "reasoning-free" (a name-similarity
  heuristic standing in for actual query-driven design), whereas the Gemini approach can
  articulate genuine schema-design rationale (query patterns, denormalization trade-offs,
  security notes) but is non-deterministic, unverifiable without re-running, and — in
  this implementation — that rationale is never actually operationalized into the
  machine-generated CQL artifact.
- The near-zero use of relational metadata (types, keys, FKs) by both approaches suggests
  that any observed quality difference between them in this repo is attributable
  primarily to "column-name semantics" (embedding similarity vs. LLM world-knowledge
  about e-commerce domain terms like `CUSTOMERID`/`PROD_ID`) rather than to structural
  understanding of the relational schema itself — a nuance worth making explicit in the
  thesis rather than implying either method deeply "understands" the schema's relational
  structure.
- The fact that the only CQL file in the repo comes from the clustering (KMeans) path,
  with Gemini's richer key-design reasoning left unparsed in a `.txt` file, suggests the
  project's automation is currently ahead on the "generate something mechanically" axis
  and behind on the "faithfully operationalize the LLM's judgment" axis — likely a
  natural discussion point for future work / limitations sections of the thesis.
