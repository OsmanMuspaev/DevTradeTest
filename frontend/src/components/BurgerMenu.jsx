import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from './useAuth.js'
import { getGithubLoginUrl } from '../services/auth.js'
import './BurgerMenu.css'

export default function BurgerMenu() {
  const [open, setOpen] = useState(false)
  const { user, isAuthenticated, logout } = useAuth()
  const location = useLocation()

  const handleLogin = async () => {
    try {
      const { url } = await getGithubLoginUrl()
      window.location.href = url
    } catch (err) {
      console.error('Failed to get login URL:', err)
    }
  }

  const isActive = (path) => location.pathname === path

  const handleLinkClick = () => setOpen(false)

  return (
    <>
      {/* Кнопка-бургер */}
      <button
        className="burger-btn"
        onClick={() => setOpen(true)}
        aria-label="Меню"
      >
        <span className="burger-line" />
        <span className="burger-line" />
        <span className="burger-line" />
      </button>

      {/* Overlay */}
      <div
        className={`burger-overlay${open ? ' burger-overlay--open' : ''}`}
        onClick={() => setOpen(false)}
      />

      {/* Drawer */}
      <div className={`burger-drawer${open ? ' burger-drawer--open' : ''}`}>
        <div className="burger-header">
          <div className="burger-title">Меню</div>
          <button className="burger-close" onClick={() => setOpen(false)}>
            ✕
          </button>
        </div>

        {/* Инфо о пользователе */}
        {isAuthenticated && user ? (
          <div className="burger-user">
            <div className="burger-user__greeting">
              👋 Привет, {user.github_username || user.full_name || 'трейдер'}!
            </div>
            <div className="burger-user__name mono">
              {user.full_name || user.github_username || '—'}
            </div>
            <div className="burger-user__balance mono">
              💰 {parseFloat(user.balance_usdt || 0).toFixed(2)} USDT
            </div>
            <div className="burger-user__id mono">ID: {user.id}</div>
          </div>
        ) : null}

        {/* Навигация */}
        <nav className="burger-nav">
          <Link
            to="/"
            className={`burger-link${isActive('/') ? ' burger-link--active' : ''}`}
            onClick={handleLinkClick}
          >
            <span>📊</span> Главная
          </Link>

          {isAuthenticated && (
            <Link
              to="/profile"
              className={`burger-link${isActive('/profile') ? ' burger-link--active' : ''}`}
              onClick={handleLinkClick}
            >
              <span>👤</span> Профиль
            </Link>
          )}

          <div className="burger-link burger-link--disabled">
            <span>⚙️</span> Настройки (скоро)
          </div>
          <div className="burger-link burger-link--disabled">
            <span>📋</span> История (скоро)
          </div>
        </nav>

        {/* Кнопка логина/логаута */}
        <div className="burger-auth">
          {isAuthenticated ? (
            <button className="burger-btn-logout" onClick={logout}>
              Выйти
            </button>
          ) : (
            <button className="burger-btn-login" onClick={handleLogin}>
              Войти через GitHub
            </button>
          )}
        </div>
      </div>
    </>
  )
}