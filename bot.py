import logging
import aiohttp
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from functools import wraps

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота и канал для проверки подписки
TELEGRAM_BOT_TOKEN = '8693966108:AAHqOBCH_Byo493EFbRq0Kl3nTawzwOS_wo'
CHANNEL_USERNAME = '@chekmillion'
CHANNEL_URL = 'https://t.me/chekmillion'

# ID администратора для получения заявок
ADMIN_ID = 6826526136
ADMIN_CONTACT_URL = 'https://t.me/+6826526136'

# OpenAI API
import os
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')

# Системный промпт для AI-помощника
AI_SYSTEM_PROMPT = """Ты — AI-помощник проекта «Чек на миллион», основанного Чингизом (Чико).
Ты помогаешь людям зарабатывать в интернете через AI, личный бренд и системный подход.

Твои правила:
- Отвечай кратко, по делу, дружелюбно и мотивирующе
- Давай практичные советы по бизнесу, заработку онлайн, AI, личному бренду, продажам
- Если спрашивают про услуги — расскажи про консультации, построение личного бренда, автоматизацию продаж, обучение
- Всегда упоминай канал @chekmillion как источник полезных материалов
- Не давай медицинских, юридических или финансовых советов (инвестиции)
- Отвечай на русском языке
- Будь энергичным и позитивным, как настоящий бизнес-наставник
"""

# --- AI функция ---
async def ask_ai(user_message: str, chat_history: list = None) -> str:
    if not OPENAI_API_KEY:
        return "AI-помощник временно недоступен. Но я могу помочь через меню — нажмите /start!"
    
    messages = [{"role": "system", "content": AI_SYSTEM_PROMPT}]
    
    if chat_history:
        messages.extend(chat_history[-6:])  # Последние 6 сообщений для контекста
    
    messages.append({"role": "user", "content": user_message})
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-4.1-mini",
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7
            }
            async with session.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result['choices'][0]['message']['content']
                else:
                    logger.error(f"AI API error: {resp.status}")
                    return "Извините, AI-помощник сейчас занят. Попробуйте позже или используйте меню /start!"
    except Exception as e:
        logger.error(f"AI error: {e}")
        return "Извините, AI-помощник сейчас занят. Попробуйте позже или используйте меню /start!"

