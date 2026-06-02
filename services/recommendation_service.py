"""Оркестратор рекомендаций. Связывает три уровня вместе и форматирует
результат для отправки в Telegram.
"""

from __future__ import annotations

from logic.cycle_builder import CycleBuilder
from logic.clinical_rules import build_user_features
from logic.exercise_selector import ExerciseSelector
from logic.ml.load_regressor import LoadRegressor
from logic.ml.ranking_service import RankingService


class RecommendationService:
    """Singleton, инициализируемый при старте бота."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_components()
        return cls._instance

    def _init_components(self):
        print("=" * 60)
        print("Инициализация RecommendationService...")
        print("=" * 60)
        self.ranker = RankingService()
        self.load_reg = LoadRegressor()
        self.exercises = ExerciseSelector()
        self.cycle_builder = CycleBuilder(
            self.ranker, self.load_reg, self.exercises
        )
        print("[RecommendationService] Готов к работе.\n")

    def recommend(self, profile: dict) -> dict:
        """Главный публичный метод. Принимает профиль из 13 полей,
        возвращает структуру цикла.
        """
        user_features = build_user_features(profile)
        weeks = profile.get("weeks", 1)
        trainings_per_week = profile.get("trainings_per_week", 3)
        medical = profile.get("medical_conditions", ["none"])

        cycle = self.cycle_builder.build(
            user_features=user_features,
            profile=profile,
            medical_conditions=medical,
            weeks=weeks,
            trainings_per_week=trainings_per_week,
        )

        # Метаданные модели
        cycle["model_info"] = {
            "model_type": self.ranker.artifact.get("model_type", "XGBRanker"),
            "objective": self.ranker.artifact.get("objective", "rank:ndcg"),
            "ndcg3": self.ranker.artifact.get("NDCG@3_test", 0.0),
        }
        return cycle

    @staticmethod
    def format_cycle_text(cycle: dict, profile: dict) -> list[str]:
        """Форматирует цикл в список Telegram-сообщений.

        Telegram имеет лимит 4096 символов на сообщение — разбиваем на части.
        """
        from config import MEDICAL_CONDITIONS
        from logic.clinical_rules import compute_bmi

        out: list[str] = []

        # Шапка
        s = cycle["user_summary"]
        bmi_class = ("Норма" if 18.5 <= s["bmi"] < 25 else
                     "Недостаток массы" if s["bmi"] < 18.5 else
                     "Избыточная масса" if s["bmi"] < 30 else
                     "Ожирение I" if s["bmi"] < 35 else
                     "Ожирение II" if s["bmi"] < 40 else "Ожирение III")
        goals_ru = {"weight_loss": "похудение", "muscle_gain": "набор массы",
                    "maintenance": "поддержание формы"}
        levels_ru = {"beginner": "новичок", "intermediate": "средний", "expert": "опытный"}

        header = (
            f"✅ <b>Анализ завершён</b>\n\n"
            f"📊 <b>Профиль:</b>\n"
            f"   ИМТ: {s['bmi']:.1f} ({bmi_class})\n"
            f"   Цель: {goals_ru.get(s['goal'], s['goal'])}\n"
            f"   Уровень: {levels_ru.get(s['level'], s['level'])}\n"
            f"   Частота тренировок: {s['weekly_frequency']} раз/нед\n"
        )
        if cycle.get("applied_protocols"):
            header += f"   Учтены протоколы: {', '.join(cycle['applied_protocols'])}\n"

        m = cycle.get("model_info", {})
        ndcg3_val = m.get("ndcg3")
        if ndcg3_val is None:
            ndcg3_val = 0.0
            
        header += (
            f"\n🤖 <b>Модель ML:</b> {m.get('model_type', 'XGBoost')} "
            f"({m.get('objective', 'rank:ndcg')})\n"
            f"   NDCG@3 на тестовой выборке: "
            f"{ndcg3_val:.4f}\n"
        )
        header += (
            f"\n📅 <b>Тренировочный цикл</b>\n"
            f"   Недель: {len(cycle['weeks'])}, "
            f"тренировок: {cycle['total_trainings']}, "
            f"уникальных упражнений: {cycle['unique_exercises']}\n"
        )
        out.append(header)

        # Тренировки по неделям
        modality_ru = {
            "cardio_low":  "Низкоударное кардио",
            "cardio_high": "Высокоударное кардио",
            "strength":    "Силовая тренировка",
            "mixed":       "Смешанная (кардио + сила)",
        }
        intensity_ru = {"low": "низкая", "moderate": "умеренная", "high": "высокая"}
        equip_ru = {"home": "дом", "gym": "зал"}

        for week in cycle["weeks"]:
            week_text = f"\n═══ <b>Неделя {week['week_number']}</b> ═══\n"
            for ti, t in enumerate(week["trainings"], start=1):
                p = t["plan"]
                load = t["load"]
                hr = t["hr_target"]

                training_text = (
                    f"\n🏋 <b>Тренировка {ti}: {t['weekday']}</b>\n"
                    f"   Тип: {modality_ru.get(p['modality'], p['modality'])}\n"
                    f"   Длительность: {p['duration_min']} мин\n"
                    f"   Интенсивность: {intensity_ru.get(p['intensity'])} "
                    f"(RPE {load['rpe']:.1f}/10)\n"
                    f"   Место: {equip_ru.get(p['equipment'], p['equipment'])}\n"
                )
                if hr:
                    training_text += f"   Целевая ЧСС: {hr[0]}–{hr[1]} уд/мин\n"
                training_text += (
                    f"   Подходов: {load['sets']}, повторов: {load['reps']}, "
                    f"отдых: {load['rest_sec']} сек\n\n"
                    f"   <b>Упражнения:</b>\n"
                )
                for ei, ex in enumerate(t["exercises"], start=1):
                    name = ex.get("name", "?")
                    eq = ex.get("equipment") or "—"
                    primary = ", ".join(ex.get("primaryMuscles") or []) or "—"
                    training_text += (
                        f"\n   {ei}. <b>{name}</b>\n"
                        f"      Мышцы: {primary}\n"
                        f"      Оборудование: {eq}\n"
                    )
                    instr = ex.get("instructions") or []
                    if instr:
                        # Показываем первые 2 шага инструкции
                        short = " ".join(instr[:2])
                        if len(short) > 280:
                            short = short[:277] + "..."
                        training_text += f"      <i>{short}</i>\n"
                week_text += training_text

            # Не накапливаем больше 3500 симв в одном сообщении
            if len(week_text) > 3500:
                # Разбиваем неделю по тренировкам
                parts = week_text.split("\n🏋")
                buf = parts[0]
                for part in parts[1:]:
                    candidate = buf + "\n🏋" + part
                    if len(candidate) > 3500:
                        out.append(buf)
                        buf = "🏋" + part
                    else:
                        buf = candidate
                if buf:
                    out.append(buf)
            else:
                out.append(week_text)

        # Подвал
        footer = (
            "\n📚 <b>Источники протоколов:</b>\n"
            "• ACSM's Guidelines for Exercise Testing and Prescription, 11th ed. (2021)\n"
            "• WHO Physical Activity Guidelines 2020\n"
            "• ACSM Exercise is Medicine Rx Series\n"
            "• NSCA Essentials of Personal Training, 4th ed.\n\n"
            "⚠️ Перед началом программы при наличии хронических заболеваний "
            "проконсультируйтесь с врачом.\n\n"
            "Команды: /restart — пройти опросник заново, /help — помощь."
        )
        out.append(footer)
        return out
