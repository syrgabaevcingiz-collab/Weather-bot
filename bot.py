import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

import requests
import json
from functools import wraps

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота и API ключ OpenAI
TELEGRAM_BOT_TOKEN = '8209372152:AAEfgr0dA-MlClYfVo3lfLiIZhNGx6RWm9g'
CHANNEL_USERNAME = '@chekmillion'
CHANNEL_URL = 'https://t.me/chekmillion'



# Обработчик команды /start
def subscription_required(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not await check_subscription(update, context):
            await send_subscription_prompt(update, context)
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

async def request_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[KeyboardButton("Отправить текущее местоположение", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Пожалуйста, отправьте мне свое местоположение или введите название города.",
        reply_markup=reply_markup
    )

@subscription_required
async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting_location_for_weather"] = True
    await request_location(update, context)

@subscription_required
async def location_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting_location_for_info"] = True
    await request_location(update, context)

@subscription_required
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    latitude = update.message.location.latitude
    longitude = update.message.location.longitude
    if context.user_data.get("awaiting_location_for_weather"):
        await update.message.reply_text(f"Получены координаты: Широта {latitude}, Долгота {longitude}. Обрабатываю запрос погоды...")
        await get_weather_and_respond(update, context, latitude=latitude, longitude=longitude)
        context.user_data["awaiting_location_for_weather"] = False
    elif context.user_data.get("awaiting_location_for_info"):
        await update.message.reply_text(f"Получены координаты: Широта {latitude}, Долгота {longitude}. Обрабатываю запрос информации о местности...")
        await get_location_info_and_respond(update, context, latitude=latitude, longitude=longitude)
        context.user_data["awaiting_location_for_info"] = False
    elif context.user_data.get("awaiting_ad_request"):
        ad_request = update.message.text
        await handle_advertise_request(update, context)
    else:
        await update.message.reply_text("Извините, я не понял вашу команду. Пожалуйста, используйте одну из доступных команд: /weather, /location, /advertise.")

@subscription_required
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    city_name = update.message.text
    if context.user_data.get("awaiting_location_for_weather"):
        await update.message.reply_text(f"Получен город: {city_name}. Обрабатываю запрос погоды...")
        await get_weather_and_respond(update, context, city_name=city_name)
        context.user_data["awaiting_location_for_weather"] = False
    elif context.user_data.get("awaiting_location_for_info"):
        await update.message.reply_text(f"Получен город: {city_name}. Обрабатываю запрос информации о местности...")
        await get_location_info_and_respond(update, context, city_name=city_name)
        context.user_data["awaiting_location_for_info"] = False
    elif context.user_data.get("awaiting_ad_request"):
        ad_request = update.message.text
        await handle_advertise_request(update, context)
    else:
        await update.message.reply_text("Извините, я не понял вашу команду. Пожалуйста, используйте одну из доступных команд: /weather, /location, /advertise.")

async def get_coordinates_from_city(city_name: str) -> tuple[float, float] | None:
    nominatim_url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
    headers = {"User-Agent": "TelegramWeatherBot/1.0"} # Nominatim требует User-Agent
    try:
        response = requests.get(nominatim_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data and len(data) > 0:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при геокодировании города {city_name} через Nominatim: {e}")
    return None

async def get_weather_data(latitude: float, longitude: float) -> dict | None:
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true&hourly=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max&timezone=auto&forecast_days=1"
    try:
        response = requests.get(weather_url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при получении данных о погоде: {e}")
    return None

@subscription_required
async def get_location_info_and_respond(update: Update, context: ContextTypes.DEFAULT_TYPE, latitude: float = None, longitude: float = None, city_name: str = None) -> None:
    if city_name:
        coords = await get_coordinates_from_city(city_name)
        if coords:
            latitude, longitude = coords
        else:
            await update.message.reply_text(f"Не удалось найти город {city_name}. Пожалуйста, попробуйте еще раз или отправьте геолокацию.")
            return

    if latitude is None or longitude is None:
        await update.message.reply_text("Не удалось получить координаты. Пожалуйста, отправьте геолокацию или название города.")
        return

    try:
        # Получаем название города по координатам для запроса в Wikipedia
        if not city_name:
            reverse_geocode_url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json&zoom=10"
            headers = {"User-Agent": "TelegramWeatherBot/1.0"}
            reverse_response = requests.get(reverse_geocode_url, headers=headers)
            reverse_response.raise_for_status()
            reverse_data = reverse_response.json()
            city_name = reverse_data.get("address", {}).get("city") or reverse_data.get("address", {}).get("town") or reverse_data.get("address", {}).get("village")

        if not city_name:
            await update.message.reply_text("Не удалось определить город по указанным координатам.")
            return

        wikipedia_url = f"https://ru.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&redirects=1&format=json&titles={city_name}"
        wikipedia_response = requests.get(wikipedia_url)
        wikipedia_response.raise_for_status()
        wikipedia_data = wikipedia_response.json()

        page = next(iter(wikipedia_data["query"]["pages"].values()))
        if "extract" in page:
            location_info = page["extract"]
            # Ограничиваем длину ответа, чтобы не перегружать пользователя
            if len(location_info) > 1000:
                location_info = location_info[:1000] + "... (подробнее на Wikipedia)"
            await update.message.reply_text(f"Вот что я нашел о {city_name}:\n\n{location_info} 🌍")
        else:
            await update.message.reply_text(f"К сожалению, не удалось найти информацию о {city_name} на Wikipedia. 😔")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при получении информации из Wikipedia: {e}")
        await update.message.reply_text("Произошла ошибка при обработке запроса информации о местности. Пожалуйста, попробуйте позже.")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при обработке информации о местности: {e}")
        await update.message.reply_text("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")


@subscription_required
async def advertise_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[KeyboardButton("Хочу разместить рекламу")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Если вы хотите разместить рекламу, пожалуйста, нажмите кнопку ниже или опишите вашу рекламную кампанию.",
        reply_markup=reply_markup
    )
    context.user_data["awaiting_ad_request"] = True

@subscription_required
async def handle_advertise_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("awaiting_ad_request"):
        ad_request = update.message.text
        # Здесь можно добавить логику сохранения заявки, например, в базу данных или отправку на email
        await update.message.reply_text(
            f"Спасибо за вашу заявку! Мы получили следующее сообщение: \n\n\'{ad_request}\'\n\nМы свяжемся с вами в ближайшее время для обсуждения деталей."
        )
        context.user_data["awaiting_ad_request"] = False
    else:
        await update.message.reply_text("Пожалуйста, используйте команду /advertise, чтобы оставить заявку на рекламу.")


@subscription_required
async def get_weather_and_respond(update: Update, context: ContextTypes.DEFAULT_TYPE, latitude: float = None, longitude: float = None, city_name: str = None) -> None:
    if city_name:
        coords = await get_coordinates_from_city(city_name)
        if coords:
            latitude, longitude = coords
        else:
            await update.message.reply_text(f"Не удалось найти город {city_name}. Пожалуйста, попробуйте еще раз или отправьте геолокацию.")
            return

    if latitude is None or longitude is None:
        await update.message.reply_text("Не удалось получить координаты. Пожалуйста, отправьте геолокацию или название города.")
        return

    weather_data = await get_weather_data(latitude, longitude)

    if weather_data:
        try:
            current_weather = weather_data.get("current_weather", {})
            hourly_data = weather_data.get("hourly", {})
            daily_data = weather_data.get("daily", {})

            temperature = current_weather.get("temperature")
            wind_speed = current_weather.get("windspeed")
            weather_code = current_weather.get("weathercode")

            # Для ощущаемой температуры и вероятности осадков возьмем первое значение из почасовых данных
            apparent_temperature = hourly_data.get("apparent_temperature", ["N/A"])[0]
            precipitation_probability = hourly_data.get("precipitation_probability", ["N/A"])[0]

            # Описание погодного кода (упрощенное)
            weather_descriptions = {
                0: "Ясно ☀️", 1: "В основном ясно 🌤️", 2: "Переменная облачность ⛅", 3: "Пасмурно ☁️",
                45: "Туман 🌫️", 48: "Изморозь 🌫️",
                51: "Легкая морось 🌧️", 53: "Умеренная морось 🌧️", 55: "Интенсивная морось 🌧️",
                56: "Легкий изморось 🌨️", 57: "Интенсивный изморось 🌨️",
                61: "Небольшой дождь ☔", 63: "Умеренный дождь ☔", 65: "Сильный дождь 🌧️",
                66: "Ледяной дождь 🧊", 67: "Сильный ледяной дождь 🧊",
                71: "Небольшой снегопад 🌨️", 73: "Умеренный снегопад 🌨️", 75: "Сильный снегопад ❄️",
                77: "Снежные зерна 🌨️",
                80: "Небольшие ливни  showers ☔", 81: "Умеренные ливни ☔", 82: "Сильные ливни 🌧️",
                85: "Небольшой снегопад 🌨️", 86: "Сильный снегопад ❄️",
                95: "Гроза ⛈️", 96: "Гроза с небольшим градом ⛈️", 99: "Гроза с сильным градом ⛈️"
            }
            weather_description = weather_descriptions.get(weather_code, "Неизвестно")

            weather_summary = (
                f"Погода в {city_name if city_name else 'вашем местоположении'}:\n"
                f"🌡️ Температура: {temperature}°C (ощущается как {apparent_temperature}°C)\n"
                f"💨 Ветер: {wind_speed} м/с\n"
                f"☁️ Условия: {weather_description}\n"
                f"💧 Вероятность осадков: {precipitation_probability}%"
            )
            await update.message.reply_text(weather_summary)
        except Exception as e:
            logger.error(f"Ошибка при формировании ответа о погоде: {e}")
            await update.message.reply_text("Произошла ошибка при обработке запроса погоды. Пожалуйста, попробуйте позже.")
    else:
        await update.message.reply_text("Не удалось получить данные о погоде. Пожалуйста, попробуйте позже.")


async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception as e:
        logger.error(f"Ошибка при проверке подписки: {e}")
    return False

async def send_subscription_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Подписаться на канал", url=CHANNEL_URL)],
        [InlineKeyboardButton("Я подписался", callback_data='check_sub')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Пожалуйста, подпишитесь на наш канал {CHANNEL_USERNAME}, чтобы получить доступ ко всем функциям бота. \n\nПосле подписки нажмите кнопку 'Я подписался'.",
        reply_markup=reply_markup
    )

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == "check_sub":
        if await check_subscription(update, context):
            await query.edit_message_text("Спасибо за подписку! Теперь вам доступны все функции бота. 🎉")
            await start(update, context) # Отправляем приветственное сообщение после успешной подписки
        else:
            await query.edit_message_text("Кажется, вы еще не подписались на канал. Пожалуйста, подпишитесь и попробуйте снова.")
            await send_subscription_prompt(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_subscription(update, context):
        await send_subscription_prompt(update, context)
        return
    user = update.effective_user
    await update.message.reply_html(
        f"Привет, {user.mention_html()}! 👋\nЯ твой персональный помощник. Я могу рассказать тебе о погоде, интересных местах вокруг и помочь с размещением рекламы.\n\nИспользуй команды:\n/weather - узнать погоду\n/location - узнать о местности\n/advertise - разместить рекламу",
    )


def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("location", location_command))
    application.add_handler(CommandHandler("advertise", advertise_command))
    application.add_handler(MessageHandler(filters.Regex("^(Хочу разместить рекламу)"), handle_advertise_request))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(Хочу разместить рекламу)"), handle_text_message))
    application.add_handler(CallbackQueryHandler(check_subscription_callback))

    # Запуск бота в режиме polling
    logger.info("Бот запущен в режиме polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
