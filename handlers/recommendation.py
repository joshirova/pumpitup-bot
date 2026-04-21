from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from services.ml_service import MLService
from services.db_service import DBService

# Состояния диалога
GENDER, AGE, HEIGHT, WEIGHT, FAT, LEVEL, ACTIVITY = range(7)

# Кнопки
RETURN_BUTTON = ["🔁 В начало"]

ml_service = MLService()
db_service = DBService()

def markup_with_return(options):
    return ReplyKeyboardMarkup([options, RETURN_BUTTON], one_time_keyboard=True, resize_keyboard=True)

async def start_recommendation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Очищаем данные предыдущей сессии, если они есть
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Привет! Я *PumpItUp* — твой персональный фитнес-бот 🤖\n\n"
        "Я помогу тебе подобрать топ-3 упражнения на основе твоих параметров и модели ML.\n\n"
        "Для начала выбери свой пол:",
        reply_markup=markup_with_return(['Мужчина', 'Женщина']),
        parse_mode="Markdown"
    )
    return GENDER

async def gender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == RETURN_BUTTON[0]:
        return await start_recommendation(update, context)
    context.user_data["gender"] = update.message.text
    await update.message.reply_text("Сколько тебе полных лет?")
    return AGE

async def age_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("Пожалуйста, введи возраст числом:")
        return AGE
    context.user_data["age"] = int(update.message.text)
    await update.message.reply_text("Какой твой рост в см (например, 175)?")
    return HEIGHT

async def height_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("Пожалуйста, введи рост числом:")
        return HEIGHT
    context.user_data["height"] = int(update.message.text)
    await update.message.reply_text("Какой твой вес в кг (например, 70)?")
    return WEIGHT

async def weight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = float(update.message.text.replace(',', '.'))
        context.user_data["weight"] = weight
        await update.message.reply_text("Какой у тебя процент жира (если не знаешь, введи примерный: 15-25)?")
        return FAT
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи вес числом:")
        return WEIGHT

async def fat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        fat = float(update.message.text.replace(',', '.'))
        context.user_data["fat"] = fat
        await update.message.reply_text(
            "Твой уровень подготовки:",
            reply_markup=markup_with_return(['Новичок', 'Средний', 'Опытный'])
        )
        return LEVEL
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи процент жира числом:")
        return FAT

async def level_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == RETURN_BUTTON[0]:
        return await start_recommendation(update, context)
    context.user_data["level"] = update.message.text
    await update.message.reply_text(
        "Каким типом тренировок хочешь заниматься?",
        reply_markup=markup_with_return(['Strength', 'Cardio', 'HIIT', 'Yoga'])
    )
    return ACTIVITY

async def activity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == RETURN_BUTTON[0]:
        return await start_recommendation(update, context)
    context.user_data["activity"] = update.message.text
    
    # Сбор всех данных
    user_info = context.user_data
    
    # 1. Расчет признаков и предсказание модели
    plan_index = ml_service.predict_plan_index(user_info)
    
    # 2. Получение рекомендаций из БД (JSON)
    exercises = db_service.get_recommendations(plan_index, user_info)
    
    # Формирование ответа
    bmi = ml_service.calculate_bmi(user_info['weight'], user_info['height'])
    goal = ml_service.get_goal(bmi, user_info['fat'])
    
    response = (
        f"✅ *Анализ завершен!*\n\n"
        f"📊 *Твои показатели:*\n"
        f"• ИМТ: {bmi}\n"
        f"• Вычисленная цель: {goal}\n\n"
        f"🚀 *Топ-3 упражнения для тебя:*\n"
    )
    
    if exercises:
        for i, ex in enumerate(exercises, 1):
            response += f"{i}. {ex}\n"
    else:
        response += "К сожалению, упражнения не найдены. Попробуй изменить параметры."

    markup = ReplyKeyboardMarkup([["🔁 Подобрать заново"]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        response, 
        parse_mode="Markdown",
        reply_markup=markup
    )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменен.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Создание ConversationHandler для экспорта
recommendation_handler = ConversationHandler(
    entry_points=[
        CommandHandler("start", start_recommendation),
        CommandHandler("recommend", start_recommendation), 
        MessageHandler(filters.Regex("^(Подбор плана|🔁 Подобрать заново)$"), start_recommendation)
    ],
    states={
        GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender_handler)],
        AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_handler)],
        HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, height_handler)],
        WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight_handler)],
        FAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, fat_handler)],
        LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, level_handler)],
        ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, activity_handler)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
