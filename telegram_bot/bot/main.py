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
    ("🎮 Gaming — Max settings, latest titles", "high_end_gaming"),
    ("🎮 Gaming — Great performance, smart price", "mid_range_gaming"),
    ("🎮 Casual gaming — Fortnite, CS2, Minecraft", "low_end_gaming"),
    ("💼 Everyday — Web, Office, Netflix", "light_work"),
    ("⚡ Power user — Editing, coding, heavy apps", "heavy_work"),
    ("🎨 Creative — Photoshop, Illustrator", "designer"),
    ("🏗️ Engineering — AutoCAD, 3D rendering", "architecture"),
]

BUDGETS = [
    ("Under €1,000 — Basic but capable", "0_1000"),
    ("€1,000 – €1,500 — Best value sweet spot ⭐", "1000_1500"),
    ("€1,500 – €2,000 — High performance", "1500_2000"),
    ("€2,000 – €3,000 — Enthusiast grade", "2000_3000"),
    ("€3,000+ — Absolute best, no limits", "over_3000"),
]

FORM_FACTORS = [
    ("🖥️ Standard — Most popular, easy to upgrade", "atx"),
    ("📦 Compact — Smaller, still very capable", "micro_atx"),
    ("🤏 Mini — Console-size, harder to upgrade", "mini_itx"),
]

CPU_BRANDS = [
    ("🤖 Let us choose — best for your budget ★", "no_preference"),
    ("🔴 AMD Ryzen — great value & multitasking", "amd"),
    ("🔵 Intel Core — great for productivity", "intel"),
]

GPU_BRANDS = [
    ("🤖 Let us choose — best for your budget ★", "no_preference"),
    ("🟢 NVIDIA GeForce — best gaming & AI", "nvidia"),
    ("🔴 AMD Radeon — solid, great value", "amd"),
]

COMPONENT_CATEGORIES = [
    ("Processor (CPU)", "cpu"),
    ("Graphics Card (GPU)", "gpu"),
    ("Motherboard", "motherboard"),
    ("Memory (RAM)", "ram"),
    ("Storage (SSD)", "storage"),
    ("Power Supply", "psu"),
    ("Case", "case"),
    ("CPU Cooler", "cooling"),
]

# (display label, note text sent to Claude)
COMMON_NOTES = [
    ("🔇 Quiet — minimal fan noise", "Quiet/silent components, low noise"),
    ("📶 Must have built-in Wi-Fi", "Must include built-in Wi-Fi"),
    ("💡 I want RGB lighting", "RGB lighting preferred"),
    ("❄️ Water cooling is fine", "Water cooling is acceptable"),
    ("⚡ Max performance", "Maximise performance within budget"),
    ("💰 Best value only", "Best value, avoid overpriced parts"),
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
    buttons.append([InlineKeyboardButton("I don't own any / Continue →", callback_data="ep_done")])
    return InlineKeyboardMarkup(buttons)


def _notes_keyboard(selected: list[int]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            f"{'✅ ' if i in selected else ''}{label}",
            callback_data=f"note_{i}",
        )]
        for i, (label, _) in enumerate(COMMON_NOTES)
    ]
    buttons.append([InlineKeyboardButton("No special preferences →", callback_data="notes_done")])
    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Hi! I'm <b>PcCoach</b>.\n\n"
        "I'll help you build the perfect PC — just answer 8 quick questions "
        "and I'll recommend the exact parts to buy, with prices and links to purchase them.\n\n"
        "It takes about 1 minute. Let's go! 👇\n\n"
        "<b>What will you mainly use this PC for?</b>",
        parse_mode="HTML",
        reply_markup=_make_keyboard(GOALS, "goal_"),
    )
    return GOAL


async def goal_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["goal"] = query.data.removeprefix("goal_")
    await query.edit_message_text(
        "💰 <b>What's your total budget?</b>\n\n"
        "This covers all the PC parts. Pick the range that feels comfortable.\n\n"
        "💡 The <b>€1,000–€1,500</b> range is the sweet spot for most people — "
        "great performance without overpaying.",
        parse_mode="HTML",
        reply_markup=_make_keyboard(BUDGETS, "budget_"),
    )
    return BUDGET


async def budget_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["budget_range"] = query.data.removeprefix("budget_")
    await query.edit_message_text(
        "📐 <b>How big should the PC be?</b>\n\n"
        "This is about the physical size of the case that sits on or under your desk.\n\n"
        "💡 Not sure? Go with <b>Standard</b> — it's the most popular choice and "
        "easiest to upgrade later.",
        parse_mode="HTML",
        reply_markup=_make_keyboard(FORM_FACTORS, "ff_"),
    )
    return FORM_FACTOR


async def form_factor_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["form_factor"] = query.data.removeprefix("ff_")
    await query.edit_message_text(
        "🧠 <b>Any preference for the processor brand?</b>\n\n"
        "The processor is the brain of the PC. Both AMD and Intel are excellent — "
        "the difference for most users is very small.\n\n"
        "💡 If you're not sure, let us pick the best one for your budget.",
        parse_mode="HTML",
        reply_markup=_make_keyboard(CPU_BRANDS, "cpu_"),
    )
    return CPU_BRAND


