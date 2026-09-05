## Monthly Research Progress Summary

**Master's Thesis: Migrating Relational (SQL) Databases to Apache Cassandra**

---

### 1. Introduction

My Master's thesis addresses a central problem in modern data engineering: how to
migrate a relational (SQL) database schema into a wide-column, NoSQL data model such as
Apache Cassandra. Cassandra does not support joins and requires a *query-driven*,
denormalized data model, which means schema migration is not a mechanical translation —
it requires re-thinking how data should be grouped, partitioned, and duplicated to serve
an application's access patterns efficiently.

During the last month, I implemented and tested **two independent approaches** for
generating a candidate Cassandra schema from a relational schema, using the DVD Store 2
(DS2) benchmark database (a MySQL e-commerce schema with 8 tables and 52 columns) as the
test case:

1. A **clustering-based approach**, which groups columns using semantic embeddings and
   unsupervised machine learning clustering.
2. An **LLM-based approach**, which prompts Google's Gemini model to reason about the
   schema directly and propose a Cassandra design.

I ran both pipelines end-to-end, generated concrete outputs (JSON table definitions, CQL
schema files, and visualizations), and built a comparison analysis between the two. This
document summarizes the implementation, the results, and what they suggest for the next
phase of the thesis.

---

### 2. Clustering-Based Approach

**Purpose.** This approach explores whether Cassandra table groupings can be discovered
automatically, without any external AI model, purely by measuring how *semantically
similar* column names are to each other.

**Input.** The pipeline connects to the MySQL DS2 database and extracts the schema using
MySQL's introspection commands (`SHOW TABLES`, `SHOW COLUMNS FROM <table>`). The result is
a flat list of strings such as `"customers.CUSTOMERID"`, `"orders.ORDERDATE"`, etc. It is
important to note that only **table and column names** are extracted — no data types, no
primary/foreign key constraints, and no sample data are used anywhere downstream.

**Processing and features.** Each `table.column` string is converted into a 384-dimension
semantic vector using the pretrained sentence-embedding model `all-MiniLM-L6-v2`
(from the `sentence-transformers` library). A pairwise **cosine similarity** matrix is then
computed across all columns, and converted into a distance matrix (`distance = 1 − similarity`).
The only "feature" driving the entire process is this embedding-based textual similarity
of column names — there is no use of column type, cardinality, or query information.

**Clustering technique.** The implementation uses **Agglomerative Hierarchical
Clustering** (`scikit-learn`, average linkage, operating on the precomputed cosine
distance matrix). The number of clusters is not learned — it is fixed in advance to equal
the number of original SQL tables (8, in the DS2 case).

**From clusters to a Cassandra schema.** Each cluster of columns becomes one candidate
Cassandra table. The table name is built by joining the names of the source tables that
contributed columns to that cluster (e.g., a cluster combining `orders`, `orderlines`,
and `reorder` becomes `orderlines_orders_reorder_data`). Within each generated table:

- **Partition key** = the *first column* in the cluster's column list — a positional
  choice, not one based on cardinality, access frequency, or any scoring method.
- **Clustering columns**: none are generated. Every resulting table has a single-column
  primary key.
- **Column types**: every column is generated as CQL `text`, regardless of its original
  SQL type (integer, date, decimal, etc.).
- **Relationships between tables**: handled only implicitly — if two columns from
  different source tables (e.g., `PROD_ID` in `products` and `PROD_ID` in `inventory`)
  are semantically close, they may end up in the same cluster and thus the same table.
  There is no explicit foreign-key traversal, because the DS2 schema itself declares
  almost no foreign keys.

**Conceptual flow:**

`SQL Schema (MySQL introspection) → table.column strings → Sentence Embeddings → Cosine Similarity / Distance Matrix → Agglomerative Clustering (k = number of tables) → Cluster → Cassandra Table mapping → CQL Schema (text columns, single-column partition key, no clustering columns)`

---

### 3. Gemini / LLM-Based Approach

**Purpose.** Where the clustering approach relies purely on name similarity, this
approach investigates whether a large language model can perform the more nuanced,
query-driven reasoning that Cassandra schema design actually requires — reasoning about
what data is likely to be queried together, and proposing denormalization accordingly.

**Input provided to Gemini.** The same flat list of `table.column` strings (identical
input to the clustering approach) is serialized as JSON and embedded directly into the
prompt text. No SQL types, constraints, or query logs are provided — Gemini only sees
column names, exactly like the clustering approach.

**Prompt construction.** Two separate prompts are sent to the Gemini API
(model: `gemini-2.5-flash`), each prepended with a short system-style instruction framing
Gemini as "an expert database architect specializing in migrating relational databases to
NoSQL column-oriented databases like Cassandra":

