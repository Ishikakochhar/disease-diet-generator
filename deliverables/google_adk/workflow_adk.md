┌─────────────────────────────────────────────────────────────────────────────┐
│                   DISEASE-SPECIFIC DIET PLAN GENERATOR WORKFLOW             │
│                              (Google ADK Implementation)                    │
└─────────────────────────────────────────────────────────────────────────────┘

                                    ┌─────────────┐
                                    │  USER INPUT │
                                    │ Disease +   │
                                    │ Allergies   │
                                    └──────┬──────┘
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ TASK 1: INPUT VALIDATION (Sequential - First)                                │
├──────────────────────────────────────────────────────────────────────────────┤
│  Agent: Input Validator                                                      │
│  Model: gemini-2.5-flash                                                     │
│  Tools: None                                                                 │
│                                                                              │
│  Actions:                                                                    │
│  1. Validate disease name is real medical condition                          │
│  2. Standardize disease name                                                 │
│  3. Parse and standardize allergens                                          │
│  4. Identify safety concerns                                                 │
│                                                                              │
│  Output: validated_input                                                     │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ TASK 2: MEDICAL RESEARCH (Sequential)                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│  Agent: Medical Researcher                                                   │
│  Model: gemini-2.5-flash                                                     │
│  Tools: • serpapi_search_tool                                                │
│                                                                              │
│  Inputs:                                                                     │
│  • validated_input                                                           │
│                                                                              │
│  Actions:                                                                    │
│  1. Search: "[disease] diet recommendations"                                 │
│  2. Search: "[disease] foods to eat"                                         │
│  3. Search: "[disease] nutritional management"                               │
│  4. Compile beneficial nutrients                                             │
│  5. Identify recommended foods and foods to avoid                            │
│                                                                              │
│  Output: research_findings                                                   │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ TASK 3: FOOD RECOMMENDATIONS (Sequential)                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│  Agent: Nutritionist                                                         │
│  Model: gemini-2.5-flash                                                     │
│  Tools: None                                                                 │
│                                                                              │
│  Inputs:                                                                     │
│  • validated_input                                                           │
│  • research_findings                                                         │
│                                                                              │
│  Actions:                                                                    │
│  1. Create food recommendations in 7 categories:                             │
│     - Proteins (5-7 items)                                                   │
│     - Vegetables (5-7 items)                                                 │
│     - Fruits (5-7 items)                                                     │
│     - Grains (3-5 items)                                                     │
│     - Healthy Fats (3-5 items)                                               │
│     - Dairy/Alternatives (3-5 items)                                         │
│     - Beverages (3-5 items)                                                  │
│  2. Include benefits and key nutrients for each                              │
│  3. List foods to avoid with reasons                                         │
│  4. Exclude all allergens                                                    │
│                                                                              │
│  Output: food_recommendations                                                │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ PARALLEL EXECUTION PHASE                                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────┐   ┌─────────────────────────────────┐   │
│  │ TASK 4A: NUTRITION DATA         │   │ TASK 4B: RECIPE CURATION        │   │
│  ├─────────────────────────────────┤   ├─────────────────────────────────┤   │
│  │ Agent: Nutrition Data Analyst   │   │ Agent: Recipe Curator           │   │
│  │ Model: gemini-2.5-flash         │   │ Model: gemini-2.0-flash         │   │
│  │ Tools: • usda_nutrition_tool    │   │ Tools: None                     │   │
│  │                                 │   │                                 │   │
│  │ Actions:                        │   │ Actions:                        │   │
│  │ 1. Extract top 10-12 foods      │   │ 1. Create 7 meal/snack ideas    │   │
│  │ 2. Query USDA API for each      │   │ 2. Use recommended foods        │   │
│  │ 3. Retrieve detailed nutrients: │   │ 3. Exclude allergens            │   │
│  │    - Calories, Protein, Fats    │   │ 4. Include benefits             │   │
│  │    - Vitamins, Minerals         │   │ 5. Add preparation steps        │   │
│  │    - Omega-3, Fiber, etc.       │   │                                 │   │
│  │ 4. Get FDC ID and serving size  │   │                                 │   │
│  │ 5. Compile as JSON list         │   │                                 │   │
│  │                                 │   │                                 │   │
│  │ Output: nutrition_data          │   │ Output: meal_ideas              │   │
│  └─────────────────────────────────┘   └─────────────────────────────────┘   │
│                                 │                   │                        │
└─────────────────────────────────┼───────────────────┼────────────────────────┘
                                  │                   │
                                  └─────────┬─────────┘
                                            ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ TASK 5: ALLERGEN SAFETY VALIDATION (Sequential)                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  Agent: Allergen Safety Validator                                            │