# --- Функции для проверки подписки ---
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
        [InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL)],
        [InlineKeyboardButton("✅ Я подписался", callback_data='check_sub')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "👋 Добро пожаловать в *Чек на миллион*!\n\n"
        "Чтобы получить доступ к боту, подпишитесь на наш канал "
        f"{CHANNEL_USERNAME}\n\n"
        "После подписки нажмите кнопку '✅ Я подписался'"
    )
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception:
            await context.bot.send_message(update.effective_chat.id, text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == "check_sub":
        if await check_subscription(update, context):
            user = update.effective_user
            welcome_message = (
                f"🎉 Спасибо за подписку, {user.first_name}!\n\n"
                "Теперь тебе доступны все функции бота.\n\n"
                "🤖 *AI-помощник* — просто напиши мне любой вопрос про бизнес, заработок или AI, и я отвечу!\n\n"
                "Или выбери раздел ниже:"
            )
            await query.edit_message_text(
                welcome_message,
                reply_markup=await main_menu_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Кажется, ты ещё не подписался. Подпишись и попробуй снова!")
            await send_subscription_prompt(update, context)

def subscription_required(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not await check_subscription(update, context):
            await send_subscription_prompt(update, context)
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# --- Главное меню --- 
async def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🎁 Бесплатный гайд по AI", callback_data='guide')],
        [InlineKeyboardButton("💼 Наши услуги", callback_data='services')],
        [InlineKeyboardButton("📈 Как это работает", callback_data='how_it_works')],
        [InlineKeyboardButton("🔥 Истории успеха", callback_data='success_stories')],
        [InlineKeyboardButton("📞 Записаться на консультацию", callback_data='consultation')],
        [InlineKeyboardButton("🤖 Задать вопрос AI", callback_data='ask_ai_mode')],
        [InlineKeyboardButton("📢 Канал @chekmillion", url=CHANNEL_URL)]
    ]
    return InlineKeyboardMarkup(keyboard)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🏠 *Главное меню*\n\nВыбери интересующий раздел или просто напиши мне вопрос — AI-помощник ответит!",
            reply_markup=await main_menu_keyboard(),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "🏠 *Главное меню*\n\nВыбери интересующий раздел или просто напиши мне вопрос — AI-помощник ответит!",
            reply_markup=await main_menu_keyboard(),
            parse_mode='Markdown'
        )

# --- Обработчик команды /start ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_subscription(update, context):
        await send_subscription_prompt(update, context)
        return

    user = update.effective_user
    welcome_message = (
        f"👋 Привет, *{user.first_name}*!\n\n"
        "Я AI-помощник проекта *«Чек на миллион»* от Чингиза.\n\n"
        "Я помогаю предпринимателям и экспертам зарабатывать больше, "
        "используя AI и системный подход.\n\n"
        "🤖 *Что я умею:*\n"
        "• Отвечать на вопросы про бизнес и заработок\n"
        "• Давать советы по AI и автоматизации\n"
        "• Помогать с идеями для контента\n"
        "• Рассказывать про наши услуги\n\n"
        "💡 *Просто напиши мне любой вопрос* или выбери раздел ниже:"
    )
    await update.message.reply_text(welcome_message, reply_markup=await main_menu_keyboard(), parse_mode='Markdown')

# --- AI режим ---
@subscription_required
async def ask_ai_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🤖 *AI-помощник активирован!*\n\n"
        "Задай мне любой вопрос про:\n"
        "• Заработок в интернете\n"
        "• Бизнес и продажи\n"
        "• AI и автоматизацию\n"
        "• Личный бренд\n"
        "• Контент и маркетинг\n\n"
        "Просто напиши свой вопрос прямо сейчас! ✍️",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    context.user_data['awaiting_consultation_details'] = False

# --- Обработчики разделов --- 
@subscription_required
async def guide_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    guide_text = (
        "🎁 *5 способов заработать с AI и внедрить их в свой бизнес*\n\n"
        "*1. AI-контент для личного бренда* 📱\n"
        "Создавай уникальный контент для соцсетей с помощью AI. "
        "Посты, рилсы, сторис — AI генерирует идеи и тексты за минуты.\n\n"
        "*2. Comment AI для Instagram* 💬\n"
        "Автоматические персонализированные ответы на комментарии. "
        "Увеличь вовлечённость и лояльность аудитории в 3 раза.\n\n"
        "*3. AI-воронки продаж* 🔄\n"
        "AI-боты квалифицируют лидов, отвечают на вопросы и "
        "ведут клиента к покупке 24/7 без твоего участия.\n\n"
        "*4. Продажа AI-услуг бизнесам* 💰\n"
        "Предлагай компаниям внедрение AI: чат-боты, автоматизация, "
        "генерация контента. Средний чек от 50 000 руб.\n\n"
        "*5. Создание и продажа AI-промптов* 📝\n"
        "Разрабатывай эффективные промпты и продавай их. "
        "Пассивный доход без ограничений!\n\n"
        "Хочешь узнать подробнее? Напиши мне вопрос или запишись на консультацию! 🚀"
    )
    await query.edit_message_text(guide_text, reply_markup=reply_markup, parse_mode='Markdown')

@subscription_required
async def services_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📞 Записаться", callback_data='consultation')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    services_text = (
        "💼 *Наши услуги*\n\n"
        "*1. Консультации 1 на 1* (60-90 мин) 🎯\n"
        "Разбор твоей ситуации + конкретный план действий на 30-90 дней\n\n"
        "*2. Построение личного бренда* 👤\n"
        "Позиционирование, стратегия контента, система прогрева, "
        "перевод подписчиков в продажи\n\n"
        "*3. Запуск и автоматизация продаж* ⚙️\n"
        "Настройка воронок (YouTube + Instagram + Telegram), "
        "создание офферов, автоматизация через AI\n\n"
        "*4. Обучение и гайды под ключ* 📚\n"
        "Готовые промпты, шаблоны, мини-курсы, чек-листы "
        "по заработку с AI и личному бренду\n\n"
        "👇 Нажми «Записаться» чтобы начать!"
    )
    await query.edit_message_text(services_text, reply_markup=reply_markup, parse_mode='Markdown')

@subscription_required
async def how_it_works_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    how_it_works_text = (
        "📈 *Как работает система Чингиза*\n\n"
        "Три ключевых столпа:\n\n"
        "*1. AI (Искусственный Интеллект)* 🤖\n"
        "Автоматизация рутины, генерация контента, "
        "персонализированные воронки продаж 24/7\n\n"
        "*2. Личный бренд* 👤\n"
        "Узнаваемый образ эксперта, который привлекает "
        "клиентов и партнёров автоматически\n\n"
        "*3. Системный подход* ⚙️\n"
        "Каждый элемент бизнеса работает как единый механизм. "
        "Стабильный и прогнозируемый рост.\n\n"
        "Результат: ты перестаёшь работать «руками» и создаёшь "
        "систему, которая приносит доход даже когда ты спишь! 💤💰"
    )
    await query.edit_message_text(how_it_works_text, reply_markup=reply_markup, parse_mode='Markdown')

