import joblib
import pandas as pd
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "logic" / "ml" / "ml_model.pkl"
ENCODERS_PATH = BASE_DIR / "logic" / "ml" / "label_encoders.pkl"

class MLService:
    def __init__(self):
        self.model = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None
        self.encoders = joblib.load(ENCODERS_PATH) if os.path.exists(ENCODERS_PATH) else {}

    def get_calculated_profile(self, height_cm, weight_kg, age, fat_pct, gender_str, gym_preference):
        """
        Рассчитывает все признаки "на лету" по правилам диплома.
        """
        bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)
        
        # Определение цели по BMI и ЖИРУ (как в тезисах)
        goal = "Поддержание формы"
        if bmi >= 30 or fat_pct > 30: goal = "Похудение"
        elif bmi < 18.5 or fat_pct < 12: goal = "Набор массы"

        # Определение группы возраста (важно сохранить тире!)
        if 16 <= age <= 20: age_group = "16–20"
        elif 20 < age <= 30: age_group = "20–30"
        elif 30 < age <= 40: age_group = "30–40"
        elif 40 < age <= 50: age_group = "40–50"
        else: age_group = "50+"

        # Тип тренировки (переводим выбор юзера в слова для JSON)
        # Если выбрали Йогу/ХИИТ -> Дом, иначе -> Зал
        workout_type = "Зал"
        if gym_preference in ["Yoga", "HIIT"]:
             workout_type = "Дом"

        return {
            "bmi": bmi,
            "goal": goal,
            "age_group": age_group,
            "gender": gender_str,
            "level": "Новичок", # Можно усложнить опросом, пока поставим заглушку или доработаем в хендлере
            "type": workout_type
        }
