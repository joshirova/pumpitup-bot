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
from logic.analyzer import generate_feature_importance_plot, predict_progress, generate_progress_plot
from logic.ml.ml_model import model, label_encoders
import matplotlib
matplotlib.use('Agg')
import pandas as pd
import numpy as np

GOAL, GENDER, AGE, LEVEL, TYPE, HEIGHT, WEIGHT, SHOW_PLAN = range(8)
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
    
    # Автоматически показываем кнопки для новых команд
    help_text = (
        "💡 *Дополнительные возможности:*\n"
        "• /explain — объяснение рекомендаций через важность признаков\n"
        "• /metrics — сравнение метрик качества (ранжирование vs классификация)\n"
        "• /progress — прогноз времени достижения цели по ИМТ"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён. Напиши /start, чтобы начать заново.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def explain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'bmi' not in context.user_data:
        await update.message.reply_text(
            "Сначала заполните параметры через /start, чтобы получить рекомендации."
        )
        return
    
    feature_names = ['goal', 'gender', 'age_group', 'level', 'type', 'bmi']
    X_sample = pd.DataFrame([{
        'goal': context.user_data.get('goal', 'Похудение'),
        'gender': context.user_data.get('gender', 'Мужчина'),
        'age_group': context.user_data.get('age', '20–30'),
        'level': context.user_data.get('level', 'Новичок'),
        'type': context.user_data.get('type', 'Дом'),
        'bmi': context.user_data.get('bmi', 25.0)
    }])
    
    for col in ['goal', 'gender', 'age_group', 'level', 'type']:
        le = label_encoders[col]
        X_sample[col] = le.transform(X_sample[col])
    
    plot_buf = generate_feature_importance_plot(model, feature_names)
    
    bmi_value = context.user_data['bmi']
    goal = context.user_data['goal']
    
    explanation = (
        f"📊 *Как формируются ваши рекомендации:*\n\n"
        f"• ИМТ ({bmi_value}) — ключевой фактор при выборе программы:\n"
        f"  - При ИМТ > 30 рекомендуются кардио-упражнения\n"
        f"  - При ИМТ < 18.5 — силовые тренировки для набора массы\n\n"
        f"• Цель «{goal}» определяет структуру тренировок:\n"
        f"  - Похудение → акцент на кардио и интервальные тренировки\n"
        f"  - Набор массы → акцент на силовые упражнения\n"
        f"  - Поддержание формы → сбалансированный подход\n\n"
        f"Это соответствует рекомендациям ВОЗ по физической активности."
    )
    
    await update.message.reply_photo(photo=plot_buf, caption=explanation, parse_mode="Markdown")

async def metrics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metrics_text = (
        "📈 *Метрики качества рекомендаций:*\n\n"
        "✅ NDCG@3 = 0.7866 (логистическая регрессия)\n"
        "✅ Hit Rate@3 = 1.0 (все модели)\n"
        "⚠️ Accuracy = 0.501 (традиционная метрика)\n"
        "⚠️ F1-score = 0.454 (традиционная метрика)\n\n"
        "*Почему мы используем ранжирование вместо классификации?*\n"
        "В фитнес-приложениях пользователю предлагается не один, а несколько вариантов тренировок (например, план на неделю). "
        "Метрики ранжирования (NDCG@3) оценивают качество позиционирования правильного плана в топ-3 рекомендаций, "
        "что соответствует реальной практике и даёт более адекватную оценку качества системы."
    )
    await update.message.reply_text(metrics_text, parse_mode="Markdown")

async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'bmi' not in context.user_data:
        await update.message.reply_text(
            "Сначала заполните параметры через /start, чтобы получить рекомендации."
        )
        return
    
    current_bmi = context.user_data['bmi']
    goal = context.user_data['goal']
    
    if goal == 'Похудение':
        target_bmi = 24.9
    elif goal == 'Набор массы':
        target_bmi = 20.0
    else:
        target_bmi = current_bmi
    
    weeks_needed, final_bmi = predict_progress(current_bmi, target_bmi)
    plot_buf = generate_progress_plot(current_bmi, target_bmi, weeks_needed)
    
    if weeks_needed == 0:
        progress_text = "🎯 Вы уже находитесь в целевой зоне ИМТ! Рекомендуем поддерживать текущий уровень активности."
    else:
        progress_text = (
            f"🎯 *Прогноз достижения цели:*\n\n"
            f"• Текущий ИМТ: {current_bmi:.1f}\n"
            f"• Целевой ИМТ: {target_bmi:.1f}\n"
            f"• Ориентировочно потребуется: {weeks_needed} недель\n\n"
            f"💡 *Рекомендации:*\n"
            f"– Регулярно выполняйте рекомендованные тренировки\n"
            f"– Следите за питанием (дефицит/профицит калорий)\n"
            f"– Измеряйте ИМТ раз в 2 недели для отслеживания прогресса"
        )
    
    await update.message.reply_photo(photo=plot_buf, caption=progress_text, parse_mode="Markdown")

def setup_handlers(app):
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
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
    # Глобальные команды, работающие в любом состоянии
    app.add_handler(CommandHandler("explain", explain_command))
    app.add_handler(CommandHandler("metrics", metrics_command))
    app.add_handler(CommandHandler("progress", progress_command))