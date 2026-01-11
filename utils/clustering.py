# Clustering based on embedding similarity
from db_service import get_table_columns
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import numpy as np

# print("=" * 60)
# print(" Embedding-based Column Clustering")
# print("=" * 60)

# Step 1: Get columns and generate embeddings
# print("\n[1] Loading columns from database...")
table_columns = get_table_columns()
print(f"    Found {len(table_columns)} columns")
print("table_columns", table_columns)
# print("\n[2] Generating embeddings...")
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(table_columns, show_progress_bar=True)
# print(f"    Generated embeddings with shape: {embeddings.shape}")

# Step 2: Calculate similarity matrix
# print("\n[3] Calculating similarity matrix...")
similarity_matrix = cosine_similarity(embeddings)
# print(f"    Similarity matrix shape: {similarity_matrix.shape}")

# Show sample similarities
# print("\n[4] Sample Similarities (first 5 pairs):")
# print("-" * 60)
for i in range(min(5, len(table_columns))):
    for j in range(i + 1, min(5, len(table_columns))):
        sim = similarity_matrix[i][j]
        print(f"    {table_columns[i]:30} <-> {table_columns[j]:30}")
        print(f"    Similarity: {sim:.4f}")
        print()

# Step 3: Clustering using Agglomerative Clustering
# print("\n[5] Clustering columns...")
# Convert similarity to distance (1 - similarity)
distance_matrix = 1 - similarity_matrix

# Determine optimal number of clusters (based on number of tables)
unique_tables = set([col.split('.')[0] for col in table_columns])
n_clusters = len(unique_tables)
# print(f"    Number of unique tables: {n_clusters}")
# print(f"    Using {n_clusters} clusters")

# Apply Agglomerative Clustering
clustering = AgglomerativeClustering(
    n_clusters=n_clusters,
    metric='precomputed',
    linkage='average'
)
labels = clustering.fit_predict(distance_matrix)

# Step 4: Display clustering results
# print("\n" + "=" * 60)
# print(" CLUSTERING RESULTS")
# print("=" * 60)

# Group columns by cluster
from collections import defaultdict
clusters = defaultdict(list)
for i, label in enumerate(labels):
    clusters[label].append(table_columns[i])

# Print each cluster
for cluster_id in sorted(clusters.keys()):
    columns = clusters[cluster_id]
    print(f"\n Cluster {cluster_id} ({len(columns)} columns):")
    print("-" * 40)
    for col in columns:
        print(f"    - {col}")

# Step 5: Show high similarity pairs across different tables
print("\n" + "=" * 60)
print(" HIGH SIMILARITY PAIRS (cross-table)")
print("=" * 60)

threshold = 0.7  # Similarity threshold
high_sim_pairs = []

for i in range(len(table_columns)):
    for j in range(i + 1, len(table_columns)):
        table_i = table_columns[i].split('.')[0]
        table_j = table_columns[j].split('.')[0]
        
        # Only show cross-table similarities
        if table_i != table_j:
            sim = similarity_matrix[i][j]
            if sim >= threshold:
                high_sim_pairs.append((table_columns[i], table_columns[j], sim))

# Sort by similarity descending
high_sim_pairs.sort(key=lambda x: x[2], reverse=True)

print(f"\nPairs with similarity >= {threshold}:")
print("-" * 60)
if high_sim_pairs:
    for col1, col2, sim in high_sim_pairs[:20]:  # Show top 20
        print(f"  {sim:.4f}  |  {col1:30} <-> {col2}")
else:
    print("  No pairs found with similarity >= threshold")

print("\n" + "=" * 60)
print(f" Total columns: {len(table_columns)}")
print(f" Total clusters: {n_clusters}")
print(f" High similarity pairs: {len(high_sim_pairs)}")
print("=" * 60)

# ============================================================
# VISUALIZATION
# ============================================================
print("\n[6] Generating visualizations...")

# Create SINGLE full-width figure
fig, ax2 = plt.subplots(figsize=(24, 14))

# Remove all margins to use full width
fig.subplots_adjust(left=0.05, right=0.95, top=0.92, bottom=0.08)
# Reduce 384D embeddings to 2D using PCA
pca = PCA(n_components=2)
embeddings_2d = pca.fit_transform(embeddings)

# Create color map for clusters
colors = plt.cm.tab10(np.linspace(0, 1, n_clusters))

# Plot each cluster with different color
for cluster_id in range(n_clusters):
    mask = labels == cluster_id
    ax2.scatter(
        embeddings_2d[mask, 0], 
        embeddings_2d[mask, 1],
        c=[colors[cluster_id]],
        label=f'Cluster {cluster_id}',
        s=100,
        alpha=0.7,
        edgecolors='white',
        linewidth=0.5
    )

# Add labels for each point
for i, col in enumerate(table_columns):
    # Shorten label to just column name (remove table prefix)
    # print("col", col)
    # short_label = col.split('.')[1][:10]  # First 10 chars of column name
    # print("short_label", short_label)
    ax2.annotate(
        col, 
        (embeddings_2d[i, 0], embeddings_2d[i, 1]),
        fontsize=12,
        alpha=0.7,
        ha='center',
        va='bottom'
    )

ax2.set_title('Cluster Visualization (PCA 2D)', fontsize=14, fontweight='bold')
ax2.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)')
ax2.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)')
ax2.legend(loc='lower right', fontsize=10, markerscale=1.5)
ax2.grid(True, alpha=0.3)

# No tight_layout - we want full control over margins

# Save the figure
output_path = '../output/clustering_visualization.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"    Saved visualization to: {output_path}")

# Show the plot
plt.show()

print("\n Done!")


