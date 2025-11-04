import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Home, MessageSquare, BookOpen, Brain, Settings, LogIn, LogOut, User } from 'lucide-react'
import { motion } from 'framer-motion'
import axios from '../api/axios'

export default function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const user = JSON.parse(localStorage.getItem('user') || 'null')
  
  const navItems = [
    { path: '/', label: 'Home', icon: Home },
    { path: '/chat', label: 'AI Chat', icon: MessageSquare },
    { path: '/resources', label: 'Resources', icon: BookOpen },
    { path: '/quizzes', label: 'Quizzes', icon: Brain },
  ]

  // Only show Teacher Dashboard for admin users
  if (user?.is_admin) {
    navItems.push({ path: '/admin', label: 'Teacher', icon: Settings })
  }

  const handleLogout = async () => {
    try {
      await axios.post('/api/logout')
      localStorage.removeItem('user')
      navigate('/login')
    } catch (error) {
      console.error('Logout error:', error)
      // Clear local storage anyway
      localStorage.removeItem('user')
      navigate('/login')
    }
  }

  return (
    <motion.nav 
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      className="bg-white/80 backdrop-blur-md border-b border-slate-200/60 sticky top-0 z-50 shadow-sm"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-200">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
                AI Learning Hub
              </h1>
              <p className="text-xs text-slate-500">Offline Education</p>
            </div>
          </Link>

          {/* Navigation Links */}
          <div className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.path
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className="relative group"
                >
                  <div className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200 ${
                    isActive 
                      ? 'text-primary-600 bg-primary-50' 
                      : 'text-slate-600 hover:text-primary-600 hover:bg-slate-50'
                  }`}>
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{item.label}</span>
                  </div>
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-primary-500 to-secondary-500"
                      transition={{ type: "spring", stiffness: 380, damping: 30 }}
                    />
                  )}
                </Link>
              )
            })}
          </div>

          {/* Login/User Button */}
          {user ? (
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2 px-3 py-2 bg-slate-100 rounded-lg">
                <User className="w-4 h-4 text-slate-600" />
                <span className="text-sm font-medium text-slate-700">{user.username}</span>
                {user.is_admin && (
                  <span className="px-2 py-0.5 bg-primary-100 text-primary-700 rounded text-xs font-semibold">
                    Teacher
                  </span>
                )}
              </div>
              <button 
                onClick={handleLogout}
                className="btn-secondary flex items-center space-x-2"
              >
                <LogOut className="w-4 h-4" />
                <span>Logout</span>
              </button>
            </div>
          ) : (
            <Link to="/login" className="btn-secondary flex items-center space-x-2">
              <LogIn className="w-4 h-4" />
              <span>Login</span>
            </Link>
          )}
        </div>
      </div>

      {/* Mobile Navigation */}
      <div className="md:hidden border-t border-slate-200/60 bg-white/95 backdrop-blur-md">
        <div className="flex justify-around items-center py-2">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex flex-col items-center px-3 py-2 rounded-lg transition-colors ${
                  isActive ? 'text-primary-600' : 'text-slate-500'
                }`}
              >
                <Icon className="w-6 h-6" />
                <span className="text-xs mt-1 font-medium">{item.label}</span>
              </Link>
            )
          })}
        </div>
      </div>
    </motion.nav>
  )
}
