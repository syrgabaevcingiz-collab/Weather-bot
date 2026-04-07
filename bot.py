import logging
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8209372152:AAEfgr0dA-MlClYfVo3lfLiIZhNGx6RWm9g"
CHANNEL_ID = "@chekmillion"

WAITING_CITY = 1
WAITING_AD_NAME = 2
WAITING_AD_CONTACT = 3
WAITING_AD_DESC = 4

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

def subscription_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Подписаться на канал", url="https://t.me/chekmillion")],
        [InlineKeyboardButton("✅ Я подписался", callback_data="check_sub")]
    ]
    return InlineKeyboardMarkup(keyboard)

def main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🌤 Погода", callback_data="weather"), InlineKeyboardButton("📍 Моя местность", callback_data="location")],
        [InlineKeyboardButton("📣 Реклама", callback_data="advertise")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_subscribed = await check_subscription(user.id, context)
    if not is_subscribed:
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            "Чтобы пользоваться ботом, нужно подписаться на наш канал 👇",
            reply_markup=subscription_keyboard()
        )
        return
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "🌍 Я помогу тебе узнать погоду и информацию о твоей местности.\n\n"
        "Выбери что тебя интересует:",
        reply_markup=main_keyboard()
    )

async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    is_subscribed = await check_subscription(user.id, context)
    if is_subscribed:
        await query.edit_message_text(
            f"✅ Отлично, {user.first_name}! Подписка подтверждена.\n\n"
            "Выбери что тебя интересует:",
            reply_markup=main_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ Ты ещё не подписался на канал. Подпишись и нажми кнопку снова!",
            reply_markup=subscription_keyboard()
        )

async def weather_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    is_subscribed = await check_subscription(user.id, context)
    if not is_subscribed:
        await query.edit_message_text(
            "Сначала подпишись на канал!",
            reply_markup=subscription_keyboard()
        )
        return
    await query.edit_message_text(
        "🌍 Введи название города для получения погоды:\n\nНапример: Москва, Алматы, Ташкент"
    )
    context.user_data["waiting_for"] = "weather"
    return WAITING_CITY

async def location_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    is_subscribed = await check_subscription(user.id, context)
    if not is_subscribed:
        await query.edit_message_text(
            "Сначала подпишись на канал!",
            reply_markup=subscription_keyboard()
        )
        return
    await query.edit_message_text(
        "📍 Введи название города для получения информации о местности:\n\nНапример: Москва, Алматы, Ташкент"
    )
    context.user_data["waiting_for"] = "location"
    return WAITING_CITY

async def advertise_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    is_subscribed = await check_subscription(user.id, context)
    if not is_subscribed:
        await query.edit_message_text(
            "Сначала подпишись на канал!",
            reply_markup=subscription_keyboard()
        )
        return
    await query.edit_message_text(
        "📣 Размещение рекламы в боте\n\n"
        "Для оформления заявки на рекламу введите ваше имя или название компании:"
    )
    return WAITING_AD_NAME

async def get_weather(city: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            # Geocoding
            geo_url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1"
            headers = {"User-Agent": "WeatherBot/1.0"}
            async with session.get(geo_url, headers=headers) as resp:
                geo_data = await resp.json()
            if not geo_data:
                return f"❌ Город '{city}' не найден. Попробуйте другое название."
            lat = float(geo_data[0]["lat"])
            lon = float(geo_data[0]["lon"])
            display_name = geo_data[0]["display_name"].split(",")[0]

            # Weather
            weather_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,apparent_temperature"
                f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code"
                f"&timezone=auto&forecast_days=3"
            )
            async with session.get(weather_url) as resp:
                weather_data = await resp.json()

            current = weather_data["current"]
            daily = weather_data["daily"]

            wmo_codes = {
                0: "☀️ Ясно", 1: "🌤 Преимущественно ясно", 2: "⛅ Переменная облачность",
                3: "☁️ Пасмурно", 45: "🌫 Туман", 48: "🌫 Изморозь",
                51: "🌦 Лёгкая морось", 53: "🌦 Морось", 55: "🌧 Сильная морось",
                61: "🌧 Небольшой дождь", 63: "🌧 Дождь", 65: "🌧 Сильный дождь",
                71: "🌨 Небольшой снег", 73: "❄️ Снег", 75: "❄️ Сильный снег",
                80: "🌦 Ливень", 81: "🌧 Сильный ливень", 82: "⛈ Очень сильный ливень",
                95: "⛈ Гроза", 96: "⛈ Гроза с градом", 99: "⛈ Сильная гроза с градом"
            }

            code = current["weather_code"]
            condition = wmo_codes.get(code, "🌡 Переменная погода")

            msg = (
                f"🌍 Погода в городе {display_name}\n"
                f"{'─' * 30}\n"
                f"{condition}\n"
                f"🌡 Температура: {current['temperature_2m']}°C (ощущается как {current['apparent_temperature']}°C)\n"
                f"💧 Влажность: {current['relative_humidity_2m']}%\n"
                f"💨 Ветер: {current['wind_speed_10m']} км/ч\n\n"
                f"📅 Прогноз на 3 дня:\n"
            )

            days = ["Сегодня", "Завтра", "Послезавтра"]
            for i in range(3):
                day_code = daily["weather_code"][i]
                day_cond = wmo_codes.get(day_code, "🌡")
                msg += (
                    f"\n{days[i]}: {day_cond}\n"
                    f"  🌡 {daily['temperature_2m_min'][i]}°C ... {daily['temperature_2m_max'][i]}°C\n"
                    f"  🌧 Осадки: {daily['precipitation_sum'][i]} мм\n"
                )
            return msg
    except Exception as e:
        logger.error(f"Weather error: {e}")
        return "❌ Не удалось получить данные о погоде. Попробуйте позже."

