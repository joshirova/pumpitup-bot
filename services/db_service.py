import json
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
EXERCISES_PATH = BASE_DIR / "data" / "exercises.json"

class DBService:
    def __init__(self):
        # Загружаем базу упражнений из JSON
        if os.path.exists(EXERCISES_PATH):
            with open(EXERCISES_PATH, "r", encoding="utf-8") as f:
                self.exercises = json.load(f)
        else:
            self.exercises = []
            print(f"⚠️ Exercises file not found at {EXERCISES_PATH}")

    def get_recommendations(self, plan_index, user_profile):
        """
        plan_index: 0, 1, 2 (предсказание модели)
        user_profile: {level, activity}
        """
        # Маппинг индекса плана в категорию упражнений
        # 0 -> strength, 1 -> cardio, 2 -> stretching (популярная схема для дипломов)
        category_map = {
            0: 'strength',
            1: 'cardio',
            2: 'stretching'
        }
        
        target_category = category_map.get(plan_index, 'strength')
        
        # Маппинг уровня подготовки пользователя в поле level в JSON
        difficulty_map = {
            'Новичок': 'beginner',
            'Средний': 'intermediate',
            'Опытный': 'expert'
        }
        target_difficulty = difficulty_map.get(user_profile['level'], 'beginner')
        
        # Фильтрация по категории и сложности
        recommended = [
            ex['name'] for ex in self.exercises 
            if ex.get('category') == target_category 
            and ex.get('level') == target_difficulty
        ]
        
        # Если упражнений мало, попробуем найти по категории без учета сложности
        if len(recommended) < 3:
            additional = [
                ex['name'] for ex in self.exercises 
                if ex.get('category') == target_category 
                and ex.get('name') not in recommended
            ]
            recommended.extend(additional)
            
        # Возвращаем топ-3 упражнения
        return recommended[:3]
