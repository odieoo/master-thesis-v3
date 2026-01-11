# Gemini Migration Analyzer Documentation

## 📋 Overview

The **Gemini Migration Analyzer** is a Python tool designed to assist in migrating relational database schemas to Apache Cassandra (a column-oriented NoSQL database). It combines **AI-powered analysis** using Google's Gemini API with **machine learning techniques** (semantic embeddings and clustering) to suggest optimal table structures for Cassandra.

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GEMINI MIGRATION ANALYZER                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │   INPUT      │     │   PROCESS    │     │   OUTPUT     │                │
│  │              │     │              │     │              │                │
│  │  JSON Schema │────▶│ 1. Gemini AI │────▶│ JSON Tables  │                │
│  │  (columns)   │     │ 2. Embeddings│     │ CQL Schema   │                │
│  │              │     │ 3. Clustering│     │ Visualization│                │
│  │              │     │ 4. PCA + Plot│     │              │                │
│  └──────────────┘     └──────────────┘     └──────────────┘                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Dependencies

```bash
pip install google-genai sentence-transformers scikit-learn matplotlib numpy
```

| Package | Purpose |
|---------|---------|
| `google-genai` | Google Gemini API client (FREE tier available) |
| `sentence-transformers` | Generate semantic embeddings for column names |
| `scikit-learn` | KMeans clustering and PCA dimensionality reduction |
| `matplotlib` | Data visualization (scatter plots) |
| `numpy` | Numerical operations on arrays |

---

## ⚙️ Configuration Variables

Located at the top of the script (lines 29-46):

```python
# Path to your JSON file containing table.column names
JSON_FILE_PATH = "../output/chinook.db_json.json"

# Google Gemini API Key (FREE) - Get from https://aistudio.google.com/app/apikey
GEMINI_API_KEY = "your-api-key-here"

# Output file for visualization
OUTPUT_IMAGE_PATH = "../output/cassandra_migration_visualization.png"

# Number of clusters (set to None for auto-detection based on tables)
N_CLUSTERS = None
```

