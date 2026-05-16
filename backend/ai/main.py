from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from psycopg.rows import dict_row

from db import close_pool, open_pool, pool
from models import ChatCreateBody, ChatRenameBody, MessageCreateBody, StrategySubmitBody
from llm import get_llm_provider, load_library_context, safe_str, logger


LIBRARY_CONTEXT = None


def get_user_id(request: Request) -> int:
    """Извлекает user_id из заголовка X-User-ID (проксируется Gateway)."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-ID header required")
    try:
        return int(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid X-User-ID")


@asynccontextmanager
async def lifespan(_: FastAPI):
    global LIBRARY_CONTEXT
    open_pool()
    LIBRARY_CONTEXT = load_library_context()
    logger.info(f"LLM Provider: {get_llm_provider().__class__.__name__}")
    try:
        yield
    finally:
        close_pool()


app = FastAPI(title="DevTrade AI Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    provider = get_llm_provider()
    return {
        "status": "ok",
        "llm_provider": provider.__class__.__name__ if provider else None
    }


def _get_chat(chat_id: int, user_id: int) -> dict | None:
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT chat_id, chat_name, created_at, updated_at FROM chats WHERE chat_id = %s AND user_id = %s",
                (chat_id, user_id),
            )
            return cur.fetchone()


def _get_history(chat_id: int) -> list:
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT role, content FROM messages WHERE chat_id = %s ORDER BY message_id ASC",
                (chat_id,),
            )
            return cur.fetchall()


@app.get("/chats")
def list_chats(request: Request):
    user_id = get_user_id(request)
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT chat_id, chat_name, created_at, updated_at
                FROM chats WHERE user_id = %s
                ORDER BY updated_at DESC LIMIT 200
                """,
                (user_id,),
            )
            return {"data": cur.fetchall()}


@app.post("/chats")
def create_chat(body: ChatCreateBody, request: Request):
    user_id = get_user_id(request)
    name = (body.name or "").strip() or "Новый чат"
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "INSERT INTO chats (user_id, chat_name) VALUES (%s, %s) RETURNING *",
                (user_id, name),
            )
            chat = cur.fetchone()
            conn.commit()
    return chat


@app.post("/chats/{chat_id}/rename")
def rename_chat(chat_id: int, body: ChatRenameBody, request: Request):
    user_id = get_user_id(request)
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "UPDATE chats SET chat_name = %s, updated_at = NOW() WHERE chat_id = %s AND user_id = %s RETURNING *",
                (body.name.strip(), chat_id, user_id),
            )
            chat = cur.fetchone()
            conn.commit()
    if not chat:
        raise HTTPException(404, "chat not found")
    return chat


@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: int, request: Request):
    user_id = get_user_id(request)
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chats WHERE chat_id = %s AND user_id = %s", (chat_id, user_id))
            deleted = cur.rowcount
            conn.commit()
    if not deleted:
        raise HTTPException(404, "chat not found")
    return {"status": "deleted"}


@app.get("/chats/{chat_id}/messages")
def list_messages(chat_id: int, request: Request):
    user_id = get_user_id(request)
    if not _get_chat(chat_id, user_id):
        raise HTTPException(404, "chat not found")
    
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT message_id, chat_id, role, content, created_at FROM messages WHERE chat_id = %s ORDER BY message_id ASC LIMIT 2000",
                (chat_id,),
            )
            return {"data": cur.fetchall()}


@app.post("/chats/{chat_id}/messages")
def create_message(chat_id: int, body: MessageCreateBody, request: Request):
    user_id = get_user_id(request)
    chat = _get_chat(chat_id, user_id)
    if not chat:
        raise HTTPException(404, "chat not found")
    
    user_text = body.content.strip()
    if not user_text:
        raise HTTPException(400, "content is empty")
    
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "INSERT INTO messages (chat_id, role, content) VALUES (%s, 'user', %s) RETURNING *",
                (chat_id, user_text),
            )
            user_msg = cur.fetchone()
            conn.commit()
    
    history = _get_history(chat_id)
    
    provider = get_llm_provider()
    if not provider:
        raise HTTPException(503, "LLM provider not available")
    
    system_prompt = provider.get_system_prompt(LIBRARY_CONTEXT or "")
    messages_for_llm = provider.prepare_messages(history, system_prompt)
    
    assistant_text = provider.generate(messages_for_llm)
    
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "INSERT INTO messages (chat_id, role, content) VALUES (%s, 'assistant', %s) RETURNING *",
                (chat_id, assistant_text),
            )
            assistant_msg = cur.fetchone()
            conn.commit()
    
    # Авто-название через LLM
    if chat.get("chat_name") in (None, "", "Новый чат"):
        title = _generate_title_via_llm(user_text, provider)
        if title:
            try:
                with pool.connection() as conn:
                    with conn.cursor(row_factory=dict_row) as cur:
                        cur.execute(
                            "UPDATE chats SET chat_name = %s, updated_at = NOW() WHERE chat_id = %s AND user_id = %s RETURNING *",
                            (title, chat_id, user_id),
                        )
                        conn.commit()
            except Exception as e:
                logger.warning(f"Auto-rename failed: {e}")
    
    return {"user": user_msg, "assistant": assistant_msg}


def _generate_title_via_llm(first_message: str, provider) -> str | None:
    """Генерирует короткое название чата через LLM."""
    if not first_message or not first_message.strip():
        return None
    
    prompt = f"""Создай КОРОТКОЕ название (2-5 слов) для чата по первому сообщению пользователя.
Отвечай ТОЛЬКО названием, без кавычек, пояснений и лишнего текста.

Сообщение: {first_message[:200]}

Название:"""
    
    try:
        title = provider.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=20,
        )
        title = title.strip().strip('"').strip("'")
        return title[:50] if title else None
    except Exception as e:
        logger.warning(f"Title generation failed: {e}")
        # Fallback: первые 3 слова
        words = first_message.strip().split()
        return " ".join(words[:3])[:40] if words else None


@app.post("/strategies/submit")
def submit_strategy(body: StrategySubmitBody, request: Request):
    user_id = get_user_id(request)
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO strategy_submissions (user_id, title, language, code)
                VALUES (%s, %s, %s, %s)
                RETURNING submission_id, title, language, created_at
                """,
                (user_id, body.title, body.language, body.code),
            )
            row = cur.fetchone()
            conn.commit()
    return row


@app.get("/provider/{name}")
def switch_provider(name: str):
    global _default_provider
    from llm import LLMFactory
    _default_provider = LLMFactory.get_provider(name)
    if _default_provider:
        return {"provider": name, "status": "switched"}
    return {"error": f"Provider {name} not available"}, 400