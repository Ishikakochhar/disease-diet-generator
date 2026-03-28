# 🥗 Disease-Specific Diet Plan Generator

An AI-powered web application built with **CrewAI**, **Google ADK**, **Gemini**, and **RAG** (Retrieval-Augmented Generation) to generate personalized, clinically-informed diet plans. Our multi-agent framework retrieves verified medical guidelines to provide safe nutritional recommendations, strict allergen cross-checks, and tailored meal ideas.

## ✨ Key Features

- **Multi-Agent Orchestration:** Utilizes specialized AI agents (Input Validator, Medical Researcher, Nutritionist, Data Analyst, Recipe Curator, Allergen Validator, and File Generator) to collaboratively build a perfect diet plan.
- **RAG for Clinical Accuracy:** A local ChromaDB vector database ingests medical guidelines (PDFs) and PubMed literature. Agents query this RAG knowledge base *before* generating recommendations, ensuring dietary advice adheres to recognized treatment paths.
- **Live Nutrient Validation (USDA API):** Automatically pulls real-time, highly-accurate macros and micronutrients from the USDA FoodData Central database.
- **Strict Allergen Checks:** A dedicated safety agent scans all chosen ingredients against user-provided allergies and flags potential cross-contamination.
- **Export to PDF:** Converts the finalized, JSON-structured diet plan into a professionally formatted PDF report, ready to be downloaded or printed by the user.

## 🛠️ Technology Stack

- **Core Frameworks:** [Google ADK](https://github.com/google/adk) & [CrewAI](https://github.com/joaomdmoura/crewAI)
- **Large Language Models:** Google Gemini 3.1 Flash-Lite Preview & Gemini 3.0 Flash Preview
- **Vector Database:** ChromaDB (Local embedded RAG)
- **External APIs:** 
  - [SerpAPI](https://serpapi.com/) for retrieving latest medical studies
  - [USDA FoodData Central API](https://fdc.nal.usda.gov/) for accurate nutrition data
- **PDF Generation:** FPDF2

## 📂 Project Structure

```text
├── disease_diet_adk/             # Implementation using Google ADK
│   ├── agent.py                  # Core agent definitions and workflow orchestration
│   └── rag/                      # RAG implementation and ChromaDB embeddings
├── disease_diet_crewai/          # Equivalent implementation using CrewAI
├── medical_guidelines_pdfs/      # Source clinical literature used in RAG (e.g. Celiac Disease, Hypertension, Diabetes)
├── outputs/                      # Generated JSON files and PDF diet reports
├── test_urls.py                  # Utility script to test endpoint health
└── requirements.txt              # Project dependencies
```

## 🚀 Getting Started

### Prerequisites

You will need the following API keys:
1. **Google Gemini API Key**
2. **SerpAPI API Key** (for live search)
3. **USDA API Key** (for `FoodData Central`)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Ishikakochhar/disease-diet-generator.git
   cd disease-diet-generator
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   Create a `.env` file in the root of your project and add your API keys:
   ```env
   GEMINI_API_KEY=your_gemini_key_here
   SERPAPI_API_KEY=your_serpapi_key_here
   USDA_API_KEY=your_usda_key_here
   ```

4. Launch the Web App (via Google ADK):
   ```bash
   .\adk web .
   ```
   Navigate to `http://localhost:8001` or your specified ADK web port in the browser to interact with the system.

## ⚕️ Medical Disclaimer

*This application is essentially for educational and demonstrative purposes. All dietary suggestions should be consulted with a registered nutritionist or physician before adhering to them.*
