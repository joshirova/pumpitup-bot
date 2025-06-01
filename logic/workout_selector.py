# logic/workout_selector.py

import json
from pathlib import Path

WORKOUT_FILE = Path(__file__).resolve().parent.parent / "data" / "sample_workouts.json"

def select_workout_plan(goal, gender, age, level, workout_type, plan_index=0):
    """
    Возвращает одну тренировку из недельного плана по указанному индексу.

    :param goal: Цель ("Похудение", "Набор массы", "Поддержание формы")
    :param gender: "Мужчина" или "Женщина"
    :param age: возрастная категория ("16–20", "20–30", "30–40", "50+")
    :param level: "Новичок", "Средний", "Опытный"
    :param workout_type: "Дом" или "Зал"
    :param plan_index: индекс плана в диапазоне [0, 2]
    :return: dict { plan, duration, index }
    """
    with open(WORKOUT_FILE, "r", encoding="utf-8") as f:
        workouts = json.load(f)

    for workout in workouts:
        if (
            workout.get("goal") == goal and
            workout.get("gender") == gender and
            workout.get("age_group") == age and
            workout.get("level") == level and
            workout.get("type", "").lower() == workout_type.lower()
        ):
            plans = workout.get("plans", [])
            if plans and 0 <= plan_index < len(plans):
                selected = plans[plan_index]
                return {
                    "plan": selected.get("plan", []),
                    "duration": selected.get("duration", "—"),
                    "index": plan_index + 1
                }

    return {
        "plan": ["К сожалению, я пока не нашёл подходящую тренировку 😔"],
        "duration": "—",
        "index": "-"
    }
