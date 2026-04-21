import json
from pathlib import Path

# Путь к вашему красивому файлу с планами
WORKOUT_FILE = Path(__file__).resolve().parent.parent / "data" / "sample_workouts.json"

def get_workout_plan(profile_data):
    """
    profiles_data: словарь со всеми параметрами пользователя (bmi, goal, age_group и т.д.)
    возвращает список упражнений или None, если совпадений нет.
    """
    try:
        with open(WORKOUT_FILE, "r", encoding="utf-8") as f:
            all_workouts = json.load(f)
    except Exception as e:
        print(f"Ошибка чтения файла: {e}")
        return None

    # Сначала находим блок профиля (кто этот пользователь)
    for workout_block in all_workouts:
        # Проверяем, совпадает ли профиль пользователя с ключами в JSON
        # Важно использовать те же поля, что посчитала нейросеть
        if (
            workout_block.get("goal") == profile_data.get("goal") and
            workout_block.get("gender") == profile_data.get("gender") and
            workout_block.get("age_group") == profile_data.get("age_group") and
            workout_block.get("level") == profile_data.get("level") and
            workout_block.get("type") == profile_data.get("type")
        ):
            # Нашли блок! Теперь берем планы внутри него.
            plans_list = workout_block.get("plans", [])
            
            # Модели предсказывают индексы 0, 1 или 2.
            # Мы выберем самый подходящий план из списка (например, первый или тот, который просили).
            # Для старта покажем План №1 (который соответствует предсказанию модели).
            if plans_list:
                # Выбираем план, который лучше всего подходит под целевой индекс (обычно индекс 0)
                chosen_plan = plans_list[0] 
                return chosen_plan
    
    # Если точного совпадения в JSON не нашлось
    return {
        "duration": "—",
        "plan": ["К сожалению, я пока не нашел идеальной программы для таких параметров 😔"],
        "note": "Попробуйте изменить тип тренировки или уровень подготовки."
    }