│  Model: gemini-2.5-flash-lite                                                │
│  Tools: • allergen_validator_tool (Custom)                                   │
│                                                                              │
│  Inputs:                                                                     │
│  • validated_input                                                           │
│  • food_recommendations                                                      │
│  • meal_ideas                                                                │
│                                                                              │
│  Actions:                                                                    │
│  1. Extract all foods from recommendations and meals                         │
│  2. Extract allergens from validated input                                   │
│  3. Cross-reference with allergen database                                   │
│  4. Flag any allergen violations                                             │
│  5. Provide safety status (SAFE/WARNING/UNSAFE)                              │
│                                                                              │
│  Output: allergen_validation                                                 │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ TASK 6: CONTENT AGGREGATION & JSON GENERATION (Sequential)                   │
├──────────────────────────────────────────────────────────────────────────────┤
│  Agent: Content Aggregator                                                   │
│  Model: gemini-2.5-flash                                                     │
│  Tools: None                                                                 │
│                                                                              │
│  Inputs:                                                                     │
│  • validated_input                                                           │
│  • research_findings                                                         │
│  • food_recommendations                                                      │
│  • nutrition_data                                                            │
│  • meal_ideas                                                                │
│  • allergen_validation                                                       │
│                                                                              │
│  Actions:                                                                    │
│  1. Parse all inputs                                                         │
│  2. Structure data into JSON format                                          │
│  3. Organize foods by category                                               │
│  4. Embed nutritional data                                                   │
│  5. Include meal ideas with details                                          │
│  6. Add general guidelines                                                   │
│  7. Include medical disclaimer                                               │
│                                                                              │
│  Output: final_diet_json                                                     │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ TASK 7: JSON VALIDATION & FIXING (Sequential)                                │
├──────────────────────────────────────────────────────────────────────────────┤
│  Agent: JSON Validator                                                       │
│  Model: gemini-2.5-flash                                                     │
│  Tools: None                                                                 │
│                                                                              │
│  Inputs:                                                                     │
│  • final_diet_json                                                           │
│                                                                              │
│  Actions:                                                                    │
│  1. Extract JSON from input (remove markdown)                                │
│  2. Validate JSON syntax                                                     │
│  3. Fix syntax errors:                                                       │
│     - Remove trailing commas                                                 │
│     - Escape quotes properly                                                 │
│     - Fix unclosed brackets                                                  │
│     - Remove invalid characters                                              │
│     - Remove newlines in strings                                             │
│  4. Ensure all required fields exist                                         │
│                                                                              │
│  Output: validated_json                                                      │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ TASK 8: FILE GENERATION (Sequential - Final)                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│  Agent: File Generator                                                       │
│  Model: gemini-2.5-flash                                                     │
│  Tools: • pdf_generator_tool (Custom)                                        │
│                                                                              │
│  Inputs:                                                                     │
│  • validated_json                                                            │
│                                                                              │
│  Actions:                                                                    │
│  1. Save validated JSON to timestamped file                                  │
│  2. Generate PDF report with sections:                                       │
│     - Title & Basic Info (Disease, Allergies, Date)                          │
│     - Foods You Can Eat (by category with benefits)                          │
│     - Foods to Avoid (with reasons)                                          │
│     - Meal Ideas (with ingredients & preparation)                            │
│     - Nutritional Data Highlights (USDA data)                                │
│     - Medical Disclaimer                                                     │
│  3. Create debug JSON file for troubleshooting                               │
│                                                                              │
│  Output: file_output (JSON + PDF paths)                                      │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
                                 ▼
                        ┌────────────────────┐
                        │  FINAL DELIVERABLES│
                        ├────────────────────┤
                        │ • JSON File        │
                        │ • PDF Report       │
                        │ • Debug Log        │
                        │ • Execution Log    │
                        └────────────────────┘

---