| Variable | Description | Default |
|----------|-------------|---------|
| `JSON_FILE_PATH` | Path to input JSON file containing `table.column` strings | `"../output/chinook.db_json.json"` |
| `GEMINI_API_KEY` | Your Google Gemini API key (get free at https://aistudio.google.com/app/apikey) | Must be set by user |
| `OUTPUT_IMAGE_PATH` | Path where visualization PNG will be saved | `"../output/cassandra_migration_visualization.png"` |
| `N_CLUSTERS` | Number of clusters for KMeans. Set to `None` for auto-detection | `None` (auto) |

---

## 🔧 Functions Reference

### 1. `load_json_schema(file_path: str) -> list`

**Purpose:** Load the database schema from a JSON file.

**Location:** Lines 52-70

```python
def load_json_schema(file_path: str) -> list:
```

**Parameters:**
- `file_path` (str): Path to the JSON file containing column names

**Returns:**
- `list`: List of strings in format `"table_name.column_name"`

**Example Input JSON:**
```json
[
  "albums.AlbumId",
  "albums.Title",
  "artists.ArtistId",
  "artists.Name"
]
```

**Error Handling:**
- Raises `FileNotFoundError` if file doesn't exist
- Raises `ValueError` if JSON is malformed

**How it works:**
1. Opens the file with UTF-8 encoding
2. Parses JSON content using `json.load()`
3. Prints success message with column count
4. Returns the list of column strings

---

### 2. `call_gemini_api(prompt: str, api_key: str, max_retries: int = 5) -> str`

**Purpose:** Send a prompt to Google Gemini API and get AI-powered migration suggestions.

**Location:** Lines 73-132

```python
def call_gemini_api(prompt: str, api_key: str, max_retries: int = 5) -> str:
```

**Parameters:**
- `prompt` (str): The question/instruction to send to Gemini
- `api_key` (str): Your Gemini API key
- `max_retries` (int): Maximum retry attempts on rate limit (default: 5)

**Returns:**
- `str`: Gemini's response text, or `None` if failed

**Key Features:**

#### a) System Context Injection
```python
full_prompt = f"""You are an expert database architect specializing in 
migrating relational databases to NoSQL column-oriented databases like Cassandra.
Provide practical, detailed migration suggestions.

{prompt}"""
```
This prepends a "system instruction" to guide Gemini's responses toward database migration expertise.

#### b) Exponential Backoff Retry Logic
```python
for attempt in range(max_retries):
    try:
        response = client.models.generate_content(...)
        return response.text
    except ClientError as e:
        if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
            wait_time = (attempt + 1) * 10  # 10s, 20s, 30s, 40s, 50s
            time.sleep(wait_time)
```

**Retry Schedule:**
| Attempt | Wait Time |
|---------|-----------|
| 1 | 10 seconds |
| 2 | 20 seconds |
| 3 | 30 seconds |
| 4 | 40 seconds |
| 5 | 50 seconds |

#### c) API Client Usage (New google.genai Package)
```python
from google import genai
from google.genai.errors import ClientError

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=full_prompt
)
```

> **Note:** This uses the new `google-genai` package, replacing the deprecated `google-generativeai`.

---

### 3. `generate_embeddings(columns: list) -> np.ndarray`

**Purpose:** Convert column names into semantic vector representations (embeddings).

**Location:** Lines 158-172

```python
def generate_embeddings(columns: list) -> np.ndarray:
```

**Parameters:**
- `columns` (list): List of `"table.column"` strings

**Returns:**
- `np.ndarray`: Matrix of shape `(n_columns, 384)` where each row is a 384-dimensional embedding vector

**How it works:**

1. **Load Pre-trained Model:**
   ```python
   model = SentenceTransformer('all-MiniLM-L6-v2')
   ```
   Uses the `all-MiniLM-L6-v2` model which:
   - Is lightweight (~80MB)
   - Produces 384-dimensional vectors
   - Is optimized for semantic similarity tasks

2. **Encode Column Names:**
   ```python
   embeddings = model.encode(columns, show_progress_bar=True)
   ```
   Converts each string like `"customers.Email"` into a vector that captures its semantic meaning.

**Why Embeddings Matter:**
- Columns with similar meanings get similar vectors
- `"customers.Email"` will be close to `"employees.Email"` in vector space
- `"tracks.Milliseconds"` will be close to `"tracks.Bytes"` (both are numeric measurements)

---

### 4. `cluster_columns(embeddings: np.ndarray, n_clusters: int) -> np.ndarray`

**Purpose:** Group similar columns together using KMeans clustering algorithm.

**Location:** Lines 175-190

```python
def cluster_columns(embeddings: np.ndarray, n_clusters: int) -> np.ndarray:
```

**Parameters:**
- `embeddings` (np.ndarray): Embedding matrix from `generate_embeddings()`
- `n_clusters` (int): Number of groups to create

**Returns:**
- `np.ndarray`: Array of cluster labels (0 to n_clusters-1) for each column

**How KMeans Works:**

```
Step 1: Initialize K random centroids
Step 2: Assign each point to nearest centroid
Step 3: Recalculate centroids as mean of assigned points
Step 4: Repeat steps 2-3 until convergence
```

**Configuration:**
```python
kmeans = KMeans(
    n_clusters=n_clusters,  # Number of Cassandra tables to create
    random_state=42,        # Reproducible results
    n_init='auto'           # Automatic initialization runs
)
```

**Example Output:**
```python
# Input: 10 columns, 3 clusters
labels = [0, 0, 1, 1, 1, 2, 2, 0, 1, 2]
# Column 0,1,7 → Cluster 0 (Cassandra Table 1)
# Column 2,3,4,8 → Cluster 1 (Cassandra Table 2)
# Column 5,6,9 → Cluster 2 (Cassandra Table 3)
```

---

### 5. `reduce_dimensions(embeddings: np.ndarray) -> tuple`

**Purpose:** Reduce 384-dimensional embeddings to 2D for visualization using PCA.

**Location:** Lines 193-208

```python
def reduce_dimensions(embeddings: np.ndarray) -> tuple:
```

**Parameters:**
- `embeddings` (np.ndarray): Original 384-dimensional embeddings

**Returns:**
- `tuple`: (2D embeddings array, PCA object)

**How PCA Works:**

```
Original Data (384D)              PCA Transformation              2D Projection
    ┌─────────┐                        ┌─────┐                    ┌───────┐
    │ 384 dims│   ───────────────▶     │ PCA │   ───────────▶     │ 2 dims│
    │ per row │                        │     │                    │ x, y  │
    └─────────┘                        └─────┘                    └───────┘
```

**Principal Component Analysis (PCA):**
1. Finds directions of maximum variance in data
2. Projects data onto these principal components
3. PC1 captures most variance, PC2 captures second-most

**Variance Explained:**
```python
variance_explained = sum(pca.explained_variance_ratio_) * 100
# Example: "45.3% variance explained"
```
This tells us how much information is preserved after dimensionality reduction.

---

### 6. `create_visualization(...)`

**Purpose:** Generate a scatter plot showing clustered columns in 2D space.

**Location:** Lines 211-289

```python
def create_visualization(
    embeddings_2d: np.ndarray,
    labels: np.ndarray,
    columns: list,
    pca: PCA,
    output_path: str,
    cassandra_suggestion: str = None
):
```

**Parameters:**
- `embeddings_2d` (np.ndarray): 2D coordinates from PCA
- `labels` (np.ndarray): Cluster assignments for each column
- `columns` (list): Original column names for labeling
- `pca` (PCA): PCA object for variance info in axis labels
- `output_path` (str): Where to save the PNG
- `cassandra_suggestion` (str, optional): Not currently used in visualization

**Visualization Features:**

#### a) Color Coding by Cluster
```python
colors = plt.cm.tab20(np.linspace(0, 1, n_clusters))
```
Uses matplotlib's `tab20` colormap for up to 20 distinct colors.

#### b) Scatter Plot with Styling
```python
ax.scatter(
    embeddings_2d[mask, 0],      # X coordinates
    embeddings_2d[mask, 1],      # Y coordinates
    c=[colors[cluster_id]],      # Cluster color
    label=f'Cassandra Table {cluster_id + 1}',
    s=150,                       # Point size
    alpha=0.7,                   # Transparency
    edgecolors='white',          # White border
    linewidth=1
)
```

#### c) Point Labels
```python
ax.annotate(
    col,                                      # Column name
    (embeddings_2d[i, 0], embeddings_2d[i, 1]),  # Position
    fontsize=9,
    fontweight='bold'
)
```

#### d) Axis Labels with Variance Info
```python
ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)')
ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)')
```

**Output:** Saves PNG at 150 DPI with tight bounding box.

---

### 7. `generate_cassandra_schema(clusters: dict, chatgpt_suggestion: str = None) -> str`

**Purpose:** Generate Cassandra Query Language (CQL) schema based on cluster groupings.

**Location:** Lines 292-332

```python
def generate_cassandra_schema(clusters: dict, chatgpt_suggestion: str = None) -> str:
```

**Parameters:**
- `clusters` (dict): Dictionary mapping `cluster_id` → `list of columns`
- `chatgpt_suggestion` (str, optional): Not currently used

**Returns:**
- `str`: Complete CQL schema as a string

**Generated Schema Structure:**

```sql
-- Cassandra Schema Migration Suggestion
-- Generated based on semantic clustering analysis

CREATE KEYSPACE IF NOT EXISTS migrated_db
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 3};

USE migrated_db;

-- Cluster 0: Combines albums, artists
CREATE TABLE IF NOT EXISTS albums_artists_data (
    albums_AlbumId text,
    albums_Title text,
    artists_ArtistId text,
    artists_Name text,
    PRIMARY KEY (albums_AlbumId)
);
```

**Table Naming Logic:**
```python
tables_in_cluster = set([col.split('.')[0] for col in columns])
table_name = '_'.join(sorted(tables_in_cluster)) + "_data"
# Example: albums + artists → "albums_artists_data"
```

**Column Naming:**
```python
col_name = col.replace('.', '_')
# "albums.Title" → "albums_Title"
```

---

### 8. `main()`

**Purpose:** Orchestrate the entire migration analysis pipeline.

**Location:** Lines 339-539

**Execution Flow:**

```
┌─────────────────────────────────────────────────────────────────┐
│                         main() PIPELINE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [1/6] Load JSON Schema                                          │
│         ↓                                                        │
│  [2/6] Consult Gemini API (2 prompts)                           │
│         ├── Prompt 1: Get structured JSON table suggestions     │
│         └── Prompt 2: Get detailed migration strategy           │
│         ↓                                                        │
│  [3/6] Generate Semantic Embeddings                              │
│         ↓                                                        │
│  [4/6] Cluster Columns with KMeans                               │
│         ↓                                                        │
│  [5/6] Reduce to 2D with PCA                                     │
│         ↓                                                        │
│  [6/6] Create Visualization & Generate CQL                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Step 2 Details: Gemini API Calls

**Prompt 1 - Structured JSON Request:**
```python
json_prompt = f"""
I have a relational database with the following tables and columns:
{json.dumps(columns, indent=2)}

Analyze this schema and suggest how to migrate to Cassandra.

IMPORTANT: Return ONLY a valid JSON object with suggested Cassandra table names as keys,
and arrays of column names as values.
"""
```

**Response Cleaning (handles markdown code blocks):**
```python
if clean_response.startswith("```"):
    clean_response = clean_response.split("```")[1]
    if clean_response.startswith("json"):
        clean_response = clean_response[4:]
```

**Prompt 2 - Detailed Strategy:**
```python
detail_prompt = f"""
Please provide detailed migration suggestions:
1. How to best migrate this to Cassandra
2. Suggested partition keys and clustering columns
3. Any denormalization strategies needed
4. Query patterns this structure would optimize for
5. Specific CQL examples
"""
```

**Rate Limit Handling:**
```python
print("\n   ⏳ Waiting 10 seconds to avoid rate limits...")
time.sleep(10)
```

---

## 📤 Output Files

| File | Description |
|------|-------------|
| `gemini_suggested_tables.json` | AI-suggested Cassandra table structure |
| `gemini_migration_suggestions.txt` | Detailed migration strategy from Gemini |
| `embedding_suggested_tables.json` | Embedding-based clustering results |
| `cassandra_schema.cql` | Ready-to-use CQL schema |
| `cassandra_migration_visualization.png` | Visual cluster diagram |

---

## 🚀 Usage

### 1. Set Up API Key
```python
GEMINI_API_KEY = "your-api-key-here"
```
Get free key at: https://aistudio.google.com/app/apikey

### 2. Prepare Input JSON
Create a JSON file with your schema:
```json
[
  "table1.column1",
  "table1.column2",
  "table2.column1"
]
```

### 3. Run Script
```bash
cd master-v3/utils
python gemini_migration_analyzer.py
```

---

## 🔬 Algorithm Deep Dive

### Semantic Similarity for Database Migration

The core insight is that **column names with similar meanings should be stored together in Cassandra** for optimal query performance.

**Example:**
```
customers.Email      ─┐
customers.Phone      ─┼──▶ Customer Contact Info Table
customers.Address    ─┘

tracks.Milliseconds  ─┐
tracks.Bytes         ─┼──▶ Track Metrics Table
tracks.UnitPrice     ─┘
```

### Why This Works

1. **Semantic Embeddings** capture the meaning of words
2. **Clustering** groups similar meanings together
3. **Cassandra** performs best when related data is co-located

### Denormalization Strategy

Cassandra requires **denormalization** (duplicating data) for performance. This tool helps identify which columns naturally belong together based on their semantic relationships, rather than their original table structure.

---

## ⚠️ Limitations

1. **Primary Key Selection:** Uses first column as partition key (may not be optimal)
2. **Data Types:** All columns default to `text` type
3. **Clustering Columns:** Not automatically detected
4. **Query Patterns:** Relies on Gemini's analysis, should be validated

---

## 🔄 Future Improvements

- [ ] Automatic primary key detection based on column names
- [ ] Data type inference from column names
- [ ] Multiple clustering algorithm options (DBSCAN, Hierarchical)
- [ ] Interactive cluster adjustment
- [ ] Export to DataStax Astra format

---

## 📚 References

- [Google Gemini API](https://ai.google.dev/docs)
- [Sentence Transformers](https://www.sbert.net/)
- [Apache Cassandra Data Modeling](https://cassandra.apache.org/doc/latest/cassandra/data_modeling/)
- [Scikit-learn KMeans](https://scikit-learn.org/stable/modules/clustering.html#k-means)
- [PCA Explained](https://scikit-learn.org/stable/modules/decomposition.html#pca)


---
Excellent question! This is a **critical challenge** in Cassandra design.

---

## ⚠️ Is Denormalization an Issue?

**Yes and No** - It's a **trade-off**, not a bug:

| Aspect | Issue? | Explanation |
|--------|--------|-------------|
| **Storage** | ⚠️ Minor | Disk is cheap, Cassandra handles it well |
| **Write Performance** | ⚠️ Yes | Must update multiple tables |
| **Read Performance** | ✅ No | This is WHY we denormalize - fast reads |
| **Data Consistency** | 🔴 **YES** | The main challenge! |

---

## 🔴 The Real Problem: Data Consistency

If `artist_name = "Beatles"` exists in 6 tables, and you need to change it to `"The Beatles"`:

```
tracks_by_id.artist_name         = "Beatles"  → Must update
tracks_by_album.artist_name      = "Beatles"  → Must update
tracks_by_genre.artist_name      = "Beatles"  → Must update
albums_by_id.artist_name         = "Beatles"  → Must update
invoice_items.artist_name        = "Beatles"  → Must update
playlist_tracks.artist_name      = "Beatles"  → Must update
```

**What if one update fails?** → Inconsistent data! 😱

---

## 🛠️ How to Handle Updates in Multiple Tables

### Strategy 1: **Batch Updates** (Atomic)

```cql
BEGIN BATCH
  UPDATE tracks_by_id SET artist_name = 'The Beatles' WHERE track_id = 1;
  UPDATE tracks_by_album SET artist_name = 'The Beatles' WHERE album_id = 1 AND track_id = 1;
  UPDATE albums_by_id SET artist_name = 'The Beatles' WHERE album_id = 1;
APPLY BATCH;
```

✅ Atomic - all succeed or all fail  
⚠️ Limited to same partition (performance)

---

### Strategy 2: **Materialized Views** (Automatic Sync)

```cql
-- Base table
CREATE TABLE tracks (
    track_id UUID PRIMARY KEY,
    track_name TEXT,
    artist_name TEXT,
    album_id UUID
);

-- Auto-synced view
CREATE MATERIALIZED VIEW tracks_by_album AS
    SELECT * FROM tracks
    WHERE album_id IS NOT NULL
    PRIMARY KEY (album_id, track_id);
```

✅ Cassandra auto-updates the view  
⚠️ Performance overhead, limited flexibility

---

### Strategy 3: **Application-Level Sync** (Most Common)

```python
def update_artist_name(artist_id, new_name):
    # Update all tables in application code
    session.execute("UPDATE tracks_by_id SET artist_name = ? WHERE ...", [new_name])
    session.execute("UPDATE tracks_by_album SET artist_name = ? WHERE ...", [new_name])
    session.execute("UPDATE albums_by_id SET artist_name = ? WHERE ...", [new_name])
    # ... etc
```

✅ Full control  
⚠️ Must handle failures manually

---

### Strategy 4: **Event-Driven / CDC** (Enterprise)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   UPDATE    │────▶│   Kafka /   │────▶│   Sync      │
│   Request   │     │   CDC       │     │   Service   │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
              ┌──────────┐            ┌──────────┐             ┌──────────┐
              │ Table 1  │            │ Table 2  │             │ Table 3  │
              └──────────┘            └──────────┘             └──────────┘
```

✅ Scalable, eventually consistent  
⚠️ Complex architecture

---

## 📊 When to Use Each Strategy

| Scenario | Best Strategy |
|----------|---------------|
| Small updates, same partition | **Batch** |
| Simple queries, auto-sync OK | **Materialized Views** |
| Complex logic, custom control | **Application-Level** |
| High scale, eventual consistency OK | **Event-Driven (Kafka)** |

---

## 💡 Best Practice: Minimize Denormalization

Gemini's 122 columns might be **over-denormalized**. Consider:

```
Instead of:                          Better approach:
─────────────────────────────        ─────────────────────────────
tracks_by_id.artist_name             tracks_by_id.artist_id
tracks_by_album.artist_name    →     (Look up artist_name from
tracks_by_genre.artist_name           artists table when needed)
```

**Trade-off:** Extra read vs. easier updates

---

## 🎯 Summary

| Question | Answer |
|----------|--------|
| Is denormalization an issue? | Yes, for **writes/updates** |
| Is it still used? | Yes, because **reads are faster** |
| How to handle updates? | Batches, Materialized Views, or App-level sync |
| Best practice? | Denormalize **only what you query frequently** |