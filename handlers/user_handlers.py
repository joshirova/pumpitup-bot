from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, ContextTypes, ConversationHandler, 
    CommandHandler, MessageHandler, filters
)
import json
from pathlib import Path

# Пути к данным проекта (относительно этого файла)
BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_WORKOUTS_PATH = BASE_DIR / "data" / "sample_workouts.json"

GENDER, AGE, HEIGHT, WEIGHT, FAT_PERCENT = range(5)

def get_markup(options):
    return ReplyKeyboardMarkup([options], resize_keyboard=True, one_time_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я *PumpItUp*.\n\n"
        "Я рассчитаю программу тренировок на основе твоего ИМТ и параметров.\n\n"
        "Выбери пол:",
        reply_markup=get_markup(['Мужчина', 'Женщина']),
        parse_mode="Markdown"
    )
    return GENDER

async def gender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gender'] = update.message.text
    await update.message.reply_text("Сколько тебе лет?")
    return AGE

async def age_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['age'] = int(update.message.text)
        await update.message.reply_text("Рост в см?")
        return HEIGHT
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число:")
        return AGE

async def height_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['height'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text("Вес в кг?")
        return WEIGHT
    except ValueError:
        await update.message.reply_text("Введи число:")
        return HEIGHT

async def weight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['weight'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text("Примерный % жира? (Для мужчин 10-20%, для женщин 15-30%)")
        return FAT_PERCENT
    except ValueError:
        await update.message.reply_text("Введи число:")
        return WEIGHT

async def fat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        f = float(update.message.text.replace(',', '.'))
        data = context.user_data
        
        # 🔹 Расчёт признаков по клиническим правилам диплома (§2.3)
        height_m = data['height'] / 100
        bmi = round(data['weight'] / (height_m ** 2), 1)
        
        # Определение цели
        if bmi >= 30 or f > 30: goal = "Похудение"
        elif bmi < 18.5 or f < 12: goal = "Набор массы"
        else: goal = "Поддержание формы"
        
        # Возрастная группа
        age = data['age']
        if 16 <= age <= 20: age_group = "16–20"
        elif 20 < age <= 30: age_group = "20–30"
        elif 30 < age <= 40: age_group = "30–40"
        elif 40 < age <= 50: age_group = "40–50"
        else: age_group = "50+"
        
        # Параметры по умолчанию для поиска в JSON (уровень и тип)
        level = "Новичок"
        workout_type = "Дом"
        
        # 🔹 Поиск готовой программы в sample_workouts.json
        try:
            with open(SAMPLE_WORKOUTS_PATH, "r", encoding="utf-8") as fw:
                workouts_db = json.load(fw)
                
            matched_plan = None
            for item in workouts_db:
                if (item.get("goal") == goal and
                    item.get("gender") == data['gender'] and
                    item.get("age_group") == age_group and
                    item.get("level") == level and
                    item.get("type") == workout_type):
                    
                    plans = item.get("plans", [])
                    if plans:
                        matched_plan = plans[0] # Берём первый рекомендованный индекс
                        break
                
            if matched_plan:
                duration = matched_plan.get("duration", "—")
                steps = matched_plan.get("plan", [])
            else:
                duration = "—"
                steps = ["⚠️ В базе пока нет программы под такие параметры. Попробуй указать иной тип тренировки или уровень подготовки."]
                
            # Формирование итогового сообщения
            msg = (
                f"✅ *Анализ завершен!* 🧐\n\n"
                f"📊 Твои показатели:\n"
                f"• ИМТ: {bmi}\n"
                f"• Вычисленная цель: {goal}\n\n"
                f"🗓 Программа ({duration}):\n"
            )
            for i, step in enumerate(steps, 1):
                msg += f"{i}. {step}\n"
                
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
            
        except FileNotFoundError:
            await update.message.reply_text("❌ Файл с упражнениями не найден. Проверьте путь `data/sample_workouts.json`.", reply_markup=ReplyKeyboardRemove())
        except Exception as e:
            await update.message.reply_text(f"Ошибка обработки: {e}", reply_markup=ReplyKeyboardRemove())
            
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректные числа.")
        return FAT_PERCENT

# ✅ Регистрация обработчиков в боте
def setup_handlers(application: Application):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender_handler)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_handler)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, height_handler)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight_handler)],
            FAT_PERCENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, fat_handler)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: u.message.reply_text("Отмена."))],
    )
    application.add_handler(conv_handler)