## Tools & Technologies
```
┌─────────────────────────────────────────────────────────────────────────┐
│                            TOOL INTEGRATION                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  EXTERNAL TOOLS (3):                                                    │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │ 1. SerpAPI (serpapi library)                                │        │
│  │    - Medical & nutrition web search                         │        │
│  │    - Used by: Medical Researcher                            │        │
│  │                                                             │        │
│  │ 2. USDA FoodData Central API (requests library)             │        │
│  │    - Official nutrition database                            │        │
│  │    - Retrieves detailed nutrient profiles                   │        │
│  │    - Used by: usda_nutrition_tool                           │        │
│  │                                                             │        │
│  │ 3. Requests (requests library)                              │        │
│  │    - HTTP requests for API calls                            │        │
│  │    - Used by: usda_nutrition_tool                           │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                                                                         │
│  CUSTOM TOOLS (3):                                                      │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │ 4. usda_nutrition_tool                                      │        │
│  │    - Queries USDA FoodData Central API                      │        │
│  │    - Returns 18+ nutrient types per food                    │        │
│  │    - Includes FDC ID, serving size, data type               │        │
│  │    - Error handling for timeouts and missing data           │        │
│  │    - Used by: Nutrition Data Analyst                        │        │
│  │                                                             │        │
│  │ 5. allergen_validator_tool                                  │        │
│  │    - Cross-references foods with allergen database          │        │
│  │    - Maps common allergens to food ingredients              │        │
│  │    - Returns flagged items and safety status                │        │
│  │    - Used by: Allergen Safety Validator                     │        │
│  │                                                             │        │
│  │ 6. pdf_generator_tool                                       │        │
│  │    - Sanitizes and parses JSON                              │        │
│  │    - Generates PDF with FPDF2                               │        │
│  │    - Creates timestamped files                              │        │
│  │    - Handles Unicode characters safely                      │        │
│  │    - Used by: File Generator                                │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram
```
User Input (Disease + Allergies)
        │
        ▼
┌───────────────────┐
│ Validated         │
│ Input             │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Research          │ ──────────┐
│ Findings          │           │
└───────────────────┘           │
        │                       │
        ▼                       │
┌───────────────────┐           │
│ Food              │           │
│ Recommendations   │           │
└───────────────────┘           │
        │                       │
        ├───────────────────────┴───────────────────────┐
        │                                               │
        ▼                                               ▼
┌───────────────────┐                         ┌───────────────────┐
│ Nutrition Data    │                         │ Meal Ideas        │
│ (USDA API)        │                         │                   │
└───────────────────┘                         └───────────────────┘
        │                                               │
        └───────────────────┬───────────────────────────┘
                            │
                            ▼
                    ┌───────────────────┐
                    │ Allergen          │
                    │ Validation        │
                    └───────────────────┘
                            │
                            ▼
                    ┌───────────────────┐
                    │ Final Diet JSON   │
                    │ (Aggregated)      │
                    └───────────────────┘
                            │
                            ▼
                    ┌───────────────────┐
                    │ Validated JSON    │
                    │ (Fixed)           │
                    └───────────────────┘
                            │
                            ▼
                    ┌───────────────────┐
                    │ JSON + PDF Files  │
                    │ + Debug Logs      │
                    └───────────────────┘
