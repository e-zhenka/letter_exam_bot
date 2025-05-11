import psycopg2
from config import Config
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        # Явное подключение с распарсенными параметрами
        self.conn = psycopg2.connect(
            host="db",  # Имя сервиса из docker-compose
            port="5432",
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        self.create_tables()

    def create_tables(self):
        with self.conn.cursor() as cur:
            cur.execute(open('init_db.sql', 'r').read())
            # Добавляем таблицу для словаря
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vocabulary (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    incorrect_word TEXT,
                    correct_word TEXT,
                    translation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()

    def add_user(self, user_id, username):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (user_id, username)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET username = EXCLUDED.username
            """, (user_id, username))
            self.conn.commit()

    def add_letter(self, user_id, text, feedback):
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO letters (user_id, text, feedback)
                    VALUES (%s, %s, %s)
                """, (user_id, text, feedback))
                self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def get_user_letters(self, user_id):
        with self.conn.cursor() as cur:
            cur.execute("SELECT text, feedback FROM letters WHERE user_id = %s", (user_id,))
            return cur.fetchall()

    def add_words_to_vocabulary(self, user_id: int, words: list[dict]):
        try:
            with self.conn.cursor() as cur:
                for word in words:
                    try:
                        cur.execute("""
                            INSERT INTO vocabulary (user_id, incorrect_word, correct_word, translation)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (user_id, incorrect_word) DO UPDATE
                            SET correct_word = EXCLUDED.correct_word,
                                translation = EXCLUDED.translation
                        """, (user_id, word['incorrect'], word['correct'], word['translation']))
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении слова {word}: {str(e)}")
                        continue  # Продолжаем с следующим словом
                self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Ошибка при добавлении слов в словарь: {str(e)}")
            raise e

    def get_user_vocabulary(self, user_id: int) -> list[dict]:
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT incorrect_word, correct_word, translation
                FROM vocabulary
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
            return [{'incorrect': row[0], 'correct': row[1], 'translation': row[2]} 
                    for row in cur.fetchall()]