@subscription_required
async def success_stories_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📞 Хочу так же!", callback_data='consultation')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    stories_text = (
        "🔥 *Истории успеха*\n\n"
        "*Анна, SMM-эксперт:* 📈\n"
        "Внедрила AI для контента и воронок. "
        "Доход вырос на 150% за 3 месяца!\n\n"
        "*Дмитрий, онлайн-школа:* 🚀\n"
        "Построил личный бренд + AI-бот для студентов. "
        "Продажи курсов выросли на 80%!\n\n"
        "*Елена, копирайтер:* 💰\n"
        "Освоила создание AI-промптов. Вышла на "
        "международный рынок, доход x2.5 за полгода!\n\n"
        "Хочешь такие же результаты? 👇"
    )
    await query.edit_message_text(stories_text, reply_markup=reply_markup, parse_mode='Markdown')

@subscription_required
async def consultation_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data['awaiting_consultation_details'] = True
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "📞 *Запись на консультацию*\n\n"
        "Напиши в одном сообщении:\n\n"
        "1️⃣ Твоё имя\n"
        "2️⃣ Сфера деятельности\n"
        "3️⃣ Главная проблема или цель\n\n"
        "_Например:_\n"
        "_Иван, маркетинг, хочу увеличить охваты в Instagram_\n\n"
        "Мы свяжемся с тобой для обсуждения деталей! ✍️",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# --- Обработчик текстовых сообщений ---
@subscription_required
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('awaiting_consultation_details'):
        details = update.message.text
        context.user_data['awaiting_consultation_details'] = False
        user = update.effective_user
        username = f"@{user.username}" if user.username else f"ID: {user.id}"
        
        # Отправляем заявку администратору
        try:
            admin_text = (
                "🔔 *Новая заявка на консультацию!*\n\n"
                f"👤 Пользователь: {user.first_name} ({username})\n"
                f"📋 Данные: {details}\n\n"
                f"💬 Написать: https://t.me/{user.username}" if user.username else 
                f"🔔 *Новая заявка на консультацию!*\n\n"
                f"👤 Пользователь: {user.first_name} (ID: {user.id})\n"
                f"📋 Данные: {details}"
            )
            await context.bot.send_message(ADMIN_ID, admin_text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Ошибка отправки заявки админу: {e}")
        
        # Отправляем пользователю подтверждение + ссылку на связь
        keyboard = [
            [InlineKeyboardButton("💬 Написать администратору", url="https://t.me/adm_chek")],
            [InlineKeyboardButton("📢 Наш канал", url=CHANNEL_URL)],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"✅ *Заявка принята!*\n\n"
            f"Твои данные:\n_{details}_\n\n"
            "Мы получили твою заявку и скоро свяжемся!\n\n"
            "А пока можешь написать напрямую нашему администратору 👇",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        # AI отвечает на любое сообщение
        user_message = update.message.text
        
        # Показываем что бот печатает
        await context.bot.send_chat_action(update.effective_chat.id, 'typing')
        
        # Получаем историю чата из контекста
        if 'chat_history' not in context.user_data:
            context.user_data['chat_history'] = []
        
        # Запрашиваем AI
        ai_response = await ask_ai(user_message, context.user_data.get('chat_history', []))
        
        # Сохраняем в историю
        context.user_data['chat_history'].append({"role": "user", "content": user_message})
        context.user_data['chat_history'].append({"role": "assistant", "content": ai_response})
        
        # Ограничиваем историю
        if len(context.user_data['chat_history']) > 20:
            context.user_data['chat_history'] = context.user_data['chat_history'][-12:]
        
        keyboard = [
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🤖 *AI-помощник:*\n\n{ai_response}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# --- Главная функция запуска бота ---
def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(check_subscription_callback, pattern='^check_sub$'))
    application.add_handler(CallbackQueryHandler(main_menu, pattern='^main_menu$'))
    application.add_handler(CallbackQueryHandler(guide_section, pattern='^guide$'))
    application.add_handler(CallbackQueryHandler(services_section, pattern='^services$'))
    application.add_handler(CallbackQueryHandler(how_it_works_section, pattern='^how_it_works$'))
    application.add_handler(CallbackQueryHandler(success_stories_section, pattern='^success_stories$'))
    application.add_handler(CallbackQueryHandler(consultation_section, pattern='^consultation$'))
    application.add_handler(CallbackQueryHandler(ask_ai_mode, pattern='^ask_ai_mode$'))

    # Обработчик текстовых сообщений (AI + консультация)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    logger.info("Бот запущен в режиме polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
