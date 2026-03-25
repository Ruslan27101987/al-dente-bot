import csv
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from urllib.parse import quote

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
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

CSV_FILE = "bookings.csv"

NAME, PHONE, DATE, TIME, GUESTS, COMMENT = range(6)


def get_main_keyboard():
    keyboard = [
        ["🍝 Меню", "🎁 Акції"],
        ["📞 Контакти", "📅 Бронювання"],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def save_booking_to_csv(data: dict):
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "Ім'я",
                "Телефон",
                "Дата",
                "Час",
                "Кількість гостей",
                "Коментар",
            ])

        writer.writerow([
            data["name"],
            data["phone"],
            data["date"],
            data["time"],
            data["guests"],
            data["comment"],
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


async def notify_admin_about_booking(context: ContextTypes.DEFAULT_TYPE, data: dict):
    if not ADMIN_CHAT_ID:
        print("ADMIN_CHAT_ID не заданий")
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
        chat_id=ADMIN_CHAT_ID,
        text=text
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Я бот AI Dente 🇮🇹\nОберіть потрібний розділ нижче 👇",
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
    }

    try:
        save_booking_to_csv(booking_data)
    except Exception as e:
        await update.message.reply_text(
            f"Не вдалося зберегти бронювання у файл.\nПомилка: {e}",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END

    email_error = None
    try:
        send_booking_email(booking_data)
    except Exception as e:
        email_error = str(e)

    try:
        await notify_admin_about_booking(context, booking_data)
    except Exception as e:
        print(f"Помилка відправки адміну в Telegram: {e}")

    calendar_error = None
    try:
        calendar_url = build_google_calendar_link(
            name=booking_data["name"],
            phone=booking_data["phone"],
            date_str=booking_data["date"],
            time_str=booking_data["time"],
            guests=booking_data["guests"],
        )

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
    except Exception as e:
        calendar_error = str(e)
        reply_markup = get_main_keyboard()
        text = "Дякуємо! Ваше бронювання прийнято ✅"

    if email_error:
    print(f"Помилка email: {email_error}")

    if calendar_error:
    print(f"Помилка календаря: {calendar_error}")


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
    else:
        await update.message.reply_text(
            "Оберіть кнопку з меню нижче 👇",
            reply_markup=get_main_keyboard()
        )


def main():
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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("promo", promo_command))
    app.add_handler(CommandHandler("contact", contact_command))
    app.add_handler(booking_handler)

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & ~filters.Regex("^📅 Бронювання$"),
            handle_buttons
        )
    )

    print("Бот запущений")
    app.run_polling()


if __name__ == "__main__":
    main()




