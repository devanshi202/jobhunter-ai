import numpy as np

# Lazy load model
model = None

def get_model():
    global model
    if model is None:
        from sentence_transformers import SentenceTransformer
        print("Loading sentence-transformers model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Model loaded successfully.")
    return model

def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text"""
    m = get_model()
    # Ensure text is string and not empty
    if not text or not isinstance(text, str):
        text = ""
    
    embedding = m.encode(text)
    
    # Convert numpy array to list of floats
    return embedding.tolist()

def compute_similarity(emb1: list[float], emb2: list[float]) -> float:
    """Compute cosine similarity between two embeddings"""
    if not emb1 or not emb2:
        return 0.0
        
    vec1 = np.array(emb1)
    vec2 = np.array(emb2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
        
    return float(dot_product / (norm1 * norm2))
