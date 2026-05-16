import { Outlet } from 'react-router-dom'
import BurgerMenu from '../components/BurgerMenu.jsx'

export default function MainLayout() {
  return (
    <>
      <BurgerMenu />
      <Outlet />
    </>
  )
}