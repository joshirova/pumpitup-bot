from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from logic.workout_selector import select_workout

# Этапы диалога
GOAL, GENDER, AGE, LEVEL, TYPE, CHOOSE_PLAN = range(6)

# Хранилище прогресса
user_progress = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [['Похудение', 'Поддержание формы', 'Набор массы']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "👋 Привет! Я *PumpItUp* — твой персональный фитнес-бот 🤖\n\n"
        "Я помогу тебе подобрать эффективную, индивидуальную тренировку — дома или в зале.\n"
        "С учётом твоих целей, пола, возраста и уровня подготовки 💪\n\n"
        "Ты будешь становиться сильнее, стройнее и увереннее с каждой тренировкой.\n\n"
        "Начнём? 💥 Какая у тебя цель?",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    return GOAL

async def goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["goal"] = update.message.text
    markup = ReplyKeyboardMarkup([['Мужчина', 'Женщина']], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Отлично! Теперь скажи, кто ты по полу:", reply_markup=markup)
    return GENDER

async def gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["gender"] = update.message.text
    markup = ReplyKeyboardMarkup([['До 60', '60+']], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Сколько тебе лет? Выбери категорию:", reply_markup=markup)
    return AGE

async def age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["age"] = update.message.text
    markup = ReplyKeyboardMarkup([['Новичок', 'Средний', 'Опытный']], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Какой у тебя уровень физической подготовки?", reply_markup=markup)
    return LEVEL

async def level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["level"] = update.message.text
    markup = ReplyKeyboardMarkup([['Дом', 'Зал']], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Где ты хочешь тренироваться? 🏠 или 🏋️‍♂️", reply_markup=markup)
    return TYPE

async def type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["type"] = update.message.text
    user_id = update.effective_user.id

    user_progress[user_id] = set()  # сбрасываем историю выполненных тренировок
    markup = ReplyKeyboardMarkup([['1', '2', '3']], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выбери, какую тренировку хочешь выполнить сегодня (1, 2 или 3):", reply_markup=markup)
    return CHOOSE_PLAN

async def choose_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        plan_index = int(update.message.text) - 1
        if not (0 <= plan_index <= 2):
            raise ValueError
    except ValueError:
        await update.message.reply_text("Пожалуйста, выбери номер тренировки: 1, 2 или 3.")
        return CHOOSE_PLAN

    context.user_data["plan_index"] = plan_index
    info = context.user_data

    result = select_workout(
        goal=info["goal"],
        gender=info["gender"],
        age=info["age"],
        level=info["level"],
        workout_type=info["type"],
        plan_index=plan_index
    )

    workout_text = "\n".join(f"💪 {step}" for step in result["plan"])
    plan_number = result["index"]
    duration = result["duration"]

    reply_keyboard = [["✅ Я выполнил тренировку", "🔁 Подобрать заново"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        f"🔥 Вот твоя программа!\n\n"
        f"🎯 Цель: {info['goal']}\n"
        f"👤 Пол: {info['gender']}\n"
        f"🎂 Возраст: {info['age']}\n"
        f"⚙️ Уровень: {info['level']}\n"
        f"📍 Тип: {info['type']}\n"
        f"🧩 Тренировка №{plan_number} из 3\n"
        f"🕒 Длительность: {duration}\n\n"
        f"{workout_text}",
        reply_markup=markup
    )
    return CHOOSE_PLAN

async def confirm_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    plan_index = context.user_data.get("plan_index")

    if user_id not in user_progress:
        user_progress[user_id] = set()

    user_progress[user_id].add(plan_index)

    # После подтверждения возвращаем только кнопку «Подобрать заново»
    markup = ReplyKeyboardMarkup([["🔁 Подобрать заново"]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "🏆 Отлично! Я отметил твою тренировку как выполненную.\nПродолжай в том же духе 💪",
        reply_markup=markup
    )
    return CHOOSE_PLAN

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён. Напиши /start, чтобы начать заново.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def setup_handlers(app):
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("🔁 Подобрать заново"), start)
        ],
        states={
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, goal)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, level)],
            TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_handler)],
            CHOOSE_PLAN: [
                MessageHandler(filters.Regex("^[123]$"), choose_plan),
                MessageHandler(filters.Regex("✅ Я выполнил тренировку"), confirm_done),
                MessageHandler(filters.Regex("🔁 Подобрать заново"), start)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)