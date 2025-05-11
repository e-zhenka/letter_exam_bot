from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import logging
import random
from database import Database

logger = logging.getLogger(__name__)

# Состояния для тренажера
TRAINING = 1

# Словарь для хранения текущего состояния тренажера для каждого пользователя
user_training_state = {}

class VocabularyTrainer:
    def __init__(self, db: Database):
        self.db = db

    async def start_training(self, update: Update, context):
        user = update.effective_user
        words = self.db.get_user_vocabulary(user.id)
        
        if not words:
            await update.message.reply_text("У вас пока нет слов в словаре для тренировки.")
            return ConversationHandler.END
        
        # Перемешиваем слова
        random.shuffle(words)
        
        # Сохраняем состояние тренажера для пользователя
        user_training_state[user.id] = {
            'words': words,
            'current_index': 0,
            'correct_answers': 0,
            'total_words': len(words)
        }
        
        # Отправляем первое слово
        await self.send_next_word(update, context)
        return TRAINING

    async def send_next_word(self, update: Update, context):
        user = update.effective_user
        state = user_training_state[user.id]
        
        if state['current_index'] >= state['total_words']:
            # Тренировка завершена
            score = state['correct_answers']
            total = state['total_words']
            await update.message.reply_text(
                f"🎉 Тренировка завершена!\n"
                f"Правильных ответов: {score} из {total}\n"
                f"Процент успешности: {round(score/total * 100)}%",
                reply_markup=ReplyKeyboardRemove()
            )
            del user_training_state[user.id]
            return ConversationHandler.END
        
        current_word = state['words'][state['current_index']]
        await update.message.reply_text(
            f"📝 Введите перевод слова:\n"
            f"«{current_word['translation']}»"
        )

    async def check_answer(self, update: Update, context):
        user = update.effective_user
        state = user_training_state[user.id]
        current_word = state['words'][state['current_index']]
        user_answer = update.message.text.strip().lower()
        correct_answer = current_word['correct'].lower()
        
        if user_answer == correct_answer:
            state['correct_answers'] += 1
            await update.message.reply_text(
                f"✅ Правильно!\n"
                f"«{current_word['translation']}» → «{correct_answer}»"
            )
        else:
            await update.message.reply_text(
                f"❌ Неправильно!\n"
                f"Правильный ответ: «{correct_answer}»\n"
                f"Ваш ответ: «{user_answer}»"
            )
        
        state['current_index'] += 1
        await self.send_next_word(update, context)
        return TRAINING

    async def cancel_training(self, update: Update, context):
        user = update.effective_user
        if user.id in user_training_state:
            del user_training_state[user.id]
        await update.message.reply_text(
            "Тренировка отменена.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    def get_handler(self):
        """Возвращает обработчик для тренажера"""
        return ConversationHandler(
            entry_points=[
                CommandHandler("train", self.start_training),
                CallbackQueryHandler(self.start_training, pattern="^start_training$")
            ],
            states={
                TRAINING: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.check_answer)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel_training)]
        )