async def get_location_info(city: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "WeatherBot/1.0"}
            # Get city info from Nominatim
            geo_url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1&addressdetails=1"
            async with session.get(geo_url, headers=headers) as resp:
                geo_data = await resp.json()
            if not geo_data:
                return f"❌ Город '{city}' не найден."

            place = geo_data[0]
            display = place.get("display_name", city)
            parts = display.split(",")
            city_name = parts[0].strip()
            country = parts[-1].strip() if len(parts) > 1 else ""

            # Wikipedia summary
            wiki_url = f"https://ru.wikipedia.org/api/rest_v1/page/summary/{city_name}"
            async with session.get(wiki_url, headers=headers) as resp:
                if resp.status == 200:
                    wiki_data = await resp.json()
                    extract = wiki_data.get("extract", "")
                    if len(extract) > 500:
                        extract = extract[:500] + "..."
                else:
                    extract = "Информация недоступна."

            msg = (
                f"📍 {city_name}{', ' + country if country else ''}\n"
                f"{'─' * 30}\n"
                f"🌐 Координаты: {float(place['lat']):.4f}°N, {float(place['lon']):.4f}°E\n\n"
                f"📖 Об этом месте:\n{extract}\n\n"
                f"🔗 Подробнее: https://ru.wikipedia.org/wiki/{city_name.replace(' ', '_')}"
            )
            return msg
    except Exception as e:
        logger.error(f"Location error: {e}")
        return "❌ Не удалось получить информацию о местности. Попробуйте позже."

async def handle_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    waiting_for = context.user_data.get("waiting_for")

    if waiting_for == "weather":
        await update.message.reply_text("⏳ Получаю данные о погоде...")
        result = await get_weather(city)
        await update.message.reply_text(result, reply_markup=main_keyboard())
    elif waiting_for == "location":
        await update.message.reply_text("⏳ Ищу информацию о местности...")
        result = await get_location_info(city)
        await update.message.reply_text(result, reply_markup=main_keyboard())

    context.user_data.pop("waiting_for", None)
    return ConversationHandler.END

async def handle_ad_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ad_name"] = update.message.text
    await update.message.reply_text("📞 Введите ваш контакт (телефон или Telegram username):")
    return WAITING_AD_CONTACT

async def handle_ad_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ad_contact"] = update.message.text
    await update.message.reply_text("📝 Опишите вашу рекламу (что рекламируем, бюджет, пожелания):")
    return WAITING_AD_DESC

async def handle_ad_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ad_desc"] = update.message.text
    name = context.user_data.get("ad_name", "")
    contact = context.user_data.get("ad_contact", "")
    desc = context.user_data.get("ad_desc", "")

    await update.message.reply_text(
        f"✅ Заявка на рекламу принята!\n\n"
        f"👤 Имя/компания: {name}\n"
        f"📞 Контакт: {contact}\n"
        f"📝 Описание: {desc}\n\n"
        f"Мы свяжемся с вами в ближайшее время! 🤝",
        reply_markup=main_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_subscribed = await check_subscription(user.id, context)
    if not is_subscribed:
        await update.message.reply_text(
            "Подпишись на канал чтобы пользоваться ботом!",
            reply_markup=subscription_keyboard()
        )
        return
    await update.message.reply_text(
        "Выбери действие из меню:",
        reply_markup=main_keyboard()
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Отменено.", reply_markup=main_keyboard())
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(weather_callback, pattern="^weather$"),
            CallbackQueryHandler(location_callback, pattern="^location$"),
            CallbackQueryHandler(advertise_callback, pattern="^advertise$"),
        ],
        states={
            WAITING_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city)],
            WAITING_AD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ad_name)],
            WAITING_AD_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ad_contact)],
            WAITING_AD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ad_desc)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