async def cpu_brand_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["cpu_brand"] = query.data.removeprefix("cpu_")
    await query.edit_message_text(
        "🎮 <b>Any preference for the graphics card brand?</b>\n\n"
        "The graphics card handles visuals — it's the most important part for gaming "
        "and creative work.\n\n"
        "💡 If you're not sure, let us pick the best value option for your budget.",
        parse_mode="HTML",
        reply_markup=_make_keyboard(GPU_BRANDS, "gpu_"),
    )
    return GPU_BRAND


async def gpu_brand_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["gpu_brand"] = query.data.removeprefix("gpu_")
    await query.edit_message_text(
        "🖥️ <b>Do you need a monitor, keyboard and mouse included?</b>\n\n"
        "If you already have these, say No and we'll spend the full budget on the PC itself.\n\n"
        "Adding peripherals typically adds <b>€150–€400</b> depending on quality.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Yes, include them", callback_data="periph_true"),
            InlineKeyboardButton("❌ No, I have them", callback_data="periph_false"),
        ]]),
    )
    return PERIPHERALS


async def peripherals_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["include_peripherals"] = query.data == "periph_true"
    context.user_data["existing_parts"] = []
    await query.edit_message_text(
        "♻️ <b>Do you already own any of these parts?</b>\n\n"
        "Tap anything you already have — we'll leave it out of the build "
        "so you don't pay for something twice.\n\n"
        "If you're starting from scratch, just tap <b>Continue</b>.",
        parse_mode="HTML",
        reply_markup=_existing_parts_keyboard([]),
    )
    return EXISTING_PARTS


async def existing_parts_toggle(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "ep_done":
        context.user_data["selected_notes"] = []
        await query.edit_message_text(
            "📝 <b>Any special preferences?</b>\n\n"
            "Tap to select any that apply — you can pick multiple.\n\n"
            "Or just type your own in plain text. Tap <b>Continue</b> if nothing applies.",
            parse_mode="HTML",
            reply_markup=_notes_keyboard([]),
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
    typed = update.message.text
    selected = context.user_data.get("selected_notes", [])
    if selected:
        selected_texts = ", ".join(COMMON_NOTES[i][1] for i in sorted(selected))
        context.user_data["notes"] = f"{selected_texts}, {typed}"
    else:
        context.user_data["notes"] = typed
    await update.message.reply_text(
        "⚙️ <b>Building your PC recommendation…</b>\n\nThis usually takes 10–20 seconds.",
        parse_mode="HTML",
    )
    await _generate_and_reply(update.message.chat_id, context)
    return ConversationHandler.END


async def notes_toggle(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    idx = int(query.data.removeprefix("note_"))
    selected = context.user_data.setdefault("selected_notes", [])
    if idx in selected:
        selected.remove(idx)
    else:
        selected.append(idx)
    await query.edit_message_reply_markup(reply_markup=_notes_keyboard(selected))
    return NOTES


async def notes_done(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    selected = context.user_data.get("selected_notes", [])
    if selected:
        notes = ", ".join(COMMON_NOTES[i][1] for i in sorted(selected))
    else:
        notes = None
    context.user_data["notes"] = notes
    await query.edit_message_text(
        "⚙️ <b>Building your PC recommendation…</b>\n\nThis usually takes 10–20 seconds.",
        parse_mode="HTML",
    )
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
        async with httpx.AsyncClient(timeout=70.0) as client:
            r = await client.post(f"{API_URL}/api/v1/build", json=payload)
            r.raise_for_status()
            build = r.json()
    except Exception as e:
        logger.error("API call failed: %s", e)
        await context.bot.send_message(
            chat_id,
            "❌ Something went wrong generating your build. Please try again with /build.",
        )
        return

    total = build.get("total_price_eur") or sum(c["price_eur"] for c in build["components"])

    lines = [
        "✅ <b>Your PC Build is ready!</b>\n",
        f"<i>{html.escape(build['summary'])}</i>\n",
        "─────────────────────",
    ]
    for c in build["components"]:
        emoji = CATEGORY_EMOJI.get(c["category"], "•")
        url = c.get("affiliate_url")
        source = c.get("affiliate_source") or "store"
        if url:
            buy = f" — <a href='{html.escape(str(url))}'>Buy on {html.escape(source)}</a>"
        else:
            buy = f" — {html.escape(source)}"
        lines.append(
            f"{emoji} <b>{html.escape(c['name'])}</b>\n"
            f"   💶 €{c['price_eur']:.0f}{buy}"
        )
    lines.append("─────────────────────")
    lines.append(f"💰 <b>Total: €{total:.0f}</b>")
    lines.append("\n<i>Tap any link to go to the store and buy that part.</i>")
    lines.append("<i>Type /build anytime to start a new recommendation.</i>")

    try:
        await context.bot.send_message(
            chat_id,
            "\n".join(lines),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error("Failed to send build result: %s", e)
        await context.bot.send_message(
            chat_id,
            "❌ Failed to send the result. Please try /build again.",
        )


async def cancel(update: Update, context) -> int:
    await update.message.reply_text(
        "No problem! Type /build whenever you're ready to start again.",
    )
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
                CallbackQueryHandler(notes_toggle, pattern=r"^note_\d+$"),
                CallbackQueryHandler(notes_done, pattern="^notes_done$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
            CommandHandler("build", start),
        ],
    )

    app.add_handler(conv)
    logger.info("Bot started")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
