"""Rule-based recommendations, meal plans, exercise plans and a real (honestly reported) ML feature.
Nothing here is medical advice. Nutrition values come from data/foods.csv (approximate, per 100 g)."""
import random
from functools import lru_cache

import pandas as pd

from utils.calculations import DIET_RANK
from utils.database import ROOT

DISCLAIMER = ("General wellness information only. Estimates are approximate and are not medical advice, "
              "a diagnosis, or a treatment plan.")

# ---------------------------------------------------------------- foods
@lru_cache(maxsize=1)
def load_foods():
    path = ROOT / "data" / "foods.csv"
    try:
        df = pd.read_csv(path)
    except (FileNotFoundError, pd.errors.ParserError) as e:
        raise RuntimeError(f"Could not read {path}: {e}") from e
    needed = {"name", "category", "diet", "calories", "protein", "carbs", "fat"}
    if not needed.issubset(df.columns):
        raise RuntimeError(f"foods.csv must contain columns: {sorted(needed)}")
    return df.set_index("name", drop=False)


def food_nutrition(name, grams):
    row = load_foods().loc[name]
    f = grams / 100.0
    return {k: round(float(row[k]) * f, 1) for k in ("calories", "protein", "carbs", "fat")}


def _sum_nutrition(items, scale=1.0):
    total = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for food, grams in items:
        for k, v in food_nutrition(food, grams * scale).items():
            total[k] += v
    return {k: round(v) for k, v in total.items()}


# ---------------------------------------------------------------- meal templates
# (meal, minimum diet level, name, [(food, grams)])
TEMPLATES = [
    ("Breakfast", "Vegan", "Oats with banana & chia", [("Rolled oats", 50), ("Soy milk (unsweetened)", 200), ("Banana", 100), ("Chia seeds", 10)]),
    ("Breakfast", "Vegan", "Peanut butter toast with fruit", [("Whole wheat bread", 70), ("Peanut butter", 20), ("Apple", 150)]),
    ("Breakfast", "Vegan", "Tofu scramble with veggies", [("Tofu (firm)", 150), ("Spinach", 50), ("Tomato", 80), ("Whole wheat bread", 50)]),
    ("Breakfast", "Vegetarian", "Greek yogurt, granola & berries", [("Greek yogurt", 170), ("Granola", 30), ("Blueberries", 80)]),
    ("Breakfast", "Vegetarian", "Boiled eggs, toast & orange", [("Egg (boiled)", 100), ("Whole wheat bread", 60), ("Orange", 130)]),
    ("Breakfast", "Vegetarian", "Idli with dal", [("Idli", 150), ("Lentils/dal (cooked)", 120)]),
    ("Breakfast", "Non-vegetarian", "Egg & avocado toast", [("Egg (boiled)", 100), ("Whole wheat bread", 60), ("Avocado", 50)]),
    ("Lunch", "Vegan", "Quinoa chickpea bowl", [("Quinoa (cooked)", 150), ("Chickpeas (cooked)", 120), ("Cucumber", 80), ("Tomato", 80), ("Olive oil", 8)]),
    ("Lunch", "Vegan", "Dal, brown rice & salad", [("Lentils/dal (cooked)", 200), ("Brown rice (cooked)", 150), ("Mixed salad greens", 60)]),
    ("Lunch", "Vegan", "Black bean & sweet potato bowl", [("Black beans (cooked)", 150), ("Sweet potato (baked)", 150), ("Avocado", 50), ("Mixed salad greens", 50)]),
    ("Lunch", "Vegetarian", "Paneer, chapati & salad", [("Paneer", 100), ("Chapati (roti)", 90), ("Mixed salad greens", 60), ("Cucumber", 60)]),
    ("Lunch", "Vegetarian", "Egg & broccoli quinoa bowl", [("Egg (boiled)", 100), ("Quinoa (cooked)", 150), ("Broccoli", 100), ("Olive oil", 6)]),
    ("Lunch", "Non-vegetarian", "Grilled chicken, rice & broccoli", [("Chicken breast (cooked)", 130), ("Brown rice (cooked)", 150), ("Broccoli", 100), ("Olive oil", 5)]),
    ("Lunch", "Non-vegetarian", "Tuna salad bowl", [("Tuna (canned in water)", 100), ("Mixed salad greens", 80), ("Chickpeas (cooked)", 80), ("Olive oil", 8), ("Whole wheat bread", 40)]),
    ("Dinner", "Vegan", "Tempeh stir-fry with rice", [("Tempeh", 120), ("Broccoli", 120), ("Carrot", 60), ("Brown rice (cooked)", 150), ("Olive oil", 8)]),
    ("Dinner", "Vegan", "Tofu & spinach curry with chapati", [("Tofu (firm)", 150), ("Tomato", 100), ("Spinach", 80), ("Chapati (roti)", 80)]),
    ("Dinner", "Vegan", "Pasta with chickpeas & spinach", [("Whole wheat pasta (cooked)", 180), ("Chickpeas (cooked)", 100), ("Spinach", 60), ("Olive oil", 8)]),
    ("Dinner", "Vegetarian", "Paneer & vegetable curry with rice", [("Paneer", 100), ("Tomato", 100), ("Spinach", 80), ("Brown rice (cooked)", 150)]),
    ("Dinner", "Vegetarian", "Lentil soup with cheese toast", [("Lentils/dal (cooked)", 250), ("Whole wheat bread", 50), ("Cheddar cheese", 20)]),
    ("Dinner", "Non-vegetarian", "Baked salmon with sweet potato", [("Salmon (cooked)", 130), ("Sweet potato (baked)", 150), ("Broccoli", 100)]),
    ("Dinner", "Non-vegetarian", "Shrimp stir-fry with rice", [("Shrimp (cooked)", 130), ("Brown rice (cooked)", 150), ("Broccoli", 100), ("Carrot", 50), ("Olive oil", 8)]),
    ("Dinner", "Non-vegetarian", "Lean beef, potato & spinach", [("Lean beef (cooked)", 100), ("Potato (boiled)", 150), ("Spinach", 80)]),
    ("Dinner", "Non-vegetarian", "Cod with quinoa & greens", [("Cod (cooked)", 150), ("Quinoa (cooked)", 120), ("Spinach", 80)]),
    ("Snack", "Vegan", "Hummus with carrot sticks", [("Hummus", 50), ("Carrot", 100)]),
    ("Snack", "Vegan", "Apple with almonds", [("Apple", 150), ("Almonds", 20)]),
    ("Snack", "Vegan", "Orange & walnuts", [("Orange", 150), ("Walnuts", 15)]),
    ("Snack", "Vegetarian", "Greek yogurt with walnuts", [("Greek yogurt", 150), ("Walnuts", 15)]),
    ("Snack", "Vegetarian", "Banana with a glass of milk", [("Banana", 100), ("Milk (whole)", 200)]),
    ("Snack", "Non-vegetarian", "Boiled egg & cucumber", [("Egg (boiled)", 50), ("Cucumber", 100), ("Whole wheat bread", 30)]),
]
MEAL_SHARE = {"Breakfast": 0.25, "Lunch": 0.35, "Dinner": 0.30, "Snack": 0.10}