```

---

## Logging & Monitoring
```
┌─────────────────────────────────────────────────────────────────────────┐
│                      MONITORING & LOGGING SYSTEM                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Log Levels:                                                            │
│  • INFO  : Successful operations, workflow progress                     │
│  • DEBUG : Detailed Google ADK internal operations                      │
│  • WARNING: Non-critical issues (e.g., no search results, missing data) │
│  • ERROR : Failures, exceptions (with stack traces)                     │
│                                                                         │
│  Logged Events:                                                         │
│  ✓ Agent execution start/end                                            │
│  ✓ Tool invocations (SerpAPI, USDA API, validators, PDF gen)            │
│  ✓ Search queries and result counts                                     │
│  ✓ USDA API calls (food item, FDC ID, nutrient count)                   │
│  ✓ Allergen validation results                                          │
│  ✓ JSON parsing attempts (sanitization steps)                           │
│  ✓ File generation (paths logged)                                       │
│  ✓ API connection tests (USDA, SerpAPI)                                 │
│  ✓ Errors with full stack traces                                        │
│                                                                         │
│  Output Files:                                                          │
│  • outputs/workflow_execution.log - Complete execution log              │
│  • outputs/debug_json_*.txt       - JSON debugging info                 │
│                                                                         │
│  Format:                                                                │
│  [timestamp] - [logger_name] - [level] - [message]                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Memory & Context Management
```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CONTEXT PASSING MECHANISM                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Method: Template-based string interpolation in agent instructions      │
│                                                                         │
│  Context Flow:                                                          │
│                                                                         │
│  validated_input ────────┬──> Medical Researcher                        │
│                          │                                              │
│                          ├──> Nutritionist                              │
│                          │                                              │
│                          ├──> Nutrition Data Analyst (Parallel)         │
│                          │                                              │
│                          ├──> Recipe Curator (Parallel)                 │
│                          │                                              │
│                          ├──> Allergen Safety Validator                 │
│                          │                                              │
│                          └──> Content Aggregator                        │
│                                                                         │
│  research_findings ──────┬──> Nutritionist                              │
│                          │                                              │
│                          └──> Content Aggregator                        │
│                                                                         │
│  food_recommendations ───┬──> Nutrition Data Analyst (Parallel)         │
│                          │                                              │
│                          ├──> Recipe Curator (Parallel)                 │
│                          │                                              │
│                          ├──> Allergen Safety Validator                 │
│                          │                                              │
│                          └──> Content Aggregator                        │
│                                                                         │
│  nutrition_data ─────────┬──> Content Aggregator                        │
│                                                                         │
│  meal_ideas ─────────────┬──> Recipe Curator                            │
│                          │                                              │
│                          └──> Content Aggregator                        │
│                                                                         │
│  allergen_validation ────┬──> Content Aggregator                        │
│                                                                         │
│  final_diet_json ────────┬──> JSON Validator                            │
│                                                                         │
│  validated_json ─────────┬──> File Generator                            │
│                                                                         │
│  Note: Context passed via output_key -> instruction template vars       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Execution Timeline
```
Time    Agent                          Status          Output Key
────────────────────────────────────────────────────────────────────────
T0      User Input                     ●               -
T1      Input Validator                ■ Sequential    validated_input
T2      Medical Researcher             ■ Sequential    research_findings
T3      Nutritionist                   ■ Sequential    food_recommendations
T4      ┌─ Nutrition Data Analyst      ▲ Parallel      nutrition_data
        └─ Recipe Curator              ▲ Parallel      meal_ideas
T5      Allergen Safety Validator      ■ Sequential    allergen_validation
T6      Content Aggregator             ■ Sequential    final_diet_json
T7      JSON Validator                 ■ Sequential    validated_json
T8      File Generator                 ■ Sequential    file_output
T9      Output Files Generated         ●               JSON + PDF + Logs

