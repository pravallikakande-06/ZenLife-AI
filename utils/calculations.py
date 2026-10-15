"""Health-related calculations. All outputs are general estimates, not medical advice."""
from datetime import time

ACTIVITY_LEVELS = {
    "Sedentary (little or no exercise)": 1.2,
    "Lightly active (1-3 days/week)": 1.375,
    "Moderately active (3-5 days/week)": 1.55,
    "Very active (6-7 days/week)": 1.725,
}
DIET_PREFS = ["Non-vegetarian", "Vegetarian", "Vegan"]
DIET_RANK = {"Vegan": 0, "Vegetarian": 1, "Non-vegetarian": 2}
SEX_OPTIONS = ["Prefer not to say", "Female", "Male"]
GOALS = ["Lose weight", "Maintain weight", "Build muscle", "Improve fitness",
         "Eat healthier", "Sleep better", "Reduce stress", "Stay hydrated"]
MOODS = {1: "😞 Very low", 2: "😕 Low", 3: "😐 Okay", 4: "🙂 Good", 5: "😄 Great"}

# Approximate MET values (Compendium of Physical Activities style estimates).
ACTIVITY_MET = {
    "Walking (easy)": 3.0, "Walking (brisk)": 4.3, "Yoga": 2.5, "Stretching": 2.3,
    "Jogging / running": 7.0, "Cycling": 6.8, "Cardio workout": 6.0, "HIIT": 8.0,
    "Strength training": 5.0, "Swimming": 6.0, "Dancing": 5.0, "Other": 4.0,
}


def bmi(weight_kg, height_cm):
    return weight_kg / ((height_cm / 100) ** 2)


def bmi_interpretation(value):
    if value < 18.5:
        cat = "Below the typical adult range"
    elif value < 25:
        cat = "Within the typical adult range"
    elif value < 30:
        cat = "Above the typical adult range"
    else:
        cat = "Well above the typical adult range"
    msg = ("BMI is a rough screening number. It doesn't measure body fat, muscle, age, or overall health, "
           "and it can be misleading for athletes, older adults, and some ethnic groups. "
           "It is not a diagnosis; a healthcare professional can interpret it for you.")
    return cat, msg


def bmr(weight_kg, height_cm, age, sex):
    """Mifflin-St Jeor. If sex is not given, use the midpoint of the two constants."""
    const = {"Male": 5, "Female": -161}.get(sex, -78)
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + const


def tdee(bmr_value, activity_level):
    return bmr_value * ACTIVITY_LEVELS.get(activity_level, 1.2)


def suggested_calories(tdee_value, goals_text=""):
    target = tdee_value
    if "Lose weight" in goals_text:
        target -= 400
    elif "Build muscle" in goals_text:
        target += 250
    return int(max(1200, round(target / 50) * 50))


def suggested_water_ml(weight_kg):
    return int(round(weight_kg * 33 / 50) * 50)


def calories_burned(activity, weight_kg, minutes):
    return round(ACTIVITY_MET.get(activity, 4.0) * weight_kg * minutes / 60)


def parse_hhmm(text, default="22:30"):
    h, m = (text or default).split(":")
    return time(int(h), int(m))


def duration_hours(bed, wake):
    """Hours slept between a bedtime and a wake time (crosses midnight if needed)."""
    minutes = ((wake.hour * 60 + wake.minute) - (bed.hour * 60 + bed.minute)) % 1440
    return round(minutes / 60, 2)


def pct(value, goal):
    if not goal:
        return 0.0
    return float(min(max(value / goal, 0.0), 1.0))
