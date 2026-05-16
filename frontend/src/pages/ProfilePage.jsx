import { Navigate } from 'react-router-dom'
import { useAuth } from '../components/useAuth.js'
import './ProfilePage.css'

export default function ProfilePage() {
  const { user, loading, isAuthenticated } = useAuth()

  if (loading) {
    return (
      <div className="profile">
        <div className="loading-screen">Загрузка профиля...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return (
    <div className="profile">
      <div className="profile__card">
        <div className="profile__header">
          <div className="profile__avatar">
            {user.github_username?.[0]?.toUpperCase() || '?'}
          </div>
          <div className="profile__info">
            <h1 className="profile__name">
              {user.full_name || user.github_username || 'Неизвестный'}
            </h1>
            <p className="profile__github mono">@{user.github_username || '—'}</p>
          </div>
        </div>

        <div className="profile__details">
          <div className="profile__row">
            <span className="profile__label">ID</span>
            <span className="profile__value mono">{user.id}</span>
          </div>
          <div className="profile__row">
            <span className="profile__label">GitHub ID</span>
            <span className="profile__value mono">{user.github_id}</span>
          </div>
          <div className="profile__row">
            <span className="profile__label">Email</span>
            <span className="profile__value mono">{user.email || '—'}</span>
          </div>
          <div className="profile__row">
            <span className="profile__label">Баланс</span>
            <span className="profile__value profile__balance mono">
              {parseFloat(user.balance_usdt || 0).toFixed(2)} USDT
            </span>
          </div>
          {user.age && (
            <div className="profile__row">
              <span className="profile__label">Возраст</span>
              <span className="profile__value mono">{user.age} лет</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}