"""
Build ChromaDB Vector Store from scraped disease-diet data.
Uses Google's text-embedding-004 for embeddings.
Run once after scraper.py to populate the vector database.
"""

import os
import json
import sys
import time

import chromadb
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY not set in .env")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

# Paths
RAG_DIR = os.path.dirname(__file__)

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--source", choices=["nih", "pubmed"], default="pubmed",
                    help="Which data source to embed: nih (scraped_data.json) or pubmed (pubmed_data.json)")
args = parser.parse_args()

if args.source == "pubmed":
    SCRAPED_DATA_PATH = os.path.join(RAG_DIR, "pubmed_data.json")
    CHROMA_DB_PATH    = os.path.join(RAG_DIR, "chroma_db")
    COLLECTION_NAME   = "disease_diet_pubmed"
else:
    SCRAPED_DATA_PATH = os.path.join(RAG_DIR, "scraped_data.json")
    CHROMA_DB_PATH    = os.path.join(RAG_DIR, "chroma_db")
    COLLECTION_NAME   = "disease_diet_knowledge"


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks for better retrieval."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if len(chunk.strip()) > 50:  # skip tiny chunks
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def get_embedding(text: str) -> list[float]:
    """Get Google gemini-embedding-001 embedding with retry/backoff on 429."""
    for attempt in range(3):
        try:
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=text,
                task_type="retrieval_document"
            )
            return result["embedding"]
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                wait = 15 * (attempt + 1)  # 15s, 30s
                print(f"    [Rate limit] Waiting {wait}s before retry {attempt+2}/3...")
                time.sleep(wait)
            else:
                raise
    return []


def build_vector_store():
    """Main function to build the ChromaDB vector store."""
    
    # Load scraped data
    if not os.path.exists(SCRAPED_DATA_PATH):
        print(f"ERROR: {SCRAPED_DATA_PATH} not found. Run scraper.py first!")
        sys.exit(1)
    
    with open(SCRAPED_DATA_PATH) as f:
        documents = json.load(f)
    
    print(f"\n{'='*60}")
    print(f"  Building ChromaDB Vector Store")
    print(f"  Loaded {len(documents)} disease documents")
    print(f"{'='*60}\n")
    
    # Initialize ChromaDB (persistent local storage)
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    # Delete existing collection if it exists (fresh rebuild)
    try:
        client.delete_collection(name=COLLECTION_NAME)
        print("Deleted existing collection for fresh rebuild.")
    except Exception:
        pass
    
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    
    all_chunks = []
    all_ids = []
    all_embeddings = []
    all_metadatas = []
    
    for doc_idx, doc in enumerate(documents):
        disease = doc["disease"]
        text = doc["combined_text"]
        
        print(f"[{doc_idx+1}/{len(documents)}] Embedding: {disease}")
        
        # Chunk the combined text
        chunks = chunk_text(text)
        print(f"  → {len(chunks)} chunks")
        
        for chunk_idx, chunk in enumerate(chunks):
            chunk_id = f"{doc_idx}_{chunk_idx}"
            
            # Get embedding from Google
            try:
                embedding = get_embedding(chunk)
            except Exception as e:
                print(f"  [Embedding error] chunk {chunk_id}: {e}")
                continue
            
            all_chunks.append(chunk)
            all_ids.append(chunk_id)
            all_embeddings.append(embedding)
            all_metadatas.append({
                "disease": disease,
                "chunk_index": chunk_idx,
                "sources": ", ".join(doc.get("sources", [])),
            })
    
    # Batch insert into ChromaDB
    print(f"\nInserting {len(all_chunks)} chunks into ChromaDB...")
    batch_size = 50
    for i in range(0, len(all_chunks), batch_size):
        collection.add(
            documents=all_chunks[i:i+batch_size],
            embeddings=all_embeddings[i:i+batch_size],
            ids=all_ids[i:i+batch_size],
            metadatas=all_metadatas[i:i+batch_size],
        )
    
    print(f"\n{'='*60}")
    print(f"  ✓ Vector store built successfully!")
    print(f"  Total chunks stored: {len(all_chunks)}")
    print(f"  ChromaDB path: {CHROMA_DB_PATH}")
    print(f"  Collection: {COLLECTION_NAME}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    build_vector_store()
