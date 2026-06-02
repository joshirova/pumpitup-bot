"""Клинические правила и вычисление производных признаков пользователя.

Источники:
  • WHO Physical Activity Guidelines 2020
  • ACSM's Guidelines for Exercise Testing and Prescription, 11th edition (2021)
  • ACSM Exercise is Medicine Rx Series
"""

from __future__ import annotations


def compute_bmi(weight_kg: float, height_cm: float) -> float:
    """ИМТ по формуле ВОЗ."""
    h_m = height_cm / 100.0
    return round(weight_kg / (h_m * h_m), 2)


def estimate_fat_percentage(bmi: float, age: int, gender: str) -> float:
    """Оценка процента жира по формуле Deurenberg (1991), если пользователь не знает.
    %fat = 1.20 * BMI + 0.23 * age - 10.8 * sex - 5.4
    sex = 1 для мужчин, 0 для женщин.
    """
    sex = 1 if gender == "male" else 0
    fat = 1.20 * bmi + 0.23 * age - 10.8 * sex - 5.4
    return round(max(8.0, min(45.0, fat)), 1)


def age_group_from_age(age: int) -> str:
    if age <= 20:
        return "16-20"
    if age <= 30:
        return "20-30"
    if age <= 40:
        return "30-40"
    if age <= 50:
        return "40-50"
    return "50+"


def goal_from_profile(bmi: float, fat_percentage: float,
                      stated_goal: str | None = None) -> str:
    """Если пользователь не указал цель — выводим из BMI/жира.
    Если указал — приоритет за пользователем (но проверяем согласованность).
    """
    objective_goal = "weight_loss" if (bmi >= 30 or fat_percentage > 30) else (
                     "muscle_gain" if (bmi < 18.5 or fat_percentage < 12) else
                     "maintenance")
    if stated_goal in ("weight_loss", "muscle_gain", "maintenance"):
        return stated_goal
    return objective_goal


def max_heart_rate(age: int) -> int:
    """Формула Tanaka (2001): HR_max = 208 - 0.7 * age. Точнее, чем 220-age."""
    return int(208 - 0.7 * age)


def target_hr_range(age: int, intensity: str) -> tuple[int, int]:
    """Диапазон ЧСС для заданной интенсивности."""
    from config import HR_INTENSITY_MAP
    pct_lo, pct_hi = HR_INTENSITY_MAP.get(intensity, (40, 60))
    hr_max = max_heart_rate(age)
    return int(hr_max * pct_lo / 100), int(hr_max * pct_hi / 100)


def build_user_features(profile: dict) -> dict:
    """Собирает 15 признаков для подачи в XGBoost."""
    bmi = compute_bmi(profile["weight_kg"], profile["height_cm"])
    fat = profile.get("fat_percentage")
    if fat is None:
        fat = estimate_fat_percentage(bmi, profile["age"], profile["gender"])
    return {
        "gender": profile["gender"],
        "age": profile["age"],
        "age_group": age_group_from_age(profile["age"]),
        "bmi": bmi,
        "fat_percentage": fat,
        "level": profile["level"],
        "equipment_pref": profile["equipment_pref"],
        "goal": goal_from_profile(bmi, fat, profile.get("stated_goal")),
        "injury_history": profile.get("injury_history", "none"),
        "weekly_frequency": profile.get("weekly_frequency", 3),
        "activity_level": profile.get("activity_level", "light"),
    }


def is_plan_contraindicated(user: dict, plan: dict,
                             medical_conditions: list[str],
                             protocols: dict) -> tuple[bool, str | None]:
    """Жёсткие противопоказания. Возвращает (is_contra, причина).
    Эта проверка дублирует часть правил релевантности модели для safety —
    модель ML не должна быть единственной точкой контроля противопоказаний.
    """
    if user["bmi"] >= 35 and (
        plan["modality"] == "cardio_high" or plan["intensity"] == "high"
    ):
        return True, "Ожирение II–III степени (ИМТ ≥ 35)"

    if user["age"] >= 50 and plan["modality"] == "cardio_high":
        return True, "Возраст 50+ — высокоударные нагрузки не рекомендуются"

    if user["level"] == "beginner" and plan["intensity"] == "high":
        return True, "Высокая интенсивность не рекомендуется новичкам"

    if user["activity_level"] == "sedentary" and plan["intensity"] == "high":
        return True, "Сидячий образ жизни — нужна постепенная адаптация"

    injury = user.get("injury_history", "none")
    if injury in ("knee", "multiple") and plan["modality"] == "cardio_high":
        return True, "Травма колена — высокоударные нагрузки противопоказаны"
    if injury in ("back", "multiple") and (
        plan["modality"] == "strength" and plan["intensity"] == "high"
    ):
        return True, "Травма спины — высокоинтенсивная силовая исключена"
    if injury in ("shoulder", "multiple") and (
        plan["modality"] == "strength" and plan["intensity"] == "high"
    ):
        return True, "Травма плеча — высокоинтенсивная силовая исключена"

    # Медицинские состояния
    for cond in medical_conditions:
        if cond == "none" or cond not in protocols:
            continue
        proto = protocols[cond]
        if plan["modality"] in proto.get("forbidden_modalities", []):
            return True, f"{proto['name_ru']}: модальность противопоказана"
        max_int = proto.get("max_intensity")
        if max_int:
            order = ["low", "moderate", "high"]
            if order.index(plan["intensity"]) > order.index(max_int):
                return True, f"{proto['name_ru']}: интенсивность выше допустимой"

    if user["weekly_frequency"] < plan["weekly_frequency_target"] - 1:
        return True, "Целевая частота плана выше готовности пользователя"

    return False, None
