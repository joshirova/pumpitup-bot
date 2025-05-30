# logic/workout_selector.py
import json
from pathlib import Path

WORKOUT_FILE = Path(__file__).resolve().parent.parent / "data" / "sample_workouts.json"

def select_workout(goal, gender, age, level, workout_type, plan_index=0):
    """
    Возвращает подходящий тренировочный план на основе входных параметров.
    
    :param goal: Цель тренировки ("Похудение", "Поддержание формы", "Набор массы")
    :param gender: Пол ("Мужчина" или "Женщина")
    :param age: Возраст ("До 60" или "60+")
    :param level: Уровень подготовки ("Новичок", "Средний", "Опытный")
    :param workout_type: Тип тренировки ("Дом" или "Зал")
    :param plan_index: Индекс плана в списке тренировок (0, 1, 2)
    :return: dict с ключами plan, duration, index
    """
    with open(WORKOUT_FILE, "r", encoding="utf-8") as f:
        workouts = json.load(f)

    # Приведение возраста к нужному формату
    age_group = "60+" if age == "60+" else "До 60"

    # Поиск соответствующей категории
    for workout in workouts:
        if (
            workout.get("goal") == goal and
            workout.get("gender") == gender and
            workout.get("age_group") == age_group and
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

    # Если ничего не найдено
    return {
        "plan": ["К сожалению, я пока не нашел подходящую тренировку 😔"],
        "duration": "—",
        "index": "-"
    }