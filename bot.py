import logging
import aiohttp
import json
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8209372152:AAEfgr0dA-MlClYfVo3lfLiIZhNGx6RWm9g"
CHANNEL_ID = "@chekmillion"

# States
WAITING_CITY_WEATHER, WAITING_CITY_LOCATION, WAITING_CITY_NEWS = range(3)

BUSINESS_TIPS = [
    "💡 Инвестируйте в себя — это самый высокодоходный актив.",
    "💡 Не бойтесь делегировать. Успешный бизнес строится командой.",
    "💡 Изучайте своих конкурентов, но не копируйте — улучшайте.",
    "💡 Клиент всегда прав? Нет. Но клиент всегда важен.",
    "💡 80% результата дают 20% усилий — найдите эти 20%.",
    "💡 Кризис — лучшее время для роста. Пока другие боятся, действуйте.",
    "💡 Репутация строится годами, разрушается за минуты. Берегите её.",
    "💡 Автоматизируйте рутину — освободите время для стратегии.",
    "💡 Нетворкинг важнее диплома. Связи решают всё.",
    "💡 Продавайте не продукт, а решение проблемы клиента.",
    "💡 Первые 3 секунды определяют впечатление о вас и вашем бизнесе.",
    "💡 Не ждите идеального момента — начните сейчас и улучшайте по ходу.",
]

CRYPTO_TIPS = [
    "🔐 Храните крипту на холодном кошельке (Ledger, Trezor) — биржи взламывают.",
    "🔐 Никогда не держите все яйца в одной корзине — диверсифицируйте портфель.",
    "🔐 Правило: не инвестируйте больше, чем готовы потерять полностью.",
    "🔐 DCA (усреднение) — покупайте регулярно небольшими суммами, не пытайтесь угадать дно.",
    "🔐 Никогда не делитесь seed-фразой — это ключ от всего вашего капитала.",
    "🔐 DYOR (Do Your Own Research) — проверяйте проекты перед инвестицией.",
    "🔐 Фиксируйте прибыль частями — не ждите максимума, которого может не быть.",
    "🔐 Избегайте FOMO — страх упустить прибыль приводит к убыткам.",
    "🔐 Bitcoin — цифровое золото. Ethereum — цифровая нефть. Остальное — риск.",
    "🔐 Налоги на крипту существуют. Ведите учёт сделок.",
]

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

def subscription_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Подписаться на канал", url=f"https://t.me/chekmillion")],
        [InlineKeyboardButton("✅ Я подписался", callback_data="check_sub")]
    ])

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌤 Погода", callback_data="weather"),
         InlineKeyboardButton("🗺 О городе", callback_data="location")],
        [InlineKeyboardButton("📰 Новости города", callback_data="news"),
         InlineKeyboardButton("💱 Курс валют", callback_data="currency")],
        [InlineKeyboardButton("📈 Крипто", callback_data="crypto"),
         InlineKeyboardButton("💼 Бизнес советы", callback_data="business")],
    ])

def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ])

def back_keyboard_with_cancel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Отмена", callback_data="main_menu")]
    ])

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
        "🤖 Я твой умный помощник! Вот что я умею:\n\n"
        "🌤 *Погода* — текущая погода и прогноз\n"
        "🗺 *О городе* — история, факты, достопримечательности\n"
        "📰 *Новости* — последние новости вашего города\n"
        "💱 *Курс валют* — USD, EUR, RUB и советы\n"
        "📈 *Крипто* — Bitcoin, Ethereum и советы\n"
        "💼 *Бизнес* — советы для предпринимателей\n\n"
        "Выбери раздел 👇",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    is_subscribed = await check_subscription(user.id, context)
    if is_subscribed:
        await query.edit_message_text(
            f"✅ Отлично, {user.first_name}! Подписка подтверждена!\n\n"
            "🤖 Я твой умный помощник! Вот что я умею:\n\n"
            "🌤 *Погода* — текущая погода и прогноз\n"
            "🗺 *О городе* — история, факты, достопримечательности\n"
            "📰 *Новости* — последние новости вашего города\n"
            "💱 *Курс валют* — USD, EUR, RUB и советы\n"
            "📈 *Крипто* — Bitcoin, Ethereum и советы\n"
            "💼 *Бизнес* — советы для предпринимателей\n\n"
            "Выбери раздел 👇",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ Ты ещё не подписался на канал.\nПодпишись и нажми кнопку снова!",
            reply_markup=subscription_keyboard()
        )

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "🏠 Главное меню\n\nВыбери раздел 👇",
        reply_markup=main_keyboard()
    )
    return ConversationHandler.END

