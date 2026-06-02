"""ConversationHandler с 13-шаговым опросником.

Использует InlineKeyboardButton для удобства мобильного ввода.
Свободный ввод используется только там, где нужны числа (возраст, рост, вес).
"""

from __future__ import annotations

from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardRemove, Update)
from telegram.ext import (CallbackQueryHandler, CommandHandler,
                          ContextTypes, ConversationHandler, MessageHandler,
                          filters)

from config import MEDICAL_CONDITIONS, INJURY_CHOICES
from services.recommendation_service import RecommendationService


# Состояния
(GENDER, AGE, HEIGHT, WEIGHT, FAT, LEVEL, ACTIVITY, FREQ,
 EQUIPMENT, WEEKS, INJURY, MEDICAL, GOAL) = range(13)


def _kb(buttons: list[tuple[str, str]], cols: int = 2) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(buttons), cols):
        rows.append([InlineKeyboardButton(text, callback_data=data)
                     for text, data in buttons[i:i+cols]])
    return InlineKeyboardMarkup(rows)


# ──────────────────── /start ────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["profile"] = {}
    text = (
        "👋 Привет! Я бот <b>PumpItUp</b>.\n\n"
        "Я подберу для тебя персональный план тренировок на 1–3 недели "
        "на основе модели машинного обучения.\n\n"
        "Алгоритм учитывает 15 признаков, включая травмы и медицинские "
        "состояния. Источники протоколов — официальные руководства ACSM "
        "и WHO.\n\n"
        "Опрос займёт около 2 минут. Начнём?\n\n"
        "<b>Шаг 1/13.</b> Укажи свой пол:"
    )
    await update.message.reply_text(
        text, parse_mode="HTML",
        reply_markup=_kb([("Мужской", "male"), ("Женский", "female")]),
    )
    return GENDER


