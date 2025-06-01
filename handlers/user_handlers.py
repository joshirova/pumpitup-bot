from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from logic.workout_selector import select_workout_plan
from logic.ml.ml_model import predict_plan_indices

GOAL, GENDER, AGE, LEVEL, TYPE, HEIGHT, WEIGHT, SHOW_PLAN = range(8)
user_progress = {}
RETURN_BUTTON = ["🔁 Вернуться в начало"]

def markup_with_return(options):
    return ReplyKeyboardMarkup([options, RETURN_BUTTON], one_time_keyboard=True, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = markup_with_return(['Похудение', 'Поддержание формы', 'Набор массы'])
    await update.message.reply_text(
        "👋 Привет! Я *PumpItUp* — твой персональный фитнес-бот 🤖\n\n"
        "Я помогу тебе подобрать эффективный план тренировок на неделю — дома или в зале.\n"
        "С учётом твоих целей, пола, возраста, уровня подготовки и даже телосложения 💪\n\n"
        "Начнём? 💥 Какая у тебя цель?",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    return GOAL

async def goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == RETURN_BUTTON[0]:
        return await start(update, context)
    context.user_data["goal"] = update.message.text
    await update.message.reply_text("Какой у тебя пол?", reply_markup=markup_with_return(['Мужчина', 'Женщина']))
    return GENDER

async def gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == RETURN_BUTTON[0]:
        return await start(update, context)
    context.user_data["gender"] = update.message.text
    await update.message.reply_text("Укажи возрастную категорию:", reply_markup=markup_with_return(['16–20', '20–30', '30–40', '50+']))
    return AGE

async def age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == RETURN_BUTTON[0]:
        return await start(update, context)
    context.user_data["age"] = update.message.text
    await update.message.reply_text("Какой у тебя уровень подготовки?", reply_markup=markup_with_return(['Новичок', 'Средний', 'Опытный']))
    return LEVEL

async def level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == RETURN_BUTTON[0]:
        return await start(update, context)
    context.user_data["level"] = update.message.text
    await update.message.reply_text("Где ты будешь тренироваться?", reply_markup=markup_with_return(['Дом', 'Зал']))
    return TYPE

async def type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == RETURN_BUTTON[0]:
        return await start(update, context)
    context.user_data["type"] = update.message.text
    await update.message.reply_text("Введи свой рост в сантиметрах (например, 170):")
    return HEIGHT

async def height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == RETURN_BUTTON[0]:
        return await start(update, context)
    try:
        height_cm = int(update.message.text)
        context.user_data["height"] = height_cm
        await update.message.reply_text("Теперь введи свой вес в кг (например, 65):")
        return WEIGHT
    except:
        await update.message.reply_text("Пожалуйста, введи число — твой рост в сантиметрах (например, 170):")
        return HEIGHT

async def weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == RETURN_BUTTON[0]:
        return await start(update, context)
    try:
        weight = float(update.message.text)
        height = context.user_data["height"]
        bmi = round(weight / ((height / 100) ** 2), 1)
        context.user_data["weight"] = weight
        context.user_data["bmi"] = bmi
        return await show_week_plan(update, context)
    except:
        await update.message.reply_text("Пожалуйста, введи число — твой вес в кг (например, 65):")
        return WEIGHT

async def show_week_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = context.user_data
    user_id = update.effective_user.id

    indices = predict_plan_indices(
        goal=info["goal"],
        gender=info["gender"],
        age_group=info["age"],
        level=info["level"],
        workout_type=info["type"],
        bmi=info["bmi"]
    )

    days = ["Понедельник", "Среда", "Пятница"]
    text = "📆 Следуй этому плану в течение месяца — и ты увидишь результат!\n\n"

    for i, day in zip(indices, days):
        workout = select_workout_plan(
            goal=info["goal"],
            gender=info["gender"],
            age=info["age"],
            level=info["level"],
            workout_type=info["type"],
            plan_index=i
        )
        text += f"🗓️ *{day}* ({workout['duration']}):\n" + "\n".join(f"💪 {step}" for step in workout["plan"]) + "\n\n"

    markup = ReplyKeyboardMarkup([["🔁 Подобрать заново"]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
    return SHOW_PLAN

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён. Напиши /start, чтобы начать заново.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def setup_handlers(app):
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("🔁 Подобрать заново"), start),
            MessageHandler(filters.Regex("🔁 Вернуться в начало"), start)
        ],
        states={
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, goal)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, level)],
            TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_handler)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, height)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight)],
            SHOW_PLAN: [MessageHandler(filters.Regex("🔁 Подобрать заново"), start)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

