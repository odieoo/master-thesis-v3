#Generating embedding section
from db_service import get_table_columns
from sentence_transformers import SentenceTransformer
import torch

# ===== Check GPU availability =====
print("=" * 50)
print("🔍 Device Check:")
print(f"   PyTorch version: {torch.__version__}")
print(f"   CUDA available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"   GPU: {torch.cuda.get_device_name(0)}")
    print(f"   CUDA version: {torch.version.cuda}")
    device = "cuda"
else:
    print("   Running on: CPU")
    device = "cpu"
print("=" * 50)

# Get table columns from database
table_columns = get_table_columns()

# Generate embeddings (automatically uses GPU if available)
model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
embeddings = model.encode(table_columns, show_progress_bar=True)

print(f"\n✅ Generated {len(embeddings)} embeddings for {len(table_columns)} columns")
print(f"   Embedding dimension: {embeddings.shape[1]}")
print(f"   Device used: {device.upper()}")

# Show first 5 embedding vectors with full values
print("\n" + "=" * 50)
print(" First 5 Embedding Vectors (Full Values):")
print("=" * 50)
for i in range(min(5, len(embeddings))):
    print(f"\n[{i}] Column: {table_columns[i]}")
    print(f"    Shape: {embeddings[i].shape}")
    print(f"    Vector values:")
    print(embeddings[i])
