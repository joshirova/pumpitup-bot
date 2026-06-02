"""Сборка тренировочного цикла на 1–3 недели.

Принцип: за весь цикл (3, 6 или 9 тренировок) ни одно упражнение
не повторяется. Если кандидатов в каталоге достаточно — это удаётся;
если нет, делаем второй проход с разрешением повторов.
"""

from __future__ import annotations

import random


WEEKDAY_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг",
                 "Пятница", "Суббота", "Воскресенье"]


def _select_weekdays(freq_per_week: int) -> list[str]:
    """Распределяет тренировки по неделе с учётом восстановления."""
    schedules = {
        2: ["Понедельник", "Четверг"],
        3: ["Понедельник", "Среда", "Пятница"],
        4: ["Понедельник", "Вторник", "Четверг", "Пятница"],
        5: ["Понедельник", "Вторник", "Среда", "Пятница", "Суббота"],
    }
    return schedules.get(freq_per_week, schedules[3])


class CycleBuilder:
    def __init__(self, ranking_service, load_regressor, exercise_selector):
        self.ranker = ranking_service
        self.load_reg = load_regressor
        self.exercises = exercise_selector

    def build(self, user_features: dict, profile: dict,
              medical_conditions: list[str],
              weeks: int = 1,
              trainings_per_week: int = 3) -> dict:
        """Главный метод. Возвращает структуру:
        {
            "weeks": [
                {
                    "week_number": 1,
                    "trainings": [
                        {
                            "weekday": "Понедельник",
                            "plan": {...},
                            "load": {sets, reps, rest_sec, rpe},
                            "hr_target": (int, int) | None,
                            "exercises": [...]
                        },
                        ...
                    ]
                },
                ...
            ],
            "user_summary": {...},
            "applied_protocols": [list of protocol names]
        }
        """
        from logic.clinical_rules import target_hr_range

        total_trainings = weeks * trainings_per_week
        weekdays = _select_weekdays(trainings_per_week)

        # Уровень 1: ML-ранжирование с safety-фильтром по протоколам.
        # Берём с запасом, чтобы потом отфильтровать.
        n_pool = max(total_trainings * 2, 9)
        candidates = self.ranker.select_top_diverse(
            user_features, n_pool,
            medical_conditions=medical_conditions,
            protocols=self.exercises.protocols,
        )

        # Берём первые total_trainings из ранжированного списка
        chosen_plans = [c[0] for c in candidates[:total_trainings]]

        # Накопитель использованных упражнений (для уникальности по всему циклу)
        used_exercise_names: set[str] = set()
        rng = random.Random(42)

        weeks_data = []
        idx = 0
        for week_num in range(1, weeks + 1):
            trainings = []
            for day_idx, weekday in enumerate(weekdays[:trainings_per_week]):
                plan = chosen_plans[idx]
                idx += 1

                # Уровень 2: ML-регрессор нагрузки
                load = self.load_reg.predict(
                    age=profile["age"],
                    bmi=user_features["bmi"],
                    level=profile["level"],
                    goal=user_features["goal"],
                    intensity=plan["intensity"],
                    injury=profile.get("injury_history", "none"),
                )

                # Целевая ЧСС (для cardio/mixed)
                hr_target = None
                if plan["modality"] in ("cardio_low", "cardio_high", "mixed"):
                    hr_target = target_hr_range(profile["age"], plan["intensity"])

                # Уровень 3: подбор упражнений
                n_ex = self._n_exercises(plan["duration_min"])
                exs = self.exercises.select(
                    plan, user_features, medical_conditions, n_ex,
                    used_exercise_names=used_exercise_names,
                    seed=rng.randint(0, 10**6),
                )
                for ex in exs:
                    used_exercise_names.add(ex.get("name", "?"))

                trainings.append({
                    "weekday":   weekday,
                    "plan":      plan,
                    "load":      load,
                    "hr_target": hr_target,
                    "exercises": exs,
                })
            weeks_data.append({"week_number": week_num, "trainings": trainings})

        # Какие протоколы применены
        applied = []
        for cond in medical_conditions:
            if cond != "none" and cond in self.exercises.protocols:
                applied.append(self.exercises.protocols[cond]["name_ru"])

        return {
            "weeks": weeks_data,
            "user_summary": {
                "bmi": user_features["bmi"],
                "fat_percentage": user_features["fat_percentage"],
                "goal": user_features["goal"],
                "level": user_features["level"],
                "weekly_frequency": user_features["weekly_frequency"],
            },
            "applied_protocols": applied,
            "total_trainings": total_trainings,
            "unique_exercises": len(used_exercise_names),
        }

    @staticmethod
    def _n_exercises(duration_min: int) -> int:
        if duration_min <= 25:
            return 5
        if duration_min <= 35:
            return 6
        return 8
