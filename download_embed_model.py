from sentence_transformers import SentenceTransformer

# Load and download the model (will pull from Hugging Face)
model = SentenceTransformer("all-mpnet-base-v2")

# Save it locally to a folder
model.save("models/mpnet-embedding")

print("✅ Model downloaded and saved to models/mpnet-embedding")