async def weather_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🌤 *Погода*\n\nВведи название города (например: Алматы, Москва, Ташкент):",
        parse_mode="Markdown",
        reply_markup=back_keyboard_with_cancel()
    )
    return WAITING_CITY_WEATHER

async def location_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🗺 *О городе*\n\nВведи название города, чтобы узнать его историю, факты и достопримечательности:",
        parse_mode="Markdown",
        reply_markup=back_keyboard_with_cancel()
    )
    return WAITING_CITY_LOCATION

async def news_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📰 *Новости города*\n\nВведи название города для поиска новостей:",
        parse_mode="Markdown",
        reply_markup=back_keyboard_with_cancel()
    )
    return WAITING_CITY_NEWS

async def currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏳ Получаю актуальные курсы валют...")
    result = await get_currency_rates()
    await query.edit_message_text(result, parse_mode="Markdown", reply_markup=back_keyboard())

async def crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏳ Получаю данные о криптовалютах...")
    result = await get_crypto_rates()
    await query.edit_message_text(result, parse_mode="Markdown", reply_markup=back_keyboard())

async def business_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tip = random.choice(BUSINESS_TIPS)
    tip2 = random.choice([t for t in BUSINESS_TIPS if t != tip])
    tip3 = random.choice([t for t in BUSINESS_TIPS if t != tip and t != tip2])
    msg = (
        "💼 *Бизнес советы дня*\n"
        f"{'─' * 30}\n\n"
        f"{tip}\n\n"
        f"{tip2}\n\n"
        f"{tip3}\n\n"
        f"{'─' * 30}\n"
        f"📅 {datetime.now().strftime('%d.%m.%Y')}"
    )
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_keyboard())

