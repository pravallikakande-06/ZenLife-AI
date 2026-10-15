# 🌿 ZenLife AI: Your Personal AI Health & Wellness Assistant

A Streamlit-only (Python) wellness app: profile & BMI, diet planner, calorie/nutrition tracker, hydration, exercise,
sleep, AI wellness chat, mood journal, analytics with a scikit-learn habit-clustering feature, reminders and goals.
Data is stored locally in SQLite.

> ZenLife AI gives **general wellness information only**. It is not a medical device and does not diagnose, treat, or
> replace professional care. BMI, calorie, nutrition and AI outputs are estimates.

## Features
| Page | What it does |
|---|---|
| Home (`app.py`) | Welcome, getting-started checklist, due reminders, quick links |
| 1 Dashboard | Today's calories/water/exercise/sleep/mood, weekly charts, progress summary, suggestions, optional AI note |
| 2 Profile | Name, age, height, weight, activity, diet, goals; BMI + interpretation; energy-needs estimate |
| 3 Diet Planner | Breakfast/lunch/dinner/snack plan for vegan, vegetarian or non-vegetarian diets, with alternatives, scaled to your calorie target; one-click logging |
| 4 Calorie Tracker | Log foods from `data/foods.csv` or manually; calories, protein, carbs, fat; goal progress; Plotly history |
| 5 Hydration | Quick-add buttons, custom goal, weekly trend, optional reminder |
| 6 Exercise | Beginner/intermediate/advanced weekly plan with rest days, activity log with MET-based calorie estimate, weekly progress |
| 7 Sleep Tracker | Log by times or duration, trends, bedtime consistency, target schedule, sleep-hygiene tips |
| 8 AI Wellness Chat | Streamlit chat with session history; real LLM if configured, honest offline fallback otherwise; clear "not a doctor" notice |
| 9 Mood Journal | Mood, stress, notes, prompts, relaxation exercises, trends; notes hidden on screen by default |
| 10 Analytics | Week-over-week comparison, trends, correlations, **K-means habit clusters**, CSV export |
| 11 Settings | Goals, reminders, optional SMTP email, AI status, data export, delete-all |

### Honesty notes
- **Machine learning:** K-means (scikit-learn) runs only when you have **14+ days** with sleep and mood entries. It reports the real silhouette score. Nothing is "pre-trained" and no accuracy is invented.
- **AI:** If no provider is configured, the app says so and uses clearly labelled rule-based guidance. It never fabricates an AI reply.
- **Nutrition values** in `data/foods.csv` are approximate per-100 g figures for testing, not verified lab data. Replace or extend the file with a trusted source for real use.
- **Reminders** show in the sidebar/Dashboard **only while the app is open**. There are no browser or background notifications. Email reminders are sent only when you click the button in Settings.

## Project structure
```
zenlife-ai/
├─ app.py                 # home page
├─ pages/                 # 1_Dashboard.py ... 11_Settings.py (Streamlit multipage)
├─ utils/
│  ├─ database.py         # SQLite schema + CRUD (parameterized SQL)
│  ├─ calculations.py     # BMI, BMR/TDEE, MET calories, helpers
│  ├─ recommendations.py  # meal/exercise plans, fallback advice, K-means
│  ├─ ai_service.py       # optional LLM (Anthropic / OpenAI-compatible / Ollama)
│  ├─ notifications.py    # in-app reminders + optional SMTP email
│  ├─ config.py           # env / .env / Streamlit secrets reader
│  └─ ui.py               # shared page setup, charts, widgets
├─ data/foods.csv         # sample food dataset (the DB file zenlife.db is created here)
├─ .streamlit/config.toml # sage / white / beige theme
├─ selftest.py            # backend smoke test
├─ requirements.txt  .env.example  .gitignore  assets/
```

