import csv
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFont

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID_RAW = os.getenv("ADMIN_CHAT_ID")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

CSV_FILE = "bookings.csv"

NAME, PHONE, DATE, TIME, GUESTS, COMMENT, CLUB_NAME, CLUB_BIRTHDAY, CLUB_PHONE, CLUB_RECEIPT = range(10)


def get_admin_chat_id():
    try:
        return int(ADMIN_CHAT_ID_RAW) if ADMIN_CHAT_ID_RAW else None
    except ValueError:
        print(f"ADMIN_CHAT_ID має неправильний формат: {ADMIN_CHAT_ID_RAW}")
        return None


def get_main_keyboard():
    keyboard = [
        ["🍝 Меню", "🎁 Акції"],
        ["📞 Контакти", "📅 Бронювання"],
        ["🛵 Доставка", "💎 Клуб"],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def ensure_csv_exists():
    if not os.path.isfile(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "Ім'я",
                "Телефон",
                "Дата",
                "Час",
                "Кількість гостей",
                "Коментар",
                "Chat ID",
            ])


def save_booking_to_csv(data: dict):
    ensure_csv_exists()

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            data["name"],
            data["phone"],
            data["date"],
            data["time"],
            data["guests"],
            data["comment"],
            data["chat_id"],
        ])


def send_booking_email(data: dict):
    if not EMAIL_SENDER or not EMAIL_APP_PASSWORD or not EMAIL_RECEIVER:
        raise ValueError("Не задані EMAIL_SENDER / EMAIL_APP_PASSWORD / EMAIL_RECEIVER")

    subject = "Нова бронь Al Dente Club"
    body = (
        "Нова заявка на бронювання\n\n"
        f"Ім'я: {data['name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Дата: {data['date']}\n"
        f"Час: {data['time']}\n"
        f"Кількість гостей: {data['guests']}\n"
        f"Коментар: {data['comment']}\n"
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
        smtp.send_message(msg)


def build_google_calendar_link(name: str, phone: str, date_str: str, time_str: str, guests: str) -> str:
    start_dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
    end_dt = start_dt + timedelta(hours=2)

    dates = start_dt.strftime("%Y%m%dT%H%M%S") + "/" + end_dt.strftime("%Y%m%dT%H%M%S")

    title = "Бронювання столика в Al Dente"
    details = (
        f"Ім'я: {name}\n"
        f"Телефон: {phone}\n"
        f"Кількість гостей: {guests}\n"
        f"Ресторан: Al Dente, Яремче"
    )
    location = "Al Dente, Яремче"

    url = (
        "https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={quote(title)}"
        f"&dates={dates}"
        f"&details={quote(details)}"
        f"&location={quote(location)}"
    )
    return url


def generate_club_card(name: str, valid_until: str) -> str:
    width, height = 800, 500

    image = Image.new("RGB", (width, height), "#0f172a")
    draw = ImageDraw.Draw(image)

    font_title = ImageFont.load_default()
    font_text = ImageFont.load_default()

    draw.text((50, 40), "AL DENTE CLUB", fill="white", font=font_title)
    draw.text((50, 200), f"Ім'я: {name}", fill="white", font=font_text)
    draw.text((50, 260), f"Дійсна до: {valid_until}", fill="white", font=font_text)

    card_number = f"AD-{str(abs(hash(name)))[:6]}"
    draw.text((50, 320), f"Карта № {card_number}", fill="white", font=font_text)

    path = f"/tmp/card_{card_number}.png"
    image.save(path)

    return path


async def notify_admin_about_booking(context: ContextTypes.DEFAULT_TYPE, data: dict):
    admin_chat_id = get_admin_chat_id()

    if not admin_chat_id:
        print("ADMIN_CHAT_ID не заданий або неправильний")
        return

    text = (
        "📥 Нова бронь!\n\n"
        f"👤 Ім'я: {data['name']}\n"
        f"📞 Телефон: {data['phone']}\n"
        f"📅 Дата: {data['date']}\n"
        f"🕒 Час: {data['time']}\n"
        f"👥 Гостей: {data['guests']}\n"
        f"💬 Коментар: {data['comment']}"
    )

    await context.bot.send_message(
        chat_id=admin_chat_id,
        text=text
    )

    print("Повідомлення адміну успішно відправлено")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Я бот Al Dente 🇮🇹\nОберіть потрібний розділ нижче 👇",
        reply_markup=get_main_keyboard()
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🍝 Відкрити меню", url="https://al-dente.choiceqr.com/menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Наше меню 👇",
        reply_markup=reply_markup
    )


async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎁 Переглянути акції", url="https://al-dente.choiceqr.com/section:akciyi-ta-propoziciyi/dlya-tebe")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Наші акції та пропозиції 👇",
        reply_markup=reply_markup
    )


