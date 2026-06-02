"""Конфигурация бота PumpItUp."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# Пути к артефактам
MODEL_PATH = BASE_DIR / "logic" / "ml" / "final_model.pkl"
EXERCISES_PATH = BASE_DIR / "data" / "exercises.json"
PLANS_PATH = BASE_DIR / "data" / "plan_pool.json"
PROTOCOLS_PATH = BASE_DIR / "data" / "medical_protocols.json"

# Параметры рекомендаций
TRAININGS_PER_WEEK = 3              # 3 тренировки в неделю (универсальный стандарт)
MIN_WEEKS = 1
MAX_WEEKS = 3
MIN_EXERCISES_PER_WORKOUT = 5
MAX_EXERCISES_PER_WORKOUT = 8

# Пороги по ЧСС (от максимальной = 220 - возраст)
HR_INTENSITY_MAP = {
    "low":      (40, 55),
    "moderate": (55, 70),
    "high":     (70, 85),
}

# Каталог состояний (для опросника)
MEDICAL_CONDITIONS = {
    "none":          "Нет хронических состояний",
    "obesity":       "Ожирение",
    "hypertension":  "Артериальная гипертензия",
    "tachycardia":   "Тахикардия / нестабильная ЧСС",
    "diabetes2":     "Сахарный диабет 2 типа",
    "back_pain":     "Хронические боли в спине",
    "knee_injury":   "Травмы / хронические боли в коленях",
}

INJURY_CHOICES = {
    "none":     "Травм нет",
    "knee":     "Колено",
    "back":     "Спина",
    "shoulder": "Плечо",
    "multiple": "Несколько / разные",
}

if not TELEGRAM_TOKEN:
    print("[WARN] TELEGRAM_TOKEN не задан. "
          "Создайте .env с TELEGRAM_TOKEN=<токен от @BotFather>.")