async def get_weather(city: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            geo_url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1"
            headers = {"User-Agent": "WeatherBot/1.0"}
            async with session.get(geo_url, headers=headers) as resp:
                geo_data = await resp.json()
            if not geo_data:
                return f"❌ Город '{city}' не найден. Проверьте название."
            lat = geo_data[0]["lat"]
            lon = geo_data[0]["lon"]
            display = geo_data[0].get("display_name", city)
            city_name = display.split(",")[0].strip()

            weather_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,apparent_temperature"
                f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code"
                f"&timezone=auto&forecast_days=5"
            )
            async with session.get(weather_url) as resp:
                weather_data = await resp.json()

            current = weather_data.get("current", {})
            daily = weather_data.get("daily", {})
            temp = current.get("temperature_2m", "N/A")
            feels = current.get("apparent_temperature", "N/A")
            humidity = current.get("relative_humidity_2m", "N/A")
            wind = current.get("wind_speed_10m", "N/A")
            code = current.get("weather_code", 0)

            weather_icons = {
                0: "☀️ Ясно", 1: "🌤 Преимущественно ясно", 2: "⛅ Переменная облачность",
                3: "☁️ Пасмурно", 45: "🌫 Туман", 48: "🌫 Изморозь",
                51: "🌦 Лёгкая морось", 53: "🌦 Морось", 55: "🌧 Сильная морось",
                61: "🌧 Лёгкий дождь", 63: "🌧 Дождь", 65: "🌧 Сильный дождь",
                71: "🌨 Лёгкий снег", 73: "❄️ Снег", 75: "❄️ Сильный снег",
                80: "🌦 Ливень", 81: "⛈ Гроза с дождём", 95: "⛈ Гроза",
            }
            condition = weather_icons.get(code, "🌡 Неизвестно")

            # 5-day forecast
            forecast_lines = []
            days_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            for i in range(min(5, len(daily.get("time", [])))):
                date_str = daily["time"][i]
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                day_name = days_ru[date_obj.weekday()]
                tmax = daily["temperature_2m_max"][i]
                tmin = daily["temperature_2m_min"][i]
                prec = daily["precipitation_sum"][i]
                d_code = daily["weather_code"][i]
                d_icon = weather_icons.get(d_code, "🌡")[:2]
                forecast_lines.append(
                    f"{d_icon} {day_name} {date_obj.strftime('%d.%m')}: {tmin:.0f}°…{tmax:.0f}°C, осадки: {prec:.1f}мм"
                )

            forecast_text = "\n".join(forecast_lines)

            return (
                f"🌍 *{city_name}*\n"
                f"{'─' * 30}\n"
                f"🌡 Температура: *{temp}°C* (ощущается {feels}°C)\n"
                f"💧 Влажность: {humidity}%\n"
                f"💨 Ветер: {wind} км/ч\n"
                f"☁️ Состояние: {condition}\n\n"
                f"📅 *Прогноз на 5 дней:*\n"
                f"{forecast_text}\n\n"
                f"🕐 Обновлено: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
            )
    except Exception as e:
        logger.error(f"Weather error: {e}")
        return "❌ Не удалось получить данные о погоде. Попробуйте позже."

async def get_location_info(city: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "WeatherBot/1.0"}
            geo_url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1&addressdetails=1"
            async with session.get(geo_url, headers=headers) as resp:
                geo_data = await resp.json()
            if not geo_data:
                return f"❌ Город '{city}' не найден."
            place = geo_data[0]
            display = place.get("display_name", city)
            city_name = display.split(",")[0].strip()
            lat = float(place["lat"])
            lon = float(place["lon"])

            # Wikipedia
            wiki_url = f"https://ru.wikipedia.org/api/rest_v1/page/summary/{city_name}"
            async with session.get(wiki_url, headers=headers) as resp:
                if resp.status == 200:
                    wiki_data = await resp.json()
                    extract = wiki_data.get("extract", "")
                    if len(extract) > 800:
                        extract = extract[:800] + "..."
                    wiki_link = wiki_data.get("content_urls", {}).get("mobile", {}).get("page", f"https://ru.wikipedia.org/wiki/{city_name.replace(' ', '_')}")
                else:
                    extract = "Информация из Википедии недоступна."
                    wiki_link = f"https://ru.wikipedia.org/wiki/{city_name.replace(' ', '_')}"

            address = place.get("address", {})
            country = address.get("country", "")
            state = address.get("state", "")

            return (
                f"🗺 *{city_name}*\n"
                f"{'─' * 30}\n"
                f"🌍 Страна: {country}\n"
                f"📍 Регион: {state}\n"
                f"🧭 Координаты: {lat:.4f}°N, {lon:.4f}°E\n\n"
                f"📖 *Об этом городе:*\n{extract}\n\n"
                f"🔗 [Подробнее в Википедии]({wiki_link})"
            )
    except Exception as e:
        logger.error(f"Location error: {e}")
        return "❌ Не удалось получить информацию о городе. Попробуйте позже."