async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 Телефон: +38067 761 77 00\n"
        "📍 Al Dente, Яремче\n"
        "🗺 Карта: https://maps.app.goo.gl/nUebD1ywHSFDgShQ9?g_st=ic",
        reply_markup=get_main_keyboard()
    )


async def delivery_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛵 Перейти до доставки", url="https://al-dente.choiceqr.com/uk/delivery")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Замовити доставку можна тут 👇",
        reply_markup=reply_markup
    )


async def club_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💎 Стати членом клубу", callback_data="club_join")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "💎 Al Dente Club\n\n"
        "Станьте членом клубу та отримуйте -30% на кухню 🍝\n\n"
        "Умови участі:\n"
        "• Вартість: 499 грн\n"
        "• Знижка: -30% на кухню\n"
        "• Не діє на акції та спецпропозиції\n"
        "• Термін дії: 2 місяці\n\n"
        "Після оплати ви отримаєте електронну клубну карту 💎\n\n"
        "Натисніть кнопку нижче, щоб продовжити 👇",
        reply_markup=reply_markup
    )


async def club_join_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["club_chat_id"] = update.effective_chat.id

    await update.message.reply_text(
        "💎 Вступ до Al Dente Club\n\n"
        "Напишіть, будь ласка, ваше ім'я:",
        reply_markup=ReplyKeyboardRemove()
    )
    return CLUB_NAME


async def club_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["club_chat_id"] = query.message.chat_id

    await query.message.reply_text(
        "💎 Вступ до Al Dente Club\n\n"
        "Напишіть, будь ласка, ваше ім'я:",
        reply_markup=ReplyKeyboardRemove()
    )
    return CLUB_NAME


async def club_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["club_name"] = update.message.text.strip()
    await update.message.reply_text("Вкажіть дату народження, наприклад: 25.03.1995")
    return CLUB_BIRTHDAY


async def club_get_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["club_birthday"] = update.message.text.strip()
    await update.message.reply_text("Вкажіть ваш телефон:")
    return CLUB_PHONE


async def club_get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["club_phone"] = update.message.text.strip()

    await update.message.reply_text(
        "💎 Ваша заявка прийнята!\n\n"
        "Для активації клубу необхідно оплатити 499 грн 👇\n\n"
        "💳 Реквізити для оплати:\n"
        "Monobank: 5408 8100 4237 2606\n"
        "Отримувач: Al Dente\n\n"
        "Після оплати надішліть, будь ласка, скрін або фото квитанції 📸",
        reply_markup=ReplyKeyboardRemove()
    )
    return CLUB_RECEIPT


