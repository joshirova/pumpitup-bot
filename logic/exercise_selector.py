"""Уровень 3: rule-based подбор упражнений из Free Exercise DB.

Принимает план (modality, intensity, equipment) и профиль пользователя,
возвращает список из 5–8 упражнений. Применяет фильтры:
  • level упражнения соответствует уровню пользователя;
  • category упражнения совместима с modality плана;
  • equipment упражнения доступно пользователю;
  • травмы → исключение упражнений с риском;
  • медицинские состояния → исключение запрещённых протоколом категорий.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from config import EXERCISES_PATH, PROTOCOLS_PATH


# Соответствие модальности плана и категорий Free Exercise DB
MODALITY_TO_CATEGORIES = {
    "cardio_low":  ["cardio", "stretching"],
    "cardio_high": ["cardio", "plyometrics"],
    "strength":    ["strength", "powerlifting"],
    "mixed":       ["strength", "cardio", "stretching"],
}

# Соответствие equipment плана и equipment упражнений
EQUIPMENT_HOME = ["body only", "bands", "exercise ball", "foam roll",
                  "medicine ball", "dumbbell", "kettlebells", "other"]
EQUIPMENT_GYM = ["body only", "barbell", "machine", "cable", "dumbbell",
                 "e-z curl bar", "kettlebells", "exercise ball",
                 "medicine ball", "foam roll", "bands", "other"]

# Соответствие уровня пользователя и допустимых уровней упражнений
LEVEL_COMPATIBILITY = {
    "beginner":     ["beginner"],
    "intermediate": ["beginner", "intermediate"],
    "expert":       ["beginner", "intermediate", "expert"],
}

# Группы мышц с риском для каждой травмы (исключаются)
INJURY_RISK_GROUPS = {
    "knee":     ["quadriceps", "calves", "hamstrings"],
    "back":     ["lower back", "lats", "middle back"],
    "shoulder": ["shoulders", "chest"],
}

# Рискованные категории при травмах
INJURY_RISK_CATEGORIES = {
    "knee":     ["plyometrics"],
    "back":     ["plyometrics", "powerlifting", "olympic weightlifting"],
    "shoulder": ["powerlifting", "olympic weightlifting"],
}


class ExerciseSelector:
    def __init__(self) -> None:
        with open(EXERCISES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        # Free Exercise DB может быть как list, так и dict[name -> obj]
        self.exercises: list[dict] = list(data) if isinstance(data, list) else list(data.values())
        with open(PROTOCOLS_PATH, encoding="utf-8") as f:
            self.protocols = json.load(f)
        print(f"[ExerciseSelector] Загружено {len(self.exercises)} упражнений.")

    def _is_compatible(self, ex: dict, plan: dict, user: dict,
                        medical_conditions: list[str]) -> bool:
        ex_level = ex.get("level")
        ex_category = ex.get("category")
        ex_equipment = ex.get("equipment") or "body only"
        ex_primary = ex.get("primaryMuscles") or []

        # 1. Уровень
        allowed_levels = LEVEL_COMPATIBILITY[user["level"]]
        if ex_level not in allowed_levels:
            return False

        # 2. Категория ↔ модальность
        if ex_category not in MODALITY_TO_CATEGORIES.get(plan["modality"], []):
            return False

        # 3. Оборудование
        eq_pool = EQUIPMENT_GYM if plan["equipment"] == "gym" else EQUIPMENT_HOME
        if ex_equipment not in eq_pool:
            return False

        # 4. Травмы
        injury = user.get("injury_history", "none")
        if injury != "none" and injury != "multiple":
            if ex_category in INJURY_RISK_CATEGORIES.get(injury, []):
                return False
            risk_groups = INJURY_RISK_GROUPS.get(injury, [])
            if any(m.lower() in [g.lower() for g in risk_groups] for m in ex_primary):
                return False
        elif injury == "multiple":
            for inj in ("knee", "back", "shoulder"):
                if ex_category in INJURY_RISK_CATEGORIES.get(inj, []):
                    return False
                risk_groups = INJURY_RISK_GROUPS.get(inj, [])
                if any(m.lower() in [g.lower() for g in risk_groups] for m in ex_primary):
                    return False

        # 5. Медицинские состояния — запрещённые категории по протоколу
        for cond in medical_conditions:
            if cond == "none" or cond not in self.protocols:
                continue
            forbidden = self.protocols[cond].get("forbidden_categories", [])
            if ex_category in forbidden:
                return False

        return True

    def select(self, plan: dict, user: dict,
               medical_conditions: list[str], n: int,
               used_exercise_names: set[str] | None = None,
               seed: int | None = None) -> list[dict]:
        """Возвращает n упражнений для одной тренировочной сессии.

        Применяет каскадный fallback: если строгий фильтр даёт мало
        кандидатов, постепенно ослабляем условия. Безопасные правила
        (травмы, противопоказания) НЕ ослабляются никогда.
        """
        used_exercise_names = used_exercise_names or set()
        rng = random.Random(seed)

        # Шаг 1: строгий фильтр + исключение использованных
        compatible = [
            ex for ex in self.exercises
            if self._is_compatible(ex, plan, user, medical_conditions)
            and ex.get("name") not in used_exercise_names
        ]

        # Шаг 2: разрешаем повторы из used (если строгий фильтр дал мало)
        if len(compatible) < n:
            extra = [ex for ex in self.exercises
                     if self._is_compatible(ex, plan, user, medical_conditions)
                     and ex not in compatible]
            compatible.extend(extra)

        # Шаг 3: расширенный набор категорий (если совсем мало)
        # Берём ВСЕ категории Free Exercise DB, кроме явно опасных
        if len(compatible) < n:
            broader = [
                ex for ex in self.exercises
                if self._is_compatible_relaxed(ex, plan, user, medical_conditions)
                and ex not in compatible
            ]
            compatible.extend(broader)

        rng.shuffle(compatible)
        return compatible[:n]

    def _is_compatible_relaxed(self, ex: dict, plan: dict, user: dict,
                                medical_conditions: list[str]) -> bool:
        """Ослабленный фильтр — НЕ ослабляет травмы и медицинские
        противопоказания, ослабляет только category/level/equipment.
        """
        ex_category = ex.get("category")
        ex_primary = ex.get("primaryMuscles") or []

        # Травмы — НЕ ослабляем
        injury = user.get("injury_history", "none")
        injuries_to_check = [injury] if injury != "multiple" else ["knee", "back", "shoulder"]
        for inj in injuries_to_check:
            if inj == "none":
                continue
            if ex_category in INJURY_RISK_CATEGORIES.get(inj, []):
                return False
            risk_groups = INJURY_RISK_GROUPS.get(inj, [])
            if any(m.lower() in [g.lower() for g in risk_groups] for m in ex_primary):
                return False

        # Медпротоколы — НЕ ослабляем
        for cond in medical_conditions:
            if cond == "none" or cond not in self.protocols:
                continue
            forbidden = self.protocols[cond].get("forbidden_categories", [])
            if ex_category in forbidden:
                return False

        # А вот категорию относительно модальности и оборудование — ослабляем
        return True
