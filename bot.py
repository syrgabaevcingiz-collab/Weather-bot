import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
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
        [InlineKeyboardButton("Подписаться на канал", url=CHANNEL_URL)],
        [InlineKeyboardButton("Я подписался", callback_data='check_sub')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(
            f"Пожалуйста, подпишитесь на наш канал {CHANNEL_USERNAME}, чтобы получить доступ ко всем функциям бота. \n\nПосле подписки нажмите кнопку 'Я подписался'.",
            reply_markup=reply_markup
        )
    else:
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
            await start_command(update, context) # Отправляем приветственное сообщение после успешной подписки
        else:
            await query.edit_message_text("Кажется, вы еще не подписались на канал. Пожалуйста, подпишитесь и попробуйте снова.")
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
        [InlineKeyboardButton("📢 Канал @chekmillion", url=CHANNEL_URL)]
    ]
    return InlineKeyboardMarkup(keyboard)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "Добро пожаловать в главное меню! Выберите интересующий раздел:",
            reply_markup=await main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "Добро пожаловать в главное меню! Выберите интересующий раздел:",
            reply_markup=await main_menu_keyboard()
        )

# --- Обработчик команды /start ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_subscription(update, context):
        await send_subscription_prompt(update, context)
        return

    user = update.effective_user
    welcome_message = (
        f"Привет, {user.mention_html()}! 👋\n\nЯ бот-помощник Чингиза, основателя проекта 'Чек на миллион'. "
        "Мы помогаем предпринимателям и экспертам кратно расти в доходе, используя AI и системный подход. "
        "Начните свой путь к миллиону прямо сейчас!\n\n" 
        "Вот ваш бесплатный мини-гайд '5 способов заработать с AI и внедрить их в свой бизнес':\n\n"
        "*1. AI-контент для личного бренда*\n" 
        "Создавайте уникальный и вовлекающий контент для своих соцсетей (посты, сторис, рилсы) с помощью AI. "
        "Это сэкономит время и поможет выделиться.\n\n"
        "*2. Comment AI для Instagram*\n" 
        "Используйте AI для автоматического и персонализированного ответа на комментарии в Instagram. "
        "Увеличьте вовлеченность и лояльность аудитории.\n\n"
        "*3. AI-воронки продаж*\n" 
        "Автоматизируйте процесс продаж с помощью AI-ботов, которые квалифицируют лидов, отвечают на вопросы и "
        "ведут клиента к покупке 24/7.\n\n"
        "*4. Продажа AI-услуг бизнесам*\n" 
        "Предлагайте другим компаниям внедрение AI-решений: от автоматизации рутины до создания "
        "инновационных продуктов. Это очень востребовано!\n\n"
        "*5. Создание и продажа AI-промптов*\n" 
        "Разрабатывайте эффективные промпты для различных AI-моделей и продавайте их тем, кто хочет "
        "получать качественные результаты без лишних усилий.\n\n"
        "Выберите раздел ниже, чтобы узнать больше или получить помощь:"
    )
    await update.message.reply_html(welcome_message, reply_markup=await main_menu_keyboard())

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
        "🎁 *Бесплатный гайд по AI: 5 способов заработать с AI и внедрить их в свой бизнес*\n\n"
        "Вот более подробное описание каждого способа:\n\n"
        "*1. AI-контент для личного бренда*\n" 
        "\t*Шаги:*\n" 
        "\t1. Определите свою целевую аудиторию и её интересы.\n" 
        "\t2. Используйте AI-инструменты (например, ChatGPT, Jasper AI) для генерации идей для постов, статей, сценариев видео.\n" 
        "\t3. Редактируйте и адаптируйте сгенерированный контент под свой стиль и голос.\n" 
        "\t4. Публикуйте и анализируйте вовлеченность, чтобы улучшать стратегию.\n\n"
        "*2. Comment AI для Instagram*\n" 
        "\t*Шаги:*\n" 
        "\t1. Выберите сервис, который интегрируется с Instagram и предлагает AI-ответы (например, ManyChat с интеграцией AI).\n" 
        "\t2. Обучите AI на примерах ваших ответов и часто задаваемых вопросов.\n" 
        "\t3. Настройте правила для автоматических ответов на комментарии и сообщения в директ.\n" 
        "\t4. Мониторьте работу AI и периодически корректируйте его ответы.\n\n"
        "*3. AI-воронки продаж*\n" 
        "\t*Шаги:*\n" 
        "\t1. Определите этапы вашей воронки продаж.\n" 
        "\t2. Создайте AI-бота (например, в Telegram, WhatsApp) для каждого этапа: от первого контакта до закрытия сделки.\n" 
        "\t3. Интегрируйте бота с CRM-системой для отслеживания лидов.\n" 
        "\t4. Тестируйте и оптимизируйте воронку для повышения конверсии.\n\n"
        "*4. Продажа AI-услуг бизнесам*\n" 
        "\t*Шаги:*\n" 
        "\t1. Изучите потребности малого и среднего бизнеса в автоматизации и оптимизации.\n" 
        "\t2. Разработайте пакеты AI-услуг (например, создание чат-ботов, анализ данных, генерация контента).\n" 
        "\t3. Создайте портфолио и кейсы успешных внедрений.\n" 
        "\t4. Активно предлагайте свои услуги через LinkedIn, холодные рассылки, партнерства.\n\n"
        "*5. Создание и продажа AI-промптов*\n" 
        "\t*Шаги:*\n" 
        "\t1. Выберите нишу, где промпты могут быть особенно полезны (маркетинг, копирайтинг, дизайн).\n" 
        "\t2. Экспериментируйте с различными AI-моделями и создавайте высококачественные, эффективные промпты.\n" 
        "\t3. Упакуйте промпты в удобные сборники или шаблоны.\n" 
        "\t4. Продавайте их на специализированных платформах (например, PromptBase) или через свой сайт/соцсети.\n\n"
        "Надеюсь, этот гайд вдохновит вас на новые свершения! ✨"
    )
    await query.edit_message_text(guide_text, reply_markup=reply_markup, parse_mode='Markdown')

