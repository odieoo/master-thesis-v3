"""
Gemini-powered Database Migration Analyzer
============================================
This script uses Google's Gemini API (FREE) to analyze relational database schema
and suggest optimal Cassandra table structures for migration.

Requirements:
    pip install google-genai sentence-transformers scikit-learn matplotlib numpy

Usage:
    1. Get free API key from: https://aistudio.google.com/app/apikey
    2. Set your Gemini API key in the GEMINI_API_KEY variable below
    3. Update JSON_FILE_PATH to point to your schema JSON file
    4. Run: python chatgpt_migration_analyzer.py

Author: Migration Analysis Tool
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from collections import defaultdict

# ============================================================
# CONFIGURATION - Modify these variables as needed
# ============================================================

# Path to your JSON file containing table.column names
JSON_FILE_PATH = "../output/chinook.db_json.json"

# Google Gemini API Key (FREE) - Get from https://aistudio.google.com/app/apikey
GEMINI_API_KEY = "AIzaSyAXprsvJy44V14AsnqoGRQOtMEaEdEZAdU"  # Replace with your Gemini API key

# [DEPRECATED] OpenAI API Key - Commented out, using Gemini instead
# OPENAI_API_KEY = "your-openai-api-key-here"

# Output file for visualization
OUTPUT_IMAGE_PATH = "../output/cassandra_migration_visualization.png"

# Number of clusters (set to None for auto-detection based on tables)
N_CLUSTERS = None

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def load_json_schema(file_path: str) -> list:
    """
    Load table columns from JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of table.column strings
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data)} columns from {file_path}")
        return data
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ JSON file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"❌ Invalid JSON file: {e}")


