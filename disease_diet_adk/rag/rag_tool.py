"""
RAG Query Tool for Disease-Specific Diet Plan Generator
Wrapped as an ADK-compatible function tool for the agents.
"""

import os
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Paths
RAG_DIR = os.path.dirname(__file__)
CHROMA_DB_PATH = os.path.join(RAG_DIR, "chroma_db")
COLLECTION_NAME = "disease_diet_pubmed"  # PubMed peer-reviewed research (primary)
COLLECTION_NAME_FALLBACK = "disease_diet_knowledge"  # NIH scraped fallback

# Singleton client — initialized once
_client = None
_collection = None


def _get_collection():
    """Lazy-initialize the ChromaDB collection."""
    global _client, _collection
    if _collection is None:
        if not os.path.exists(CHROMA_DB_PATH):
            raise RuntimeError(
                "ChromaDB not found at expected path. "
                "Please run disease_diet_adk/rag/build_db.py first."
            )
        _client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        _collection = _client.get_collection(name=COLLECTION_NAME)
    return _collection


def _embed_query(query: str) -> list[float]:
    """Embed a query string using Google's text-embedding-004."""
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=query,
        task_type="retrieval_query"
    )
    return result["embedding"]


def query_medical_knowledge(disease_name: str, query: str, top_k: int = 5) -> str:
    """
    Query the medical knowledge vector database for diet and allergen information.
    
    Args:
        disease_name: The disease or condition (e.g., 'Atopic Dermatitis', 'Type 2 Diabetes')
        query: Specific question about diet, allergens, or nutrition
        top_k: Number of relevant chunks to return (default: 5)
    
    Returns:
        str: Retrieved relevant medical knowledge about diet and allergens for this disease.
    """
    try:
        collection = _get_collection()
        query_embedding = _embed_query(f"{disease_name}: {query}")
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        if not docs:
            return f"No specific dietary information found for {disease_name} in the knowledge base."
        
        output_lines = [f"Medical Knowledge Base Results for: {disease_name}",
                        f"Query: {query}",
                        "=" * 50]
        
        for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
            relevance = round((1 - dist) * 100, 1)
            source = meta.get("sources", "Unknown Source")
            disease = meta.get("disease", disease_name)
            output_lines.append(f"\n[Result {i+1}] Relevance: {relevance}% | Disease: {disease} | Source: {source}")
            output_lines.append(doc)
        
        return "\n".join(output_lines)
    
    except RuntimeError as e:
        return f"RAG knowledge base unavailable: {str(e)}. Proceeding with general medical knowledge."
    except Exception as e:
        return f"Error querying medical knowledge base: {str(e)}. Using general knowledge instead."


def query_allergen_risks(disease_name: str, user_allergens: str) -> str:
    """
    Check if a disease has known additional allergen associations beyond what the user stated.
    
    Args:
        disease_name: The disease condition (e.g., 'Atopic Dermatitis')
        user_allergens: Allergens the user already mentioned (e.g., 'tree nuts, peanuts')
    
    Returns:
        str: Known allergen risks and food triggers for this disease from medical literature.
    """
    query = f"food triggers allergens to avoid dietary restrictions for {disease_name}"
    result = query_medical_knowledge(disease_name, query, top_k=4)
    
    if user_allergens.lower() not in ("none", "no", ""):
        result += f"\n\nNote: User has already declared these allergens: {user_allergens}. Cross-reference with results above."
    
    return result
