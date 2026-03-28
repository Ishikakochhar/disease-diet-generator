"""
Disease-Specific Diet Plan Generator using CrewAI
Generates: What you CAN eat, Benefits, and saves JSON output
"""

import os
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
import requests
import json
from fpdf import FPDF
from datetime import datetime

# ========================
# CONFIGURATION
# ========================

# Set your API keys here
os.environ["GOOGLE_API_KEY"] = "YOUR_GOOGLE_API_KEY_HERE"
os.environ["SERPAPI_API_KEY"] = "YOUR_SERPAPI_API_KEY_HERE"  # Free tier available

# Initialize Gemini LLM
llm = LLM(
    model="gemini/gemini-2.5-flash",
    temperature=0.7
)

# ========================
# TOOLS
# ========================

@tool("Web Search Tool")
def web_search_tool(query: str) -> str:
    """Search the web using SerpAPI"""
    try:
        api_key = os.environ.get("SERPAPI_API_KEY")
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": api_key,
            "engine": "google",
            "num": 3
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        results = []
        if "organic_results" in data:
            for result in data["organic_results"][:3]:
                results.append({
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", "")
                })
        
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Search info: Using medical knowledge base for {query}"

@tool("Nutrition Tool")
def nutrition_tool(food_item: str) -> str:
    """Get nutrition info from USDA"""
    try:
        url = "https://api.nal.usda.gov/fdc/v1/foods/search"
        params = {
            "query": food_item,
            "pageSize": 1,
            "api_key": "DEMO_KEY"
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("foods"):
            food = data["foods"][0]
            nutrients = {}
            for nutrient in food.get("foodNutrients", [])[:8]:
                nutrients[nutrient.get("nutrientName")] = str(nutrient.get("value", 0)) + " " + nutrient.get("unitName", "")
            
            return json.dumps({"food": food.get("description"), "nutrients": nutrients}, indent=2)
        
        return f"Nutrition data for {food_item}: Standard nutritional values"
    except Exception as e:
        return f"Nutrition info for {food_item}: Using standard values"

@tool("JSON Saver")
def save_json(data: str) -> str:
    """Save data as JSON file"""
    try:
        os.makedirs('outputs', exist_ok=True)
        filename = f"outputs/diet_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Try to parse if it's a JSON string
        try:
            json_data = json.loads(data)
        except:
            json_data = {"raw_data": data}
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        return f"JSON saved: {filename}"
    except Exception as e:
        return f"JSON save note: {str(e)}"

@tool("PDF Generator")
def pdf_generator(content: str) -> str:
    """Generate PDF report"""
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Diet Recommendations Report", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.ln(5)
        
        # --- FIX for Markdown ---
        
        # Process the content line by line
        lines = content.split('\n')
        
        for line in lines:
            # Clean up the line
            line_stripped = line.strip()
            
            try:
                if line_stripped.startswith('## '):
                    # Handle '##' as a Sub-Header
                    pdf.set_font("Arial", "B", 14)
                    content = line_stripped[3:].encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 7, content)
                    pdf.ln(2)
                elif line_stripped.startswith('### '):
                    # Handle '###' as a smaller Sub-Header
                    pdf.set_font("Arial", "B", 12)
                    content = line_stripped[4:].encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 6, content)
                    pdf.ln(1)
                elif line_stripped.startswith('* '):
                    # Handle '*' as a bullet point
                    pdf.set_font("Arial", "", 10)
                    
                    # Clean out other markdown like **bold** or *italic*
                    content = line_stripped[2:].replace('**', '').replace('*', '')
                    content = f"\x95 {content}".encode('latin-1', 'replace').decode('latin-1')
                    
                    pdf.cell(5) # Indent
                    pdf.multi_cell(0, 5, content)
                elif line_stripped: 
                    # Handle a regular paragraph line
                    pdf.set_font("Arial", "", 10)
                    
                    # Clean out any stray markdown
                    content = line_stripped.replace('**', '').replace('*', '').encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 5, content)
                else:
                    # This is an empty line, add a small space
                    pdf.ln(3) 
            
            except Exception as e:
                print(f"PDF line error: {e} | Line: {line}")
                pdf.multi_cell(0, 5, "[... error rendering line ...]")
            
            # Reset font to default after each line
            pdf.set_font("Arial", "", 10)
            
        # --- END FIX ---
        
        # Save
        os.makedirs('outputs', exist_ok=True)
        filename = f"outputs/diet_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf.output(filename)
        
        return f"PDF created: {filename}"
    except Exception as e:
        return f"PDF generation error: {str(e)}"

# ========================
# AGENTS
# ========================

agent1 = Agent(
    role="Input Validator",
    goal="Validate disease and allergy information",
    backstory="You validate medical inputs ensuring accuracy and safety.",
    llm=llm,
    verbose=True
)

agent2 = Agent(
    role="Medical Researcher",
    goal="Research disease-diet connections",
    backstory="You research how nutrition affects diseases using scientific sources.",
    tools=[web_search_tool],
    llm=llm,
    verbose=True
)

agent3 = Agent(
    role="Nutritionist",
    goal="Create comprehensive food recommendations with benefits",
    backstory="You identify foods that can be eaten for specific conditions and explain their health benefits.",
    llm=llm,
    verbose=True
)

agent4 = Agent(
    role="Nutrition Data Analyst",
    goal="Get detailed nutritional information for recommended foods",
    backstory="You look up detailed nutritional data for foods to provide complete information.",
    tools=[nutrition_tool],
    llm=llm,
    verbose=True
)

