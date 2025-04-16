from telegram import Update
from telegram.ext import ContextTypes
import database


async def admin_generate_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != database.ADMIN_ID:
        return

    code, error = database.create_referral(user.id, is_admin=True)
    if error:
        await update.message.reply_text(f"❌ {error}")
        return

    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start=ref_{code}"

    await update.message.reply_text(
        f"🔗 لینک دعوت ادمین:\n{referral_link}\n"
        "⏳ اعتبار: 1 سال\n"
        "👥 تعداد استفاده نامحدود"
    )


async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != database.ADMIN_ID:
        return

    users = database.get_all_users()

    response = "👥 لیست کاربران:\n\n"
    for user in users:
        response += f"🆔 {user[0]} - 📞 {user[2]}\n"

    await update.message.reply_text(response)