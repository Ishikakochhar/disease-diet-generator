import requests

urls = {
    "Celiac": "https://celiac.org/wp-content/uploads/2015/11/7-Day-Meal-Plan-Final.pdf",
    "Diabetes": "https://www.sja.org.uk/globalassets/sja/first-aid-advice/first-aid-posters/diabetes.pdf",
    "Stanford_Diabetes": "https://stanfordhealthcare.org/content/dam/SHC/for-patients-component/programs-services/clinical-nutrition-services/docs/pdf-diabetes-diet.pdf",
    "Eczema": "https://nationaleczema.org/wp-content/uploads/2018/03/FactSheet_Diet_Eczema.pdf",
    "WHO_Nutrition": "https://cdn.who.int/media/docs/default-source/nutritionlibrary/healthy-diets/healthy-diet-fact-sheet-394.pdf"
}

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

for name, url in urls.items():
    try:
        r = requests.get(url, headers=headers, timeout=5)
        print(f"{name}: {r.status_code}")
    except Exception as e:
        print(f"{name}: ERROR {e}")