@subscription_required
async def services_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    services_text = (
        "💼 *Наши услуги*\n\n"
        "Мы предлагаем комплексные решения для вашего роста:\n\n"
        "*1. Консультации и разборы 1 на 1 (60-90 мин)*\n" 
        "\tИндивидуальный подход к вашим задачам, глубокий анализ ситуации и разработка "
        "персональной стратегии роста с использованием AI.\n\n"
        "*2. Построение личного бренда*\n" 
        "\tПоможем вам создать сильный и узнаваемый личный бренд, который будет "
        "привлекать клиентов и партнеров. Включает стратегию контента, позиционирование и "
        "использование AI-инструментов.\n\n"
        "*3. Запуск и автоматизация онлайн-продаж*\n" 
        "\tРазработаем и внедрим эффективные воронки продаж, настроим автоматизацию "
        "процессов, чтобы ваш бизнес работал как часы и приносил стабильный доход.\n\n"
        "*4. Обучение и гайды под ключ*\n" 
        "\tПредоставим готовые обучающие материалы и пошаговые гайды по внедрению AI "
        "и автоматизации в ваш бизнес. Все, что нужно для самостоятельного старта!\n\n"
        "Чтобы узнать подробнее или записаться, выберите соответствующий раздел в главном меню или "
        "нажмите кнопку 'Записаться на консультацию'."
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
        "📈 *Как это работает: Система Чингиза*\n\n"
        "Наша уникальная система основана на трех ключевых столпах, которые гарантируют "
        "взрывной рост вашего бизнеса и личного бренда:\n\n"
        "*1. AI (Искусственный Интеллект)* 🤖\n" 
        "\tМы используем передовые AI-технологии для автоматизации рутинных задач, "
        "генерации высококачественного контента, анализа данных и создания "
        "персонализированных воронок продаж. AI становится вашим незаменимым "
        "помощником, работающим 24/7.\n\n"
        "*2. Личный бренд* 👤\n" 
        "\tСильный личный бренд — это магнит для клиентов и возможностей. Мы поможем "
        "вам выстроить узнаваемый образ эксперта, который вызывает доверие и "
        "привлекает целевую аудиторию. Ваш бренд будет работать на вас, даже когда вы спите.\n\n"
        "*3. Системный подход* ⚙️\n" 
        "\tМы не предлагаем разовых решений, а строим целостные, масштабируемые "
        "системы. Это означает, что каждый элемент вашего бизнеса будет работать "
        "эффективно и взаимосвязанно, обеспечивая стабильный и прогнозируемый рост. "
        "Мы создаем фундамент для вашего долгосрочного успеха.\n\n"
        "Сочетание этих трех элементов позволяет нашим клиентам достигать "
        "выдающихся результатов и выходить на новый уровень дохода! 🚀"
    )
    await query.edit_message_text(how_it_works_text, reply_markup=reply_markup, parse_mode='Markdown')

