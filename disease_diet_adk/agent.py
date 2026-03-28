"""
Disease-Specific Diet Plan Generator using Google ADK
Advanced Features: Memory, Parallel Execution, Validation, Monitoring
"""

import logging
import os
from fpdf import FPDF
import serpapi
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import requests
from dotenv import load_dotenv

from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.models.google_llm import Gemini
import litellm
import time
import sys

# Add rag directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "rag"))
try:
    from rag_tool import query_medical_knowledge, query_allergen_risks
    RAG_AVAILABLE = True
except Exception:
    RAG_AVAILABLE = False
    def query_medical_knowledge(disease_name: str, query: str, top_k: int = 5) -> str:
        return "RAG knowledge base not available. Use general medical knowledge."
    def query_allergen_risks(disease_name: str, user_allergens: str) -> str:
        return "RAG knowledge base not available. Use general medical knowledge."

# Load environment variables FIRST so API keys are available
load_dotenv()

# Model Initialization
gemini_15_rpm = Gemini(
    model="gemini-3.1-flash-lite-preview",
)

gemini_5_rpm_A = Gemini(
    model="gemini-3-flash-preview",
)

gemini_5_rpm_B = Gemini(
    model="gemini-3-flash-preview",
)
# ========================
# 1. LOGGING CONFIGURATION
# ========================

# Create outputs directory if it doesn't exist
os.makedirs('outputs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('outputs/workflow_execution.log'),
        logging.StreamHandler()
    ]
)
logging.getLogger('google.adk').setLevel(logging.DEBUG)

# ========================
# 2. TOOL DEFINITIONS
# ========================

def serpapi_search_tool(query: str) -> dict:
    """
    Performs medical/nutrition web search using SerpAPI.
    Args:
        query (str): The search query.
    Returns:
        dict: Search results with status and content.
    """
    try:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            logging.error("SERPAPI_API_KEY environment variable not set.")
            return {
                "status": "error", 
                "message": "SERPAPI_API_KEY not set. Using medical knowledge base."
            }
        
        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "num": 5
        }
        
        logging.info(f"Executing SerpApi search: {query}")
        search_result = serpapi.search(params)
        
        if hasattr(search_result, 'as_dict'):
            results = search_result.as_dict()
        elif isinstance(search_result, dict):
            results = search_result
        else:
            results = {}
        
        organic_results = results.get('organic_results', [])
        
        if not organic_results:
            logging.warning(f"No results found for: {query}")
            return {
                "status": "success", 
                "content": f"No search results for '{query}'. Using medical knowledge base."
            }

        summary_content = ""
        for idx, result in enumerate(organic_results, 1):
            title = result.get('title', 'No Title')
            snippet = result.get('snippet', 'No Snippet')
            link = result.get('link', 'No Link')
            summary_content += f"Result {idx}:\nTitle: {title}\nSnippet: {snippet}\nSource: {link}\n\n"

        logging.info(f"Search successful. Found {len(organic_results)} results.")
        return {"status": "success", "content": summary_content.strip()}

    except Exception as e:
        logging.error(f"SerpApi request failed: {str(e)}", exc_info=True)
        return {
            "status": "error", 
            "message": f"Search failed: {str(e)}. Using medical knowledge base."
        }


