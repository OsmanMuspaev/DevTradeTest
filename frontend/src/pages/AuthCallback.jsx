import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../components/useAuth.js'

export default function AuthCallback() {
  const navigate = useNavigate()
  const { fetchUser } = useAuth()
  const [message, setMessage] = useState('Завершаем вход...')
  const processedRef = useRef(false)

  useEffect(() => {
    if (processedRef.current) return
    processedRef.current = true

    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')

    if (!code) {
      Promise.resolve().then(() => {
        setMessage('Ошибка: нет кода авторизации')
      })
      setTimeout(() => navigate('/', { replace: true }), 2000)
      return
    }

    fetch(`/api/users/auth/github/callback?code=${code}`)
      .then(res => {
        if (!res.ok) throw new Error('Auth failed')
        return res.json()
      })
      .then(data => {
        if (data.token) {
          return fetchUser(data.token)
        } else {
          throw new Error('No token in response')
        }
      })
      .then(() => {
        navigate('/', { replace: true })
      })
      .catch(err => {
        Promise.resolve().then(() => {
          setMessage(`Ошибка: ${err.message}`)
        })
        setTimeout(() => navigate('/', { replace: true }), 3000)
      })
  }, [navigate, fetchUser])

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      color: 'var(--text)',
      fontFamily: 'var(--sans)',
    }}>
      <div style={{ textAlign: 'center' }}>
        <p>{message}</p>
      </div>
    </div>
  )
}