Legend: ● Event  ■ Sequential  ▲ Parallel
```

---

## Error Handling & Robustness
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ROBUSTNESS MECHANISMS                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. Search Failures (SerpAPI):                                          │
│     • Graceful degradation to medical knowledge base                    │
│     • Warning logged, workflow continues                                │
│     • No search results handled explicitly                              │
│                                                                         │
│  2. USDA API Failures:                                                  │
│     • Timeout protection (10 seconds)                                   │
│     • Missing data handled gracefully                                   │
│     • Falls back to nutritional knowledge base                          │
│     • Invalid responses caught with try-catch                           │
│     • HTTP errors logged with details                                   │
│                                                                         │
│  3. JSON Parsing & Sanitization:                                        │
│     • Remove markdown code blocks                                       │
│     • Extract valid JSON from text                                      │
│     • Fix trailing commas                                               │
│     • Escape special characters                                         │
│     • Remove newlines in strings                                        │
│     • Dedicated JSON Validator agent                                    │
│                                                                         │
│  4. Allergen Validation:                                                │
│     • Comprehensive allergen mapping (8+ categories)                    │
│     • Cross-reference with 40+ related foods                            │
│     • Flag violations as WARNING/UNSAFE                                 │
│     • Exception handling for validation errors                          │
│                                                                         │
│  5. PDF Generation:                                                     │
│     • Unicode bullet replacements for Helvetica font                    │
│     • Safe text function for special characters                         │
│     • Automatic page breaks                                             │
│     • Creates output directory if missing                               │
│     • Debug JSON saved for troubleshooting                              │
│                                                                         │
│  6. API Connection Testing:                                             │
│     • Pre-flight checks for USDA and SerpAPI                            │
│     • Test queries before main workflow                                 │
│     • API key validation                                                │
│     • Connection status reporting                                       │
│                                                                         │
│  7. Global Exception Handling:                                          │
│     • Try-catch in main execution                                       │
│     • Full stack traces logged                                          │
│     • Keyboard interrupt handling                                       │
│     • User-friendly error messages                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Output Structure
```
outputs/
├── diet_data_YYYYMMDD_HHMMSS.json
│   {
│     "disease": "string",
│     "allergies": "string",
│     "generated_date": "YYYY-MM-DD",
│     "validation_status": "SAFE|WARNING|UNSAFE",
│     "foods_you_can_eat": {
│       "proteins": [
│         {
│           "name": "string",
│           "benefits": "string",
│           "key_nutrients": "string"
│         }
│       ],
│       "vegetables": [...],
│       "fruits": [...],
│       "grains": [...],
│       "healthy_fats": [...],
│       "dairy_alternatives": [...],
│       "beverages": [...]
│     },
│     "foods_to_avoid": [
│       {
│         "name": "string",
│         "reason": "string"
│       }
│     ],
│     "nutritional_data": [
│       {
│         "status": "success",
│         "food": "string",
│         "fdc_id": "string",
│         "data_type": "Foundation|SR Legacy",
│         "nutrients": {
│           "Calories": "value unit",
│           "Protein": "value unit",
│           "Total Fat": "value unit",
│           "Carbohydrates": "value unit",
│           "Dietary Fiber": "value unit",
│           "Calcium": "value unit",
│           "Iron": "value unit",
│           "Vitamin C": "value unit",
│           "...": "..."
│         },
│         "serving_size": "string",
│         "nutrient_count": integer
│       }
│     ],
│     "meal_ideas": [
│       {
│         "name": "string",
│         "ingredients": "string",
│         "benefits": "string",
│         "preparation": "string"
│       }
│     ],
│     "general_guidelines": ["string"],
│     "allergen_check": "string",
│     "medical_disclaimer": "string"
│   }
│
├── diet_plan_YYYYMMDD_HHMMSS.pdf
│   ├── Title Page
│   ├── Basic Info (Disease, Allergies, Date)
│   ├── Foods You Can Eat (7 categories with benefits)
│   ├── Foods to Avoid (with reasons)
│   ├── Meal Ideas (7 meals with details)
│   ├── Nutritional Data Highlights (USDA data with FDC IDs)
│   └── Medical Disclaimer
│
├── debug_json_YYYYMMDD_HHMMSS.txt
│   ├── Original JSON (before sanitization)
│   └── Cleaned JSON (after sanitization)
│
└── workflow_execution.log
    └── Complete execution log with timestamps
