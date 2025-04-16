import os
from telegram.ext import CallbackQueryHandler

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters
)

import database

from handlers.admin_handlers import admin_generate_referral
from handlers.file_handlers import (
    handle_files,
    handle_reply,  # اضافه شده
    handle_callback
)
from handlers.user_handlers import (
    FULL_NAME,
    PHONE,
    cancel_registration,
    get_full_name,
    get_phone,
    handle_active_orders,
    handle_archive,
    show_archive,
    start, generate_user_referral, handle_gift_request
)
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG  # تغییر به DEBUG برای نمایش تمام لاگ‌ها
)


db_path = "print3d.db"  # اگر مسیرش فرق داره، اصلاح کن

if os.path.exists(db_path):
    os.remove(db_path)
    print("📦 دیتابیس حذف شد.")
else:
    print("ℹ️ دیتابیس وجود نداشت.")



TOKEN = "7943645778:AAEXYzDKUc2D7mWaTcLrSkH4AjlJvVq7PaU"




def main():
    database.create_tables()

    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
            PHONE: [MessageHandler(filters.CONTACT | filters.TEXT & ~filters.COMMAND, get_phone)]
        },
        fallbacks=[CommandHandler("cancel", cancel_registration)],
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.Document.ALL, handle_files))
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, handle_reply))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.Regex("📂 آرشیو"), show_archive))
    app.add_handler(MessageHandler(filters.Regex("^(🕒 هفته اخیر|📅 ماه اخیر|📂 کل آرشیو)$"),handle_archive))
    app.add_handler(MessageHandler(
        filters.Regex(r"^🔄 درحال انجام(\(\d+\))?$"),  # قبول هر دو فرمت با و بدون عدد
        handle_active_orders
    ))
    # تغییر قسمت اضافه کردن هندلر
    app.add_handler(MessageHandler(filters.Regex("🔗 تولید لینک دعوت نامحدود"), admin_generate_referral))
    app.add_handler(CallbackQueryHandler(handle_callback))  # اضافه کردن هندلر
    # به لیست handlers اضافه کنید:

    # در بخش اضافه کردن هندلرها:
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^🎁 دریافت هدیه$"),  # مطمئن شوید متن دکمه دقیقاً همین باشد
            generate_user_referral
        )
    )


    app.run_polling()


#
if __name__ == "__main__":
    main()