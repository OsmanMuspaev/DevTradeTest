CREATE TABLE IF NOT EXISTS chats (
  chat_id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL DEFAULT 1,
  chat_name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chats_user_updated
  ON chats (user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS messages (
  message_id BIGSERIAL PRIMARY KEY,
  chat_id BIGINT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_chat_created
  ON messages (chat_id, created_at);


CREATE OR REPLACE FUNCTION touch_chat_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE chats
    SET updated_at = NOW()
    WHERE chat_id = NEW.chat_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS messages_touch_chat ON messages;
CREATE TRIGGER messages_touch_chat
AFTER INSERT ON messages
FOR EACH ROW
EXECUTE FUNCTION touch_chat_updated_at();