async def get_news(city: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "WeatherBot/1.0"}
            # Use GNews RSS via rss2json
            query = city.replace(" ", "+")
            url = f"https://news.google.com/rss/search?q={query}&hl=ru&gl=RU&ceid=RU:ru"
            async with session.get(url, headers=headers) as resp:
                text = await resp.text()

            # Parse RSS manually
            import re
            items = re.findall(r'<item>(.*?)</item>', text, re.DOTALL)
            news_lines = []
            for item in items[:6]:
                title_match = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item)
                link_match = re.search(r'<link>(.*?)</link>', item)
                if not title_match:
                    title_match = re.search(r'<title>(.*?)</title>', item)
                if title_match:
                    title = title_match.group(1).strip()
                    link = link_match.group(1).strip() if link_match else ""
                    if len(title) > 80:
                        title = title[:80] + "..."
                    if link:
                        news_lines.append(f"• [{title}]({link})")
                    else:
                        news_lines.append(f"• {title}")

            if not news_lines:
                return f"📰 По запросу *{city}* новостей не найдено.\n\nПопробуйте другой город."

            return (
                f"📰 *Новости: {city}*\n"
                f"{'─' * 30}\n\n"
                + "\n\n".join(news_lines) +
                f"\n\n🕐 {datetime.now().strftime('%H:%M %d.%m.%Y')}"
            )
    except Exception as e:
        logger.error(f"News error: {e}")
        return "❌ Не удалось получить новости. Попробуйте позже."

async def get_currency_rates() -> str:
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://open.er-api.com/v6/latest/USD"
            async with session.get(url) as resp:
                data = await resp.json()

            rates = data.get("rates", {})
            usd_kzt = rates.get("KZT", 0)
            usd_rub = rates.get("RUB", 0)
            usd_eur = 1 / rates.get("EUR", 1)
            usd_uzs = rates.get("UZS", 0)
            eur_kzt = usd_kzt / (1 / usd_eur) if usd_eur else 0

            # Simple buy/sell advice based on time
            hour = datetime.now().hour
            if 9 <= hour <= 11:
                advice = "📊 Утро — хорошее время для покупки валюты (рынок только открылся)"
            elif 14 <= hour <= 16:
                advice = "📊 Дневное время — курсы стабильны, можно покупать или продавать"
            elif 18 <= hour <= 20:
                advice = "📊 Вечер — часто курс немного снижается, хорошо для покупки"
            else:
                advice = "📊 Следите за новостями — они влияют на курс больше всего"

            return (
                f"💱 *Курс валют*\n"
                f"{'─' * 30}\n\n"
                f"🇺🇸 *USD* (Доллар)\n"
                f"  → 🇰🇿 KZT: *{usd_kzt:.2f}* тенге\n"
                f"  → 🇷🇺 RUB: *{usd_rub:.2f}* рублей\n"
                f"  → 🇺🇿 UZS: *{usd_uzs:.0f}* сум\n\n"
                f"🇪🇺 *EUR* (Евро)\n"
                f"  → 🇺🇸 USD: *{1/rates.get('EUR',1):.4f}*\n"
                f"  → 🇰🇿 KZT: *{eur_kzt:.2f}* тенге\n\n"
                f"{'─' * 30}\n"
                f"💡 *Совет:*\n{advice}\n\n"
                f"⚠️ Покупайте валюту когда курс низкий, продавайте когда высокий.\n"
                f"📌 Следите за новостями ФРС и ЦБ — они двигают рынок.\n\n"
                f"🕐 Обновлено: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
            )
    except Exception as e:
        logger.error(f"Currency error: {e}")
        return "❌ Не удалось получить курсы валют. Попробуйте позже."

