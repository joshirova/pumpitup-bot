# logic/ml/ml_model.py

import pickle
import pandas as pd
from pathlib import Path

# Пути к файлам модели и энкодеров
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "ml_model.pkl"
ENCODERS_PATH = BASE_DIR / "label_encoders.pkl"

# Загрузка модели и энкодеров
with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

with open(ENCODERS_PATH, "rb") as f:
    label_encoders = pickle.load(f)

def predict_plan_indices(goal, gender, age_group, level, workout_type, bmi):
    """
    Возвращает 3 индекса тренировок, наиболее подходящих под параметры пользователя.

    :param goal: Цель тренировки
    :param gender: Пол
    :param age_group: Возрастная категория
    :param level: Уровень подготовки
    :param workout_type: Тип тренировки
    :param bmi: Индекс массы тела (float)
    :return: Список из трёх индексов тренировок (0-based)
    """
    try:
        # Подготовка входных данных
        data = {
            "goal": [goal],
            "gender": [gender],
            "age_group": [age_group],
            "level": [level],
            "type": [workout_type],
            "bmi": [bmi]
        }

        df = pd.DataFrame(data)

        # Кодируем категориальные признаки
        for column in ["goal", "gender", "age_group", "level", "type"]:
            le = label_encoders[column]
            df[column] = le.transform(df[column])

        # Получаем вероятности классов
        probas = model.predict_proba(df)[0]

        # Возвращаем 3 наиболее вероятных индекса плана
        top3_indices = sorted(range(len(probas)), key=lambda i: probas[i], reverse=True)[:3]
        return top3_indices

    except Exception as e:
        print(f"❌ ML prediction error: {e}")
        return [0, 1, 2]  # fallback

