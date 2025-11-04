import { motion } from 'framer-motion'
import { Brain, Trophy, Clock } from 'lucide-react'

export default function Quizzes() {
  const quizzes = [
    { id: 1, title: 'Python Basics', questions: 10, duration: '15 min', difficulty: 'Easy', color: 'from-green-500 to-emerald-500' },
    { id: 2, title: 'Data Structures', questions: 15, duration: '25 min', difficulty: 'Medium', color: 'from-blue-500 to-cyan-500' },
    { id: 3, title: 'Algorithms Advanced', questions: 20, duration: '40 min', difficulty: 'Hard', color: 'from-purple-500 to-pink-500' },
  ]

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold mb-2 text-slate-800">Interactive Quizzes</h1>
          <p className="text-slate-600">Test your knowledge and track your progress</p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {quizzes.map((quiz, idx) => (
            <motion.div
              key={quiz.id}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              whileHover={{ scale: 1.05, y: -10 }}
              className="card p-6 cursor-pointer group"
            >
              <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${quiz.color} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                <Brain className="w-7 h-7 text-white" />
              </div>
              
              <h3 className="text-xl font-bold mb-3 text-slate-800">{quiz.title}</h3>
              
              <div className="space-y-2 mb-4">
                <div className="flex items-center text-sm text-slate-600">
                  <Trophy className="w-4 h-4 mr-2" />
                  <span>{quiz.questions} Questions</span>
                </div>
                <div className="flex items-center text-sm text-slate-600">
                  <Clock className="w-4 h-4 mr-2" />
                  <span>{quiz.duration}</span>
                </div>
              </div>

              <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${
                quiz.difficulty === 'Easy' ? 'bg-green-100 text-green-700' :
                quiz.difficulty === 'Medium' ? 'bg-blue-100 text-blue-700' :
                'bg-purple-100 text-purple-700'
              }`}>
                {quiz.difficulty}
              </span>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}
