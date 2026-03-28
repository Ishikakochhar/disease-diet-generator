# PubMed RAG Pipeline: Technical Architecture & Specification

## Executive Summary
This system implements a robust **Retrieval-Augmented Generation (RAG)** pipeline designed specifically for the **Disease-Specific Diet Plan Generator**. Instead of allowing LLMs (like Google Gemini) to hallucinate medical advice or rely on random web searches, this pipeline forces the AI agents to ground their dietary and allergen recommendations purely in **peer-reviewed clinical research** pulled directly from the **NCBI PubMed Database**.

Currently, the system is actively tracking and researching **500 distinct ICD-10 medical conditions**.

---

## 🏗️ 1. Data Ingestion: The Parallel PubMed Scraper (`pubmed_scraper.py`)

### The Challenge
The National Center for Biotechnology Information (NCBI) provides a free REST API (`E-utilities`), but strictly enforces a rate limit of **3 requests per second** for unauthenticated users. Scraping 500 diseases sequentially would take roughly 45 minutes and is prone to network failure. 

### The Implementation
1. **Target Matrix**: We replaced abstract terms (like "liver disease") with **500 precise ICD-10 medical terms** (e.g., `Non-Alcoholic Fatty Liver Disease`, `Primary Sclerosing Cholangitis`, `Tay-Sachs Disease`).
2. **Boolean Search Query**: The script pings the `eSearch.fcgi` endpoint with a highly targeted Boolean constraint to filter out pure pathology papers and only return dietary interventions:
   ```text
   "{disease}"[Title/Abstract] AND (diet[Title/Abstract] OR nutrition[Title/Abstract] OR "dietary"[Title/Abstract] OR "allergen"[Title/Abstract])
   ```
3. **Concurrency & Rate Limiting**: 
   - Operations are distributed across a `ThreadPoolExecutor` with **3 concurrent workers**.
   - To strictly respect NCBI limits, a global `threading.Lock()` checks `time.monotonic()` before every single network request. 
   - If less than **0.34 seconds** have passed since the previous request (globally across all threads), the active thread yields via `time.sleep()`. This perfectly caps throughput at `~2.94 req/s`.
   - On encountering HTTP `429 Too Many Requests` or `502 Bad Gateway`, individual threads invoke an **exponential backoff** (`time.sleep(5 * (attempt + 1))`), retrying up to 3 times before abandoning the specific chunk.
4. **Data Extraction**: Once PMIDs are fetched, `eFetch.fcgi` downloads the `retmode=xml` payload. The script parses the structured XML (extracting Title, Authors, Year, and the `AbstractText` blocks (e.g., Background, Methods, Results, Conclusion)).
5. **Output**: The output is serialized into a flat `pubmed_data.json` schema, capturing the aggregated abstracts. Note: The current pipeline successfully yielded 435 valid, populated disease structures.

---

## 🗄️ 2. Vectorization: The Embedder (`build_db.py`)

### The Challenge
Raw JSON text is useless for semantic search. The unstructured medical text needed to be converted into mathematical vectors, but large-scale generation pushes against Google's Gemini Free Tier quota (1,500 requests/day).

### The Implementation
1. **Text Chunking Pipeline**:
   Using `langchain_text_splitters.RecursiveCharacterTextSplitter`, the aggregate PubMed abstract for each disease is split into granular segments:
   - `chunk_size = 600`: Large enough to capture a full medical hypothesis or conclusion.
   - `chunk_overlap = 100`: Prevents critical context (like a "However, we found...") from being severed across chunk boundaries.
2. **Embedding Model**: The text chunks are vectorized mathematically using `gemini-embedding-001`.
3. **Resiliency & Free-Tier Quota Handling**:
   - The embedder specifically catches `429 Resource Exhausted` exceptions typical of hitting the 1,500 daily requests limit.
   - Instead of breaking the build, the python process enters a hibernation cycle (waiting `15s`, then `30s`, etc.) allowing Google's dynamic sliding-window quota bucket to replenish.
4. **Database Storage**: The vectors and metadata (Disease Name, PMID Source, Year) are committed to a local persistent **ChromaDB** instance stored at `disease_diet_adk/rag/chroma_db/`. The current database active collection is `disease_diet_pubmed` and contains exactly **804 distinct medical vector chunks**.

---

## 🧠 3. Agent Integration: The RAG Interface (`rag_tool.py`)

### The Implementation
This script initializes the persistent ChromaDB client and exposes two explicit semantic search tools that the `crewai` Agents use:

1. **`query_medical_knowledge(disease: str, requirement_query: str)`**
   - **User**: The `medical_researcher` Agent.
   - **Mechanics**: When a user inputs a profile (e.g., `disease = "Celiac Disease"`, `goal = "Weight Lifting"`), the agent converts this into a semantic search string. ChromaDB calculates the cosine similarity against the 804 PubMed chunks, returning the `top_k=3` most mathematically relevant chunks. 
   - **Value**: The agent bases its core caloric and macro guidelines on clinical consensus rather than standard LLM training data.

2. **`query_allergen_risks(disease: str, proposed_food: str)`**
   - **User**: The `allergen_validator` Agent.
   - **Mechanics**: Acts as an enforcement firewall. Before the final plan is returned to the user, the validator loops through the proposed meal plan. If it sees `proposed_food = "Whole Wheat Pasta"`, it queries the medical RAG. The system fetches the PubMed abstracts outlining gluten's destruction of intestinal villi in Celiac patients, and the validator forcefully strips the food from the plan. 

### Conclusion
By coupling specific ICD-10 medical terminology with hard clinical literature (PubMed NCBI constraints) and robust RAG vectorization (ChromaDB + Gemini), the pipeline systematically suppresses the core flaw of LLMs in the medical space: generic and hallucinated advice. Every diet plan is anchored securely to empirical, published medical research.cal literature.
