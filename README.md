# Food Verse AI — Streamlit Edition

A Streamlit app with five AI-assisted food intelligence modules:
1. Food recognition and estimated nutrition
2. Visible freshness assessment
3. Kitchen hygiene review
4. Smart recipe assistant
5. Personalized 7-day meal planner and grocery list

## Run locally

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

Set your Gemini key as an environment variable (do not commit it):
```powershell
# Windows PowerShell
$env:GEMINI_API_KEY="YOUR_KEY_HERE"
streamlit run app.py
```
```bash
# macOS/Linux
export GEMINI_API_KEY="YOUR_KEY_HERE"
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Create a GitHub repository and upload the contents of this folder.
2. In Streamlit Community Cloud, choose **Create app** and select the repository, branch, and `app.py`.
3. Open app settings → **Secrets** and add:

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_MODEL = "gemini-2.5-flash"
```

4. Deploy. Never commit your actual API key to GitHub.

## Notes and limitations

- Gemini-powered features require a valid Google Gemini API key and may incur API usage.
- Nutrition values and visual assessments are estimates. A photo cannot detect invisible foodborne pathogens or guarantee safety.
- The kitchen review is educational, not a regulatory inspection.
- BMR/TDEE and meal plans are estimates and are not medical advice.
