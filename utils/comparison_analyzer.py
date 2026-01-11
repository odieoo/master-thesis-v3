"""
Migration Approach Comparison Analyzer
======================================
Compares Gemini AI suggestions with Embedding-based clustering approach
and creates a side-by-side scatter plot visualization showing both approaches.

Usage:
    python comparison_analyzer.py

Author: Migration Analysis Tool
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from collections import defaultdict
from sklearn.decomposition import PCA
from sentence_transformers import SentenceTransformer


def compare_migration_approaches(
    gemini_json_path: str,
    embedding_json_path: str,
    original_columns_path: str = "../output/chinook.db_json.json",
    output_path: str = "../output/comparison_visualization.png"
):
    """
    Compare Gemini AI suggestions with Embedding-based clustering approach.
    Creates a side-by-side scatter plot visualization showing both approaches.
    
    Args:
        gemini_json_path: Path to Gemini suggested tables JSON
        embedding_json_path: Path to embedding-based suggested tables JSON
        original_columns_path: Path to original columns JSON
        output_path: Path to save the comparison visualization
        
    Returns:
        dict: Comparison metrics and analysis results
    """
    
    # =========================================
    # 1. LOAD ALL JSON FILES
    # =========================================
    print("\n" + "=" * 60)
    print(" MIGRATION APPROACH COMPARISON")
    print("=" * 60)
    
    with open(gemini_json_path, 'r', encoding='utf-8') as f:
        gemini_tables = json.load(f)
    print(f"[OK] Loaded Gemini suggestions: {len(gemini_tables)} tables")
    
    with open(embedding_json_path, 'r', encoding='utf-8') as f:
        embedding_tables = json.load(f)
    print(f"[OK] Loaded Embedding clusters: {len(embedding_tables)} tables")
    
    with open(original_columns_path, 'r', encoding='utf-8') as f:
        original_columns = json.load(f)
    print(f"[OK] Loaded original columns: {len(original_columns)} columns")
    
    # =========================================
    # 2. GENERATE EMBEDDINGS FOR ORIGINAL COLUMNS
    # =========================================
    print("\n[EMBED] Generating embeddings for visualization...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(original_columns, show_progress_bar=True)
    print(f"[OK] Generated embeddings with shape: {embeddings.shape}")
    
    # Reduce to 2D using PCA
    print("[PCA] Reducing dimensions to 2D...")
    pca = PCA(n_components=2)
    embeddings_2d = pca.fit_transform(embeddings)
    print(f"[OK] PCA complete - {sum(pca.explained_variance_ratio_)*100:.1f}% variance explained")
    
    # =========================================
    # 3. MAP COLUMNS TO TABLES (EMBEDDING)
    # =========================================
    # For embedding tables, columns are in "table.Column" format
    embedding_column_to_table = {}
    for table_name, columns in embedding_tables.items():
        for col in columns:
            embedding_column_to_table[col] = table_name
    
    # Create labels for embedding clustering
    embedding_table_names = list(embedding_tables.keys())
    embedding_labels = []
    for col in original_columns:
        if col in embedding_column_to_table:
            table_name = embedding_column_to_table[col]
            embedding_labels.append(embedding_table_names.index(table_name))
        else:
            embedding_labels.append(-1)  # Unknown
    embedding_labels = np.array(embedding_labels)
    
    # =========================================
    # 4. NORMALIZE COLUMN NAMES FOR COMPARISON
    # =========================================
    def normalize_column(col):
        """Normalize column name for comparison (remove table prefix, lowercase)."""
        if '.' in col:
            return col.split('.')[-1].lower().replace('_', '')
        return col.lower().replace('_', '')
    
    # Create normalized versions
    gemini_normalized = {}
    for table, columns in gemini_tables.items():
        gemini_normalized[table] = set([normalize_column(c) for c in columns])
    
    embedding_normalized = {}
    for table, columns in embedding_tables.items():
        embedding_normalized[table] = set([normalize_column(c) for c in columns])
    
    # =========================================
    # 5. CALCULATE SIMILARITY METRICS
    # =========================================
    print("\n" + "-" * 40)
    print(" SIMILARITY ANALYSIS")
    print("-" * 40)
    
    # Find best matches between Gemini and Embedding tables
    matches = []
    
    for g_table, g_cols in gemini_normalized.items():
        best_match = None
        best_score = 0
        
        for e_table, e_cols in embedding_normalized.items():
            # Jaccard similarity
            intersection = len(g_cols & e_cols)
            union = len(g_cols | e_cols)
            similarity = intersection / union if union > 0 else 0
            
            if similarity > best_score:
                best_score = similarity
                best_match = e_table
        
        matches.append({
            'gemini_table': g_table,
            'embedding_table': best_match,
            'similarity': best_score,
            'gemini_cols': len(gemini_tables[g_table]),
            'common_cols': len(g_cols & embedding_normalized.get(best_match, set()))
        })
    
    # Sort by similarity
    matches.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Print comparison table
    print(f"\n{'Gemini Table':<30} {'Best Match (Embedding)':<35} {'Similarity':<12} {'Common Cols'}")
    print("-" * 90)
    for m in matches:
        sim_bar = "#" * int(m['similarity'] * 10)
        print(f"{m['gemini_table']:<30} {m['embedding_table'] or 'None':<35} {m['similarity']:.2f} {sim_bar:<10} {m['common_cols']}")
    
    # Calculate overall metrics
    avg_similarity = np.mean([m['similarity'] for m in matches])
    high_matches = sum(1 for m in matches if m['similarity'] > 0.5)
    perfect_matches = sum(1 for m in matches if m['similarity'] > 0.9)
    
    print(f"\n[STAT] Average Similarity: {avg_similarity:.2%}")
    print(f"[STAT] High Matches (>50%): {high_matches}/{len(matches)}")
    
    # =========================================
    # 6. CREATE VISUALIZATION - TWO SCATTER PLOTS SIDE BY SIDE
    # =========================================
    print("\n" + "-" * 40)
    print(" CREATING VISUALIZATION")
    print("-" * 40)
    
    # Create figure with 2 subplots side by side
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(28, 14))
    fig.subplots_adjust(left=0.05, right=0.95, top=0.90, bottom=0.08, wspace=0.15)
    
    # =========================================
    # LEFT PLOT: Embedding Clustering Approach
    # =========================================
    n_embedding_clusters = len(embedding_tables)
    colors_embedding = plt.cm.tab20(np.linspace(0, 1, n_embedding_clusters))
    
    # Plot each embedding cluster with different color
    for cluster_id in range(n_embedding_clusters):
        mask = embedding_labels == cluster_id
        if np.sum(mask) > 0:
            ax1.scatter(
                embeddings_2d[mask, 0],
                embeddings_2d[mask, 1],
                c=[colors_embedding[cluster_id]],
                label=f'{embedding_table_names[cluster_id][:20]}',
                s=150,
                alpha=0.7,
                edgecolors='white',
                linewidth=1
            )
    
    # Add labels for each point (embedding)
    for i, col in enumerate(original_columns):
        ax1.annotate(
            col,
            (embeddings_2d[i, 0], embeddings_2d[i, 1]),
            fontsize=8,
            alpha=0.7,
            ha='center',
            va='bottom'
        )
    
    ax1.set_title('Embedding Clustering Approach\n(Semantic Similarity Based)', fontsize=7, fontweight='bold')
    ax1.title.set_position((0.3, 1.0))
    ax1.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)', fontsize=7)
    ax1.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)', fontsize=7)
    ax1.legend(loc='lower right', fontsize=8, markerscale=1.2, title='Clusters')
    ax1.grid(True, alpha=0.3)
    
    # =========================================
    # RIGHT PLOT: Gemini AI Approach (Best Match Coloring)
    # =========================================
    # For Gemini, we need to map original columns to Gemini tables
    # Since Gemini uses different column names, we'll color by best-matching embedding cluster
    
    # Create a mapping from original columns to their normalized form
    original_normalized = {col: normalize_column(col) for col in original_columns}
    
    # Find which Gemini table each original column best matches
    gemini_table_names = list(gemini_tables.keys())
    gemini_labels = []
    
    for col in original_columns:
        col_norm = original_normalized[col]
        best_table_idx = -1
        best_match_count = 0
        
        for idx, (table_name, table_cols) in enumerate(gemini_tables.items()):
            table_cols_norm = set([normalize_column(c) for c in table_cols])
            if col_norm in table_cols_norm:
                # Direct match
                best_table_idx = idx
                break
        
        gemini_labels.append(best_table_idx)
    
    gemini_labels = np.array(gemini_labels)
    
    # Create colors for Gemini tables
    n_gemini_tables = len(gemini_tables)
    colors_gemini = plt.cm.Set3(np.linspace(0, 1, n_gemini_tables))
    
    # Plot each Gemini table with different color
    for table_idx in range(n_gemini_tables):
        mask = gemini_labels == table_idx
        if np.sum(mask) > 0:
            ax2.scatter(
                embeddings_2d[mask, 0],
                embeddings_2d[mask, 1],
                c=[colors_gemini[table_idx]],
                label=f'{gemini_table_names[table_idx][:20]}',
                s=150,
                alpha=0.7,
                edgecolors='white',
                linewidth=1
            )
    
    # Plot unmatched columns in gray
    unmatched_mask = gemini_labels == -1
    if np.sum(unmatched_mask) > 0:
        ax2.scatter(
            embeddings_2d[unmatched_mask, 0],
            embeddings_2d[unmatched_mask, 1],
            c='lightgray',
            label='Not in Gemini',
            s=150,
            alpha=0.5,
            edgecolors='gray',
            linewidth=1
        )
    
    # Add labels for each point (gemini)
    for i, col in enumerate(original_columns):
        ax2.annotate(
            col,
            (embeddings_2d[i, 0], embeddings_2d[i, 1]),
            fontsize=8,
            alpha=0.7,
            ha='center',
            va='bottom'
        )
    
    ax2.set_title('Gemini AI Approach\n(Query-Pattern Denormalization)', fontsize=7, fontweight='bold')
    ax2.title.set_position((0.7, 1.0))
    ax2.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)', fontsize=7)
    ax2.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)', fontsize=7)
    ax2.legend(loc='lower right', fontsize=7, markerscale=1.0, title='Tables', ncol=2)
    ax2.grid(True, alpha=0.3)
    
    # Main title with statistics
    main_title = f'Database Migration Comparison: Embedding Clustering vs Gemini AI\n'
    main_title += f'[Embedding: {n_embedding_clusters} clusters, {len(original_columns)} cols] '
    main_title += f'[Gemini: {n_gemini_tables} tables, {sum(len(c) for c in gemini_tables.values())} cols (denormalized)] '
    main_title += f'[Avg Similarity: {avg_similarity:.1%}]'
    
    fig.suptitle(main_title, fontsize=10, fontweight='normal', y=0.97)
    
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"[OK] Comparison visualization saved to: {output_path}")
    plt.show()
    
    # =========================================
    # 7. RETURN COMPARISON RESULTS
    # =========================================
    comparison_results = {
        'gemini_table_count': len(gemini_tables),
        'embedding_table_count': len(embedding_tables),
        'gemini_total_columns': sum(len(c) for c in gemini_tables.values()),
        'embedding_total_columns': sum(len(c) for c in embedding_tables.values()),
        'original_columns': len(original_columns),
        'average_similarity': float(avg_similarity),
        'high_matches': high_matches,
        'perfect_matches': perfect_matches,
        'matches': matches,
        'pca_variance_explained': [float(v) for v in pca.explained_variance_ratio_]
    }
    
    # Save comparison results as JSON
    results_path = "../output/comparison_results.json"
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(comparison_results, f, indent=2)
    print(f"[OK] Comparison results saved to: {results_path}")
    
    return comparison_results


if __name__ == "__main__":
    # Run the comparison
    results = compare_migration_approaches(
        gemini_json_path="../output/gemini_suggested_tables.json",
        embedding_json_path="../output/embedding_suggested_tables.json",
        original_columns_path="../output/chinook.db_json.json",
        output_path="../output/comparison_visualization.png"
    )
    
    print("\n" + "=" * 60)
    print(" COMPARISON COMPLETE!")
    print("=" * 60)
    print(f"\nOutput files:")
    print(f"  [VIZ] Visualization: ../output/comparison_visualization.png")
    print(f"  [JSON] Results JSON:  ../output/comparison_results.json")
    print(f"\nKey Insights:")
    print(f"  - Embedding uses {results['embedding_table_count']} clusters for {results['original_columns']} columns")
    print(f"  - Gemini suggests {results['gemini_table_count']} denormalized tables with {results['gemini_total_columns']} total columns")
    print(f"  - Average similarity between approaches: {results['average_similarity']:.1%}")
