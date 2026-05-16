import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { 
  createChat, 
  renameChat, 
  deleteChat as deleteChatApi, 
  listChats, 
  listMessages, 
  sendMessage
} from '../services/ai.js'
import './AiChat.css'

function formatTs(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return String(ts)
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

export default function AiChat() {
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState(null)
  const [chats, setChats] = useState([])
  const [activeChatId, setActiveChatId] = useState(null)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [renamingChatId, setRenamingChatId] = useState(null)
  const [renamingName, setRenamingName] = useState('')
  const listRef = useRef(null)

  const activeChat = useMemo(
    () => chats.find((c) => String(c.chat_id) === String(activeChatId)) ?? null,
    [activeChatId, chats],
  )

  const loadMessages = useCallback(async (chatId) => {
    try {
      const res = await listMessages(chatId)
      setMessages(res.messages)
      requestAnimationFrame(() => {
        const el = listRef.current
        if (el) el.scrollTop = el.scrollHeight
      })
    } catch (err) {
      setError(err?.message || String(err))
    }
  }, [])

  const refreshChats = useCallback(async ({ keepActive = true } = {}) => {
    try {
      const data = await listChats()
      setChats(data)
      if (!keepActive) return
      if (!data.length) {
        setActiveChatId(null)
        return
      }
      if (!activeChatId) {
        setActiveChatId(data[0].chat_id)
        await loadMessages(data[0].chat_id)
        return
      }
      const exists = data.some((c) => String(c.chat_id) === String(activeChatId))
      if (!exists) {
        setActiveChatId(data[0].chat_id)
        await loadMessages(data[0].chat_id)
      }
    } catch (err) {
      setError(err?.message || String(err))
    }
  }, [activeChatId, loadMessages])

  // Загрузка чатов при монтировании
  useEffect(() => {
    let mounted = true

    ;(async () => {
      try {
        const data = await listChats()
        if (!mounted) return
        setChats(data)
        if (!data.length) {
          const created = await createChat()
          if (!mounted) return
          setChats([created])
          setActiveChatId(created.chat_id)
          setMessages([])
        } else {
          setActiveChatId((prev) => prev ?? data[0].chat_id)
          await loadMessages(data[0].chat_id)
        }
        setStatus('ready')
      } catch (err) {
        if (!mounted) return
        setStatus('error')
        setError(err?.message || String(err))
      }
    })()

    return () => {
      mounted = false
    }
  }, [loadMessages])

  // Загрузка сообщений при смене чата
  useEffect(() => {
    if (!activeChatId) return
    
    let mounted = true

    ;(async () => {
      try {
        await loadMessages(activeChatId)
        if (!mounted) return
        setStatus('ready')
      } catch (err) {
        if (!mounted) return
        setStatus('error')
        setError(err?.message || String(err))
      }
    })()

    return () => {
      mounted = false
    }
  }, [activeChatId, loadMessages])

  // Создание нового чата
  const handleNewChat = useCallback(async () => {
    setSending(true)
    setError(null)
    try {
      const created = await createChat()
      await refreshChats({ keepActive: false })
      setActiveChatId(created.chat_id)
      setMessages([])
    } catch (err) {
      setError(err?.message || String(err))
    } finally {
      setSending(false)
    }
  }, [refreshChats])

  // Удаление чата
  const handleDeleteChat = useCallback(async (chatId, e) => {
    e.stopPropagation()
    
    if (!confirm('Вы уверены, что хотите удалить этот чат? Все сообщения будут потеряны.')) {
      return
    }
    
    try {
      await deleteChatApi(chatId)
      
      const updatedChats = chats.filter(c => c.chat_id !== chatId)
      setChats(updatedChats)
      
      if (activeChatId === chatId) {
        if (updatedChats.length > 0) {
          setActiveChatId(updatedChats[0].chat_id)
          await loadMessages(updatedChats[0].chat_id)
        } else {
          setActiveChatId(null)
          setMessages([])
          // Создаём новый чат если не осталось
          const created = await createChat()
          setChats([created])
          setActiveChatId(created.chat_id)
        }
      }
    } catch (err) {
      console.error('Failed to delete chat:', err)
      alert('Не удалось удалить чат: ' + err.message)
    }
  }, [chats, activeChatId, loadMessages])

  // Переименование чата
  const handleRenameStart = useCallback((chatId, currentName, e) => {
    e.stopPropagation()
    setRenamingChatId(chatId)
    setRenamingName(currentName || '')
  }, [])

  const handleRenameSave = useCallback(async (chatId) => {
    const newName = renamingName.trim()
    if (!newName || newName === chats.find(c => c.chat_id === chatId)?.chat_name) {
      setRenamingChatId(null)
      return
    }
    
    try {
      await renameChat(chatId, { name: newName })
      setChats(prev => prev.map(c => 
        c.chat_id === chatId ? { ...c, chat_name: newName } : c
      ))
    } catch (err) {
      console.error('Failed to rename chat:', err)
      alert('Не удалось переименовать чат: ' + err.message)
    } finally {
      setRenamingChatId(null)
      setRenamingName('')
    }
  }, [renamingName, chats])

  const handleRenameCancel = useCallback(() => {
    setRenamingChatId(null)
    setRenamingName('')
  }, [])

  const onSend = useCallback(async () => {
    const text = draft.trim()
    if (!text || !activeChatId) return
    if (sending) return

    setDraft('')
    setSending(true)
    setError(null)

    const tempId = `temp-${Date.now()}`

    setMessages((m) => [
      ...m,
      {
        message_id: tempId,
        chat_id: activeChatId,
        role: 'assistant',
        content: '🤔 Думаю...',
        created_at: new Date().toISOString(),
        _thinking: true,
      },
    ])
    
    requestAnimationFrame(() => {
      const el = listRef.current
      if (el) el.scrollTop = el.scrollHeight
    })

    try {
      const res = await sendMessage(activeChatId, { content: text })
      
      setMessages((m) => {
        const withoutThinking = m.filter((x) => !x._thinking)
        return [...withoutThinking, res.user, res.assistant]
      })
      
      await refreshChats()
    } catch (err) {
      setMessages((m) => m.filter((x) => !x._thinking))
      setError(err?.message || String(err))
    } finally {
      setSending(false)
      requestAnimationFrame(() => {
        const el = listRef.current
        if (el) el.scrollTop = el.scrollHeight
      })
    }
  }, [activeChatId, draft, refreshChats, sending])

  const onComposerKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void onSend()
    }
  }

  const handleSelectChat = useCallback(async (chatId) => {
    setActiveChatId(chatId)
    await loadMessages(chatId)
  }, [loadMessages])

  return (
    <div className="ai">
      <div className="ai__top">
        <div>
          <div className="ai__title">AI</div>
          <div className="ai__subtitle mono">
            {activeChat ? activeChat.chat_name : 'чат'}
          </div>
        </div>

        <button
          type="button"
          className="ai__btn"
          onClick={() => void handleNewChat()}
          disabled={sending}
          title="Новый чат"
        >
          +
        </button>
      </div>

      {/* Горизонтальные чаты */}
      <div className="ai-tabs" role="tablist" aria-label="Чаты">
        {chats.map((c) => (
          <div
            key={c.chat_id}
            className={`ai-tab-wrapper${String(c.chat_id) === String(activeChatId) ? ' ai-tab-wrapper--active' : ''}`}
          >
            {renamingChatId === c.chat_id ? (
              <input
                className="ai-tab__rename-input"
                value={renamingName}
                onChange={(e) => setRenamingName(e.target.value)}
                onBlur={() => handleRenameSave(c.chat_id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleRenameSave(c.chat_id)
                  if (e.key === 'Escape') handleRenameCancel()
                }}
                autoFocus
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <button
                type="button"
                className={`ai-tab${String(c.chat_id) === String(activeChatId) ? ' ai-tab--active' : ''}`}
                onClick={() => handleSelectChat(c.chat_id)}
                role="tab"
                aria-selected={String(c.chat_id) === String(activeChatId)}
                title={c.chat_name}
              >
                <span className="ai-tab__name">{c.chat_name}</span>
                <div className="ai-tab__actions">
                  <span
                    className="ai-tab__rename"
                    onClick={(e) => handleRenameStart(c.chat_id, c.chat_name, e)}
                    title="Переименовать"
                  >
                    ✎
                  </span>
                  <span
                    className="ai-tab__delete"
                    onClick={(e) => handleDeleteChat(c.chat_id, e)}
                    title="Удалить чат"
                  >
                    🗑
                  </span>
                </div>
              </button>
            )}
          </div>
        ))}
      </div>

      <div ref={listRef} className="ai-log">
        {status === 'loading' ? <div className="ai-empty muted">Загружаю…</div> : null}
        {status === 'error' && !messages.length ? (
          <div className="ai-empty muted">Ошибка: {error}</div>
        ) : null}
        {status !== 'loading' && !messages.length ? (
          <div className="ai-empty muted">Напиши сообщение — я сохраню историю справа.</div>
        ) : null}

        {messages.map((m) => (
          <div key={m.message_id} className={`ai-msg ai-msg--${m.role}`}>
            <div className="ai-msg__meta mono">
              {m.role}
              {m.created_at ? <span className="ai-dot">·</span> : null}
              {m.created_at ? formatTs(m.created_at) : null}
            </div>
            <div className="ai-msg__content">{m.content}</div>
          </div>
        ))}
      </div>

      <div className="ai-compose">
        <textarea
          className="ai-compose__input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onComposerKeyDown}
          placeholder="Спроси про стратегию, ошибки в коде, архитектуру…"
          spellCheck={false}
        />
        <button
          type="button"
          className="ai-compose__send"
          onClick={() => void onSend()}
          disabled={!draft.trim() || sending || !activeChatId}
          title="Enter — отправить, Shift+Enter — новая строка"
        >
          ↵
        </button>
      </div>

      {error ? <div className="ai-error mono">{error}</div> : null}
    </div>
  )
}