┌─────────────────────────────────────────────────────────────────────────┐
│      USER INPUT                                                         │
│      • Disease/Condition (e.g., "Diabetes")                             │
│      • Allergies (e.g., "Peanuts", "none")                              │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│      CREW INITIALIZATION & KICKOFF                                      │
│       Process Type: Sequential with a Parallel Phase                    │
│       (Tasks 4 & 5 run in parallel via async_execution=True)            │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   SEQUENTIAL PHASE   │
                    └──────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│  TASK 1: Input Validation                              [SEQUENTIAL]     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Agent: Input Validator                                         │    │
│  │  Tools: None (LLM reasoning)                                    │    │
│  │  Actions:                                                       │    │
│  │    1. Standardize disease name                                  │    │
│  │    2. List allergies clearly                                    │    │
│  │    3. Provide a clean summary of the validated inputs           │    │
│  │  Output: Validated disease and allergy information              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  TASK 2: Medical Research                              [SEQUENTIAL]       │
│  ┌─────────────────────────────────────────────────────────────────┐      │
│  │  Agent: Medical Researcher                                      │      │
│  │  Tools: • Web Search Tool (SerpAPI)                             │      │
│  │  Dependencies: Task 1                                           │      │
│  │  Actions:                                                       │      │
│  │    1. Search for beneficial nutrients for the disease           │      │
│  │    2. Search for foods to eat and foods to avoid                │      │
│  │    3. Research why these dietary changes help manage symptoms   │      │
│  │  Output: Research summary on disease-nutrition relationship     │      │
│  └─────────────────────────────────────────────────────────────────┘      │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  TASK 3: Food Recommendation                           [SEQUENTIAL]       │
│  ┌─────────────────────────────────────────────────────────────────┐      │
│  │  Agent: Nutritionist                                            │      │
│  │  Tools: None (LLM reasoning)                                    │      │
│  │  Dependencies: Task 1, Task 2                                   │      │
│  │  Actions:                                                       │      │
│  │    1. Create list: "FOODS YOU CAN EAT" (by category)            │      │
│  │    2. For each food, explain benefits and key nutrients         │      │
│  │    3. Create list: "FOODS TO AVOID" (with reasons)              │      │
│  │    4. CRITICAL: Filter out all foods matching user allergies    │      │
│  │  Output: Categorized food lists (Markdown)                      │      │
│  └─────────────────────────────────────────────────────────────────┘      │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │
                                    ├──────────────────────────────────┐
                                    │                                  │
                           ┌─────────▼─────────┐              ┌─────────▼────────┐
                           │ PARALLEL PHASE    │              │  PARALLEL PHASE  │
                           └───────────────────┘              └──────────────────┘
                                    │                                  │
┌───────────────────────────────────▼──────────────────┐  ┌────────────────▼──────────────────────┐
│  TASK 4: Nutrition Analysis            [PARALLEL 1]  │  │  TASK 5: Recipe Curation  [PARALLEL 2]│
│  ┌────────────────────────────────────────────────┐  │  │  ┌─────────────────────────────────┐  │
│  │  Agent: Nutrition Data Analyst                 │  │  │  │  Agent: Recipe Curator          │  │
│  │  Tools: • Nutrition Tool (USDA)                │  │  │  │  Tools: None (LLM reasoning)    │  │
│  │  Dependencies: Task 3                          │  │  │  │  Dependencies: Task 3           │  │
│  │  Actions:                                      │  │  │  │  Actions:                       │  │
│  │    1. Get nutrition data for top 10 foods      │  │  │  │    1. Create 5-7 simple meal    │  │
│  │    2. List calories, macros, vitamins          │  │  │  │       snack ideas               │  │
│  │    3. Suggest serving sizes                    │  │  │  │    2. List main ingredients     │  │
│  │                                                │  │  │  │    3. Explain benefits of  meal │  │
│  │  Output: Detailed nutritional data             │  │  │  │    4. Write simple prep notes   │  │
│  └────────────────────────────────────────────────┘  │  │  │  Output: Simple meal ideas      │  │
│                                                      │  │  └─────────────────────────────────┘  │
└────────────────────┬─────────────────────────────────┘  └────────────────┬──────────────────────┘
                     │                                                     │
                     └──────────────┬──────────────────────────────────────┘
                                    │
                         ┌──────────▼────────┐
                         │ SEQUENTIAL PHASE  │
                         └───────────────────┘
                                    │