def _scaled(template, target_kcal):
    meal, _, name, items = template
    base = _sum_nutrition(items)["calories"] or 1
    scale = min(max(target_kcal / base, 0.7), 1.5)
    scaled = [(f, int(round(g * scale / 5) * 5) or 5) for f, g in items]
    return {"meal": meal, "name": name, "items": scaled, **_sum_nutrition(scaled)}


def generate_meal_plan(diet_pref, calorie_target, seed):
    rng = random.Random(seed)
    rank = DIET_RANK.get(diet_pref, 2)
    plan = []
    for meal, share in MEAL_SHARE.items():
        options = [t for t in TEMPLATES if t[0] == meal and DIET_RANK[t[1]] <= rank]
        rng.shuffle(options)
        main, alts = options[0], options[1:3]
        target = calorie_target * share
        entry = _scaled(main, target)
        entry["alternatives"] = [_scaled(a, target) for a in alts]
        plan.append(entry)
    return plan


# ---------------------------------------------------------------- exercise
EXERCISES = {
    "Walking": {"Beginner": ("Easy walk at a comfortable, conversational pace", 20),
                "Intermediate": ("Brisk walk; add a few hills or stairs", 35),
                "Advanced": ("Power walk or incline walk with short faster intervals", 50)},
    "Yoga": {"Beginner": ("Gentle flow: cat-cow, child's pose, downward dog, seated twist", 20),
             "Intermediate": ("Sun salutations and standing poses, holding each 5 breaths", 35),
             "Advanced": ("Longer flow with balance poses and deeper holds", 50)},
    "Stretching": {"Beginner": ("Neck, shoulders, hamstrings, hips, calves: hold each 20-30 s", 15),
                   "Intermediate": ("Full-body stretch with hip and spine mobility", 20),
                   "Advanced": ("Extended mobility session, including thoracic and hip work", 25)},
    "Cardio": {"Beginner": ("Low impact: marching in place, step-touch, or easy cycling", 15),
               "Intermediate": ("Jog or cycle intervals: 1 min harder, 2 min easy", 30),
               "Advanced": ("30 s hard / 60 s easy x 10 after a proper warm-up", 40)},
    "Strength": {"Beginner": ("Bodyweight basics: sit-to-stand, wall push-ups, glute bridges, 2 sets of 8-10", 20),
                 "Intermediate": ("Squats, push-ups, rows, plank: 3 sets of 10-12", 35),
                 "Advanced": ("Progressive compound lifts or circuits, 3-4 sets, rest 60-90 s", 45)},
}
REST_DAY_IDEAS = ["Easy 10-20 minute walk", "Gentle stretching or foam rolling", "Light yoga or breathing practice",
                  "Complete rest: recovery is part of training"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_PATTERN = {3: [0, 2, 4], 4: [0, 1, 3, 5], 5: [0, 1, 2, 4, 5]}


def weekly_exercise_plan(level, prefs):
    prefs = prefs or list(EXERCISES)
    n = {"Beginner": 3, "Intermediate": 4, "Advanced": 5}[level]
    active, plan, k = _PATTERN[n], [], 0
    for i, day in enumerate(DAYS):
        if i in active:
            kind = prefs[k % len(prefs)]
            k += 1
            desc, mins = EXERCISES[kind][level]
            plan.append({"Day": day, "Activity": kind, "What to do": desc, "Minutes": mins})
        else:
            plan.append({"Day": day, "Activity": "Rest day", "What to do": REST_DAY_IDEAS[i % len(REST_DAY_IDEAS)], "Minutes": 0})
    return plan


# ---------------------------------------------------------------- sleep / mood content
SLEEP_TIPS = [
    "Keep a consistent bedtime and wake time, even on weekends.",
    "Get daylight in the morning and dim lights in the hour before bed.",
    "Keep the bedroom cool, dark and quiet.",
    "Avoid caffeine in the afternoon and large meals close to bedtime.",
    "Put screens away 30-60 minutes before bed, or use a wind-down routine such as reading.",
    "If you can't fall asleep after ~20 minutes, get up, do something calm, and return when sleepy.",
]
JOURNAL_PROMPTS = ["What is one thing that went well today?", "What is taking most of your energy right now?",
                   "Name three things you're grateful for today.", "What would make tomorrow feel 10% better?",
                   "What did your body need today, and did it get it?", "Describe a moment today when you felt calm."]
RELAXATION = {
    "Box breathing (2 min)": "Inhale for 4 counts, hold 4, exhale 4, hold 4. Repeat for about 8 rounds.",
    "5-4-3-2-1 grounding": "Notice 5 things you see, 4 you can touch, 3 you hear, 2 you smell, 1 you taste.",
    "Body scan (5 min)": "Lying down, move attention slowly from your toes to your head, softening each area as you go.",
    "Progressive muscle relaxation": "Tense each muscle group for 5 seconds, then release for 10, from feet up to face.",
}


# ---------------------------------------------------------------- summaries and fallback advice
def progress_summary(daily, goals):
    lines = []
    logged = daily[daily["calories"] > 0]
    if len(logged):
        lines.append(f"Calories: averaged {logged['calories'].mean():.0f} kcal on {len(logged)} logged day(s) (goal {goals['calories']:.0f}).")
    wd = daily[daily["water_ml"] > 0]
    if len(wd):
        met = int((daily["water_ml"] >= goals["water_ml"]).sum())
        lines.append(f"Hydration: reached your goal on {met} of {len(daily)} days; average {daily['water_ml'].mean():.0f} ml/day.")
    lines.append(f"Exercise: {daily['exercise_min'].sum():.0f} minutes in this period (weekly goal {goals['exercise_week']:.0f}).")
    if daily["sleep_hours"].notna().any():
        lines.append(f"Sleep: averaged {daily['sleep_hours'].mean():.1f} h per logged night (goal {goals['sleep_hours']:.1f} h).")
    if daily["mood"].notna().any():
        lines.append(f"Mood: average {daily['mood'].mean():.1f}/5, stress {daily['stress'].mean():.1f}/10 on logged days.")
    return lines


def fallback_recommendations(daily, goals):
    tips = []
    if daily["calories"].gt(0).sum() == 0:
        tips.append("Log a few meals so ZenLife can show how your intake compares with your goal.")
    if daily["water_ml"].mean() < 0.7 * goals["water_ml"]:
        tips.append("Water intake is below 70% of your goal on average: try a glass with each meal and one on waking.")
    if daily["sleep_hours"].notna().any() and daily["sleep_hours"].mean() < goals["sleep_hours"] - 1:
        tips.append("Sleep is more than an hour under target on average: try moving bedtime 15 minutes earlier each few days.")
    if daily["exercise_min"].sum() < goals["exercise_week"] * len(daily) / 7:
        tips.append("Activity is behind your weekly goal: a 10-minute walk after a meal is an easy way to add minutes.")
    if daily["stress"].notna().any() and daily["stress"].mean() >= 7:
        tips.append("Stress has been high: consider the relaxation exercises in the Mood Journal, and talk to someone you trust or a professional if it persists.")
    tips.append("Small, consistent habits matter more than perfect days.")
    return tips


RED_FLAGS = ["chest pain", "can't breathe", "cannot breathe", "shortness of breath", "faint", "blood in", "suicid",
             "kill myself", "self-harm", "self harm", "overdose", "severe pain", "stroke", "seizure", "unconscious"]
EMERGENCY_NOTE = ("⚠️ What you describe may need urgent attention. I can't assess it. Please contact a doctor or your local "
                  "emergency services now, or reach out to a crisis line if you're thinking about harming yourself.\n\n")


def red_flag(text):
    t = text.lower()
    return any(k in t for k in RED_FLAGS)


def fallback_chat_reply(question, profile):
    q = question.lower()
    diet = (profile or {}).get("diet_pref", "").lower() or "your"
    if any(w in q for w in ("water", "hydrat", "thirst")):
        body = ("A common rule of thumb is roughly 30-35 ml of fluid per kg of body weight per day, from drinks and food. "
                "Needs vary with heat, activity and health conditions. Pale-yellow urine is a rough guide.")
    elif any(w in q for w in ("sleep", "insomnia", "tired", "nap")):
        body = "Most adults do well with 7-9 hours. " + " ".join(SLEEP_TIPS[:3]) + " Long-term trouble sleeping is worth discussing with a clinician."
    elif any(w in q for w in ("protein", "diet", "eat", "meal", "food", "calorie", "nutrition")):
        body = (f"A balanced plate: roughly half vegetables and fruit, a quarter protein ({diet} options such as lentils, tofu, "
                "eggs, dairy or fish as fits you), and a quarter whole grains, plus some healthy fats. "
                "The Diet Planner page can build a sample day.")
    elif any(w in q for w in ("exercise", "workout", "walk", "gym", "run", "yoga", "strength", "fitness")):
        body = ("Adults are generally encouraged to aim for about 150 minutes of moderate activity a week plus two strength sessions. "
                "Start small, increase gradually, and take rest days. Check with a clinician before starting if you have health concerns.")
    elif any(w in q for w in ("stress", "anxi", "mood", "sad", "overwhelm", "relax")):
        body = ("Try slow breathing (inhale 4, exhale 6), a short walk, or writing down what's on your mind. "
                "If low mood or anxiety lasts or affects daily life, please talk to a mental-health professional.")
    elif any(w in q for w in ("weight", "lose", "fat")):
        body = ("Gradual change tends to be more sustainable: a modest calorie gap, protein and fibre at meals, regular movement and good sleep. "
                "For a personal target, ask a doctor or registered dietitian.")
    else:
        body = ("I can share general guidance on nutrition, exercise, hydration, sleep and stress. "
                "Try asking something like \"How much water should I drink?\" or \"How can I sleep better?\"")
    return body + "\n\n*Offline guidance: rule-based, not AI-generated. I'm not a doctor and can't diagnose or treat conditions.*"


# ---------------------------------------------------------------- machine learning
ML_FEATURES = ["water_ml", "exercise_min", "sleep_hours", "mood", "stress"]
ML_MIN_DAYS = 14


def cluster_habits(daily):
    """K-means over days with sleep + mood data. Returns an honest status; nothing is faked."""
    data = daily.dropna(subset=["sleep_hours", "mood", "stress"])[ML_FEATURES]
    if len(data) < ML_MIN_DAYS:
        return {"status": "insufficient", "n": len(data), "needed": ML_MIN_DAYS}
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler
    X = StandardScaler().fit_transform(data)
    best = None
    try:
        for k in range(2, min(4, len(data) // 5) + 1):
            labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(X)
            score = silhouette_score(X, labels)
            if best is None or score > best[0]:
                best = (score, k, labels)
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    if best is None:
        return {"status": "error", "message": "Not enough variety in the data to form clusters."}
    score, k, labels = best
    out = data.copy()
    out["cluster"] = labels + 1
    profile = out.groupby("cluster").mean().round(2)
    profile.insert(0, "days", out.groupby("cluster").size())
    return {"status": "ok", "n": len(data), "k": k, "silhouette": float(score), "data": out, "profiles": profile}
