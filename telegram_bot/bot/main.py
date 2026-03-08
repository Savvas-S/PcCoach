import html
import logging
import os

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = os.getenv("API_URL", "http://backend:8000")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Conversation states
GOAL, BUDGET, FORM_FACTOR, CPU_BRAND, GPU_BRAND, PERIPHERALS, EXISTING_PARTS, NOTES = range(8)

GOALS = [
    ("🎮 High-End Gaming", "high_end_gaming"),
    ("🎮 Mid-Range Gaming", "mid_range_gaming"),
    ("🎮 Low-End Gaming", "low_end_gaming"),
    ("💼 Light Work", "light_work"),
    ("⚡ Heavy Work", "heavy_work"),
    ("🎨 Designer", "designer"),
    ("🏗️ Architecture", "architecture"),
]

BUDGETS = [
    ("Under €1,000", "0_1000"),
    ("€1,000 – €1,500", "1000_1500"),
    ("€1,500 – €2,000", "1500_2000"),
    ("€2,000 – €3,000", "2000_3000"),
    ("€3,000+", "over_3000"),
]

FORM_FACTORS = [
    ("ATX — Standard", "atx"),
    ("Micro ATX — Compact", "micro_atx"),
    ("Mini ITX — Small", "mini_itx"),
]

CPU_BRANDS = [
    ("AMD", "amd"),
    ("Intel", "intel"),
    ("No preference", "no_preference"),
]

GPU_BRANDS = [
    ("NVIDIA", "nvidia"),
    ("AMD", "amd"),
    ("No preference", "no_preference"),
]

COMPONENT_CATEGORIES = [
    ("CPU", "cpu"),
    ("GPU", "gpu"),
    ("Motherboard", "motherboard"),
    ("RAM", "ram"),
    ("Storage", "storage"),
    ("PSU", "psu"),
    ("Case", "case"),
    ("Cooling", "cooling"),
]

CATEGORY_EMOJI = {
    "cpu": "🧠", "gpu": "🎮", "motherboard": "🔧", "ram": "💾",
    "storage": "💿", "psu": "⚡", "case": "📦", "cooling": "❄️",
    "monitor": "🖥️", "keyboard": "⌨️", "mouse": "🖱️",
}


def _make_keyboard(options: list[tuple[str, str]], prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=f"{prefix}{value}")]
        for label, value in options
    ])


def _existing_parts_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            f"{'✅ ' if value in selected else ''}{label}",
            callback_data=f"ep_{value}",
        )]
        for label, value in COMPONENT_CATEGORIES
    ]
    buttons.append([InlineKeyboardButton("Continue →", callback_data="ep_done")])
    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Welcome to *PcCoach*\\!\n\nI'll help you pick the perfect PC components\\. "
        "Just answer a few questions and I'll generate a full build with prices and links\\.\n\n"
        "*What's the main purpose of this PC?*",
        parse_mode="MarkdownV2",
        reply_markup=_make_keyboard(GOALS, "goal_"),
    )
    return GOAL


async def goal_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["goal"] = query.data.removeprefix("goal_")
    await query.edit_message_text(
        "💰 *What's your budget?*",
        parse_mode="MarkdownV2",
        reply_markup=_make_keyboard(BUDGETS, "budget_"),
    )
    return BUDGET


async def budget_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["budget_range"] = query.data.removeprefix("budget_")
    await query.edit_message_text(
        "🖥️ *What case size do you prefer?*",
        parse_mode="MarkdownV2",
        reply_markup=_make_keyboard(FORM_FACTORS, "ff_"),
    )
    return FORM_FACTOR


async def form_factor_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["form_factor"] = query.data.removeprefix("ff_")
    await query.edit_message_text(
        "⚙️ *CPU brand preference?*",
        parse_mode="MarkdownV2",
        reply_markup=_make_keyboard(CPU_BRANDS, "cpu_"),
    )
    return CPU_BRAND


async def cpu_brand_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["cpu_brand"] = query.data.removeprefix("cpu_")
    await query.edit_message_text(
        "🎮 *GPU brand preference?*",
        parse_mode="MarkdownV2",
        reply_markup=_make_keyboard(GPU_BRANDS, "gpu_"),
    )
    return GPU_BRAND


async def gpu_brand_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["gpu_brand"] = query.data.removeprefix("gpu_")
    await query.edit_message_text(
        "🖱️ *Include peripherals?*\n\nMonitor, keyboard, and mouse\\.",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Yes", callback_data="periph_true"),
            InlineKeyboardButton("❌ No", callback_data="periph_false"),
        ]]),
    )
    return PERIPHERALS


