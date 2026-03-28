"""
PubMed RAG Scraper for Disease-Specific Diet Plan Generator

Uses the NCBI PubMed E-utilities API (free, no key required for basic use)
to fetch real peer-reviewed research abstracts about disease-specific diet
and nutrition. Zero hardcoded medical knowledge.

Saves results to pubmed_data.json (separate from the NIH scraped_data.json fallback).

Run once:
    python pubmed_scraper.py --max 50
"""

import requests
import json
import time
import os
import xml.etree.ElementTree as ET
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "pubmed_data.json")

# NCBI E-utilities base URLs
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Common params — add your NCBI API key here if you have one (free to get, 10 req/s vs 3 req/s)
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")  # optional

# ─────────────────────────────────────────────────────────────
# Disease list — sourced from ICD-10-CM common conditions
# These are all medically recognised disease names, NOT generic topics
# ─────────────────────────────────────────────────────────────
DISEASES = [
    # Original 100 — Metabolic, Diabetes, GI, Allergy, Autoimmune, Cancer, Nutritional
    "Type 2 Diabetes Mellitus",
    "Type 1 Diabetes Mellitus",
    "Atopic Dermatitis",
    "Celiac Disease",
    "Crohn Disease",
    "Ulcerative Colitis",
    "Irritable Bowel Syndrome",
    "Gastroesophageal Reflux Disease",
    "Rheumatoid Arthritis",
    "Psoriasis",
    "Lupus Erythematosus",
    "Gout",
    "Hypertension",
    "Chronic Kidney Disease",
    "Non-Alcoholic Fatty Liver Disease",
    "Hypothyroidism",
    "Hyperthyroidism",
    "Anemia",
    "Iron Deficiency Anemia",
    "Osteoporosis",
    "Coronary Artery Disease",
    "Heart Failure",
    "Chronic Obstructive Pulmonary Disease",
    "Asthma",
    "Pancreatitis",
    "Polycystic Ovary Syndrome",
    "Metabolic Syndrome",
    "Obesity",
    "Multiple Sclerosis",
    "Parkinson Disease",
    "Alzheimer Disease",
    "Epilepsy",
    "Migraine",
    "Depression",
    "Anxiety Disorder",
    "Schizophrenia",
    "Bipolar Disorder",
    "Attention Deficit Hyperactivity Disorder",
    "Autism Spectrum Disorder",
    "Food Allergy",
    "Peanut Allergy",
    "Tree Nut Allergy",
    "Milk Allergy",
    "Egg Allergy",
    "Wheat Allergy",
    "Soy Allergy",
    "Shellfish Allergy",
    "Lactose Intolerance",
    "Fructose Malabsorption",
    "Phenylketonuria",
    "Maple Syrup Urine Disease",
    "Galactosemia",
    "Wilson Disease",
    "Hemochromatosis",
    "Cystic Fibrosis",
    "Inflammatory Bowel Disease",
    "Diverticulitis",
    "Gastritis",
    "Peptic Ulcer Disease",
    "Kidney Stones",
    "Hyperuricemia",
    "Hyperlipidemia",
    "Hypercholesterolemia",
    "Hypertriglyceridemia",
    "Fatty Acid Oxidation Disorders",
    "Short Bowel Syndrome",
    "Dumping Syndrome",
    "Eating Disorders",
    "Anorexia Nervosa",
    "Bulimia Nervosa",
    "Malnutrition",
    "Vitamin D Deficiency",
    "Vitamin B12 Deficiency",
    "Folate Deficiency",
    "Zinc Deficiency",
    "Magnesium Deficiency",
    "Calcium Deficiency",
    "Selenium Deficiency",
    "Iodine Deficiency",
    "Scurvy",
    "Pellagra",
    "Rickets",
    "Beriberi",
    "Kwashiorkor",
    "Colorectal Cancer",
    "Gastric Cancer",
    "Esophageal Cancer",
    "Pancreatic Cancer",
    "Liver Cancer",
    "Breast Cancer",
    "Prostate Cancer",
    "Endometrial Cancer",
    "Bladder Cancer",
    "Kidney Cancer",
    "Thyroid Cancer",
    "Leukemia",
    "Lymphoma",
    "Multiple Myeloma",
    "Hepatitis B",
    "Hepatitis C",
    "HIV Infection",
    "Tuberculosis",
    "Sarcopenia",
    "Cachexia",
    # Metabolic & Endocrine (101–140)
    "Cushing Syndrome",
    "Addison Disease",
    "Acromegaly",
    "Pituitary Adenoma",
    "Hyperparathyroidism",
    "Hypoparathyroidism",
    "Primary Aldosteronism",
    "Pheochromocytoma",
    "Carcinoid Syndrome",
    "Insulinoma",
    "Glycogen Storage Disease",
    "Gaucher Disease",
    "Fabry Disease",
    "Niemann-Pick Disease",
    "Tay-Sachs Disease",
    "Mucopolysaccharidosis",
    "Homocystinuria",
    "Tyrosinemia",
    "Organic Acidemia",
    "Urea Cycle Disorders",
    "Biotinidase Deficiency",
    "Propionic Acidemia",
    "Methylmalonic Acidemia",
    "Glutaric Aciduria",
    "Isovaleric Acidemia",
    "Medium Chain Acyl-CoA Dehydrogenase Deficiency",
    "Long Chain Acyl-CoA Dehydrogenase Deficiency",
    "Very Long Chain Acyl-CoA Dehydrogenase Deficiency",
    "Carnitine Deficiency",
    "Mitochondrial Disease",
    "Peroxisomal Disorders",
    "Zellweger Syndrome",
    "Smith-Lemli-Opitz Syndrome",
    "Congenital Disorders of Glycosylation",
    "Abetalipoproteinemia",
    "Familial Hypercholesterolemia",
    "Familial Combined Hyperlipidemia",
    "Sitosterolemia",
    "Tangier Disease",
    # GI / Liver / Hepatology (141–185)
    "Autoimmune Hepatitis",
    "Primary Biliary Cholangitis",
    "Primary Sclerosing Cholangitis",
    "Cirrhosis",
    "Hepatic Encephalopathy",
    "Liver Failure",
    "Cholestasis",
    "Cholecystitis",
    "Cholelithiasis",
    "Eosinophilic Esophagitis",
    "Achalasia",
    "Gastroparesis",
    "Small Intestinal Bacterial Overgrowth",
    "Microscopic Colitis",
    "Collagenous Colitis",
    "Pouchitis",
    "Radiation Enteritis",
    "Whipple Disease",
    "Tropical Sprue",
    "Intestinal Lymphangiectasia",
    "Protein Losing Enteropathy",
    "Bile Acid Malabsorption",
    "Exocrine Pancreatic Insufficiency",
    "Autoimmune Pancreatitis",
    "Mesenteric Ischemia",
    "Ischemic Colitis",
    "Diverticular Disease",
    "Anal Fistula Nutrition",
    "Hemorrhoids",
    "Colon Polyps Diet",
    "Barrett Esophagus",
    "Helicobacter Pylori Infection",
    "Clostridioides Difficile Infection",
    "Giardiasis",
    "Amoebiasis",
    "Cryptosporidiosis",
    "Intestinal Parasites",
    "Cyclospora Infection",
    "Food Poisoning",
    "Traveler Diarrhea",
    "Lactase Deficiency",
    "Sucrase-Isomaltase Deficiency",
    "Trehalase Deficiency",
    # Renal / Urological (186–210)
    "Nephrotic Syndrome",
    "Nephrolithiasis",
    "IgA Nephropathy",
    "Membranous Nephropathy",
    "Focal Segmental Glomerulosclerosis",
    "Polycystic Kidney Disease",
    "Alport Syndrome",
    "Renal Tubular Acidosis",
    "Fanconi Syndrome",
    "Hyperoxaluria",
    "Cystinuria",
    "End Stage Renal Disease",
    "Dialysis Nutrition",
    "Renal Transplant Nutrition",
    "Nephrogenic Diabetes Insipidus",
    "Hyponatremia",
    "Hyperkalemia",
    "Hyperphosphatemia",
    "Renal Osteodystrophy",
    "Urinary Tract Infection",
    "Interstitial Cystitis Diet",
    "Vesicoureteral Reflux",
    "Benign Prostatic Hyperplasia",
    "Prostatitis",
    "Bladder Cancer Nutrition",
    # Cardiovascular (211–240)
    "Atrial Fibrillation",
    "Hypertrophic Cardiomyopathy",
    "Dilated Cardiomyopathy",
    "Restrictive Cardiomyopathy",
    "Cardiac Amyloidosis",
    "Infective Endocarditis",
    "Pericarditis",
    "Myocarditis",
    "Peripheral Artery Disease",
    "Aortic Stenosis",
    "Marfan Syndrome",
    "Ehlers-Danlos Syndrome",
    "Vasculitis",
    "Raynaud Disease",
    "Deep Vein Thrombosis",
    "Pulmonary Embolism",
    "Anticoagulation Diet",
    "DASH Diet Hypertension",
    "Mediterranean Diet Heart Disease",
    "Dyslipidemia",
    "Angina Pectoris",
    "Myocardial Infarction Recovery",
    "Cardiac Rehabilitation Nutrition",
    "Congenital Heart Disease",
    "Fontan Circulation Nutrition",
    "Heart Transplant Nutrition",
    "Ventricular Assist Device Nutrition",
    "Pacemaker Patient Diet",
    "Warfarin Diet Interaction",
    "Sodium Restriction",
    # Respiratory / Pulmonary (241–265)
    "Pulmonary Fibrosis",
    "Sarcoidosis",
    "Pulmonary Hypertension",
    "Bronchiectasis",
    "Alpha-1 Antitrypsin Deficiency",
    "Obstructive Sleep Apnea",
    "Hypersensitivity Pneumonitis",
    "Eosinophilic Pneumonia",
    "Lung Cancer",
    "Mesothelioma",
    "Pleural Effusion",
    "Pulmonary Tuberculosis",
    "COVID-19",
    "Long COVID Syndrome",
    "Post-COVID Fatigue",
    "Respiratory Failure Nutrition",
    "Mechanical Ventilation Nutrition",
    "Tracheostomy Nutrition",
    "Pneumonia Recovery Diet",
    "Influenza Recovery Diet",
    "Cystic Fibrosis Nutrition in Adults",
    "Primary Ciliary Dyskinesia",
    "Lymphangioleiomyomatosis",
    "Chylothorax",
    "Plastic Bronchitis",
    # Rheumatological / Autoimmune (266–300)
    "Sjögren Syndrome",
    "Systemic Sclerosis",
    "Polymyositis",
    "Dermatomyositis",
    "Polymyalgia Rheumatica",
    "Giant Cell Arteritis",
    "Ankylosing Spondylitis",
    "Psoriatic Arthritis",
    "Reactive Arthritis",
    "Juvenile Idiopathic Arthritis",
    "Antiphospholipid Syndrome",
    "Mixed Connective Tissue Disease",
    "Relapsing Polychondritis",
    "Behçet Disease",
    "Adult Still Disease",
    "Fibromyalgia",
    "Osteoarthritis",
    "Anti-GBM Disease",
    "ANCA Vasculitis",
    "Polyarteritis Nodosa",
    "Granulomatosis with Polyangiitis",
    "Microscopic Polyangiitis",
    "Eosinophilic Granulomatosis",
    "Takayasu Arteritis",
    "Henoch-Schönlein Purpura",
    "Cryoglobulinemia",
    "Myasthenia Gravis",
    "Lambert-Eaton Syndrome",
    "Stiff Person Syndrome",
    "IgG4 Related Disease",
    "VEXAS Syndrome",
    "Immune Reconstitution Inflammatory Syndrome",
    "Sarcoidosis Diet",
    "Undifferentiated Connective Tissue Disease",
    "Overlap Syndrome",
    # Neurological (301–340)
    "Amyotrophic Lateral Sclerosis",
    "Huntington Disease",
    "Spinocerebellar Ataxia",
    "Friedreich Ataxia",
    "Charcot-Marie-Tooth Disease",
    "Guillain-Barré Syndrome",
    "Chronic Inflammatory Demyelinating Polyneuropathy",
    "Peripheral Neuropathy",
    "Diabetic Neuropathy",
    "Restless Legs Syndrome",
    "Narcolepsy",
    "Stroke Recovery Diet",
    "Traumatic Brain Injury Nutrition",
    "Spinal Cord Injury Nutrition",
    "Hydrocephalus",
    "Meningitis Recovery",
    "Encephalitis Recovery",
    "Prion Disease",
    "Motor Neuron Disease",
    "Tourette Syndrome",
    "Cerebral Palsy Nutrition",
    "Spina Bifida Nutrition",
    "Muscular Dystrophy",
    "Becker Muscular Dystrophy",
    "Duchenne Muscular Dystrophy",
    "Spinal Muscular Atrophy",
    "Pompe Disease",
    "Myotonic Dystrophy",
    "Dementia with Lewy Bodies",
    "Frontotemporal Dementia",
    "Normal Pressure Hydrocephalus",
    "Essential Tremor",
    "Cervical Dystonia",
    "Hemiplegic Migraine",
    "Cluster Headache",
    "Idiopathic Intracranial Hypertension",
    "Transverse Myelitis",
    "Neuromyelitis Optica",
    "Progressive Supranuclear Palsy",
    "Multiple System Atrophy",
    # Dermatological (341–360)
    "Acne Vulgaris",
    "Rosacea",
    "Urticaria",
    "Angioedema",
    "Vitiligo",
    "Alopecia Areata",
    "Pemphigus Vulgaris",
    "Bullous Pemphigoid",
    "Epidermolysis Bullosa",
    "Seborrheic Dermatitis",
    "Contact Dermatitis",
    "Hidradenitis Suppurativa",
    "Lichen Planus",
    "Mycosis Fungoides",
    "Dermatitis Herpetiformis",
    "Ichthyosis",
    "Palmoplantar Keratoderma",
    "Netherton Syndrome",
    "Erythroderma",
    "Toxic Epidermal Necrolysis",
    # Hematological (361–385)
    "Sickle Cell Disease",
    "Thalassemia",
    "Hemophilia",
    "Von Willebrand Disease",
    "Thrombocytopenia",
    "Aplastic Anemia",
    "Polycythemia Vera",
    "Essential Thrombocythemia",
    "Myelofibrosis",
    "Myelodysplastic Syndrome",
    "Pernicious Anemia",
    "G6PD Deficiency",
    "Hereditary Spherocytosis",
    "Paroxysmal Nocturnal Hemoglobinuria",
    "Diamond-Blackfan Anemia",
    "Fanconi Anemia",
    "Autoimmune Hemolytic Anemia",
    "Thrombotic Thrombocytopenic Purpura",
    "Hemolytic Uremic Syndrome",
    "Disseminated Intravascular Coagulation",
    "Hyperviscosity Syndrome",
    "Mastocytosis",
    "Hypereosinophilic Syndrome",
    "Castleman Disease",
    "Amyloidosis",
    # Gynecological / Reproductive (386–400)
    "Endometriosis",
    "Uterine Fibroids",
    "Premature Ovarian Insufficiency",
    "Hyperemesis Gravidarum",
    "Gestational Diabetes",
    "Preeclampsia",
    "Menopause",
    "Premenstrual Syndrome",
    "Recurrent Miscarriage",
    "Preterm Labor Nutrition",
    "Infertility Nutrition",
    "PCOS Insulin Resistance",
    "Ovarian Hyperstimulation Syndrome",
    "Postpartum Depression Nutrition",
    "Breastfeeding Nutrition",
    # Oncology Nutrition (401–425)
    "Cancer Cachexia",
    "Chemotherapy Nutrition",
    "Radiation Therapy Nutrition",
    "Head and Neck Cancer Nutrition",
    "Hematopoietic Stem Cell Transplant Nutrition",
    "Oral Cancer",
    "Cervical Cancer",
    "Ovarian Cancer",
    "Testicular Cancer",
    "Melanoma",
    "Brain Tumor Nutrition",
    "Osteosarcoma",
    "Neuroblastoma",
    "Hepatocellular Carcinoma",
    "Cholangiocarcinoma",
    "Gallbladder Cancer",
    "Small Intestine Cancer",
    "Appendix Cancer",
    "Anal Cancer",
    "Peritoneal Carcinomatosis",
    "Neuroendocrine Tumor",
    "Pheochromocytoma Diet",
    "Paraneoplastic Syndrome",
    "Tumor Lysis Syndrome",
    "Graft versus Host Disease",
    # Pediatric / Developmental (426–450)
    "Failure to Thrive",
    "Pediatric Inflammatory Bowel Disease",
    "Necrotizing Enterocolitis",
    "Childhood Obesity",
    "Prematurity and Nutrition",
    "Congenital Heart Disease Nutrition",
    "Short Gut Syndrome Infant",
    "Biliary Atresia",
    "Alagille Syndrome",
    "Progressive Familial Intrahepatic Cholestasis",
    "Inborn Errors of Metabolism Infant",
    "Prader-Willi Syndrome",
    "Down Syndrome Nutrition",
    "Turner Syndrome Nutrition",
    "Williams Syndrome",
    "Fragile X Syndrome",
    "Rett Syndrome",
    "Angelman Syndrome",
    "Tuberous Sclerosis",
    "Neurofibromatosis",
    "Pediatric Celiac Disease",
    "Pediatric Food Allergy",
    "Pediatric Type 1 Diabetes",
    "Neonatal Abstinence Syndrome",
    "Congenital Sucrase-Isomaltase Deficiency",
    # Mental Health (451–465)
    "Post-Traumatic Stress Disorder",
    "Obsessive-Compulsive Disorder",
    "Binge Eating Disorder",
    "Avoidant Restrictive Food Intake Disorder",
    "Orthorexia Nervosa",
    "Night Eating Syndrome",
    "Alcohol Use Disorder",
    "Opioid Use Disorder",
    "Eating Disorders in Athletes",
    "Refeeding Syndrome",
    "Pica",
    "Rumination Syndrome",
    "Merycism",
    "Psychogenic Polydipsia",
    "Social Anxiety and Food",
    # Surgical / Post-operative (466–490)
    "Bariatric Surgery Nutrition",
    "Gastric Bypass Nutrition",
    "Sleeve Gastrectomy Nutrition",
    "Colostomy Nutrition",
    "Ileostomy Nutrition",
    "Post-Gastrectomy Syndrome",
    "Pancreaticoduodenectomy Nutrition",
    "Liver Transplant Nutrition",
    "Kidney Transplant Nutrition",
    "Cardiac Surgery Nutrition",
    "Burn Injury Nutrition",
    "Sepsis Nutrition",
    "Critical Illness Nutrition",
    "Enteral Nutrition",
    "Parenteral Nutrition",
    "Ketogenic Diet Therapy",
    "Modified Atkins Diet",
    "Low Glycemic Index Diet",
    "FODMAP Diet",
    "Specific Carbohydrate Diet",
    "Gut Microbiome and Diet",
    "Prebiotic Foods",
    "Probiotic Therapy",
    "Postbiotic Nutrition",
    "Immunonutrition",
    # Rare/Genetic (491–500)
    "Acrodermatitis Enteropathica",
    "Hartnup Disease",
    "Menkes Disease",
    "Hereditary Fructose Intolerance",
    "MELAS Syndrome",
    "Pyruvate Dehydrogenase Deficiency",
    "Kearns-Sayre Syndrome",
    "Refsum Disease",
    "Transcobalamin Deficiency",
    "Hyperinsulinism Congenital",
]

