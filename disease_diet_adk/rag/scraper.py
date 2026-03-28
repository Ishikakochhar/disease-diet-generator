"""
RAG Scraper for Disease-Specific Diet Plan Generator

Dynamically discovers diseases from NIH MedlinePlus A-Z Health Topics index,
then scrapes each disease page + Healthline for diet/allergy/nutrition information.

NO static hardcoded data — everything comes from the web.
Run once to populate scraped_data.json.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "scraped_data.json")

# Keywords used to filter which scraped text is actually diet/nutrition related
DIET_KEYWORDS = [
    "diet", "food", "eat", "eating", "nutrition", "nutrient", "vitamin",
    "mineral", "protein", "fiber", "fat", "carbohydrate", "calorie",
    "avoid", "restrict", "allerg", "trigger", "intolerance", "supplement",
    "omega", "calcium", "iron", "sodium", "potassium", "gluten", "dairy",
    "sugar", "meal", "gut", "digestion", "weight",
]


def safe_get(url: str) -> BeautifulSoup | None:
    """Fetch a URL with retry logic, return BeautifulSoup or None."""
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "html.parser")
            print(f"    [HTTP {resp.status_code}] {url}")
            return None
        except Exception as e:
            print(f"    [Attempt {attempt+1} Error] {url}: {e}")
            time.sleep(2)
    return None


def is_diet_related(text: str) -> bool:
    """Return True if the text contains any diet/nutrition-related keywords."""
    t = text.lower()
    return any(kw in t for kw in DIET_KEYWORDS)


# ─────────────────────────────────────────────────────────────
# STEP 1: Dynamic Disease Discovery from NIH MedlinePlus A-Z
# ─────────────────────────────────────────────────────────────

def discover_diseases_from_nih() -> list[dict]:
    """
    Scrape the NIH MedlinePlus A-Z Health Topics index to dynamically discover
    diseases and their topic URLs. Returns list of {name, url} dicts.
    """
    print("Discovering diseases from NIH MedlinePlus A-Z index...")
    
    diseases = []
    
    # NIH MedlinePlus has per-letter pages like /healthtopics/a.html
    alphabet = "abcdefghijklmnopqrstuvwxyz0"  # '0' covers numbers like '5-HTP'
    
    for letter in alphabet:
        url = f"https://medlineplus.gov/healthtopics_{letter}.html"
        soup = safe_get(url)
        if not soup:
            time.sleep(1)
            continue
        
        # Each topic is a link in the topic list
        topic_section = soup.find("div", id="topic-list")
        if not topic_section:
            topic_section = soup
        
        links = topic_section.find_all("a", href=True)
        for link in links:
            href = link["href"]
            name = link.get_text(strip=True)
            
            # Filter: must be absolute medlineplus.gov disease page URLs
            if not href.startswith("https://medlineplus.gov/"):
                continue
            if not href.endswith(".html"):
                continue
            # Skip known non-disease pages
            skip_patterns = [
                "healthtopics", "druginformation", "encyclopedia", "genetics",
                "lab-tests", "sitemap", "about", "whatsnew", "spanish",
                "all_health", "drugsupplements"
            ]
            if any(s in href for s in skip_patterns):
                continue
            if not name or len(name) < 3:
                continue
            
            diseases.append({"name": name, "url": href})
        
        time.sleep(0.8)  # Be polite
    
    # Deduplicate by URL
    seen = set()
    unique = []
    for d in diseases:
        if d["url"] not in seen:
            seen.add(d["url"])
            unique.append(d)
    
    print(f"  Discovered {len(unique)} unique disease/health topics.\n")
    return unique


# ─────────────────────────────────────────────────────────────
# STEP 2: Scrape each NIH MedlinePlus disease page
# ─────────────────────────────────────────────────────────────

def scrape_medlineplus_topic(url: str, disease: str) -> dict:
    """Scrape a single NIH MedlinePlus health topic page for diet/nutritional content."""
    soup = safe_get(url)
    if not soup:
        return {"source": "NIH MedlinePlus", "url": url, "disease": disease, "content": []}
    
    content = []
    
    # Grab the summary section
    summary = soup.find("div", id="topic-summary")
    if summary:
        for p in summary.find_all("p")[:6]:
            text = p.get_text(strip=True)
            if text and len(text) > 40:
                content.append(text)
    
    # Grab all page text and filter by diet relevance
    all_text = soup.get_text(separator="\n")
    lines = [l.strip() for l in all_text.split("\n") if l.strip()]
    diet_lines = [l for l in lines if is_diet_related(l) and len(l) > 40]
    content.extend(diet_lines[:20])  # Cap at 20 to keep per-topic size manageable
    
    return {
        "source": "NIH MedlinePlus",
        "url": url,
        "disease": disease,
        "content": list(dict.fromkeys(content)),  # Deduplicate
    }


# ─────────────────────────────────────────────────────────────
# STEP 3: Search Healthline for diet articles on each disease
# ─────────────────────────────────────────────────────────────

def search_healthline_for_disease(disease_name: str) -> dict:
    """
    Search Healthline for diet/nutrition articles related to the disease.
    Uses Healthline's own search endpoint.
    """
    query = f"{disease_name} diet foods to eat avoid"
    search_url = f"https://www.healthline.com/search?q1={requests.utils.quote(query)}"
    
    soup = safe_get(search_url)
    if not soup:
        return {"source": "Healthline", "disease": disease_name, "content": []}
    
    # Find the first article link in search results
    article_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/health/" in href or "/nutrition/" in href:
            if disease_name.lower().split()[0] in href.lower() or "diet" in href.lower():
                full = href if href.startswith("http") else f"https://www.healthline.com{href}"
                article_links.append(full)
    
    if not article_links:
        return {"source": "Healthline", "disease": disease_name, "content": []}
    
    # Re-scrape the first matching article
    article_url = article_links[0]
    article_soup = safe_get(article_url)
    if not article_soup:
        return {"source": "Healthline", "disease": disease_name, "content": []}
    
    content = []
    body = article_soup.find("article") or article_soup.find("main") or article_soup
    for el in body.find_all(["p", "li", "h2", "h3"]):
        text = el.get_text(strip=True)
        if is_diet_related(text) and len(text) > 40:
            content.append(text)
    
    return {
        "source": "Healthline",
        "url": article_url,
        "disease": disease_name,
        "content": content[:30],
    }


# ─────────────────────────────────────────────────────────────
# STEP 4: Build combined document for ChromaDB indexing
# ─────────────────────────────────────────────────────────────

def build_document(disease_name: str, scraped_results: list[dict]) -> dict:
    """Combine all scraped text chunks into one structured document per disease."""
    all_lines = [f"Disease: {disease_name}"]
    sources = []
    
    for result in scraped_results:
        src = result.get("source", "Unknown")
        if result.get("content"):
            sources.append(src)
            for chunk in result["content"]:
                all_lines.append(f"[{src}] {chunk}")
    
    return {
        "disease": disease_name,
        "combined_text": "\n".join(all_lines),
        "sources": list(set(sources)),
        "num_lines": len(all_lines),
    }


# ─────────────────────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ─────────────────────────────────────────────────────────────

def run_scraper(max_diseases: int = 200):
    """
    Main scraping orchestrator.
    Args:
        max_diseases: Max number of diseases to process (default 200).
    """
    print(f"\n{'='*60}")
    print("  Disease RAG Scraper — Starting")
    print(f"  Will scrape up to {max_diseases} diseases from NIH MedlinePlus A-Z")
    print(f"{'='*60}\n")
    
    # Step 1: Discover all diseases from NIH A-Z
    diseases = discover_diseases_from_nih()
    diseases = diseases[:max_diseases]
    
    all_documents = []
    
    for i, disease_entry in enumerate(diseases):
        name = disease_entry["name"]
        url = disease_entry["url"]
        print(f"[{i+1}/{len(diseases)}] {name}")
        
        scraped = []
        
        # NIH page for this disease
        nih_data = scrape_medlineplus_topic(url, name)
        if nih_data.get("content"):
            scraped.append(nih_data)
        
        # If no diet content found on NIH, search Healthline
        if not scraped or len(scraped[0]["content"]) < 3:
            time.sleep(0.5)
            hl_data = search_healthline_for_disease(name)
            if hl_data.get("content"):
                scraped.append(hl_data)
        
        doc = build_document(name, scraped)
        
        # Only keep documents that have meaningful diet content
        if doc["num_lines"] > 2:
            all_documents.append(doc)
            print(f"  ✓ {doc['num_lines']} lines | Sources: {doc['sources']}")
        else:
            print(f"  ✗ Skipped (no diet content found)")
        
        time.sleep(1.0)  # Polite crawl delay
    
    # Save to JSON
    with open(OUTPUT_PATH, "w") as f:
        json.dump(all_documents, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"  ✓ Scraping complete!")
    print(f"  {len(all_documents)} disease documents saved to scraped_data.json")
    print(f"  Path: {OUTPUT_PATH}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=200, help="Max diseases to scrape")
    args = parser.parse_args()
    run_scraper(max_diseases=args.max)
