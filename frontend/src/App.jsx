import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import Chat from './pages/Chat'
import Resources from './pages/Resources'
import Quizzes from './pages/Quizzes'
import Admin from './pages/Admin'
import Login from './pages/Login'

// Protected Route for Teachers only
function TeacherRoute({ children }) {
  const user = JSON.parse(localStorage.getItem('user') || 'null')
  
  if (!user) {
    return <Navigate to="/login" replace />
  }
  
  if (!user.is_admin) {
    return <Navigate to="/" replace />
  }
  
  return children
}

function App() {
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div className="min-h-screen">
        <Navbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/resources" element={<Resources />} />
          <Route path="/quizzes" element={<Quizzes />} />
          <Route path="/admin" element={
            <TeacherRoute>
              <Admin />
            </TeacherRoute>
          } />
          <Route path="/login" element={<Login />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