## Windows setup (PowerShell)
1. Install **Python 3.10+** from python.org (tick *Add python.exe to PATH*).
2. Open PowerShell in the project folder and run:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```
3. Your browser opens at http://localhost:8501. The database is created automatically at `data/zenlife.db` and data persists between restarts.

If PowerShell blocks the activation script, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again.
To stop the app press `Ctrl+C` in the terminal. Optional check: `python selftest.py`.

### Optional: enable AI
Copy `.env.example` to `.env` (`copy .env.example .env`), set one provider (e.g. `ANTHROPIC_API_KEY=...` or `OPENAI_API_KEY=...`, or `AI_PROVIDER=ollama` for a local model), and restart. Keys are read from environment variables, `.env`, or `.streamlit/secrets.toml`, never from source code. Only general profile facts and your chat messages are sent; journal notes never are.

### Optional: passcode and email
Set `APP_PASSCODE` to require a passcode, and `SMTP_*` values for email reminders (see `.env.example`).

## Privacy & users
ZenLife is a **single-profile, local-first** app: there is no multi-user login, so every record belongs to one profile (`user_id = 1`) on the machine running it. Journal entries are not shared with anyone and not sent to the AI. **If you deploy it publicly, anyone with the URL could see the data**, so set `APP_PASSCODE` at minimum, or add real authentication and per-user rows first (all tables already carry `user_id`).

## Deployment notes
- **Local / home network:** `streamlit run app.py --server.address 0.0.0.0` (use a passcode).
- **Streamlit Community Cloud:** put keys in *Secrets*. The disk is ephemeral, so SQLite data can be lost on restart; use a persistent host or a hosted database for real use.
- **Docker/VPS:** mount a volume for `data/` and set `ZENLIFE_DB` to a path on it.

## Beginner debugging guide
| Symptom | Fix |
|---|---|
| `streamlit` is not recognized | Activate the venv (`.venv\Scripts\Activate.ps1`) and re-run `pip install -r requirements.txt` |
| `ModuleNotFoundError: utils` | Start from the project folder with `streamlit run app.py` (not from `pages/`) |
| "Database problem" message | Close other programs using `data/zenlife.db`; make sure the folder is writable; as a last resort rename the file to start fresh |
| Port already in use | `streamlit run app.py --server.port 8502` |
| AI replies say "Offline rule-based guidance" | No key found: check `.env` is in the project root, has no quotes/spaces around `=`, then restart |
| AI error (HTTP 401/404) | Wrong key or model name: set `AI_MODEL` |
| Changes to `.env` ignored | Stop (`Ctrl+C`) and restart Streamlit |
| Charts empty | Log some data first; charts show the last 7-90 days |
| Anything else | Read the terminal output (full traceback), or run `python selftest.py` to test the backend |

## Final verification checklist
- [ ] `streamlit run app.py` opens and `data/zenlife.db` appears
- [ ] Profile saves; BMI and interpretation show; page survives a browser refresh
- [ ] Diet Planner shows 4 meals with alternatives for each diet type; "Shuffle" changes the plan; "Log this meal" adds rows
- [ ] Calorie Tracker: dataset entry and manual entry both save; totals, progress bars and charts update; delete works
- [ ] Hydration: quick-add and custom amounts; goal change; weekly chart
- [ ] Exercise: plan shows rest days; logging computes kcal; weekly progress updates
- [ ] Sleep: both logging modes; re-saving the same date replaces it; target schedule updates the sleep goal
- [ ] Chat: shows "not a doctor" notice; answers (AI or labelled offline); history persists during the session; "Clear conversation" works
- [ ] Mood: entry saves; notes hidden until checkbox ticked; trend chart appears
- [ ] Dashboard and Analytics show data; CSV downloads work; clustering says "not enough data" until 14 days
- [ ] Reminders: enable one for a time already passed; it appears in the sidebar and Dashboard
- [ ] Settings: goals save; delete-all requires typing DELETE
- [ ] Stop and restart the app: all data is still there
