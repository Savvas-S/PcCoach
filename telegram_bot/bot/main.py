import html
import json
import logging
import os
from pathlib import Path

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

_NOTES_MAX_LENGTH = 500

# Conversation states
GOAL, BUDGET, FORM_FACTOR, CPU_BRAND, GPU_BRAND, COOLING_PREFERENCE, PERIPHERALS, EXISTING_PARTS, NOTES = range(9)

# Goal value → display label (bot-specific, emoji-enhanced).
# Valid goals per budget are loaded from the shared canonical source below.
_GOAL_LABELS: dict[str, str] = {
    "high_end_gaming": "🎮 Gaming — Max settings, latest titles",
    "mid_range_gaming": "🎮 Gaming — Great performance, smart price",
    "low_end_gaming": "🎮 Casual gaming — Fortnite, CS2, Minecraft",
    "light_work": "💼 Everyday — Web, Office, Netflix",
    "heavy_work": "⚡ Power user — Editing, coding, heavy apps",
    "designer": "🎨 Creative — Photoshop, Illustrator",
    "architecture": "🏗️ Engineering — AutoCAD, 3D rendering",
}

# Loaded from shared/budget_goals.json (synced via `make sync-config`).
# Edit shared/budget_goals.json and run `make sync-config` — do not edit this copy directly.
_budget_goals_file = Path(__file__).parent.parent / "budget_goals.json"
try:
    _budget_goals_raw: dict[str, list[str]] = json.loads(
        _budget_goals_file.read_text(encoding="utf-8")
    )
except FileNotFoundError:
    raise RuntimeError(
        f"budget_goals.json not found at {_budget_goals_file}. "
        "Run `make sync-config` to copy it from shared/budget_goals.json."
    ) from None

# Validate that every goal in the JSON has a display label — fail loudly if not.
_missing = [g for goals in _budget_goals_raw.values() for g in goals if g not in _GOAL_LABELS]
if _missing:
    raise RuntimeError(
        f"Goals in budget_goals.json have no entry in _GOAL_LABELS: {_missing}. "
        "Add a display label for each new goal."
    )

# Convert to bot keyboard format: {budget: [(label, value), ...]}
BUDGET_GOALS: dict[str, list[tuple[str, str]]] = {
    budget: [(_GOAL_LABELS[g], g) for g in goals]
    for budget, goals in _budget_goals_raw.items()
}

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

COOLING_OPTIONS = [
    ("🤖 Let us choose — best for your build ★", "no_preference"),
    ("❄️ Liquid AIO — quieter & better thermals", "liquid"),
    ("💨 Air cooler — reliable & cost-effective", "air"),
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


async def help_command(update: Update, context) -> None:
    await update.message.reply_text(
        "🖥️ <b>PcCoach</b> — AI-powered PC build recommendations\n\n"
        "Answer a few quick questions and I'll recommend the exact parts to buy, "
        "with prices and links to purchase them.\n\n"
        "<b>Commands:</b>\n"
        "/build — Start a new build recommendation\n"
        "/help — Show this message\n"
        "/cancel — Cancel the current build wizard",
        parse_mode="HTML",
    )


async def start(update: Update, context) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Hi! I'm <b>PcCoach</b>.\n\n"
        "I'll help you build the perfect PC — just answer a few quick questions "
        "and I'll recommend the exact parts to buy, with prices and links to purchase them.\n\n"
        "It takes about 1 minute. Let's go! 👇\n\n"
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
    goals = BUDGET_GOALS.get(context.user_data["budget_range"])
    if goals is None:
        logger.warning("Unexpected budget value: %s", context.user_data["budget_range"])
        goals = list(dict.fromkeys(g for gs in BUDGET_GOALS.values() for g in gs))
    await query.edit_message_text(
        "🎯 <b>What will you mainly use this PC for?</b>\n\n"
        "Based on your budget, here are the best-fit options for you.",
        parse_mode="HTML",
        reply_markup=_make_keyboard(goals, "goal_"),
    )
    return GOAL


async def goal_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["goal"] = query.data.removeprefix("goal_")
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
        "❄️ <b>What cooling do you prefer?</b>\n\n"
        "<b>Liquid AIO</b> — quieter and keeps temperatures lower, ideal for high-end builds.\n"
        "<b>Air cooler</b> — reliable, no risk of leaks, and great value.\n\n"
        "💡 Not sure? Let us pick the best option for your build.",
        parse_mode="HTML",
        reply_markup=_make_keyboard(COOLING_OPTIONS, "cool_"),
    )
    return COOLING_PREFERENCE


async def cooling_selected(update: Update, context) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["cooling_preference"] = query.data.removeprefix("cool_")
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
    if len(typed) > _NOTES_MAX_LENGTH:
        await update.message.reply_text(
            f"⚠️ Your note is too long ({len(typed)} characters). "
            f"Please keep it under {_NOTES_MAX_LENGTH} characters and try again.",
        )
        return NOTES

    selected = context.user_data.get("selected_notes", [])
    if selected:
        selected_texts = ", ".join(COMMON_NOTES[i][1] for i in sorted(selected))
        notes = f"{selected_texts}, {typed}"
    else:
        notes = typed

    if len(notes) > _NOTES_MAX_LENGTH:
        await update.message.reply_text(
            f"⚠️ Your note is too long when combined with your selections "
            f"({len(notes)} characters). Please shorten your typed note and try again.",
        )
        return NOTES

    context.user_data["notes"] = notes
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
        "cooling_preference": data.get("cooling_preference", "no_preference"),
        "include_peripherals": data["include_peripherals"],
        "existing_parts": data.get("existing_parts", []),
        "notes": data.get("notes"),
    }

    try:
        async with httpx.AsyncClient(timeout=95.0) as client:
            r = await client.post(f"{API_URL}/api/v1/build", json=payload)
            r.raise_for_status()
            build = r.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning("Rate limit hit for chat_id=%s", chat_id)
            await context.bot.send_message(
                chat_id,
                "⏳ You've reached the hourly build limit. Please wait a few minutes and try /build again.",
            )
        else:
            logger.error("API error %s for chat_id=%s: %s", e.response.status_code, chat_id, e)
            await context.bot.send_message(
                chat_id,
                "❌ Something went wrong generating your build. Please try again with /build.",
            )
        return
    except Exception as e:
        logger.error("API call failed for chat_id=%s: %s", chat_id, e)
        await context.bot.send_message(
            chat_id,
            "❌ Something went wrong generating your build. Please try again with /build.",
        )
        return

    total = build.get("total_price_eur") or sum(c["price_eur"] for c in build["components"])

    lines = [
        "✅ <b>Your PC Build is ready!</b>\n",
        f"<i>{html.escape(build.get('summary') or '')}</i>\n",
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

    # Write PID file so the Docker healthcheck can verify this process is alive
    Path("/tmp/bot.pid").write_text(str(os.getpid()), encoding="utf-8")

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
            GPU_BRAND:         [CallbackQueryHandler(gpu_brand_selected, pattern="^gpu_")],
            COOLING_PREFERENCE:[CallbackQueryHandler(cooling_selected, pattern="^cool_")],
            PERIPHERALS:       [CallbackQueryHandler(peripherals_selected, pattern="^periph_")],
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
            CommandHandler("help", help_command),
        ],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("help", help_command))
    logger.info("Bot started")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
