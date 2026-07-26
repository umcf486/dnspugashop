import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = '8631736538:AAFkNgUY5QM4Gr8eqQsviUk6NxkLcZvT5yc'

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('سلام! ربات فعال است ✅')

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    print('🚀 ربات در حال اجراست...')
    app.run_polling()

if __name__ == '__main__':
    main()