async def get_crypto_rates() -> str:
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,toncoin,binancecoin&vs_currencies=usd,kzt&include_24hr_change=true"
            async with session.get(url) as resp:
                data = await resp.json()

            def fmt_change(val):
                if val is None:
                    return "N/A"
                arrow = "📈" if val > 0 else "📉"
                return f"{arrow} {val:+.2f}%"

            btc = data.get("bitcoin", {})
            eth = data.get("ethereum", {})
            ton = data.get("toncoin", {})
            bnb = data.get("binancecoin", {})

            tip = random.choice(CRYPTO_TIPS)

            # Buy/hold/sell advice based on 24h change
            btc_change = btc.get("usd_24h_change", 0) or 0
            if btc_change < -5:
                market_advice = "🟢 *Рынок упал* — хорошая возможность для покупки (DCA стратегия)"
            elif btc_change > 5:
                market_advice = "🔴 *Рынок вырос* — осторожно, возможна коррекция. Фиксируйте часть прибыли"
            else:
                market_advice = "🟡 *Рынок стабилен* — держите позиции, следите за новостями"

            return (
                f"📈 *Криптовалюты*\n"
                f"{'─' * 30}\n\n"
                f"₿ *Bitcoin (BTC)*\n"
                f"  💵 ${btc.get('usd', 'N/A'):,}\n"
                f"  🇰🇿 {btc.get('kzt', 'N/A'):,} KZT\n"
                f"  24ч: {fmt_change(btc.get('usd_24h_change'))}\n\n"
                f"Ξ *Ethereum (ETH)*\n"
                f"  💵 ${eth.get('usd', 'N/A'):,}\n"
                f"  🇰🇿 {eth.get('kzt', 'N/A'):,} KZT\n"
                f"  24ч: {fmt_change(eth.get('usd_24h_change'))}\n\n"
                f"💎 *TON*\n"
                f"  💵 ${ton.get('usd', 'N/A')}\n"
                f"  24ч: {fmt_change(ton.get('usd_24h_change'))}\n\n"
                f"🔶 *BNB*\n"
                f"  💵 ${bnb.get('usd', 'N/A')}\n"
                f"  24ч: {fmt_change(bnb.get('usd_24h_change'))}\n\n"
                f"{'─' * 30}\n"
                f"📊 *Анализ рынка:*\n{market_advice}\n\n"
                f"🔐 *Совет по хранению:*\n{tip}\n\n"
                f"🕐 Обновлено: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
            )
    except Exception as e:
        logger.error(f"Crypto error: {e}")
        return "❌ Не удалось получить данные о криптовалютах. Попробуйте позже."

async def handle_city_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    msg = await update.message.reply_text("⏳ Получаю данные о погоде...")
    result = await get_weather(city)
    await msg.edit_text(result, parse_mode="Markdown", reply_markup=back_keyboard())
    return ConversationHandler.END

async def handle_city_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    msg = await update.message.reply_text("⏳ Ищу информацию о городе...")
    result = await get_location_info(city)
    await msg.edit_text(result, parse_mode="Markdown", reply_markup=back_keyboard())
    return ConversationHandler.END

async def handle_city_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    msg = await update.message.reply_text("⏳ Ищу новости...")
    result = await get_news(city)
    await msg.edit_text(result, parse_mode="Markdown", reply_markup=back_keyboard())
    return ConversationHandler.END

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_subscribed = await check_subscription(user.id, context)
    if not is_subscribed:
        await update.message.reply_text(
            "❌ Сначала подпишись на канал!",
            reply_markup=subscription_keyboard()
        )
        return
    await update.message.reply_text(
        "👇 Выбери раздел из меню:",
        reply_markup=main_keyboard()
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "🏠 Главное меню\n\nВыбери раздел 👇",
            reply_markup=main_keyboard()
        )
    else:
        await update.message.reply_text("🏠 Главное меню", reply_markup=main_keyboard())
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(weather_callback, pattern="^weather$"),
            CallbackQueryHandler(location_callback, pattern="^location$"),
            CallbackQueryHandler(news_callback, pattern="^news$"),
        ],
        states={
            WAITING_CITY_WEATHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city_weather)],
            WAITING_CITY_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city_location)],
            WAITING_CITY_NEWS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city_news)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^main_menu$"),
            CommandHandler("cancel", cancel),
        ],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(currency_callback, pattern="^currency$"))
    app.add_handler(CallbackQueryHandler(crypto_callback, pattern="^crypto$"))
    app.add_handler(CallbackQueryHandler(business_callback, pattern="^business$"))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
