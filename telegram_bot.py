from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import Config
from database import Database
from llm_client import analyze_writing
from trainer import VocabularyTrainer
import logging
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

async def start(update: Update, context):
    user = update.effective_user
    db.add_user(user.id, user.username)
    await update.message.reply_text(
        "Привет! Отправь мне свое письмо на английском, и я помогу тебе его улучшить!"
    )

async def show_vocabulary(update: Update, context):
    user = update.effective_user
    words = db.get_user_vocabulary(user.id)
    
    if not words:
        await update.message.reply_text("У вас пока нет слов в словаре.")
        return
    
    message = "📚 Ваш словарь:\n\n"
    for word in words:
        message += f"❌ {word['incorrect']} → ✅ {word['correct']}\n"
        message += f"📝 {word['translation']}\n\n"
    
    # Добавляем кнопку для начала тренировки
    keyboard = [
        [InlineKeyboardButton("🎯 Начать тренировку", callback_data="start_training")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup)

async def handle_message(update: Update, context):
    user = update.effective_user
    text = update.message.text
    
    try:
        # Гарантированно добавляем/обновляем пользователя
        db.add_user(user.id, user.username or "Unknown")
        
        # Отправляем сообщение о начале проверки
        status_message = await update.message.reply_text("⏳ Начинаю проверку письма...")
        
        # Получаем результаты проверки
        feedback_results = analyze_writing(text)
        
        # Обновляем статусное сообщение
        await status_message.edit_text("✅ Проверка завершена!")
        
        # Форматируем и отправляем результаты по каждому критерию
        criteria_info = {
            "K1": "Решение коммуникативной задачи",
            "K2": "Организация текста",
            "K3": "Лексико-грамматическое оформление",
            "K4": "Орфография и пунктуация"
        }
        
        total_score = 0
        max_score = 0
        
        for criterion, title in criteria_info.items():
            result = feedback_results[criterion]
            
            # Подсчет общего балла
            score = result['score']
            total_score += score
            max_score += 3 if criterion in ['K1', 'K3'] else 2
            
            # Форматируем сообщение
            message = (
                f"📌 {title} (K{criterion[-1]})\n\n"
                f"Балл: {score}/{3 if criterion in ['K1', 'K3'] else 2}\n\n"
                f"Обоснование:\n{result['justification']}\n"
            )
            
            if result['recommendations']:
                message += f"\nРекомендации:\n{result['recommendations']}"
            
            await update.message.reply_text(message)
            await asyncio.sleep(1)  # Небольшая пауза между сообщениями
        
        # Отправляем итоговый результат
        final_message = (
            f"📊 Итоговый результат:\n"
            f"Общий балл: {total_score}/{max_score}\n"
            f"Процент выполнения: {round(total_score/max_score * 100)}%"
        )
        await update.message.reply_text(final_message)
        
        # Сохраняем результаты в базу данных
        db.add_letter(user.id, text, str(feedback_results))
        
        # После проверки K3 сохраняем слова в словарь
        if 'K3' in feedback_results and 'mistaken_words' in feedback_results['K3']:
            try:
                db.add_words_to_vocabulary(user.id, feedback_results['K3']['mistaken_words'])
            except Exception as e:
                logger.error(f"Ошибка при сохранении слов в словарь: {str(e)}")
                # Не прерываем выполнение, продолжаем показывать результаты
        
        # Добавляем кнопку для просмотра словаря
        keyboard = [
            [InlineKeyboardButton("📚 Показать словарь", callback_data="show_vocabulary")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Хотите посмотреть свой словарь?", reply_markup=reply_markup)
        
    except Exception as e:
        db.conn.rollback()
        logger.error(f"Ошибка в handle_message: {str(e)}")
        await update.message.reply_text("⚠️ Произошла ошибка при проверке письма. Попробуйте отправить текст еще раз.")

async def button_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == "show_vocabulary":
        user = query.from_user
        words = db.get_user_vocabulary(user.id)
        
        if not words:
            await query.message.reply_text("У вас пока нет слов в словаре.")
            return
        
        message = "📚 Ваш словарь:\n\n"
        for word in words:
            message += f"❌ {word['incorrect']} → ✅ {word['correct']}\n"
            message += f"📝 {word['translation']}\n\n"
        
        await query.message.reply_text(message)

def main():
    application = Application.builder().token(Config.TELEGRAM_TOKEN).build()
    trainer = VocabularyTrainer(db)
    
    application.add_handler(trainer.get_handler()) 
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("vocabulary", show_vocabulary))
     # Должен быть ДО MessageHandler!
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.run_polling()

if __name__ == "__main__":
    main()