- **Prompt 1 (structured request):** asks Gemini to group the given columns into
  Cassandra tables and to "Return ONLY a valid JSON object" mapping table names to
  column-name arrays, explicitly instructing it to "group columns that are frequently
  queried together" and to "consider denormalization for query optimization."
- **Prompt 2 (detailed strategy):** asks Gemini, in free text, to explain (1) the overall
  migration approach, (2) suggested partition keys and clustering columns, (3)
  denormalization strategy, (4) which query patterns the design optimizes for, and (5)
  example CQL statements.

No temperature, sampling, or structured-output/JSON-mode setting is configured for these
calls — the API is invoked with its default generation settings, and JSON formatting is
requested through prompt wording only, not through a schema-enforcing API feature.

**Parsing and validation.** Gemini's response to Prompt 1 is cleaned of markdown code
fences (stripping ` ``` ` and a leading `json` tag) and parsed with `json.loads()`. If
parsing fails, the failure is logged and the run continues without that output — there is
no retry with a corrected prompt, and no validation that the columns Gemini names
actually exist in the original schema. A retry mechanism does exist, but only for API
rate-limit errors (up to 5 attempts with increasing wait times). Gemini's response to
Prompt 2 is not parsed at all — it is saved as-is, as a human-readable text report.

**From Gemini's response to a Cassandra schema.** The structured JSON output
(table → column list) is the only machine-readable schema Gemini produces. It contains
**no partition-key or clustering-key information** — that reasoning exists only in the
unstructured Prompt 2 text (e.g., "Partition Key: `category`, Clustering Columns:
`title`, `prod_id`"), which is never programmatically converted into an executable CQL
schema. In the current implementation, no separate CQL file is generated from Gemini's
suggestions at all.

**Conceptual flow:**

`SQL Schema (table.column strings) → Prompt Construction (system framing + schema + task instructions) → Gemini API (gemini-2.5-flash, two sequential calls) → JSON response (table→columns) + free-text strategy → Markdown-fence stripping + json.loads() → Validated structured tables (no keys) + unparsed key/denormalization rationale (text only)`

---

### 4. Results / Outputs

Both pipelines were run against the same DS2 schema (8 tables, 52 columns), and their
outputs were compared programmatically.

- The **clustering approach** produced **7 tables covering 49 of the 52 original
  columns**, with almost no column duplication — its output behaves closer to a straight
  *partition* of the schema than a denormalized redesign. Every table has a single-column
  primary key chosen positionally, and no clustering columns.
- The **Gemini approach** produced **6 tables using 79 column-slots** derived from the
  same 52 source columns — meaning columns are duplicated across roughly 1.5 tables on
  average. This reflects deliberate denormalization: for example, its
  `order_details_by_order` table (25 columns) merges data from `orders`, `orderlines`,
  `customers`, and `products` into one wide row, explicitly designed to answer "get
  everything about this order" in a single query.
- A quantitative comparison (Jaccard similarity between each Gemini table and its
  best-matching clustering-approach table) showed an **average similarity of 58%**, with
  **zero table pairs above 90% similarity** — the two methods never fully agree on how
  columns should be grouped, even where they align reasonably well (their best match, on
  reorder/inventory-related data, was 71%).

**What this demonstrates:** the clustering approach tends to preserve something close to
the original table boundaries (grouping by name similarity mostly recovers each source
table on its own), while the Gemini approach actively reorganizes the schema around
inferred *query intent* — it is willing to duplicate data across tables in a way the
clustering approach never does, because nothing in the clustering approach represents the
concept of "a query" at all. However, this richer reasoning from Gemini is only available
as human-readable prose; the machine-readable JSON it produces is, in terms of structure,
just as key-less as the clustering approach's output. This is an important practical
limitation: today, neither pipeline's *automatically parseable* output actually contains
a full partition-key/clustering-key design — only Gemini's unstructured text does.

---

### 5. Comparison and Discussion

| Aspect | Clustering Approach | Gemini/LLM Approach |
|---|---|---|
| Basis for decisions | Textual/semantic similarity of column names only | Model's inferred understanding of likely query patterns |
| Denormalization | Minimal / incidental | Deliberate and explicit |
| Partition key selection | Positional (first column in cluster) | Reasoned about in text, but not present in structured output |
| Clustering columns | Never generated | Proposed in text only, not machine-parsed |
| Determinism | Fully deterministic given the same input | Not deterministic (no fixed seed/temperature); can vary between runs |
| Explainability | Low — similarity score has no domain rationale | High in the free-text output; low in the structured JSON output |
| External dependency | None (fully local computation) | Requires Gemini API access, quota, and a valid key |
| Ease of adapting to a new schema | Automatic, no manual work | Automatic, but quality depends on the model's domain reasoning |

**Advantages of clustering:** reproducible, fully local, fast, and requires no external
service — useful as a deterministic baseline.

**Advantages of the Gemini approach:** captures query-driven reasoning and produces
human-readable justifications for design choices (something the clustering approach
cannot do at all), which is closer to how Cassandra modeling is actually taught and
practiced.

**Key limitation shared by both, as currently implemented:** neither pipeline uses column
data types, primary/foreign key constraints, or real query logs — both work from column
names alone. This is partly a property of the test schema itself (the DS2 database
declares almost no foreign keys), so the current comparison under-tests how well either
method would handle a schema with richer relational metadata.

**Future work:** incorporate column types and any available key constraints into the
feature set for clustering; enforce a structured/schema-validated output from Gemini so
that its partition/clustering-key reasoning becomes machine-usable rather than
prose-only; and, as already outlined in project notes but not yet implemented, incorporate
real or simulated query-log data to prioritize which access patterns should drive table
design, rather than relying on name similarity or model inference alone.

---

### 6. Figures

Three visualizations were generated directly by the project code and are available in the
`output/` folder:

- **Figure 1 — `clustering_visualization.png`** (Clustering approach). A 2D projection
  (via PCA) of the column embeddings, colored by the Agglomerative Clustering result. It
  shows columns from the same source table (e.g., all `customers.*` fields) landing close
  together, while a few cross-table columns sharing naming patterns (e.g., `PROD_ID`
  across `products`, `inventory`, `reorder`) drift toward each other in embedding space.

- **Figure 2 — `cassandra_migration_visualization.png`** (Gemini pipeline's internal
  KMeans clustering step). The same style of 2D PCA projection, but based on the KMeans
  clustering computed inside the Gemini script; used for visual comparison against Figure 1.

- **Figure 3 — `comparison_visualization.png`**. A side-by-side pair of scatter plots
  directly contrasting the clustering-based table groupings (left) against the columns
  Gemini assigned to each of its suggested tables (right), making the difference in
  grouping strategy visually apparent.

Two figures that would be useful to add in a future iteration:

- A **table-level comparison diagram** (e.g., a Sankey or alluvial diagram) showing how
  columns from each original SQL table were redistributed across the final Cassandra
  tables in each approach — this would make the denormalization difference more
  intuitive than the scatter plots alone.
- A **side-by-side CQL schema diagram** rendering the actual generated `CREATE TABLE`
  statements from both approaches next to the original DS2 entity-relationship diagram
  (`output/DELL-DVD-ERD-diagram.svg`, already present in the repository) to visually trace
  which source tables fed into which target table.

---

### Summary of Progress

- Implemented and ran a **clustering-based Cassandra schema migration pipeline** using
  sentence embeddings (`all-MiniLM-L6-v2`) and Agglomerative Clustering over the DS2
  relational schema.
- Implemented and ran an **LLM-based migration pipeline** using Google's Gemini API,
  including structured (JSON) and free-text prompting strategies.
- Generated and inspected concrete outputs from both approaches: candidate Cassandra
  table definitions, a CQL schema file, and PCA-based visualizations.
- Built a **quantitative comparison** between the two approaches (Jaccard similarity
  across generated tables), showing an average agreement of only 58% and no
  near-identical table matches.
- Identified concrete implementation limitations in both pipelines (no partition/
  clustering-key logic in the clustering approach; Gemini's key-design reasoning
  existing only as unstructured text) that will inform the next phase of the thesis.

### Next Steps

1. Extend the schema-extraction step to capture column data types and any declared
   primary/foreign keys, and feed this information into both pipelines instead of using
   column names alone.
2. Convert Gemini's free-text partition-key/clustering-key reasoning into a
   machine-parsable, validated schema (e.g., by requesting structured output with an
   explicit key-design field) so it can be automatically turned into CQL.
3. Investigate query-log-driven prioritization, as outlined conceptually in the project's
   own notes but not yet implemented, to ground table-design decisions in actual or
   simulated access patterns rather than name similarity or model inference alone.
4. Test both pipelines against a schema with richer relational metadata (explicit foreign
   keys) to evaluate relationship-handling more rigorously than the current DS2 dataset
   allows.
5. Define an evaluation methodology for schema "quality" beyond similarity between the
   two approaches — e.g., measuring read-query efficiency of the generated schemas
   against a representative workload.