def call_gemini_api(prompt: str, api_key: str, max_retries: int = 5) -> str:
    """
    Call Google Gemini API (FREE) to get migration suggestions.
    Uses the new google.genai package with automatic retry logic for rate limits.
    
    Args:
        prompt: The prompt to send to Gemini
        api_key: Google Gemini API key
        max_retries: Maximum number of retries on rate limit
        
    Returns:
        Gemini response text
    """
    import time
    
    try:
        from google import genai
        from google.genai.errors import ClientError
    except ImportError:
        print("⚠️ Google GenAI library not installed.")
        print("   Install with: pip install google-genai")
        return None
    
    # Create the client
    client = genai.Client(api_key=api_key)
    
    # Add system context to prompt
    full_prompt = f"""You are an expert database architect specializing in 
migrating relational databases to NoSQL column-oriented databases like Cassandra.
Provide practical, detailed migration suggestions.

{prompt}"""
    
    # Retry logic with exponential backoff
    for attempt in range(max_retries):
        try:
            # Generate response using new API
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_prompt
            )
            return response.text
            
        except ClientError as e:
            error_str = str(e)
            
            # Check if it's a rate limit error (RESOURCE_EXHAUSTED)
            if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                wait_time = (attempt + 1) * 10  # 10s, 20s, 30s, 40s, 50s
                print(f"⚠️ Rate limit hit. Waiting {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"⚠️ Gemini API Error: {e}")
                return None
        except Exception as e:
            print(f"⚠️ Unexpected Error: {e}")
            return None
    
    print("❌ Max retries exceeded. Please wait a minute and try again.")
    return None


# [DEPRECATED] ChatGPT API function - Commented out, using Gemini instead
# def call_chatgpt_api(prompt: str, api_key: str) -> str:
#     """
#     Call OpenAI ChatGPT API to get migration suggestions.
#     """
#     try:
#         import openai
#         client = openai.OpenAI(api_key=api_key)
#         response = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "system", "content": "You are an expert database architect..."},
#                 {"role": "user", "content": prompt}
#             ],
#             max_tokens=2000,
#             temperature=0.7
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         print(f"⚠️ ChatGPT API Error: {e}")
#         return None


def generate_embeddings(columns: list) -> np.ndarray:
    """
    Generate semantic embeddings for column names.
    
    Args:
        columns: List of table.column strings
        
    Returns:
        NumPy array of embeddings
    """
    print("🔄 Generating embeddings...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(columns, show_progress_bar=True)
    print(f"✅ Generated embeddings with shape: {embeddings.shape}")
    return embeddings


def cluster_columns(embeddings: np.ndarray, n_clusters: int) -> np.ndarray:
    """
    Cluster columns based on their embeddings.
    
    Args:
        embeddings: NumPy array of embeddings
        n_clusters: Number of clusters
        
    Returns:
        Array of cluster labels
    """
    print(f"🔄 Clustering into {n_clusters} groups...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
    labels = kmeans.fit_predict(embeddings)
    print("✅ Clustering complete")
    return labels


def reduce_dimensions(embeddings: np.ndarray) -> tuple:
    """
    Reduce embeddings to 2D using PCA for visualization.
    
    Args:
        embeddings: NumPy array of embeddings
        
    Returns:
        Tuple of (2D embeddings, PCA object)
    """
    print("🔄 Reducing dimensions with PCA...")
    pca = PCA(n_components=2)
    embeddings_2d = pca.fit_transform(embeddings)
    variance_explained = sum(pca.explained_variance_ratio_) * 100
    print(f"✅ PCA complete - {variance_explained:.1f}% variance explained")
    return embeddings_2d, pca


def create_visualization(
    embeddings_2d: np.ndarray,
    labels: np.ndarray,
    columns: list,
    pca: PCA,
    output_path: str,
    cassandra_suggestion: str = None
):
    """
    Create and save the cluster visualization.
    
    Args:
        embeddings_2d: 2D reduced embeddings
        labels: Cluster labels
        columns: Original column names
        pca: PCA object for variance info
        output_path: Path to save the PNG
        cassandra_suggestion: Optional ChatGPT suggestion text
    """
    print("🔄 Creating visualization...")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(20, 14))
    fig.subplots_adjust(left=0.08, right=0.92, top=0.90, bottom=0.10)
    
    # Get unique clusters
    n_clusters = len(set(labels))
    colors = plt.cm.tab20(np.linspace(0, 1, n_clusters))
    
    # Plot each cluster
    for cluster_id in range(n_clusters):
        mask = labels == cluster_id
        ax.scatter(
            embeddings_2d[mask, 0],
            embeddings_2d[mask, 1],
            c=[colors[cluster_id]],
            label=f'Cassandra Table {cluster_id + 1}',
            s=150,
            alpha=0.7,
            edgecolors='white',
            linewidth=1
        )
    
    # Add labels for each point
    for i, col in enumerate(columns):
        ax.annotate(
            col,
            (embeddings_2d[i, 0], embeddings_2d[i, 1]),
            fontsize=9,
            alpha=0.8,
            ha='center',
            va='bottom',
            fontweight='bold'
        )
    
    # Styling
    ax.set_title(
        'Relational to Cassandra Migration: Column Clustering Analysis',
        fontsize=16,
        fontweight='bold',
        pad=20
    )
    ax.set_xlabel(
        f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)',
        fontsize=12
    )
    ax.set_ylabel(
        f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)',
        fontsize=12
    )
    ax.legend(loc='lower right', fontsize=10, markerscale=1.2)
    ax.grid(True, alpha=0.3)
    
    # Save figure
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ Visualization saved to: {output_path}")
    
    # Show plot
    plt.show()


def generate_cassandra_schema(clusters: dict, chatgpt_suggestion: str = None) -> str:
    """
    Generate Cassandra CQL schema based on clusters.
    
    Args:
        clusters: Dictionary of cluster_id -> list of columns
        chatgpt_suggestion: Optional ChatGPT suggestion
        
    Returns:
        CQL schema string
    """
    cql_schema = []
    cql_schema.append("-- Cassandra Schema Migration Suggestion")
    cql_schema.append("-- Generated based on semantic clustering analysis")
    cql_schema.append("")
    cql_schema.append("CREATE KEYSPACE IF NOT EXISTS migrated_db")
    cql_schema.append("WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 3};")
    cql_schema.append("")
    cql_schema.append("USE migrated_db;")
    cql_schema.append("")
    
    for cluster_id, columns in sorted(clusters.items()):
        # Extract table names from columns
        tables_in_cluster = set([col.split('.')[0] for col in columns])
        table_name = '_'.join(sorted(tables_in_cluster)) + "_data"
        
        cql_schema.append(f"-- Cluster {cluster_id}: Combines {', '.join(tables_in_cluster)}")
        cql_schema.append(f"CREATE TABLE IF NOT EXISTS {table_name} (")
        
        # Add columns
        for i, col in enumerate(columns):
            col_name = col.replace('.', '_')
            cql_schema.append(f"    {col_name} text,")
        
        # Add primary key (first column as partition key)
        first_col = columns[0].replace('.', '_')
        cql_schema.append(f"    PRIMARY KEY ({first_col})")
        cql_schema.append(");")
        cql_schema.append("")
    
    return '\n'.join(cql_schema)


# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    """Main execution function."""
    
    print("=" * 70)
    print(" Gemini-Powered Database Migration Analyzer (FREE)")
    print(" Relational DB → Cassandra Column-Oriented DB")
    print("=" * 70)
    
    # Step 1: Load JSON schema
    print("\n[1/6] Loading schema...")
    columns = load_json_schema(JSON_FILE_PATH)
    
    # Step 2: Call Gemini API for migration suggestions
    print("\n[2/6] Consulting Google Gemini for migration strategy...")
    
    gemini_response = None
    if GEMINI_API_KEY and GEMINI_API_KEY != "your-gemini-api-key-here":
        # First prompt: Get structured JSON suggestion
        json_prompt = f"""
        I have a relational database with the following tables and columns:
        
        {json.dumps(columns, indent=2)}
        
        Analyze this schema and suggest how to migrate to Cassandra (column-oriented database).
        
        IMPORTANT: Return ONLY a valid JSON object with suggested Cassandra table names as keys,
        and arrays of column names as values. Format:
        
        {{
            "cassandra_table_name_1": ["column1", "column2", "column3"],
            "cassandra_table_name_2": ["column4", "column5"]
        }}
        
        Group columns that are frequently queried together.
        Consider denormalization for query optimization.
        Return ONLY the JSON, no other text.
        """
        
        print("   Requesting structured table suggestions...")
        json_response = call_gemini_api(json_prompt, GEMINI_API_KEY)
        
        # Try to parse the JSON response
        suggested_tables = None
        if json_response:
            try:
                # Clean the response - remove markdown code blocks if present
                clean_response = json_response.strip()
                if clean_response.startswith("```"):
                    clean_response = clean_response.split("```")[1]
                    if clean_response.startswith("json"):
                        clean_response = clean_response[4:]
                clean_response = clean_response.strip()
                
                suggested_tables = json.loads(clean_response)
                
                # Save the suggested tables as JSON
                suggested_tables_path = "../output/gemini_suggested_tables.json"
                with open(suggested_tables_path, 'w', encoding='utf-8') as f:
                    json.dump(suggested_tables, f, indent=2)
                print(f"✅ Suggested tables saved to: {suggested_tables_path}")
                
                # Print the suggested structure
                print("\n" + "=" * 50)
                print(" Gemini Suggested Cassandra Tables:")
                print("=" * 50)
                for table_name, table_columns in suggested_tables.items():
                    print(f"\n📦 {table_name}:")
                    for col in table_columns:
                        print(f"   - {col}")
                print("=" * 50)
                
            except json.JSONDecodeError as e:
                print(f"⚠️ Could not parse JSON response: {e}")
                print("   Raw response saved to text file")
        
        # Wait between API calls to avoid rate limiting
        import time
        print("\n   ⏳ Waiting 10 seconds to avoid rate limits...")
        time.sleep(10)
        
        # Second prompt: Get detailed explanation
        detail_prompt = f"""
        I have a relational database with the following tables and columns:
        
        {json.dumps(columns, indent=2)}
        
        Please provide detailed migration suggestions:
        1. How to best migrate this to Cassandra (column-oriented database)
        2. Suggested partition keys and clustering columns
        3. Any denormalization strategies needed
        4. Query patterns this structure would optimize for
        5. Specific CQL (Cassandra Query Language) examples
        """
        
        print("\n   Requesting detailed migration strategy...")
        gemini_response = call_gemini_api(detail_prompt, GEMINI_API_KEY)
        
        if gemini_response:
            print("\n" + "=" * 50)
            print(" Gemini Migration Strategy:")
            print("=" * 50)
            print(gemini_response)
            print("=" * 50 + "\n")
            
            # Save Gemini response
            response_path = "../output/gemini_migration_suggestions.txt"
            with open(response_path, 'w', encoding='utf-8') as f:
                f.write(gemini_response)
            print(f"✅ Gemini suggestions saved to: {response_path}")
    else:
        print("⚠️ Skipping Gemini API (no API key provided)")
        print("   Get FREE API key from: https://aistudio.google.com/app/apikey")
        print("   Set GEMINI_API_KEY to get AI-powered suggestions")
    
    # Step 3: Generate embeddings
    print("\n[3/6] Generating semantic embeddings...")
    embeddings = generate_embeddings(columns)
    
    # Step 4: Determine number of clusters
    if N_CLUSTERS is None:
        # Auto-detect based on unique tables
        unique_tables = set([col.split('.')[0] for col in columns])
        n_clusters = len(unique_tables)
        print(f"   Auto-detected {n_clusters} tables → using {n_clusters} clusters")
    else:
        n_clusters = N_CLUSTERS
    
    # Step 5: Cluster columns
    print("\n[4/6] Clustering columns for Cassandra tables...")
    labels = cluster_columns(embeddings, n_clusters)
    
    # Group columns by cluster
    clusters = defaultdict(list)
    for i, label in enumerate(labels):
        clusters[label].append(columns[i])
    
    # Print cluster results
    print("\n" + "=" * 50)
    print(" Embedding-based Cassandra Table Groupings:")
    print("=" * 50)
    
    # Create JSON structure for embedding-based clusters
    embedding_suggested_tables = {}
    
    for cluster_id, cols in sorted(clusters.items()):
        tables = set([c.split('.')[0] for c in cols])
        table_name = '_'.join(sorted(tables)) + "_data"
        embedding_suggested_tables[table_name] = cols
        
        print(f"\n📦 {table_name} (from: {', '.join(tables)}):")
        for col in cols:
            print(f"   - {col}")
    
    # Save embedding-based clusters as JSON
    embedding_tables_path = "../output/embedding_suggested_tables.json"
    with open(embedding_tables_path, 'w', encoding='utf-8') as f:
        json.dump(embedding_suggested_tables, f, indent=2)
    print(f"\n✅ Embedding-based tables saved to: {embedding_tables_path}")
    
    # Step 6: Reduce to 2D and visualize
    print("\n[5/6] Reducing dimensions for visualization...")
    embeddings_2d, pca = reduce_dimensions(embeddings)
    
    print("\n[6/6] Creating visualization...")
    create_visualization(
        embeddings_2d,
        labels,
        columns,
        pca,
        OUTPUT_IMAGE_PATH,
        gemini_response
    )
    
    # Generate and save CQL schema
    print("\n" + "=" * 50)
    print(" Generated Cassandra CQL Schema:")
    print("=" * 50)
    cql_schema = generate_cassandra_schema(clusters, gemini_response)
    print(cql_schema)
    
    # Save CQL schema
    cql_path = "../output/cassandra_schema.cql"
    with open(cql_path, 'w', encoding='utf-8') as f:
        f.write(cql_schema)
    print(f"\n✅ CQL schema saved to: {cql_path}")
    
    print("\n" + "=" * 70)
    print(" Migration Analysis Complete!")
    print("=" * 70)
    print(f"\nOutput files:")
    print(f"  📊 Visualization:           {OUTPUT_IMAGE_PATH}")
    print(f"  📝 CQL Schema:              {cql_path}")
    print(f"  📦 Embedding Tables (JSON): ../output/embedding_suggested_tables.json")
    if gemini_response:
        print(f"  🤖 Gemini Tables (JSON):    ../output/gemini_suggested_tables.json")
        print(f"  📄 Gemini Strategy:         ../output/gemini_migration_suggestions.txt")
    print("\n")


if __name__ == "__main__":
    main()