def usda_nutrition_tool(food_item: str) -> dict:
    """
    CUSTOM TOOL: Get nutrition info from USDA FoodData Central API.
    Uses your personal API key from .env file.
    Args:
        food_item (str): Name of the food item.
    Returns:
        dict: Nutritional data or error message.
    """
    try:
        logging.info(f"Fetching nutrition data for: {food_item}")
        
        # Get API key from environment
        api_key = os.getenv("USDA_API_KEY")
        if not api_key:
            logging.error("USDA_API_KEY not found in environment variables")
            return {
                "status": "error",
                "message": "USDA_API_KEY not configured. Using nutritional knowledge base.",
                "food": food_item
            }
        
        # USDA FoodData Central Search Endpoint
        url = "https://api.nal.usda.gov/fdc/v1/foods/search"
        
        # Request parameters - prioritize high-quality data sources
        params = {
            "query": food_item,
            "dataType": ["Foundation", "SR Legacy"],  # Best quality nutrient data
            "pageSize": 3,  # Get top 3 matches for better results
            "api_key": api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check if we got results
        foods = data.get("foods", [])
        
        if not foods:
            logging.warning(f"No USDA database results for: {food_item}")
            return {
                "status": "success",
                "message": f"No database entry for '{food_item}'. Using general nutritional knowledge.",
                "food": food_item
            }
        
        # Get the best match (first result)
        food = foods[0]
        food_description = food.get("description", food_item)
        fdc_id = food.get("fdcId", "N/A")
        data_type = food.get("dataType", "Unknown")
        
        # Extract nutrients
        food_nutrients = food.get("foodNutrients", [])
        
        if not food_nutrients:
            logging.warning(f"No nutrient data available for: {food_description}")
            return {
                "status": "success",
                "message": f"Limited data for '{food_description}'. Using nutritional knowledge.",
                "food": food_description
            }
        
        # Priority nutrients mapping (technical name -> user-friendly name)
        nutrient_mapping = {
            "Energy": "Calories",
            "Protein": "Protein",
            "Total lipid (fat)": "Total Fat",
            "Carbohydrate, by difference": "Carbohydrates",
            "Fiber, total dietary": "Dietary Fiber",
            "Sugars, total including NLEA": "Total Sugars",
            "Calcium, Ca": "Calcium",
            "Iron, Fe": "Iron",
            "Potassium, K": "Potassium",
            "Sodium, Na": "Sodium",
            "Vitamin C, total ascorbic acid": "Vitamin C",
            "Vitamin A, RAE": "Vitamin A",
            "Vitamin D (D2 + D3)": "Vitamin D",
            "Vitamin E (alpha-tocopherol)": "Vitamin E",
            "Vitamin K (phylloquinone)": "Vitamin K",
            "Folate, total": "Folate",
            "Vitamin B-12": "Vitamin B12",
            "Fatty acids, total omega-3": "Omega-3",
            "Cholesterol": "Cholesterol"
        }
        
        nutrients = {}
        
        # Extract and format nutrients
        for nutrient_obj in food_nutrients:
            nutrient_name = nutrient_obj.get("nutrientName", "")
            nutrient_value = nutrient_obj.get("value")
            nutrient_unit = nutrient_obj.get("unitName", "")
            
            # Skip if no value
            if nutrient_value is None:
                continue
            
            # Check if this is a priority nutrient
            for full_name, simple_name in nutrient_mapping.items():
                if full_name.lower() in nutrient_name.lower():
                    # Format based on unit and value
                    if nutrient_unit.lower() in ["kcal", "kj"]:
                        formatted_value = f"{round(nutrient_value)}"
                    elif nutrient_value < 0.1:
                        formatted_value = f"{round(nutrient_value, 3)}"
                    elif nutrient_value < 1:
                        formatted_value = f"{round(nutrient_value, 2)}"
                    elif nutrient_value < 10:
                        formatted_value = f"{round(nutrient_value, 1)}"
                    else:
                        formatted_value = f"{round(nutrient_value, 1)}"
                    
                    nutrients[simple_name] = f"{formatted_value} {nutrient_unit}"
                    break
        
        # Get serving size information
        serving_size = food.get("servingSize")
        serving_unit = food.get("servingSizeUnit", "g")
        
        if serving_size:
            serving_info = f"{serving_size} {serving_unit}"
        else:
            serving_info = "100 g (standard reference)"
        
        # Build result
        result = {
            "status": "success",
            "food": food_description,
            "fdc_id": fdc_id, # === MODIFIED SECTION (Bug Fix) ===
            "data_type": data_type,
            "nutrients": nutrients,
            "serving_size": serving_info,
            "nutrient_count": len(nutrients)
        }
        
        logging.info(f"✓ Retrieved {len(nutrients)} nutrients for '{food_description}' (FDC ID: {fdc_id})")
        return result
        
    except requests.exceptions.Timeout:
        logging.error(f"USDA API timeout for {food_item}")
        return {
            "status": "error",
            "message": f"Request timeout for '{food_item}'. Using nutritional knowledge base.",
            "food": food_item
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"USDA API request failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"API connection error for '{food_item}'. Using nutritional knowledge.",
            "food": food_item
        }
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON response from USDA API: {str(e)}")
        return {
            "status": "error",
            "message": f"Invalid API response for '{food_item}'. Using nutritional knowledge.",
            "food": food_item
        }
    except Exception as e:
        logging.error(f"Unexpected error in nutrition lookup: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Lookup failed for '{food_item}'. Using nutritional knowledge base.",
            "food": food_item
        }


def usda_batch_nutrition_tool(food_names: str) -> str:
    """
    Fetches USDA nutrition data for multiple foods in one call.
    Args:
        food_names (str): Comma-separated list of food names,
                          e.g. "salmon, spinach, avocado, blueberries"
    Returns:
        str: JSON list string of nutrition results for all foods.
    """
    
    foods = [f.strip() for f in food_names.split(',') if f.strip()]
    results = []
    for food in foods[:7]:  # cap at 7 items to prevent huge TPM payload
        result = usda_nutrition_tool(food)
        if result.get('status') == 'success' and result.get('nutrients'):
            results.append(result)
    import json as _json
    return _json.dumps(results)


def allergen_validator_tool(food_list: str, allergens: str) -> dict:
    """
    CUSTOM TOOL: Validates that foods don't contain specified allergens.
    Args:
        food_list (str): Comma-separated list of foods.
        allergens (str): Comma-separated list of allergens.
    Returns:
        dict: Validation results.
    """
    try:
        logging.info("Validating foods against allergens")
        
        foods = [f.strip().lower() for f in food_list.split(',')]
        allergen_list = [a.strip().lower() for a in allergens.split(',')]
        
        if "no known allergies" in allergens.lower() or "none" in allergens.lower():
            logging.info("No allergens to check")
            return {
                "status": "success",
                "message": "No allergens specified. All foods approved.",
                "flagged_foods": []
            }
        
        # Common allergen mappings
        allergen_map = {
            "dairy": ["milk", "cheese", "yogurt", "butter", "cream", "whey", "casein"],
            "nuts": ["almond", "walnut", "cashew", "pecan", "pistachio", "hazelnut"],
            "peanuts": ["peanut", "peanut butter"],
            "soy": ["soy", "tofu", "edamame", "tempeh", "soy sauce"],
            "eggs": ["egg", "mayonnaise"],
            "fish": ["salmon", "tuna", "cod", "fish", "seafood"],
            "shellfish": ["shrimp", "crab", "lobster", "clam", "oyster"],
            "wheat": ["wheat", "bread", "pasta", "flour"],
            "gluten": ["wheat", "barley", "rye", "bread", "pasta"]
        }
        
        flagged = []
        for food in foods:
            for allergen in allergen_list:
                allergen_key = allergen.lower()
                related_foods = allergen_map.get(allergen_key, [allergen_key])
                
                for related in related_foods:
                    if related in food:
                        flagged.append(f"{food} (contains {allergen})")
                        logging.warning(f"Flagged: {food} contains {allergen}")
                        break
        
        if flagged:
            return {
                "status": "warning",
                "message": f"Found {len(flagged)} foods with allergens",
                "flagged_foods": flagged
            }
        else:
            return {
                "status": "success",
                "message": "All foods are safe (no allergens detected)",
                "flagged_foods": []
            }
            
    except Exception as e:
        logging.error(f"Allergen validation failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Validation error: {str(e)}",
            "flagged_foods": []
        }


def sanitize_json_string(json_str: str) -> str:
    """
    Remove markdown code blocks and fix common JSON issues.
    """
    # Remove markdown code blocks
    json_str = re.sub(r'^```json\s*', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'^```\s*$', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'```', '', json_str)
    
    # Remove any leading/trailing whitespace
    json_str = json_str.strip()
    
    # Find the first { or [ and last } or ]
    start = -1
    for i, char in enumerate(json_str):
        if char in ['{', '[']:
            start = i
            break
            
    end = -1
    for i in range(len(json_str) - 1, -1, -1):
        if json_str[i] in ['}', ']']:
            end = i
            break
    
    if start != -1 and end != -1:
        json_str = json_str[start:end+1]
    
    return json_str


def pdf_generator_tool(diet_data_json: str) -> dict:
    """
    Generates JSON file and PDF report from diet plan data.
    Args:
        diet_data_json (str): Complete diet plan as JSON string.
    Returns:
        dict: Confirmation with file paths.
    """
    try:
        logging.info("Starting PDF generation")
        
        # Clean the JSON string
        cleaned_json = sanitize_json_string(diet_data_json)
        
        # Save the raw JSON attempt for debugging
        os.makedirs('outputs', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_path = f"outputs/debug_json_{timestamp}.txt"
        
        with open(debug_path, 'w', encoding='utf-8') as f:
            f.write("=== ORIGINAL JSON ===\n")
            f.write(diet_data_json)
            f.write("\n\n=== CLEANED JSON ===\n")
            f.write(cleaned_json)
        
        logging.info(f"Debug JSON saved to: {debug_path}")
        
        # Try to parse JSON
        try:
            data = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            logging.error(f"JSON parse error at line {e.lineno}, col {e.colno}: {e.msg}")
            logging.error(f"Error context: {cleaned_json[max(0, e.pos-100):e.pos+100]}")
            
            # Try to fix common issues
            cleaned_json = cleaned_json.replace('\n', ' ')  # Remove newlines in strings
            cleaned_json = re.sub(r',\s*}', '}', cleaned_json)  # Remove trailing commas
            cleaned_json = re.sub(r',\s*]', ']', cleaned_json)  # Remove trailing commas in arrays
            
            # Try parsing again
            data = json.loads(cleaned_json)
        
        # Validate required fields
        required_fields = ['disease', 'allergies']
        for field in required_fields:
            if field not in data:
                data[field] = 'Not specified'
        
        if 'generated_date' not in data:
            data['generated_date'] = datetime.now().strftime("%Y-%m-%d")
        
        # Save validated JSON
        json_path = f"outputs/diet_data_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info(f"JSON saved: {json_path}")
        
        # =========================================================
        # === THIS IS THE FIX: Define pdf_path before using it ===
        pdf_path = f"outputs/diet_plan_{timestamp}.pdf"
        # =========================================================
        
        # Generate PDF
        pdf = FPDF()
        pdf.set_font("Helvetica", '', 11)
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        def safe_text(text):
            """Replace Unicode characters for Helvetica compatibility."""
            if isinstance(text, str):
                text = text.replace('•', '-').replace('●', '-').replace('◆', '-')
                text = text.replace('\u2022', '-').replace('\u2013', '-').replace('\u2014', '-')
                text = text.encode('latin-1', 'replace').decode('latin-1')
            return str(text)
        
        # Title
        pdf.set_font("Helvetica", 'B', 24)
        pdf.cell(0, 10, "Personalized Diet Plan", ln=True, align='C')
        pdf.ln(10)
        
        # Basic Info
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 8, safe_text(f"Disease/Condition: {data.get('disease', 'N/A')}"), ln=True)
        pdf.cell(0, 8, safe_text(f"Allergies: {data.get('allergies', 'N/A')}"), ln=True)
        pdf.cell(0, 8, safe_text(f"Generated: {data.get('generated_date', 'N/A')}"), ln=True)
        pdf.ln(10)
        
        # Foods You Can Eat
        if 'foods_you_can_eat' in data and data['foods_you_can_eat']:
            pdf.set_font("Helvetica", 'B', 16)
            pdf.cell(0, 10, "Foods You Can Eat", ln=True)
            pdf.set_font("Helvetica", '', 11)
            
            for category, items in data['foods_you_can_eat'].items():
                pdf.set_font("Helvetica", 'B', 14)
                pdf.cell(0, 8, safe_text(category.replace('_', ' ').title()), ln=True)
                pdf.set_font("Helvetica", '', 11)
                
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            name = safe_text(item.get('name', 'N/A'))
                            benefits = safe_text(item.get('benefits', 'N/A'))
                            pdf.multi_cell(0, 6, f"- {name}", ln=True)
                            pdf.multi_cell(0, 5, f"  Benefits: {benefits}", ln=True)
                            pdf.ln(2)
                        elif isinstance(item, str):
                            pdf.multi_cell(0, 6, safe_text(f"- {item}"), ln=True)
                pdf.ln(5)
        
        # Foods to Avoid
        if 'foods_to_avoid' in data and data['foods_to_avoid']:
            pdf.set_font("Helvetica", 'B', 16)
            pdf.cell(0, 10, "Foods to Avoid", ln=True)
            pdf.set_font("Helvetica", '', 11)
            for item in data['foods_to_avoid']:
                if isinstance(item, dict):
                    name = safe_text(item.get('name', 'N/A'))
                    reason = safe_text(item.get('reason', 'N/A'))
                    pdf.multi_cell(0, 6, f"- {name}", ln=True)
                    pdf.multi_cell(0, 5, f"  Reason: {reason}", ln=True)
                    pdf.ln(2)
                elif isinstance(item, str):
                    pdf.multi_cell(0, 6, safe_text(f"- {item}"), ln=True)
        
        # Meal Ideas
        if 'meal_ideas' in data and data['meal_ideas']:
            pdf.set_font("Helvetica", 'B', 16)
            pdf.cell(0, 10, "Meal Ideas", ln=True)
            pdf.set_font("Helvetica", '', 11)
            for meal in data['meal_ideas']:
                if isinstance(meal, dict):
                    pdf.set_font("Helvetica", 'B', 12)
                    pdf.cell(0, 8, safe_text(meal.get('name', 'Meal')), ln=True)
                    pdf.set_font("Helvetica", '', 11)
                    
                    ingredients = safe_text(meal.get('ingredients', 'N/A'))
                    benefits = safe_text(meal.get('benefits', 'N/A'))
                    
                    pdf.multi_cell(0, 5, f"Ingredients: {ingredients}", ln=True)
                    pdf.multi_cell(0, 5, f"Benefits: {benefits}", ln=True)
                    pdf.ln(3)

        # Nutritional Data Highlights
        if 'nutritional_data' in data and data['nutritional_data']:
            pdf.set_font("Helvetica", 'B', 16)
            pdf.cell(0, 10, "Nutritional Data Highlights", ln=True)
            
            for item in data['nutritional_data']:
                if isinstance(item, dict) and item.get('status') == 'success':
                    food_name = safe_text(item.get('food', 'Food Item'))
                    serving_size = safe_text(item.get('serving_size', 'N/A'))
                    nutrients = item.get('nutrients', {})
                    fdc_id = safe_text(item.get('fdc_id', 'N/A'))
                    
                    pdf.set_font("Helvetica", 'B', 12)
                    pdf.cell(0, 8, food_name, ln=True)
                    
                    pdf.set_font("Helvetica", 'I', 11)
                    pdf.cell(0, 6, safe_text(f"  (FDC ID: {fdc_id} / Serving: {serving_size})"), ln=True)
                    
                    pdf.set_font("Helvetica", '', 11)
                    if not nutrients:
                        pdf.multi_cell(0, 5, "    - No detailed nutrient data available.", ln=True)
                    else:
                        for key, value in nutrients.items():
                            pdf.multi_cell(0, 5, safe_text(f"    - {key}: {value}"), ln=True)
                    pdf.ln(3)
        
        # Medical Disclaimer
        pdf.set_font("Helvetica", 'B', 14)
        pdf.cell(0, 10, "Medical Disclaimer", ln=True)
        pdf.set_font("Helvetica", '', 11)
        disclaimer = data.get('medical_disclaimer', 'Consult healthcare providers before dietary changes.')
        pdf.multi_cell(0, 6, safe_text(disclaimer), ln=True)
        
        pdf.output(pdf_path) # Now this line will work
        logging.info(f"PDF saved: {pdf_path}")

        return {
            "status": "success",
            "message": f"Successfully generated:\n- JSON Format: http://localhost:8001/{json_path}\n- PDF Report: http://localhost:8001/{pdf_path}",
            "json_path": f"http://localhost:8001/{json_path}",
            "pdf_path": f"http://localhost:8001/{pdf_path}"
        }
        
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON at line {e.lineno}, col {e.colno}: {e.msg}"
        logging.error(error_msg, exc_info=True)
        return {
            "status": "error", 
            "message": f"JSON parsing failed: {error_msg}\nCheck debug file: {debug_path}"
        }
    except Exception as e:
        logging.error(f"PDF generation failed: {e}", exc_info=True)
        return {"status": "error", "message": f"File generation failed: {str(e)}"}


# ========================
# 3. AGENT DEFINITIONS
# ========================

# AGENT 1: Input Validator
input_validator = LlmAgent(
    name="input_validator",
    model=gemini_15_rpm,
    instruction="""You are an Input Validator for medical diet planning.

The user will provide:
- Disease/condition
- Allergies

Your task:
1. Validate the disease name is a real medical condition
2. Standardize the disease name
3. Parse and standardize allergens
4. Identify any safety concerns

Output format:
---
DISEASE: [standardized disease name]
ALLERGIES: [standardized allergen list or "No known allergies"]
SAFETY_NOTES: [any warnings or notes]
---

Be thorough and professional.""",
    output_key="validated_input"
)

# AGENT 2: Medical Researcher (uses RAG knowledge base + web search)
medical_researcher = LlmAgent(
    name="medical_researcher",
    model=gemini_5_rpm_A,
    instruction="""You are a Medical Researcher specializing in nutrition.

Validated Input:
{validated_input}

Extract the disease name and allergens from above.

STEP 1 — Query Medical Knowledge Base first:
  Call query_medical_knowledge with the disease name and query: "dietary recommendations foods to eat and avoid allergens"
  This returns peer-reviewed, curated medical information about this disease.

STEP 2 — Web Search for additional info:
  Use serpapi_search_tool to search: "[disease] diet recommendations latest research"

Compile findings on:
- Beneficial nutrients (prioritize RAG results)
- Recommended foods (combining RAG + web search)
- Foods to limit/avoid (prioritize RAG results for allergens)
- Why these dietary changes help

Provide comprehensive research summary combining both sources.""",
    tools=[query_medical_knowledge, serpapi_search_tool],
    output_key="research_findings"
)

# AGENT 3: Nutritionist (creates food recommendations)
nutritionist = LlmAgent(
    name="nutritionist",
    model=gemini_15_rpm,
    instruction="""You are a Clinical Nutritionist.

Validated Input:
{validated_input}

Research Findings:
{research_findings}

Create comprehensive food recommendations in categories:
- Proteins (5-7 items with benefits)
- Vegetables (5-7 items with benefits)
- Fruits (5-7 items with benefits)
- Grains (3-5 items with benefits)
- Healthy Fats (3-5 items with benefits)
- Dairy/Alternatives (3-5 items with benefits)
- Beverages (3-5 items with benefits)

For EACH food:
1. Why it benefits this disease
2. Key nutrients
3. How it helps symptoms

Also list FOODS TO AVOID with reasons.

CRITICAL: Exclude ALL allergens mentioned in validated input!

Format as:
PROTEINS:
- Food 1: [benefits and nutrients]
- Food 2: [benefits and nutrients]

VEGETABLES:
...

FOODS TO AVOID:
- Food 1: [reason]
...""",
    output_key="food_recommendations"
)

# PARALLEL AGENTS: Nutrition Data + Recipe Ideas

# === MODIFIED SECTION: nutrition_analyst Instruction ===
nutrition_analyst = LlmAgent(
    name="nutrition_data_analyst",
    model=gemini_15_rpm,
    instruction="""You are a Nutrition Data Analyst with access to the USDA nutrition database.

Food Recommendations:
{food_recommendations}

Task: Call usda_batch_nutrition_tool ONCE with a comma-separated list of the TOP 10-12 most important simple food names from the recommendations above.

Rules:
- Use simple food names only (e.g. "salmon, spinach, avocado, blueberries, lentils, chicken, oats, sweet potato, quinoa, chia seeds")
- Make exactly ONE tool call with all food names together
- After the tool returns, output its result directly as your final response

CRITICAL: Your final output must be ONLY the JSON list returned by the tool. No extra text.""",
    tools=[usda_batch_nutrition_tool],
    output_key="nutrition_data"
)

recipe_curator = LlmAgent(
    name="recipe_curator",
    model=gemini_5_rpm_B,
    instruction="""You are a Recipe Curator.

Food Recommendations:
{food_recommendations}

Validated Input:
{validated_input}

Create 7 simple meal/snack ideas using recommended foods.

For each:
- Meal name
- Main ingredients (exclude allergens!)
- Why it's good for this condition
- Simple preparation (2-3 sentences)

Format as:
MEAL 1:
Name: [name]
Ingredients: [list]
Benefits: [why good]
Preparation: [how to make]

MEAL 2:
...""",
    output_key="meal_ideas"
)

# Sequential fallback — Mistral rate limits are unavoidable in parallel
parallel_nutrition_phase = ParallelAgent(
    name="parallel_nutrition_phase",
    sub_agents=[nutrition_analyst, recipe_curator]
)

# AGENT 4: Allergen Validator (HALLUCINATION MITIGATION)
allergen_validator = LlmAgent(
    name="allergen_safety_validator",
    model=gemini_15_rpm,
    instruction="""You are an Allergen Safety Validator - CRITICAL SAFETY ROLE.

Allergens to avoid (from user input):
{validated_input}

Nutrition Data (Foods being used):
{nutrition_data}

Task: 
1. Extract the allergen list from the validated_input above.
2. Extract the food names from the nutrition_data JSON above (look for the "food" keys).
3. Call allergen_validator_tool ONCE with:
- food_list: A comma-separated string of the food names you extracted.
- allergens: The allergens you extracted.

CRITICAL: Make exactly ONE allergen_validator_tool call. Do NOT call it multiple times.

Optionally, also call query_allergen_risks with the disease name and user allergens to check if the disease has additional known food triggers not declared by the user.

After the tool responds, output:
VALIDATION RESULTS:
Status: [SAFE/WARNING/UNSAFE]
Flagged Items: [any flagged foods]
Safety Notes: [any concerns]""",
    tools=[allergen_validator_tool, query_allergen_risks],
    output_key="allergen_validation"
)

# === MODIFIED SECTION: content_aggregator Instruction ===
content_aggregator = LlmAgent(
    name="content_aggregator",
    model=gemini_5_rpm_A,
    instruction="""You are a Content Aggregator creating structured medical data.

Inputs:
1. {validated_input}
2. {food_recommendations}
3. {nutrition_data}  <- This is a string containing a JSON list, e.g., '[{"food": "Salmon", ...}]'
4. {meal_ideas}
5. {allergen_validation}

Task: Create ONE valid JSON object with all data.

CRITICAL: The {nutrition_data} input is a JSON list as a string. You must embed it DIRECTLY as the value for the 'nutritional_data' key. Do NOT wrap it in quotes.

CRITICAL JSON RULES:
1. Output ONLY valid JSON - no markdown, no explanations, no text before or after
2. ALL string values must have properly escaped quotes: use \\" for quotes inside strings
3. Use plain text only - NO special characters, bullets, or markdown (*, **, _, #, `)
4. Use \\n for line breaks inside JSON strings
5. NO trailing commas before } or ]
6. All property names must be in double quotes
7. String values must be in double quotes
8. Test your JSON is valid before outputting

JSON Structure:
{
  "disease": "disease name here",
  "allergies": "allergen list or none",
  "validation_status": "status from allergen validation",
  "foods_you_can_eat": {
    "proteins": [
      {
        "name": "food name",
        "benefits": "benefits description",
        "key_nutrients": "nutrients list"
      }
    ],
    "vegetables": [],
    "fruits": [],
    "grains": [],
    "healthy_fats": [],
    "dairy_alternatives": [],
    "beverages": []
  },
  "foods_to_avoid": [
    {
      "name": "food name",
      "reason": "reason to avoid"
    }
  ],
  "nutritional_data": {nutrition_data},
  "meal_ideas": [
    {
      "name": "meal name",
      "ingredients": "ingredient list",
      "benefits": "health benefits",
      "preparation": "how to prepare"
    }
  ],
  "general_guidelines": [
    "guideline one",
    "guideline two",
    "guideline three"
  ],
  "allergen_check": "validation summary",
  "medical_disclaimer": "This is educational information only. Consult healthcare providers before making dietary changes."
}

REMEMBER: 
- The value for "nutritional_data" must be the raw JSON list from {nutrition_data}, NOT a string.
- NO text outside the JSON
```python
- NO markdown formatting
- Properly escape all special characters
- Validate JSON structure before output

OUTPUT ONLY THE VALID JSON OBJECT:""",
    output_key="final_diet_json"
)

# AGENT 7: File Generator
file_generator = LlmAgent(
    name="file_generator",
    model=gemini_15_rpm,
    instruction="""You are a File Generator.

Validated JSON:
{final_diet_json}

Task: Call pdf_generator_tool with the JSON string above.

Do not modify the JSON. Just call the tool and report the results.""",
    tools=[pdf_generator_tool],
    output_key="file_output"
)

# ========================
# 4. ROOT WORKFLOW
# ========================

root_agent = SequentialAgent(
    name="disease_diet_plan_workflow",
    sub_agents=[
        input_validator,
        medical_researcher,
        nutritionist,
        parallel_nutrition_phase,
        allergen_validator,
        content_aggregator,
        file_generator
    ]
)

# ========================
# 5. MAIN EXECUTION
# ========================

if __name__ == "__main__":
    try:
        # Test USDA API connection first
        print("\n" + "="*70)
        print("TESTING API CONNECTIONS")
        print("="*70)
        
        print("\n[1/2] Testing USDA API...")
        usda_key = os.getenv("USDA_API_KEY")
        if usda_key:
            print(f"✓ USDA_API_KEY found: {usda_key[:10]}...")
            test_result = usda_nutrition_tool("salmon")
            if test_result.get('status') == 'success':
                if test_result.get('nutrients'):
                    print(f"✓ USDA API working - Found {test_result.get('nutrient_count', 0)} nutrients for salmon")
                else:
                    print(f"⚠ USDA API connected but limited data")
            else:
                print(f"✗ USDA API error: {test_result.get('message')}")
        else:
            print("✗ USDA_API_KEY not found in .env file")
        
        print("\n[2/2] Testing SerpAPI...")
        serpapi_key = os.getenv("SERPAPI_API_KEY")
        if serpapi_key:
            print(f"✓ SERPAPI_API_KEY found: {serpapi_key[:10]}...")
        else:
            print("⚠ SERPAPI_API_KEY not found (will use medical knowledge base)")
        
        print("="*70 + "\n")
        
        # Main workflow
        print("="*70)
        print("DISEASE-SPECIFIC DIET PLAN GENERATOR (Google ADK)")
        print("Advanced Features: Memory, Parallel, Validation, Monitoring")
        print("="*70 + "\n")
        
        # Get user input
        disease = input("Enter disease/condition: ").strip()
        if not disease:
            print("Error: Disease required!")
            exit(1)
        
        allergies = input("Enter allergies (or 'none'): ").strip()
        if not allergies or allergies.lower() == 'none':
            allergies = "No known allergies"
        
        user_input = f"Disease: {disease}\nAllergies: {allergies}"
        
        print(f"\n{'='*70}")
        print(f"Generating personalized diet plan for: {disease}")
        print(f"Allergies: {allergies}")
        print(f"{'='*70}\n")
        print("Starting workflow execution...")
        print("This may take 2-3 minutes...\n")
        
        logging.info("="*70)
        logging.info("WORKFLOW STARTED")
        logging.info(f"Disease: {disease}, Allergies: {allergies}")
        logging.info("="*70)
        
        # Execute workflow
        result = root_agent.run_live(user_input)
        
        logging.info("="*70)
        logging.info("WORKFLOW COMPLETED SUCCESSFULLY")
        logging.info("="*70)
        
        print("\n" + "="*70)
        print("✅ DIET PLAN GENERATION COMPLETE!")
        print("="*70)
        print(f"\n{result}\n")
        print("="*70)
        print("📁 OUTPUT FILES GENERATED:")
        print("="*70)
        print("Check the 'outputs' folder for:")
        print("  1. 📄 diet_data_*.json       - Structured diet data")
        print("  2. 📋 diet_plan_*.pdf        - Formatted PDF report")
        print("  3. 📝 workflow_execution.log - Execution details")
        print("  4. 🐛 debug_json_*.txt       - JSON debugging info")
        print("="*70 + "\n")
        
        # Show summary
        try:
            import glob
            latest_json = max(glob.glob('outputs/diet_data_*.json'), key=os.path.getctime)
            with open(latest_json, 'r') as f:
                summary_data = json.load(f)
            
            print("📊 SUMMARY:")
            print(f"  - Disease: {summary_data.get('disease', 'N/A')}")
            print(f"  - Validation Status: {summary_data.get('validation_status', 'N/A')}")
            
            if 'foods_you_can_eat' in summary_data:
                total_foods = sum(len(items) for items in summary_data['foods_you_can_eat'].values() if isinstance(items, list))
                print(f"  - Recommended Foods: {total_foods}")
            
            if 'meal_ideas' in summary_data:
                print(f"  - Meal Ideas: {len(summary_data['meal_ideas'])}")
            
            if 'nutritional_data' in summary_data:
                print(f"  - Nutritional Data Points: {len(summary_data['nutritional_data'])}")
                
            print("="*70 + "\n")
        except:
            pass
        
    except KeyboardInterrupt:
        print("\n\n⚠ Workflow interrupted by user")
        logging.warning("Workflow interrupted by user")
    except Exception as e:
        logging.error(f"Workflow failed: {e}", exc_info=True)
        print(f"\n❌ ERROR: {str(e)}")
        print("\n📋 Troubleshooting:")
        print("  1. Check outputs/workflow_execution.log for details")
        print("  2. Verify API keys in .env file")
        print("  3. Check outputs/debug_json_*.txt for JSON issues")
        print("="*70 + "\n")
        raise