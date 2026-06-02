"""Уровень 2: ML-регрессор персональной нагрузки.

Предсказывает для пользователя и плана:
  • число подходов (sets)
  • число повторений (reps)
  • длительность отдыха в секундах (rest_sec)
  • RPE (Rate of Perceived Exertion, 1–10)

Модель — лёгкий MLPRegressor с одним скрытым слоем. Обучается на синтетических
примерах, сгенерированных из руководства NSCA Essentials of Personal Training,
4th ed. (2021). На границах диапазонов руководства MLP даёт плавную
интерполяцию вместо ступенчатых значений if-else.

Обучение запускается при первом импорте модуля, веса кэшируются в .pkl.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

CACHE_PATH = Path(__file__).parent / "load_regressor.pkl"


def _generate_training_examples(n: int = 5000, seed: int = 42) -> tuple:
    """Генерирует синтетические примеры по правилам NSCA.

    Зависимость нагрузки от признаков (упрощённая модель):
      • Цель muscle_gain → 3-5 sets, 6-12 reps, 60-120 sec rest
      • Цель weight_loss → 2-3 sets, 12-15 reps, 30-60 sec rest
      • Цель maintenance → 3 sets, 10-12 reps, 60-90 sec rest
      • Уровень beginner → меньше sets, больше rest
      • Уровень expert → больше sets, меньше rest
      • Возраст 50+ → больше rest
      • Травма → уменьшение sets и интенсивности
      • BMI > 30 → больше rest
    """
    rng = np.random.default_rng(seed)
    X, y = [], []

    for _ in range(n):
        age = rng.integers(18, 65)
        bmi = rng.normal(26, 5)
        bmi = float(np.clip(bmi, 16, 45))
        level_n = rng.integers(0, 3)        # 0=beg, 1=int, 2=exp
        goal_n = rng.integers(0, 3)         # 0=loss, 1=gain, 2=maintain
        intensity_n = rng.integers(0, 3)    # 0=low, 1=mod, 2=high
        injury_n = rng.integers(0, 5)       # 0=none, 1=knee, 2=back, 3=shoulder, 4=multiple

        # Базовые значения по NSCA для каждой цели
        if goal_n == 0:    # weight_loss → круговая, мало отдыха, много повторов
            sets, reps, rest = 2.5, 13.0, 45.0
        elif goal_n == 1:  # muscle_gain → гипертрофия 6-12 reps, 60-120 rest
            sets, reps, rest = 4.0, 9.0, 90.0
        else:              # maintenance
            sets, reps, rest = 3.0, 11.0, 75.0

        # Корректировка по уровню
        if level_n == 0:                  # новичок
            sets -= 0.7
            rest += 15.0
        elif level_n == 2:                # эксперт
            sets += 1.0
            rest -= 10.0

        # Корректировка по интенсивности
        if intensity_n == 0:              # low
            reps += 2.0
            rest -= 10.0
        elif intensity_n == 2:            # high
            reps -= 2.0
            rest += 20.0

        # Возраст
        if age >= 50:
            sets -= 0.3
            rest += 15.0
        elif age >= 40:
            rest += 5.0

        # BMI
        if bmi >= 30:
            rest += 10.0
        if bmi >= 35:
            sets -= 0.5

        # Травмы — уменьшаем общую нагрузку
        if injury_n != 0:
            sets -= 0.5
            reps -= 1.0
        if injury_n == 4:                 # multiple
            sets -= 0.5

        # RPE — субъективное усилие, зависит от intensity
        rpe = 4.0 + 1.5 * intensity_n + 0.4 * level_n  # эксперт может больше
        if injury_n != 0:
            rpe -= 1.0

        # Малый шум для регуляризации
        sets += rng.normal(0, 0.2)
        reps += rng.normal(0, 0.5)
        rest += rng.normal(0, 4.0)
        rpe += rng.normal(0, 0.3)

        # Клиппинг
        sets = float(np.clip(sets, 1, 6))
        reps = float(np.clip(reps, 5, 20))
        rest = float(np.clip(rest, 20, 180))
        rpe = float(np.clip(rpe, 2, 10))

        X.append([age, bmi, level_n, goal_n, intensity_n, injury_n])
        y.append([sets, reps, rest, rpe])

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


class LoadRegressor:
    """Обёртка над MLPRegressor с кэшированием весов."""

    LEVEL_MAP = {"beginner": 0, "intermediate": 1, "expert": 2}
    GOAL_MAP = {"weight_loss": 0, "muscle_gain": 1, "maintenance": 2}
    INTENSITY_MAP = {"low": 0, "moderate": 1, "high": 2}
    INJURY_MAP = {"none": 0, "knee": 1, "back": 2, "shoulder": 3, "multiple": 4}

    def __init__(self) -> None:
        if CACHE_PATH.exists():
            with open(CACHE_PATH, "rb") as f:
                cache = pickle.load(f)
            self.model = cache["model"]
            self.scaler_x = cache["scaler_x"]
            self.scaler_y = cache["scaler_y"]
            print("[LoadRegressor] Загружен из кэша.")
        else:
            print("[LoadRegressor] Обучаю на синтетике (NSCA-правила)...")
            self._train_and_cache()

    def _train_and_cache(self) -> None:
        X, y = _generate_training_examples()
        self.scaler_x = StandardScaler().fit(X)
        self.scaler_y = StandardScaler().fit(y)
        Xn = self.scaler_x.transform(X)
        yn = self.scaler_y.transform(y)
        self.model = MLPRegressor(
            hidden_layer_sizes=(32, 16),
            activation="relu",
            max_iter=200,
            random_state=42,
            early_stopping=True,
        )
        self.model.fit(Xn, yn)
        with open(CACHE_PATH, "wb") as f:
            pickle.dump({
                "model": self.model,
                "scaler_x": self.scaler_x,
                "scaler_y": self.scaler_y,
            }, f)
        print(f"[LoadRegressor] Обучение завершено. R²={self.model.score(Xn, yn):.4f}")

    def predict(self, age: int, bmi: float, level: str, goal: str,
                intensity: str, injury: str) -> dict:
        x = np.array([[
            age, bmi,
            self.LEVEL_MAP.get(level, 1),
            self.GOAL_MAP.get(goal, 2),
            self.INTENSITY_MAP.get(intensity, 1),
            self.INJURY_MAP.get(injury, 0),
        ]], dtype=np.float32)
        xn = self.scaler_x.transform(x)
        yn = self.model.predict(xn)
        y = self.scaler_y.inverse_transform(yn.reshape(1, -1))[0]
        return {
            "sets":     int(round(np.clip(y[0], 1, 6))),
            "reps":     int(round(np.clip(y[1], 5, 20))),
            "rest_sec": int(round(np.clip(y[2], 20, 180))),
            "rpe":      round(float(np.clip(y[3], 2, 10)), 1),
        }