# ──────────────────── шаг 1: пол ────────────────────
async def on_gender(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    ctx.user_data["profile"]["gender"] = q.data
    await q.edit_message_text(
        "<b>Шаг 2/13.</b> Сколько тебе полных лет?\n"
        "<i>(введи число от 16 до 80)</i>",
        parse_mode="HTML",
    )
    return AGE


# ──────────────────── шаг 2: возраст ────────────────────
async def on_age(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age = int(update.message.text.strip())
        assert 16 <= age <= 80
    except (ValueError, AssertionError):
        await update.message.reply_text(
            "❌ Возраст должен быть целым числом от 16 до 80. Попробуй ещё раз."
        )
        return AGE
    ctx.user_data["profile"]["age"] = age
    await update.message.reply_text(
        "<b>Шаг 3/13.</b> Какой у тебя рост в сантиметрах?\n"
        "<i>(например: 175)</i>",
        parse_mode="HTML",
    )
    return HEIGHT


# ──────────────────── шаг 3: рост ────────────────────
async def on_height(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        h = float(update.message.text.replace(",", ".").strip())
        assert 130 <= h <= 220
    except (ValueError, AssertionError):
        await update.message.reply_text(
            "❌ Рост должен быть числом от 130 до 220 см. Попробуй ещё раз."
        )
        return HEIGHT
    ctx.user_data["profile"]["height_cm"] = h
    await update.message.reply_text(
        "<b>Шаг 4/13.</b> Какой у тебя вес в килограммах?\n"
        "<i>(например: 72.5)</i>",
        parse_mode="HTML",
    )
    return WEIGHT


# ──────────────────── шаг 4: вес ────────────────────
async def on_weight(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        w = float(update.message.text.replace(",", ".").strip())
        assert 35 <= w <= 250
    except (ValueError, AssertionError):
        await update.message.reply_text(
            "❌ Вес должен быть числом от 35 до 250 кг. Попробуй ещё раз."
        )
        return WEIGHT
    ctx.user_data["profile"]["weight_kg"] = w
    await update.message.reply_text(
        "<b>Шаг 5/13.</b> Какой у тебя процент жира?\n"
        "<i>(введи число или нажми «Не знаю» — оценим автоматически)</i>",
        parse_mode="HTML",
        reply_markup=_kb([("Не знаю", "skip_fat")]),
    )
    return FAT


# ──────────────────── шаг 5: процент жира ────────────────────
async def on_fat(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        ctx.user_data["profile"]["fat_percentage"] = None
        msg = update.callback_query.edit_message_text
    else:
        try:
            f = float(update.message.text.replace(",", ".").strip())
            assert 5 <= f <= 50
            ctx.user_data["profile"]["fat_percentage"] = f
        except (ValueError, AssertionError):
            await update.message.reply_text(
                "❌ Процент жира должен быть числом от 5 до 50. Попробуй ещё раз."
            )
            return FAT
        msg = update.message.reply_text

    await msg(
        "<b>Шаг 6/13.</b> Каков твой уровень тренировочной подготовки?",
        parse_mode="HTML",
        reply_markup=_kb([
            ("Новичок", "beginner"),
            ("Средний", "intermediate"),
            ("Опытный", "expert"),
        ]),
    )
    return LEVEL


# ──────────────────── шаг 6: уровень ────────────────────
async def on_level(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    ctx.user_data["profile"]["level"] = q.data
    await q.edit_message_text(
        "<b>Шаг 7/13.</b> Какой у тебя уровень повседневной активности "
        "<i>(вне тренировок)</i>?\n\n"
        "• <b>Сидячий</b> — офисная работа, мало хожу\n"
        "• <b>Умеренный</b> — иногда хожу пешком, лестницы\n"
        "• <b>Активный</b> — много двигаюсь, физический труд",
        parse_mode="HTML",
        reply_markup=_kb([
            ("Сидячий", "sedentary"),
            ("Умеренный", "light"),
            ("Активный", "active"),
        ]),
    )
    return ACTIVITY


# ──────────────────── шаг 7: активность ────────────────────
async def on_activity(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    ctx.user_data["profile"]["activity_level"] = q.data
    await q.edit_message_text(
        "<b>Шаг 8/13.</b> Сколько раз в неделю готов тренироваться?",
        parse_mode="HTML",
        reply_markup=_kb([("2", "2"), ("3", "3"), ("4", "4"), ("5", "5")], cols=4),
    )
    return FREQ


# ──────────────────── шаг 8: частота ────────────────────
async def on_freq(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    ctx.user_data["profile"]["weekly_frequency"] = int(q.data)
    await q.edit_message_text(
        "<b>Шаг 9/13.</b> Где будешь тренироваться?",
        parse_mode="HTML",
        reply_markup=_kb([("Дом", "home"), ("Зал", "gym")]),
    )
    return EQUIPMENT


# ──────────────────── шаг 9: оборудование ────────────────────
async def on_equipment(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    ctx.user_data["profile"]["equipment_pref"] = q.data
    await q.edit_message_text(
        "<b>Шаг 10/13.</b> На сколько недель построить программу?",
        parse_mode="HTML",
        reply_markup=_kb([("1 неделя", "1"), ("2 недели", "2"), ("3 недели", "3")], cols=3),
    )
    return WEEKS


# ──────────────────── шаг 10: число недель ────────────────────
async def on_weeks(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    ctx.user_data["profile"]["weeks"] = int(q.data)
    await q.edit_message_text(
        "<b>Шаг 11/13.</b> Есть ли у тебя травмы?",
        parse_mode="HTML",
        reply_markup=_kb(
            [(label, key) for key, label in INJURY_CHOICES.items()], cols=2
        ),
    )
    return INJURY


# ──────────────────── шаг 11: травмы ────────────────────
async def on_injury(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    ctx.user_data["profile"]["injury_history"] = q.data

    # Готовим мультивыбор медицинских состояний
    ctx.user_data["medical_selected"] = set()
    await q.edit_message_text(
        _medical_text(set()),
        parse_mode="HTML",
        reply_markup=_medical_kb(set()),
    )
    return MEDICAL


def _medical_text(selected: set) -> str:
    sel_list = (", ".join(MEDICAL_CONDITIONS[k] for k in selected)
                if selected else "—")
    return (
        "<b>Шаг 12/13.</b> Есть ли хронические состояния? "
        "(можно выбрать несколько)\n\n"
        f"<i>Выбрано:</i> {sel_list}\n\n"
        "Нажмите состояние, чтобы добавить/убрать. Когда закончите — "
        "нажмите ✅ Готово."
    )


def _medical_kb(selected: set) -> InlineKeyboardMarkup:
    btns = []
    for key, label in MEDICAL_CONDITIONS.items():
        prefix = "✓ " if key in selected else ""
        btns.append((f"{prefix}{label}", f"med:{key}"))
    btns.append(("✅ Готово", "med:done"))
    return _kb(btns, cols=1)


# ──────────────────── шаг 12: медицина (мультивыбор) ────────────────────
async def on_medical(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    selected = ctx.user_data.get("medical_selected", set())
    payload = q.data.split(":", 1)[1]

    if payload == "done":
        if not selected:
            selected = {"none"}
        # Если "none" в выборе — игнорируем остальные
        if "none" in selected and len(selected) > 1:
            selected = {"none"}
        ctx.user_data["profile"]["medical_conditions"] = list(selected)
        await q.edit_message_text(
            "<b>Шаг 13/13.</b> Какова твоя главная цель?",
            parse_mode="HTML",
            reply_markup=_kb([
                ("Похудение", "weight_loss"),
                ("Набор массы", "muscle_gain"),
                ("Поддержание формы", "maintenance"),
            ], cols=1),
        )
        return GOAL

    # Переключаем чекбокс
    if payload in selected:
        selected.discard(payload)
    else:
        # Если выбираем "none" — снимаем остальные
        if payload == "none":
            selected = {"none"}
        else:
            selected.discard("none")
            selected.add(payload)
    ctx.user_data["medical_selected"] = selected

    await q.edit_message_text(
        _medical_text(selected),
        parse_mode="HTML",
        reply_markup=_medical_kb(selected),
    )
    return MEDICAL


# ──────────────────── шаг 13: цель + расчёт ────────────────────
async def on_goal(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    ctx.user_data["profile"]["stated_goal"] = q.data
    profile = ctx.user_data["profile"]

    await q.edit_message_text(
        "⏳ Анализирую профиль и подбираю план...\n"
        "<i>Это займёт несколько секунд.</i>",
        parse_mode="HTML",
    )

    try:
        rec_service = RecommendationService()
        cycle = rec_service.recommend(profile)
        messages = rec_service.format_cycle_text(cycle, profile)
        for m in messages:
            await ctx.bot.send_message(
                chat_id=q.message.chat_id, text=m, parse_mode="HTML",
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        await ctx.bot.send_message(
            chat_id=q.message.chat_id,
            text=f"❌ Ошибка при генерации плана: {e}\n"
                 "Используй /restart, чтобы попробовать снова.",
        )

    return ConversationHandler.END


# ──────────────────── /restart ────────────────────
async def cmd_restart(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.clear()
    return await cmd_start(update, ctx)


# ──────────────────── /cancel ────────────────────
async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Опрос отменён. Команда /start — начать заново.",
        reply_markup=ReplyKeyboardRemove(),
    )
    ctx.user_data.clear()
    return ConversationHandler.END


# ──────────────────── /help ────────────────────
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "<b>PumpItUp — бот для подбора тренировок</b>\n\n"
        "Команды:\n"
        "/start — пройти опросник и получить план\n"
        "/restart — заполнить опросник заново\n"
        "/cancel — прервать текущий опрос\n"
        "/help — это сообщение\n\n"
        "Алгоритм бота состоит из трёх уровней:\n"
        "1. <b>ML-ранжирование</b> (XGBoost rank:ndcg) — выбирает лучшие "
        "планы из пула 60 шаблонов.\n"
        "2. <b>ML-регрессор нагрузки</b> (MLP) — рассчитывает sets/reps/"
        "rest_sec/RPE по правилам NSCA.\n"
        "3. <b>Rule-based фильтр упражнений</b> — отбирает упражнения "
        "из Free Exercise DB с учётом травм и протоколов ACSM.",
        parse_mode="HTML",
    )


# ──────────────────── Сборка ConversationHandler ────────────────────
def get_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            CommandHandler("restart", cmd_restart),
        ],
        states={
            GENDER:    [CallbackQueryHandler(on_gender, pattern="^(male|female)$")],
            AGE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, on_age)],
            HEIGHT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, on_height)],
            WEIGHT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, on_weight)],
            FAT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_fat),
                CallbackQueryHandler(on_fat, pattern="^skip_fat$"),
            ],
            LEVEL:     [CallbackQueryHandler(on_level, pattern="^(beginner|intermediate|expert)$")],
            ACTIVITY:  [CallbackQueryHandler(on_activity, pattern="^(sedentary|light|active)$")],
            FREQ:      [CallbackQueryHandler(on_freq, pattern="^[2345]$")],
            EQUIPMENT: [CallbackQueryHandler(on_equipment, pattern="^(home|gym)$")],
            WEEKS:     [CallbackQueryHandler(on_weeks, pattern="^[123]$")],
            INJURY:    [CallbackQueryHandler(on_injury, pattern="^(none|knee|back|shoulder|multiple)$")],
            MEDICAL:   [CallbackQueryHandler(on_medical, pattern="^med:")],
            GOAL:      [CallbackQueryHandler(on_goal, pattern="^(weight_loss|muscle_gain|maintenance)$")],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            CommandHandler("restart", cmd_restart),
        ],
    )
