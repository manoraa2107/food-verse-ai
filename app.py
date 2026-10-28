import json
import os
import re
from typing import Any

import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

APP_TITLE = "Food Verse AI"
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

st.set_page_config(
    page_title="Food Verse AI",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root { color-scheme: light; }
.stApp { background: linear-gradient(180deg, #f7fbf5 0%, #ffffff 42%); }
[data-testid="stSidebar"] { background: #eef6eb; }
.hero {
  padding: 1.5rem 1.7rem; border-radius: 22px;
  background: linear-gradient(115deg, #173f35, #2d7657);
  color: white; margin-bottom: 1.1rem;
}
.hero h1 { color: white; margin: 0; font-size: 2.25rem; }
.hero p { color: #e3f4e7; margin: .45rem 0 0 0; font-size: 1.05rem; }
.pill { display:inline-block; padding:.25rem .65rem; border-radius:99px;
  background:#e4f3e7; color:#20563b; font-size:.82rem; margin:.15rem .2rem .15rem 0; }
div[data-testid="stMetric"] { background:#f3f8f1; padding: .8rem; border-radius: 14px; }
.small-note { color:#53645a; font-size:.88rem; }
</style>
""", unsafe_allow_html=True)

def get_client():
    key = st.secrets.get("GEMINI_API_KEY", None) if hasattr(st, "secrets") else None
    key = key or os.getenv("GEMINI_API_KEY")
    if not key or key.strip() in ("", "MY_GEMINI_API_KEY"):
        return None
    return genai.Client(api_key=key.strip())

def extract_json(text: str) -> Any:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end+1])
        raise ValueError("The AI response was not valid JSON. Please try again.")

def ask_ai(prompt: str, image: Image.Image | None = None, json_mode: bool = False) -> str:
    client = get_client()
    if client is None:
        raise RuntimeError("Gemini API key is not configured. Add GEMINI_API_KEY in Streamlit Secrets or your local .env environment.")
    contents = [prompt]
    if image is not None:
        contents = [image, prompt]
    config = types.GenerateContentConfig(
        response_mime_type="application/json" if json_mode else "text/plain",
        temperature=0.3,
    )
    response = client.models.generate_content(model=MODEL, contents=contents, config=config)
    if not response.text:
        raise RuntimeError("The AI returned an empty response. Please try again.")
    return response.text

def show_json_result(data: Any):
    if isinstance(data, dict):
        # Display common top-level metrics if available
        nutrition = data.get("nutrition")
        if isinstance(nutrition, dict):
            cols = st.columns(4)
            for col, label, key, suffix in zip(
                cols, ["Calories", "Protein", "Carbs", "Fat"],
                ["calories", "protein", "carbohydrates", "fat"], ["kcal", "g", "g", "g"]
            ):
                value = nutrition.get(key, "—")
                col.metric(label, f"{value} {suffix}" if value != "—" else "—")
        for key, value in data.items():
            if key == "nutrition":
                continue
            label = key.replace("_", " ").replace("Pct", " %").title()
            if isinstance(value, (dict, list)):
                with st.expander(label, expanded=(key in ("visualObservations", "identifiedIngredients", "handlingRecommendations", "steps"))):
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                st.markdown("**" + str(item.get("indicator", item.get("name", "Item"))) + "**")
                                st.write(item.get("observation", item.get("detail", item)))
                                if item.get("status"):
                                    st.caption("Status: " + str(item["status"]))
                            else:
                                st.write(f"• {item}")
                    else:
                        st.json(value)
            else:
                if key.lower() in ("safetywarning", "disclaimer", "dietitianadvice"):
                    st.info(f"**{label}:** {value}")
                else:
                    st.markdown(f"**{label}:** {value}")
    else:
        st.write(data)

def render_header():
    st.markdown("""
    <div class="hero">
      <h1>🥗 Food Verse AI</h1>
      <p>Your multimodal food intelligence assistant — nutrition, freshness, kitchen hygiene, recipes and meal planning.</p>
    </div>
    <span class="pill">AI-powered food insights</span>
    <span class="pill">5 integrated modules</span>
    <span class="pill">Gemini vision + text</span>
    """, unsafe_allow_html=True)

def module_food_nutrition():
    st.subheader("🍎 Food Recognition & Nutrition")
    st.write("Upload a meal photo to estimate the dish, ingredients, serving size, nutrition, allergens and an indicative health score.")
    image_file = st.file_uploader("Upload food image", type=["png", "jpg", "jpeg", "webp"], key="nutrition_image")
    portion = st.text_input("Portion note (optional)", placeholder="e.g., one medium bowl, homemade with little oil")
    if image_file:
        img = Image.open(image_file).convert("RGB")
        st.image(img, caption="Uploaded food image", use_container_width=True)
        if st.button("Analyze food & nutrition", type="primary", use_container_width=True):
            prompt = f"""You are a careful food scientist and nutrition estimation assistant. Analyze the attached food photo and estimate the visible serving. Portion note: {portion or 'Standard visible serving'}.
Return ONLY valid JSON with these keys:
{{
"dishName":"", "cuisine":"", "confidenceScore":0, "estimatedServingSize":"",
"identifiedIngredients":[""], "nutrition":{{"calories":0,"protein":0,"carbohydrates":0,"fat":0,"fiber":0,"sodium_mg":0,"sugars_g":0}},
"macroPercentages":{{"proteinPct":0,"carbsPct":0,"fatPct":0}}, "healthScore":0,
"healthScoreExplanation":"", "micronutrientHighlights":[""], "potentialAllergens":[""],
"dietaryLabels":[""], "dietitianAdvice":"", "disclaimer":"Nutrition values are approximate visual estimates and not laboratory measurements."
}}
Be realistic, state uncertainty, and never imply exact measurement from a photo."""
            with st.spinner("Analyzing the meal image…"):
                try:
                    data = extract_json(ask_ai(prompt, img, json_mode=True))
                    st.success("Analysis complete")
                    show_json_result(data)
                except Exception as e:
                    st.error(str(e))
    else:
        st.info("Upload a food photo to begin. For best results, use a clear image with the meal fully visible.")

def module_freshness():
    st.subheader("🥬 Food Freshness & Spoilage Assessment")
    st.write("Assess visible signs of freshness. A photo cannot determine hidden pathogens or guarantee food safety.")
    image_file = st.file_uploader("Upload fruit, vegetable or food image", type=["png", "jpg", "jpeg", "webp"], key="freshness_image")
    item = st.text_input("Food item (optional)", placeholder="e.g., tomato, spinach, cooked rice")
    if image_file:
        img = Image.open(image_file).convert("RGB")
        st.image(img, caption="Uploaded food image", use_container_width=True)
        if st.button("Assess visible freshness", type="primary", use_container_width=True):
            prompt = f"""Act as a cautious food quality specialist. Assess ONLY visible features in this image. Claimed item: {item or 'identify from image'}.
Return ONLY JSON with keys:
{{"identifiedItem":"","conditionClassification":"Uncertain","freshnessScore":0,
"visualObservations":[{{"indicator":"","status":"","observation":""}}],
"spoilageRiskFactors":[""],"estimatedShelfLife":"Cannot reliably determine from image alone",
"handlingRecommendations":[""],"safetyWarning":"Visual analysis cannot detect invisible pathogens. If food smells unusual, is slimy, has unexpected mold, or storage history is uncertain, discard it."}}
conditionClassification must be exactly one of Fresh, Moderately Fresh, Spoiled, Uncertain. Do not claim that food is safe to eat based only on appearance. Avoid precise shelf-life claims unless strongly qualified."""
            with st.spinner("Reviewing visible freshness indicators…"):
                try:
                    data = extract_json(ask_ai(prompt, img, json_mode=True))
                    st.success("Visual assessment complete")
                    show_json_result(data)
                except Exception as e:
                    st.error(str(e))
    else:
        st.info("Upload a clear image of the item. The assessment is visual guidance only.")

def module_hygiene():
    st.subheader("🧼 Kitchen Hygiene & Sanitation Review")
    st.write("Upload a kitchen/preparation-area photo for an educational visual review of visible hygiene risks.")
    image_file = st.file_uploader("Upload kitchen image", type=["png", "jpg", "jpeg", "webp"], key="hygiene_image")
    context = st.text_input("Context (optional)", placeholder="e.g., home kitchen, restaurant prep counter")
    if image_file:
        img = Image.open(image_file).convert("RGB")
        st.image(img, caption="Uploaded kitchen image", use_container_width=True)
        if st.button("Review kitchen hygiene", type="primary", use_container_width=True):
            prompt = f"""You are an educational kitchen hygiene reviewer. Inspect only what is visible in the image. Context: {context or 'food preparation area'}.
Look for cleanliness of surfaces, separation of raw and ready-to-eat foods, handwashing/PPE where visible, storage, waste, and cross-contamination risks. Do not infer hidden behavior.
Return ONLY JSON:
{{"overallScore":0,"grade":"C","summary":"","observations":[{{"area":"","status":"Unclear","observation":"","recommendedAction":""}}],
"priorityActions":[""],"disclaimer":"This is an educational visual review, not an official health inspection or regulatory certification."}}
Grade must be A, B, C, or Critical Action. Status should be Pass, Risk Detected, Violation Warning, or Unclear. Be constructive and explicitly mark things that cannot be judged from the photo."""
            with st.spinner("Reviewing visible hygiene indicators…"):
                try:
                    data = extract_json(ask_ai(prompt, img, json_mode=True))
                    st.success("Review complete")
                    show_json_result(data)
                except Exception as e:
                    st.error(str(e))
    else:
        st.info("Use a wide, well-lit photo that shows the main preparation surfaces.")

def module_recipes():
    st.subheader("👨‍🍳 Smart Recipe Assistant")
    st.write("Turn ingredients you already have into practical recipes.")
    ingredients = st.text_area("Ingredients available", placeholder="e.g., potatoes, peas, tomatoes, rice, yogurt", height=100)
    diet = st.selectbox("Dietary preference", ["No restriction", "Vegetarian", "Vegan", "High protein", "Keto", "Mediterranean", "Gluten-free", "Dairy-free"])
    allergies = st.text_input("Allergies or ingredients to avoid", placeholder="e.g., peanuts, milk")
    servings = st.number_input("Servings", min_value=1, max_value=12, value=2)
    time_limit = st.slider("Maximum preparation time (minutes)", 10, 120, 40, 5)
    if st.button("Generate recipes", type="primary", use_container_width=True):
        if not ingredients.strip():
            st.warning("Enter at least one ingredient first.")
            return
        prompt = f"""You are a helpful, safety-conscious culinary assistant. Create 3 distinct recipes primarily using these available ingredients: {ingredients}.
Dietary preference: {diet}. Allergies/avoid: {allergies or 'none specified'}. Servings: {servings}. Maximum time: {time_limit} minutes.
Do not include stated allergens. If cross-contact is possible, mention it. Return readable markdown with for each recipe: name, short description, prep/cook/total time, difficulty, ingredients with quantities, numbered steps, substitutions, chef tip, and approximate nutrition per serving. Prefer accessible ingredients and clearly flag assumptions."""
        with st.spinner("Creating recipes from your pantry…"):
            try:
                st.markdown(ask_ai(prompt))
            except Exception as e:
                st.error(str(e))
    st.divider()
    st.caption("Tip: double-check packaged ingredient labels for allergens and verify food is fully cooked.")

def module_meal_planner():
    st.subheader("📅 Personalized Meal Planner")
    st.write("Estimate daily energy needs and generate a seven-day meal plan. This is general information, not a medical prescription.")
    c1, c2, c3 = st.columns(3)
    with c1:
        sex = st.selectbox("Equation setting", ["Female", "Male"])
        age = st.number_input("Age (years)", 18, 100, 25)
    with c2:
        weight = st.number_input("Weight (kg)", 25.0, 300.0, 60.0, 0.5)
        height = st.number_input("Height (cm)", 100.0, 240.0, 165.0, 0.5)
    with c3:
        activity_label = st.selectbox("Activity level", ["Sedentary", "Lightly active", "Moderately active", "Very active", "Extra active"])
        goal = st.selectbox("Goal", ["Fat loss", "Maintenance", "Muscle gain"])
    dietary = st.selectbox("Food preference", ["Vegetarian", "Vegan", "Omnivore", "Pescatarian", "Dairy-free"])
    exclude = st.text_input("Foods to avoid / allergies", placeholder="e.g., peanuts, mushrooms")
    activity = {"Sedentary": 1.2, "Lightly active": 1.375, "Moderately active": 1.55, "Very active": 1.725, "Extra active": 1.9}[activity_label]
    bmr = 10 * weight + 6.25 * height - 5 * age + (5 if sex == "Male" else -161)
    tdee = bmr * activity
    target = tdee + {"Fat loss": -400, "Maintenance": 0, "Muscle gain": 300}[goal]
    m1, m2, m3 = st.columns(3)
    m1.metric("Estimated BMR", f"{round(bmr):,} kcal/day")
    m2.metric("Estimated TDEE", f"{round(tdee):,} kcal/day")
    m3.metric("Goal target", f"{max(1200, round(target)):,} kcal/day")
    st.caption("Mifflin–St Jeor estimate. Actual needs vary; avoid aggressive calorie restriction and seek qualified advice for medical or specialized nutrition needs.")
    if st.button("Build 7-day meal plan", type="primary", use_container_width=True):
        prompt = f"""Create a realistic 7-day meal plan with breakfast, lunch, snack and dinner each day.
Profile: age {age}, equation setting {sex}, weight {weight} kg, height {height} cm, activity {activity_label}, goal {goal}.
Estimated calorie target about {max(1200, round(target))} kcal/day. Diet: {dietary}. Allergies/avoid: {exclude or 'none specified'}.
Use common, affordable ingredients and variety across days. Include approximate portion sizes and daily calories/protein estimates, plus a categorized grocery list for the full week. Clearly identify estimates. Do not make medical claims. Avoid any listed allergens/foods. Use markdown tables where readable."""
        with st.spinner("Planning your week…"):
            try:
                st.markdown(ask_ai(prompt))
            except Exception as e:
                st.error(str(e))

def main():
    render_header()
    pages = {
        "Food & Nutrition": "🍎",
        "Freshness Check": "🥬",
        "Kitchen Hygiene": "🧼",
        "Recipe Assistant": "👨‍🍳",
        "Meal Planner": "📅",
        "About & Safety": "ℹ️",
    }
    with st.sidebar:
        st.markdown("## 🥗 Food Verse AI")
        st.caption("Multimodal food intelligence")
        choice = st.radio("Choose a module", list(pages.keys()), format_func=lambda x: f"{pages[x]}  {x}")
        st.divider()
        client = get_client()
        if client:
            st.success(f"Gemini connected · {MODEL}")
        else:
            st.warning("Gemini API key not set")
            st.caption("Add GEMINI_API_KEY in Streamlit Cloud → Settings → Secrets.")
        st.markdown("---")
        st.caption("Food insights are estimates, not laboratory testing.")
    if choice == "Food & Nutrition":
        module_food_nutrition()
    elif choice == "Freshness Check":
        module_freshness()
    elif choice == "Kitchen Hygiene":
        module_hygiene()
    elif choice == "Recipe Assistant":
        module_recipes()
    elif choice == "Meal Planner":
        module_meal_planner()
    else:
        st.subheader("ℹ️ About Food Verse AI")
        st.markdown("""
**Food Verse AI** is a five-module food intelligence demo combining image-based food analysis with practical culinary and meal-planning assistance.

- **Food recognition & nutrition:** identifies likely dishes and estimates macros, ingredients, allergens and a health score.
- **Freshness assessment:** comments on visible freshness indicators only.
- **Kitchen hygiene:** highlights visible risks in a preparation area.
- **Recipe assistant:** generates recipes from available ingredients and dietary preferences.
- **Meal planner:** estimates BMR/TDEE and creates a weekly plan and grocery list.

### Important limitations
- Nutrition values inferred from images can be substantially inaccurate.
- A photo cannot identify invisible pathogens, toxins or internal spoilage. Never rely on appearance alone to determine food safety.
- The kitchen review is educational and is not an official inspection or certification.
- BMR/TDEE and meal plans are estimates, not medical advice. Consult a qualified professional for medical conditions, pregnancy, eating-disorder history or specialized diets.
        """)
    st.divider()
    st.markdown('<p class="small-note">Built with Streamlit + Google Gemini. Please verify AI-generated information before acting on it.</p>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