┌───────────────────────────────────▼──────────────────────────────────────┐
│   TASK 6: Report Compilation                          [SEQUENTIAL]       │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │  Agent: Report Compiler & Data Manager                          │     │
│  │  Tools: • JSON Saver, • PDF Generator                           │     │
│  │  Dependencies: All (Tasks 1, 2, 3, 4, 5)                        │     │
│  │  Actions:A                                                      │     │
│  │    1. Compile all data into the required JSON structure         │     │
│  │    2. Add timestamp and medical disclaimer                      │     │
│  │    3. Call save_json tool to save the structured data           │     │
│  │    4. Call pdf_generator tool to create the final report        │     │
│  │    5. Generate timestamped PDF + JSON files                     │     │
│  │  Output: File paths for generated PDF and JSON                  │     │
│  └─────────────────────────────────────────────────────────────────┘     │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          FILE GENERATION                               │
│  ┌──────────────────────────┐     ┌──────────────────────────┐         │
│  │  PDF Report              │     │  JSON Data File          │         │
│  │  • Rich formatting       │     │  • Structured data       │         |
│  │  • Markdown rendering    │     │  • Machine-readable      │         │
│  └──────────────────────────┘     └──────────────────────────┘         │
│                                                            Request     │
│  Location: outputs/diet_plan_YYYYMMDD_HHMMSS.pdf                       │
│  Location: outputs/diet_data_YYYYMMDD_HHMMSS.json                      │
└────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════
                          Example  AGENT SUMMARY
═══════════════════════════════════════════════════════════════════════════

Agent 1: Input Validator
├─ Tools: None
├─ Role: Validate and standardize disease/allergy input
└─ Output: Validated info summary

Agent 2: Medical Researcher
├─ Tools: Web Search Tool (SerpAPI)
├─ Role: Research disease-diet connections
└─ Output: Research summary on nutrition

Agent 3: Nutritionist
├─ Tools: None (LLM reasoning)
├─ Role: Create "eat/avoid" lists, explain benefits, filter allergies
└─ Output: Categorized food lists (Markdown)

Agent 4: Nutrition Data Analyst
├─ Tools: Nutrition Tool (USDA)
├─ Role: Get detailed nutritional data for top recommended foods
└─ Output: List of nutritional data

Agent 5: Recipe Curator
├─ Tools: None (LLM reasoning)
├─ Role: Create simple meal ideas using recommended foods
└─ Output: List of meal/snack ideas

Agent 6: Report Compiler & Data Manager
├─ Tools: • JSON Saver, • PDF Generator
├─ Role: Compile all data into final JSON and PDF files
└─ Output: File paths for generated PDF and JSON

═══════════════════════════════════════════════════════════════════════════
                        DEPENDENCY GRAPH
═══════════════════════════════════════════════════════════════════════════

Task 1 (Validation)
  │
  └──→ Task 2 (Research)
       │
(1,2) ──┴──→ Task 3 (Food Lists)
              │
              ├──→ Task 4 (Nutrition Data) [Async] ──┐
              │                                      │
              └──→ Task 5 (Recipes) [Async] ──────────┤
                                                      │
                     (All previous tasks) ───────────┴──→ Task 6 (Compilation) → PDF + JSON

═══════════════════════════════════════════════════════════════════════════
                    EXECUTION TIMELINE: 2-5 Minutes
═══════════════════════════════════════════════════════════════════════════