import threading
_rate_lock = threading.Lock()
_last_request_time = [0.0]  # shared mutable float via list

def _rate_limited_get(url: str, params: dict, timeout: int) -> requests.Response:
    """Thread-safe rate-limited GET — max 3 req/s across all threads."""
    with _rate_lock:
        now = time.monotonic()
        elapsed = now - _last_request_time[0]
        if elapsed < 0.34:
            time.sleep(0.34 - elapsed)
        _last_request_time[0] = time.monotonic()
    return requests.get(url, params=params, timeout=timeout)
def esearch(disease: str, max_results: int = 5) -> list[str]:
    """Search PubMed for PMIDs, retries on 429 with backoff."""
    query = f'"{disease}"[Title/Abstract] AND (diet[Title/Abstract] OR nutrition[Title/Abstract] OR "dietary"[Title/Abstract] OR "allergen"[Title/Abstract])'
    params = {
        "db": "pubmed", "term": query, "retmax": max_results,
        "retmode": "json", "sort": "relevance", "usehistory": "n",
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    for attempt in range(3):
        try:
            resp = _rate_limited_get(ESEARCH_URL, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json().get("esearchresult", {}).get("idlist", [])
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                time.sleep(5 * (attempt + 1))
            else:
                print(f"    [eSearch error] {e}")
                return []
    return []


def efetch_abstracts(pmids: list[str]) -> list[dict]:
    """
    Fetch full abstracts for a list of PMIDs using PubMed eFetch.
    Retries up to 3 times on 429 rate limit errors.
    """
    if not pmids:
        return []
    
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    
    for attempt in range(3):
        try:
            resp = requests.get(EFETCH_URL, params=params, timeout=20)
            resp.raise_for_status()
            break
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                wait = 3 * (attempt + 1)
                time.sleep(wait)
            else:
                print(f"    [eFetch error] {e}")
                return []
    else:
        return []
    
    results = []
    try:
        root = ET.fromstring(resp.content)
        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else "unknown"
            
            title_el = article.find(".//ArticleTitle")
            title = (title_el.text or "").strip() if title_el is not None else ""
            
            # Abstract may have multiple sections (Background, Methods, etc.)
            abstract_parts = []
            for ab in article.findall(".//AbstractText"):
                label = ab.get("Label", "")
                text = ab.text or ""
                if label:
                    abstract_parts.append(f"{label}: {text.strip()}")
                else:
                    abstract_parts.append(text.strip())
            abstract = " ".join(abstract_parts).strip()
            
            # Year
            year_el = article.find(".//PubDate/Year")
            year = year_el.text if year_el is not None else ""
            
            # Authors
            authors = []
            for author in article.findall(".//Author")[:3]:
                ln = author.find("LastName")
                fn = author.find("ForeName")
                if ln is not None:
                    name = ln.text or ""
                    if fn is not None:
                        name += f" {fn.text or ''}"
                    authors.append(name.strip())
            
            if abstract and len(abstract) > 100:
                results.append({
                    "pmid": pmid,
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "year": year,
                })
    except ET.ParseError as e:
        print(f"    [XML parse error] {e}")
    
    return results


def build_document(disease: str, articles: list[dict]) -> dict:
    """Build a combined ChromaDB-ready document from PubMed articles."""
    all_lines = [f"Disease: {disease}", f"PubMed Research Summary — {len(articles)} peer-reviewed articles"]
    
    for art in articles:
        all_lines.append(f"\n[PubMed PMID:{art['pmid']} {art['year']}] {art['title']}")
        if art["authors"]:
            all_lines.append(f"Authors: {', '.join(art['authors'])}")
        all_lines.append(art["abstract"])
    
    return {
        "disease": disease,
        "combined_text": "\n".join(all_lines),
        "sources": ["PubMed"],
        "article_count": len(articles),
        "pmids": [a["pmid"] for a in articles],
    }


def fetch_disease(args: tuple) -> dict | None:
    """Fetch one disease from PubMed. Called in parallel."""
    idx, total, disease, abstracts_per_disease = args
    
    pmids = esearch(disease, max_results=abstracts_per_disease)
    if not pmids:
        print(f"  [{idx}/{total}] {disease} — no PubMed results, skipping")
        return None
    
    time.sleep(0.35)  # space out eFetch calls per thread (~3 req/s with 5 workers)
    articles = efetch_abstracts(pmids)
    if not articles:
        print(f"  [{idx}/{total}] {disease} — no usable abstracts, skipping")
        return None
    
    doc = build_document(disease, articles)
    print(f"  [{idx}/{total}] ✓ {disease}  ({len(articles)} abstracts)")
    return doc


def run_pubmed_scraper(max_diseases: int = 500, abstracts_per_disease: int = 3, workers: int = 3):
    """Parallel orchestrator using ThreadPoolExecutor."""
    print(f"\n{'='*60}")
    print(f"  PubMed RAG Scraper — Parallel Mode  ({workers} workers)")
    print(f"  Diseases: {max_diseases} | Abstracts per disease: {abstracts_per_disease}")
    print(f"  Source: NCBI PubMed E-utilities (peer-reviewed research)")
    print(f"{'='*60}\n")

    diseases = DISEASES[:max_diseases]
    total = len(diseases)
    args_list = [(i + 1, total, d, abstracts_per_disease) for i, d in enumerate(diseases)]

    all_documents = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_disease, args): args for args in args_list}
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                all_documents.append(result)

    # Sort by original list order for consistency
    order = {d: i for i, d in enumerate(diseases)}
    all_documents.sort(key=lambda x: order.get(x["disease"], 9999))

    with open(OUTPUT_PATH, "w") as f:
        json.dump(all_documents, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  ✓ PubMed scraping complete!")
    print(f"  {len(all_documents)} disease documents saved to pubmed_data.json")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=500, help="Max diseases to scrape")
    parser.add_argument("--abstracts", type=int, default=3, help="Abstracts per disease")
    parser.add_argument("--workers", type=int, default=3, help="Parallel workers (default 3 to respect NCBI rate limit)")
    args = parser.parse_args()
    run_pubmed_scraper(max_diseases=args.max, abstracts_per_disease=args.abstracts, workers=args.workers)