@subscription_required
async def success_stories_section(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    stories_text = (
        "🔥 *Истории успеха наших клиентов*\n\n"
        "Мы гордимся результатами наших клиентов. Вот несколько примеров того, "
        "как наша система помогла им достичь новых высот:\n\n"
        "*1. Анна, эксперт по SMM:*\n" 
        "\tДо работы с нами Анна тратила часы на создание контента и "
        "привлечение клиентов. После внедрения AI-инструментов для контента и "
        "автоматизации воронок, её доход вырос на 150% за 3 месяца, а свободного "
        "времени стало вдвое больше! 📈\n\n"
        "*2. Дмитрий, владелец онлайн-школы:*\n" 
        "\tДмитрий столкнулся с проблемой масштабирования и удержания клиентов. "
        "Мы помогли ему построить сильный личный бренд и запустить AI-бота для "
        "поддержки студентов. Результат: увеличение продаж курсов на 80% и "
        "повышение лояльности аудитории. 🚀\n\n"
        "*3. Елена, фрилансер-копирайтер:*\n" 
        "\tЕлена хотела увеличить количество заказов и повысить свой средний чек. "
        "С нашей помощью она освоила создание и продажу AI-промптов, что "
        "позволило ей выйти на международный рынок и увеличить доход в 2.5 раза "
        "за полгода. 💰\n\n"
        "Эти истории — лишь малая часть того, что возможно с правильным подходом "
        "и использованием современных технологий!"
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
        "📞 *Записаться на консультацию*\n\n" 
        "Чтобы записаться на индивидуальную консультацию, пожалуйста, "
        "напишите в одном сообщении следующую информацию:\n\n" 
        "*1. Ваше имя:*\n" 
        "*2. Ваша сфера деятельности:*\n" 
        "*3. Ваша основная проблема или цель, которую вы хотите решить:*
        "\nНапример: \nИмя: Иван \nСфера: Маркетинг \nПроблема: Не могу увеличить охваты в Instagram\n\n" 
        "Мы свяжемся с вами в ближайшее время для уточнения деталей и "
        "назначения удобного времени. \n\n" 
        "Также вы можете напрямую написать Чингизу в Telegram: @chekmillion",
        reply_markup=reply_markup, parse_mode='Markdown'
    )

@subscription_required
async def handle_consultation_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('awaiting_consultation_details'):
        details = update.message.text
        # Здесь можно добавить логику сохранения заявки, например, в базу данных или отправку на email
        # В данном случае, просто перенаправляем пользователя в канал
        await update.message.reply_text(
            f"Спасибо за вашу заявку на консультацию! Мы получили следующую информацию:\n\n\'{details}\'\n\n" 
            "Мы свяжемся с вами в ближайшее время для обсуждения деталей. "
            "А пока, присоединяйтесь к нашему каналу, чтобы не пропустить полезные материалы: "
            f"{CHANNEL_URL}"
        )
        context.user_data['awaiting_consultation_details'] = False
    else:
        await update.message.reply_text("Пожалуйста, используйте кнопку 'Записаться на консультацию' в главном меню.")

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

    # Обработчик для текстовых сообщений, когда ожидаются детали консультации
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_consultation_details))

    logger.info("Бот запущен в режиме polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