async def club_get_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(
            "Будь ласка, надішліть саме фото або скрін квитанції 📸"
        )
        return CLUB_RECEIPT

    photo = update.message.photo[-1].file_id

    guest_name = context.user_data.get("club_name", "")
    guest_birthday = context.user_data.get("club_birthday", "")
    guest_phone = context.user_data.get("club_phone", "")
    guest_chat_id = context.user_data.get("club_chat_id", "")

    caption = (
        "💎 Нова оплата клубу\n\n"
        f"👤 Ім'я: {guest_name}\n"
        f"🎂 Дата народження: {guest_birthday}\n"
        f"📞 Телефон: {guest_phone}\n"
        f"🆔 Chat ID: {guest_chat_id}"
    )

    admin_chat_id = get_admin_chat_id()
    if admin_chat_id:
        try:
            keyboard = [
                [InlineKeyboardButton("✅ Підтвердити оплату", callback_data=f"club_paid:{guest_chat_id}:{guest_name}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_photo(
                chat_id=admin_chat_id,
                photo=photo,
                caption=caption,
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Помилка відправки квитанції адміну: {e}")

    await update.message.reply_text(
        "Дякуємо! Квитанцію отримано ✅\n\n"
        "Після перевірки оплати ми активуємо вашу клубну карту 💎",
        reply_markup=get_main_keyboard()
    )

    context.user_data.pop("club_name", None)
    context.user_data.pop("club_birthday", None)
    context.user_data.pop("club_phone", None)
    context.user_data.pop("club_chat_id", None)

    return ConversationHandler.END


async def club_paid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split(":", 2)

    if len(parts) < 3:
        await query.message.reply_text("Помилка підтвердження оплати.")
        return

    guest_chat_id = parts[1]
    guest_name = parts[2]
    valid_until = (datetime.now() + timedelta(days=60)).strftime("%d.%m.%Y")

    try:
        card_path = generate_club_card(guest_name, valid_until)

        with open(card_path, "rb") as card_file:
            await context.bot.send_photo(
                chat_id=int(guest_chat_id),
                photo=card_file,
                caption=(
                    "💎 Ваша клубна карта готова!\n\n"
                    f"Ім'я: {guest_name}\n"
                    f"Діє до: {valid_until}\n\n"
                    "Покажіть цю карту при візиті 💎"
                )
            )

        await query.message.reply_text("✅ Карта створена та надіслана гостю.")
    except Exception as e:
        await query.message.reply_text(f"Помилка надсилання гостю: {e}")


async def book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Бронювання столика 🍽️\n\nНапишіть, будь ласка, ваше ім'я:",
        reply_markup=ReplyKeyboardRemove()
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Вкажіть ваш телефон:")
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text.strip()
    await update.message.reply_text("Вкажіть дату бронювання, наприклад: 25.03.2026")
    return DATE


async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["date"] = update.message.text.strip()
    await update.message.reply_text("Вкажіть час, наприклад: 19:00")
    return TIME


async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["time"] = update.message.text.strip()
    await update.message.reply_text("Скільки буде гостей?")
    return GUESTS


async def get_guests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["guests"] = update.message.text.strip()
    await update.message.reply_text(
        "Напишіть коментар до бронювання або надішліть '-' якщо без коментаря:"
    )
    return COMMENT


async def get_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment = update.message.text.strip()
    if comment == "-":
        comment = "Без коментаря"

    context.user_data["comment"] = comment

    booking_data = {
        "name": context.user_data["name"],
        "phone": context.user_data["phone"],
        "date": context.user_data["date"],
        "time": context.user_data["time"],
        "guests": context.user_data["guests"],
        "comment": context.user_data["comment"],
        "chat_id": update.effective_chat.id,
    }

    print(f"Нова бронь: {booking_data}")

    try:
        save_booking_to_csv(booking_data)
        print("Бронювання збережено в CSV")
    except Exception as e:
        print(f"Помилка збереження CSV: {e}")
        await update.message.reply_text(
            f"Не вдалося зберегти бронювання у файл.\nПомилка: {e}",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END

    try:
        send_booking_email(booking_data)
        print("Email успішно відправлено")
    except Exception as e:
        print(f"Помилка email: {e}")

    try:
        await notify_admin_about_booking(context, booking_data)
    except Exception as e:
        print(f"Помилка відправки адміну: {e}")

    calendar_url = None
    try:
        calendar_url = build_google_calendar_link(
            name=booking_data["name"],
            phone=booking_data["phone"],
            date_str=booking_data["date"],
            time_str=booking_data["time"],
            guests=booking_data["guests"],
        )
        print("Посилання на календар створено")
    except Exception as e:
        print(f"Помилка календаря: {e}")

    if calendar_url:
        keyboard = [
            [InlineKeyboardButton("📅 Додати в Google Календар", url=calendar_url)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "Дякуємо! Ваше бронювання прийнято ✅\n\n"
            f"📅 {booking_data['date']}\n"
            f"🕒 {booking_data['time']}\n"
            f"👥 Гостей: {booking_data['guests']}\n\n"
            "Додайте бронювання в календар 👇"
        )
    else:
        reply_markup = get_main_keyboard()
        text = "Дякуємо! Ваше бронювання прийнято ✅"

    await update.message.reply_text(
        text,
        reply_markup=reply_markup
    )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Бронювання скасовано.",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🍝 Меню":
        await menu_command(update, context)
    elif text == "🎁 Акції":
        await promo_command(update, context)
    elif text == "📞 Контакти":
        await contact_command(update, context)
    elif text == "📅 Бронювання":
        return await book_start(update, context)
    elif text == "🛵 Доставка":
        await delivery_command(update, context)
    elif text == "💎 Клуб":
        await club_command(update, context)
    else:
        await update.message.reply_text(
            "Оберіть кнопку з меню нижче 👇",
            reply_markup=get_main_keyboard()
        )


def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN не заданий")

    ensure_csv_exists()

    app = ApplicationBuilder().token(TOKEN).build()

    booking_handler = ConversationHandler(
        entry_points=[
            CommandHandler("book", book_start),
            MessageHandler(filters.Regex("^📅 Бронювання$"), book_start),
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)],
            GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_guests)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_comment)],
        },
        fallbacks=[CommandHandler("cancel", cancel_booking)],
    )

    club_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & filters.Regex("Стати членом клубу"), club_join_start),
            CallbackQueryHandler(club_join_callback, pattern="^club_join$"),
        ],
        states={
            CLUB_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, club_get_name)],
            CLUB_BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, club_get_birthday)],
            CLUB_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, club_get_phone)],
            CLUB_RECEIPT: [MessageHandler(filters.PHOTO, club_get_receipt)],
        },
        fallbacks=[CommandHandler("cancel", cancel_booking)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("promo", promo_command))
    app.add_handler(CommandHandler("contact", contact_command))
    app.add_handler(CommandHandler("delivery", delivery_command))
    app.add_handler(CommandHandler("club", club_command))
    app.add_handler(booking_handler)
    app.add_handler(club_handler)
    app.add_handler(CallbackQueryHandler(club_paid_callback, pattern=r"^club_paid:"))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & ~filters.Regex("^📅 Бронювання$"),
            handle_buttons
        )
    )

    print("Бот запущений")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()