```

---

## API Integration Details
```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USDA API INTEGRATION                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Endpoint: https://api.nal.usda.gov/fdc/v1/foods/search                 │
│                                                                         │
│  Parameters:                                                            │
│  • query: Food item name                                                │
│  • dataType: ["Foundation", "SR Legacy"] - High quality data            │
│  • pageSize: 3 - Top 3 matches                                          │
│  • api_key: From .env file (USDA_API_KEY)                               │
│                                                                         │
│  Retrieved Data:                                                        │
│  • Food description                                                     │
│  • FDC ID (unique identifier)                                           │
│  • Data type (Foundation/SR Legacy)                                     │
│  • 18+ nutrient types:                                                  │
│    - Macronutrients: Calories, Protein, Fats, Carbs, Fiber, Sugars      │
│    - Minerals: Calcium, Iron, Potassium, Sodium                         │
│    - Vitamins: A, C, D, E, K, B12, Folate                               │
│    - Fatty Acids: Omega-3, Cholesterol                                  │
│  • Serving size information                                             │
│                                                                         │
│  Error Handling:                                                        │
│  • Timeout: 10 seconds                                                  │
│  • Missing API key: Falls back to knowledge base                        │
│  • No results: Uses general nutritional knowledge                       │
│  • Invalid JSON: Logs error and continues                               │
│  • Network errors: Caught and logged                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Allergen Database
```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ALLERGEN MAPPING SYSTEM                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Allergen Categories & Related Foods:                                   │
│                                                                         │
│  1. Dairy                                                               │
│     - milk, cheese, yogurt, butter, cream, whey, casein                 │
│                                                                         │
│  2. Nuts                                                                │
│     - almond, walnut, cashew, pecan, pistachio, hazelnut                │
│                                                                         │
│  3. Peanuts                                                             │
│     - peanut, peanut butter                                             │
│                                                                         │
│  4. Soy                                                                 │
│     - soy, tofu, edamame, tempeh, soy sauce                             │
│                                                                         │
│  5. Eggs                                                                │
│     - egg, mayonnaise                                                   │
│                                                                         │
│  6. Fish                                                                │
│     - salmon, tuna, cod, fish, seafood                                  │
│                                                                         │
│  7. Shellfish                                                           │
│     - shrimp, crab, lobster, clam, oyster                               │
│                                                                         │
│  8. Wheat                                                               │
│     - wheat, bread, pasta, flour                                        │
│                                                                         │
│  9. Gluten                                                              │
│     - wheat, barley, rye, bread, pasta                                  │
│                                                                         │
│  Validation Process:                                                    │
│  • Parse user allergens (comma-separated)                               │
│  • Extract all foods from recommendations and meals                     │
│  • Cross-reference each food with allergen database                     │
│  • Flag foods containing allergens                                      │
│  • Return status: SAFE/WARNING/UNSAFE                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Feature Highlights
```
┌─────────────────────────────────────────────────────────────────────────┐
│                          ADVANCED FEATURES                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. REAL-TIME MEDICAL RESEARCH                                          │
│     • Web search integration via SerpAPI                                │
│     • Evidence-based diet recommendations                               │
│     • Current medical guidelines                                        │
│                                                                         │
│  2. OFFICIAL NUTRITIONAL DATA                                           │
│     • USDA FoodData Central integration                                 │
│     • 18+ nutrient types per food                                       │
│     • Verified serving sizes and FDC IDs                                │
│     • Foundation & SR Legacy data sources                               │
│                                                                         │
│  3. PARALLEL PROCESSING                                                 │
│     • Nutrition data fetching + recipe curation run simultaneously      │
│     • Reduces overall execution time                                    │
│     • Independent task optimization                                     │
│                                                                         │
│  4. SAFETY VALIDATION & HALLUCINATION MITIGATION                        │
│     • Comprehensive allergen checking                                   │
│     • Multi-layer validation (before and after aggregation)             │
│     • Flags potential safety issues                                     │
│     • Medical disclaimer included                                       │
│     • Allergen & JSON Validators                                        │
│                                                                         │
│  5. ROBUST ERROR HANDLING                                               │
│     • Graceful API failure recovery                                     │
│     • JSON sanitization and validation                                  │
│     • Detailed error logging                                            │
│     • Debug file generation                                             │
│                                                                         │
│  6. COMPREHENSIVE OUTPUT                                                │
│     • Structured JSON for programmatic use                              │
│     • Professional PDF report for human reading                         │
│     • Clickable links in PDF                                            │
│     • Complete execution logs                                           │
│                                                                         │
│  7. MEMORY & CONTEXT PASSING                                            │
│     • Sequential context propagation                                    │
│     • Each agent builds on previous outputs                             │
│     • Template-based instruction interpolation                          │
│     • No data loss between stages                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Environment Configuration
```
┌─────────────────────────────────────────────────────────────────────────┐
│                        REQUIRED ENVIRONMENT SETUP                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  File: .env (in project root)                                           │
│                                                                         │
│  Required Variables:                                                    │
│  ┌───────────────────────────────────────────────────────────────┐      │
│  │ USDA_API_KEY=your_usda_api_key_here                           │      │
│  │ SERPAPI_API_KEY=your_serpapi_key_here                         │      │
│  │ GOOGLE_API_KEY=your_serpapi_key_here                          │      │
│  └───────────────────────────────────────────────────────────────┘      │
│                                                                         │
│  How to Obtain Keys:                                                    │
│                                                                         │
│  1. USDA API Key:                                                       │
│     - Visit: https://fdc.nal.usda.gov/api-key-signup.html               │
│     - Sign up for free API access                                       │
│     - Use for nutritional data queries                                  │
│                                                                         │
│  2. SerpAPI Key:                                                        │
│     - Visit: https://serpapi.com/                                       │
│     - Sign up for free tier (100 searches/month)                        │
│     - Use for medical research searches                                 │
│                                                                         │
│  Dependencies:                                                          │
│  • google.adk.agents - Google ADK framework                             │
│  • fpdf2 - PDF generation                                               │
│  • serpapi - Web search                                                 │
│  • requests - HTTP requests                                             │
│  • python-dotenv - Environment variable loading                         │
│                                                                         │
│  Installation:                                                          │
│  $ pip install google-adk fpdf2 serpapi requests python-dotenv          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Usage Examples
```
┌─────────────────────────────────────────────────────────────────────────┐
│                            USAGE EXAMPLES                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Example 1: Diabetes Type 2 with Gluten Allergy                         │
│  ──────────────────────────────────────────────────────────────         │
│  Input:                                                                 │
│    Disease: Type 2 Diabetes                                             │
│    Allergies: gluten, wheat                                             │
│                                                                         │
│  Output:                                                                │
│    • 40+ gluten-free foods across 7 categories                          │
│    • USDA data for top 12 foods (with blood sugar impact info)          │
│    • 7 gluten-free meal ideas                                           │
│    • Allergen validation: SAFE (no gluten detected)                     │
│    • PDF report with detailed nutritional data                          │
│                                                                         │
│  ──────────────────────────────────────────────────────────────         │
│                                                                         │
│  Example 2: Heart Disease with Multiple Allergies                       │
│  ──────────────────────────────────────────────────────────────         │
│  Input:                                                                 │
│    Disease: Coronary Heart Disease                                      │
│    Allergies: dairy, nuts, shellfish                                    │
│                                                                         │
│  Output:                                                                │
│    • Heart-healthy foods excluding all allergens                        │
│    • Focus on omega-3 rich fish (avoiding shellfish)                    │
│    • Plant-based alternatives to dairy                                  │
│    • Seed-based alternatives to nuts                                    │
│    • USDA omega-3 data for recommended fish                             │
│    • Allergen validation: SAFE (all allergens excluded)                 │
│                                                                         │
│  ──────────────────────────────────────────────────────────────         │
│                                                                         │
│  Example 3: Celiac Disease (No Allergies)                               │
│  ──────────────────────────────────────────────────────────────         │
│  Input:                                                                 │
│    Disease: Celiac Disease                                              │
│    Allergies: none                                                      │
│                                                                         │
│  Output:                                                                │
│    • Comprehensive gluten-free diet plan                                │
│    • Alternative grains (quinoa, rice, buckwheat)                       │
│    • Hidden gluten source warnings                                      │
│    • USDA data showing nutrient profiles of alternatives                │
│    • 7 gluten-free meal ideas with preparation tips                     │
│    • Foods to avoid: wheat, barley, rye products                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Performance Metrics
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TYPICAL EXECUTION METRICS                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Execution Time: 2-3 minutes (total)                                    │
│  ├── Input Validation:          ~5 seconds                              │
│  ├── Medical Research:           ~30-45 seconds                         │
│  ├── Food Recommendations:       ~20-30 seconds                         │
│  ├── Parallel Phase:             ~40-60 seconds                         │
│  │   ├── Nutrition Data (10-12 USDA API calls)                          │
│  │   └── Recipe Curation                                                │
│  ├── Allergen Validation:        ~10 seconds                            │
│  ├── Content Aggregation:        ~15 seconds                            │
│  ├── JSON Validation:            ~5 seconds                             │
│  └── File Generation:            ~10 seconds                            │
│                                                                         │
│  Output Sizes:                                                          │
│  • JSON File: 15-25 KB                                                  │
│  • PDF Report: 3-5 pages, 200-400 KB                                    │
│  • Execution Log: 50-100 KB                                             │
│  • Debug JSON: 10-20 KB                                                 │
│                                                                         │
│  Data Points Generated:                                                 │
│  • 40-50 recommended foods (across 7 categories)                        │
│  • 10-15 foods to avoid (with reasons)                                  │
│  • 10-12 detailed nutritional profiles (USDA data)                      │
│  • 180-220 individual nutrient data points                              │
│  • 7 complete meal ideas (with ingredients & prep)                      │
│  • 5-10 general dietary guidelines                                      │
│                                                                         │
│  API Calls:                                                             │
│  • SerpAPI: 3 searches (medical research)                               │
│  • USDA API: 10-12 queries (nutrition data)                             │
│  • Total API requests: 13-15                                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting Guide
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         COMMON ISSUES & SOLUTIONS                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ISSUE 1: "USDA_API_KEY not found"                                      │
│  ──────────────────────────────────────────────────────────────         │
│  Solution:                                                              │
│  • Create .env file in project root                                     │
│  • Add: USDA_API_KEY=your_key_here                                      │
│  • Verify file is named exactly ".env" (not .env.txt)                   │
│                                                                         │
│  ──────────────────────────────────────────────────────────────         │
│                                                                         │
│  ISSUE 2: "JSON parsing failed"                                         │
│  ──────────────────────────────────────────────────────────────         │
│  Solution:                                                              │
│  • Check outputs/debug_json_*.txt for details                           │
│  • JSON Validator agent should auto-fix most issues                     │
│  • If persistent, check for special characters in disease name          │
│                                                                         │
│  ──────────────────────────────────────────────────────────────         │
│                                                                         │
│  ISSUE 3: "No USDA data for food item"                                  │
│  ──────────────────────────────────────────────────────────────         │
│  Solution:                                                              │
│  • This is normal - some foods aren't in USDA database                  │
│  • Agent uses nutritional knowledge base as fallback                    │
│  • Try simpler food names (e.g., "salmon" not "grilled salmon")         │
│                                                                         │
│  ──────────────────────────────────────────────────────────────         │
│                                                                         │
│  ISSUE 4: "SerpAPI search failed"                                       │
│  ──────────────────────────────────────────────────────────────         │
│  Solution:                                                              │
│  • Verify SERPAPI_API_KEY in .env                                       │
│  • Check if monthly quota exceeded (100 free searches)                  │
│  • Agent falls back to medical knowledge base                           │
│                                                                         │
│  ──────────────────────────────────────────────────────────────         │
│                                                                         │
│  ISSUE 5: "PDF generation error"                                        │
│  ──────────────────────────────────────────────────────────────         │
│  Solution:                                                              │
│  • Ensure fpdf2 is installed: pip install fpdf2                         │
│  • Check outputs folder has write permissions                           │
│  • Review outputs/workflow_execution.log for details                    │
│                                                                         │
│  ──────────────────────────────────────────────────────────────         │
│                                                                         │
│  ISSUE 6: "Allergen not detected correctly"                             │
│  ──────────────────────────────────────────────────────────────         │
│  Solution:                                                              │
│  • Use standard allergen names: dairy, nuts, gluten, etc.               │
│  • Separate multiple allergens with commas                              │
│  • Check allergen_validation section in JSON output                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Future Enhancements
```
┌─────────────────────────────────────────────────────────────────────────┐
│                       POTENTIAL IMPROVEMENTS                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. PERSONALIZATION                                                     │
│     • Add age, gender, activity level inputs                            │
│     • Calculate personalized caloric needs                              │
│     • Adjust nutrient recommendations accordingly                       │
│                                                                         │
│  2. MEAL PLANNING                                                       │
│     • Generate weekly meal plans                                        │
│     • Shopping list generation                                          │
│     • Meal prep instructions                                            │
│                                                                         │
│  3. INTEGRATION EXPANSION                                               │
│     • Add recipe APIs (Spoonacular, Edamam)                             │
│     • Integrate with grocery delivery services                          │
│     • Connect to fitness tracking apps                                  │
│                                                                         │
│  4. PROGRESS TRACKING                                                   │
│     • Database integration for user history                             │
│     • Track adherence to diet plan                                      │
│     • Monitor health metrics over time                                  │
│                                                                         │
│  5. MULTILINGUAL SUPPORT                                                │
│     • Translate diet plans to multiple languages                        │
│     • Regional food alternatives                                        │
│     • Cultural dietary preferences                                      │
│                                                                         │
│  6. ADVANCED ANALYTICS                                                  │
│     • Macro/micronutrient visualizations                                │
│     • Cost analysis of recommended foods                                │
│     • Environmental impact metrics                                      │
│                                                                         │
│  7. MOBILE APP                                                          │
│     • iOS/Android companion app                                         │
│     • Push notifications for meal reminders                             │
│     • Barcode scanning for food logging                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