agent5 = Agent(
    role="Recipe Curator",
    goal="Provide sample recipes and meal ideas",
    backstory="You create simple, practical meal ideas and recipes using recommended foods.",
    llm=llm,
    verbose=True
)

agent6 = Agent(
    role="Report Compiler & Data Manager",
    goal="Compile final report, save JSON data, and generate PDF",
    backstory="You organize all information into structured formats (JSON and PDF).",
    tools=[save_json, pdf_generator],
    llm=llm,
    verbose=True
)

# ========================
# MAIN FUNCTION
# ========================

def main():
    print("\n" + "="*70)
    print("DISEASE-SPECIFIC DIET RECOMMENDATIONS GENERATOR")
    print("What You CAN Eat + Benefits + JSON Output")
    print("="*70 + "\n")
    
    # Get input
    disease = input("Enter disease/condition: ").strip()
    if not disease:
        print("Error: Disease required!")
        return
    
    allergies = input("Enter allergies (or 'none'): ").strip()
    if not allergies or allergies.lower() == 'none':
        allergies = "No known allergies"
    
    print(f"\nGenerating recommendations for: {disease}")
    print(f"Allergies: {allergies}\n")
    
    # Create tasks
    task1 = Task(
        description=f"""Validate this input:
Disease: {disease}
Allergies: {allergies}

Provide a clean, standardized summary.""",
        agent=agent1,
        expected_output="Validated disease and allergy information"
    )
    
    task2 = Task(
        description="""Research how diet affects this disease:
1. What nutrients are beneficial
2. What foods help manage the condition
3. What foods should be limited or avoided
4. Why these dietary changes help

Use web search to find current medical information.""",
        agent=agent2,
        expected_output="Research summary on disease-nutrition relationship",
        context=[task1]
    )
    
    task3 = Task(
        description="""Create a comprehensive list of FOODS YOU CAN EAT with their benefits.

Format as categories:
- Proteins (list foods with benefits for the disease)
- Vegetables (list foods with benefits)
- Fruits (list foods with benefits)
- Grains (list foods with benefits)
- Healthy Fats (list foods with benefits)
- Dairy/Alternatives (list foods with benefits)
- Beverages (list drinks with benefits)

For EACH food item, explain:
1. Why it's beneficial for this disease
2. Key nutrients it provides
3. How it helps manage symptoms

Also create a separate "FOODS TO AVOID" list with reasons.

IMPORTANT: Exclude all allergens the patient has!""",
        agent=agent3,
        expected_output="Categorized list of foods with detailed benefits and foods to avoid",
        context=[task1, task2]
    )
    
    task4 = Task(
        description="""Use the nutrition tool to get detailed nutritional data for the TOP 10 most important recommended foods.

Provide:
- Food name
- Calories per serving
- Protein, carbs, fats
- Key vitamins and minerals
- Serving size recommendations""",
        agent=agent4,
        expected_output="Detailed nutritional data for key foods",
        async_execution=True,
        context=[task3]
    )
    
    task5 = Task(
        description="""Create 5-7 simple meal/snack ideas using the recommended foods.

For each idea provide:
- Meal name
- Main ingredients
- Why it's good for this condition
- Simple preparation notes (2-3 sentences)

Keep it practical and easy to prepare.""",
        agent=agent5,
        expected_output="Simple meal ideas with preparation notes",
        async_execution=True,
        context=[task3]
    )
    
    task6 = Task(
        description=f"""Compile the final report in this EXACT JSON structure:

{{
  "disease": "{disease}",
  "allergies": "{allergies}",
  "generated_date": "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
  "foods_you_can_eat": {{
    "proteins": [
      {{"name": "food name", "benefits": "why it helps", "key_nutrients": "nutrients"}}
    ],
    "vegetables": [...],
    "fruits": [...],
    "grains": [...],
    "healthy_fats": [...],
    "dairy_alternatives": [...],
    "beverages": [...]
  }},
  "foods_to_avoid": [
    {{"name": "food name", "reason": "why avoid"}}
  ],
  "nutritional_data": [
    {{"food": "name", "nutrition": "data from nutrition tool"}}
  ],
  "meal_ideas": [
    {{"name": "meal name", "ingredients": "list", "benefits": "why good", "preparation": "how to make"}}
  ],
  "general_guidelines": [
    "guideline 1",
    "guideline 2"
  ],
  "medical_disclaimer": "This is educational information only. Consult healthcare providers before making dietary changes."
}}

Steps:
1. Structure ALL previous information into this JSON format
2. Use save_json tool to save this JSON data
3. Create a readable PDF report with all the information
4. Use pdf_generator tool to save the PDF

Return confirmation of both files created.""",
        agent=agent6,
        expected_output="JSON file and PDF file created with all diet recommendations",
        context=[task1, task2, task3, task4, task5]
    )
    
    # Create crew
    crew = Crew(
        agents=[agent1, agent2, agent3, agent4, agent5, agent6],
        tasks=[task1, task2, task3, task4, task5, task6],
        process=Process.sequential,
        verbose=True
    )
    
    # Run
    print("\n" + "="*70)
    print("Starting crew execution...")
    print("="*70 + "\n")
    
    result = crew.kickoff()
    
    print("\n" + "="*70)
    print("✅ COMPLETED!")
    print("="*70)
    print(f"\n{result}\n")
    print("Check the 'outputs' folder for:")
    print("  - JSON file (diet_data_*.json)")
    print("  - PDF file (diet_plan_*.pdf)")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()