async def peripherals_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["include_peripherals"] = query.data == "periph_true"
    context.user_data["existing_parts"] = []
    await query.edit_message_text(
        "♻️ *Do you already own any of these parts?*\n\nSelect all that apply, then tap *Continue*\\.",
        parse_mode="MarkdownV2",
        reply_markup=_existing_parts_keyboard([]),
    )
    return EXISTING_PARTS


COMMON_NOTES = [
    ("🔇 Prefer quiet components", "Prefer quiet components"),
    ("📶 Need Wi-Fi", "Need Wi-Fi"),
    ("💡 RGB lighting", "RGB lighting preferred"),
    ("❄️ Water cooling OK", "Water cooling is acceptable"),
    ("⚡ Best performance possible", "Prioritise performance over everything else"),
    ("💰 Best value for money", "Best value for money, avoid overpriced parts"),
]


async def existing_parts_toggle(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "ep_done":
        buttons = [
            [InlineKeyboardButton(label, callback_data=f"note_{value}")]
            for label, value in COMMON_NOTES
        ]
        buttons.append([InlineKeyboardButton("Skip →", callback_data="notes_skip")])
        await query.edit_message_text(
            "📝 *Any preferences?*\n\nPick one below or just type your own note\\.",
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return NOTES

    part = query.data.removeprefix("ep_")
    existing = context.user_data["existing_parts"]
    if part in existing:
        existing.remove(part)
    else:
        existing.append(part)

    await query.edit_message_reply_markup(
        reply_markup=_existing_parts_keyboard(existing),
    )
    return EXISTING_PARTS


async def notes_received(update: Update, context) -> int:
    context.user_data["notes"] = update.message.text
    await update.message.reply_text("⚙️ Generating your build, this may take a moment…")
    await _generate_and_reply(update.message.chat_id, context)
    return ConversationHandler.END


async def note_picked(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["notes"] = query.data.removeprefix("note_")
    await query.edit_message_text("⚙️ Generating your build, this may take a moment…")
    await _generate_and_reply(query.message.chat_id, context)
    return ConversationHandler.END


async def notes_skipped(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["notes"] = None
    await query.edit_message_text("⚙️ Generating your build, this may take a moment…")
    await _generate_and_reply(query.message.chat_id, context)
    return ConversationHandler.END


async def _generate_and_reply(chat_id: int, context) -> None:
    data = context.user_data
    payload = {
        "goal": data["goal"],
        "budget_range": data["budget_range"],
        "form_factor": data["form_factor"],
        "cpu_brand": data["cpu_brand"],
        "gpu_brand": data["gpu_brand"],
        "include_peripherals": data["include_peripherals"],
        "existing_parts": data.get("existing_parts", []),
        "notes": data.get("notes"),
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            r = await client.post(f"{API_URL}/api/v1/build", json=payload)
            r.raise_for_status()
            build = r.json()
    except Exception as e:
        logger.error("API call failed: %s", e)
        await context.bot.send_message(
            chat_id,
            "❌ Failed to generate build. Please try again with /build.",
        )
        return

    lines = [
        f"✅ <b>Your PC Build — €{build['total_price_eur']:.0f} total</b>\n",
        f"<i>{html.escape(build['summary'])}</i>\n",
    ]
    for c in build["components"]:
        emoji = CATEGORY_EMOJI.get(c["category"], "•")
        lines.append(
            f"{emoji} <b>{html.escape(c['name'])}</b> — €{c['price_eur']:.0f}\n"
            f"   <a href='{c['affiliate_url']}'>{c['affiliate_source']}</a>"
        )
    lines.append("\n<i>Tap any link to buy the component.</i>")

    try:
        await context.bot.send_message(
            chat_id,
            "\n".join(lines),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error("Failed to send build result: %s", e)
        await context.bot.send_message(chat_id, "❌ Failed to send result. Please try /build again.")


async def cancel(update: Update, context) -> int:
    await update.message.reply_text("Cancelled. Type /build to start a new build.")
    return ConversationHandler.END


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("build", start),
        ],
        states={
            GOAL:           [CallbackQueryHandler(goal_selected, pattern="^goal_")],
            BUDGET:         [CallbackQueryHandler(budget_selected, pattern="^budget_")],
            FORM_FACTOR:    [CallbackQueryHandler(form_factor_selected, pattern="^ff_")],
            CPU_BRAND:      [CallbackQueryHandler(cpu_brand_selected, pattern="^cpu_")],
            GPU_BRAND:      [CallbackQueryHandler(gpu_brand_selected, pattern="^gpu_")],
            PERIPHERALS:    [CallbackQueryHandler(peripherals_selected, pattern="^periph_")],
            EXISTING_PARTS: [CallbackQueryHandler(existing_parts_toggle, pattern="^ep_")],
            NOTES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, notes_received),
                CallbackQueryHandler(note_picked, pattern="^note_"),
                CallbackQueryHandler(notes_skipped, pattern="^notes_skip$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    logger.info("Bot started")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
