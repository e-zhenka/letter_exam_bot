CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(32),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS letters (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    text TEXT NOT NULL,
    feedback TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vocabulary (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    incorrect_word TEXT,
    correct_word TEXT,
    translation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, incorrect_word)
);

-- Добавляем уникальный индекс, если его еще нет
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'vocabulary_user_word_unique'
    ) THEN
        ALTER TABLE vocabulary ADD CONSTRAINT vocabulary_user_word_unique 
        UNIQUE (user_id, incorrect_word);
    END IF;
END $$;