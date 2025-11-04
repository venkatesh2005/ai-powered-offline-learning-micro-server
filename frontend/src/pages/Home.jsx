import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { MessageSquare, BookOpen, Brain, Zap, Shield, Wifi } from 'lucide-react'

export default function Home() {
  const features = [
    {
      icon: MessageSquare,
      title: 'AI-Powered Chat',
      description: 'Get instant answers from our offline AI assistant trained on your learning materials',
      color: 'from-blue-500 to-cyan-500'
    },
    {
      icon: BookOpen,
      title: 'Rich Resources',
      description: 'Access PDFs, videos, and documents - all indexed and searchable offline',
      color: 'from-purple-500 to-pink-500'
    },
    {
      icon: Brain,
      title: 'Interactive Quizzes',
      description: 'Test your knowledge with adaptive quizzes and track your progress',
      color: 'from-orange-500 to-red-500'
    },
    {
      icon: Zap,
      title: 'Lightning Fast',
      description: 'No internet needed - everything runs locally on your device',
      color: 'from-green-500 to-emerald-500'
    },
    {
      icon: Shield,
      title: 'Privacy First',
      description: 'Your data never leaves your device - complete privacy guaranteed',
      color: 'from-indigo-500 to-purple-500'
    },
    {
      icon: Wifi,
      title: '100% Offline',
      description: 'Works anywhere, anytime - no internet connection required',
      color: 'from-pink-500 to-rose-500'
    }
  ]

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center"
          >
            <div className="inline-block mb-4 px-4 py-2 bg-primary-100 text-primary-700 rounded-full text-sm font-semibold">
              🚀 Powered by AI - Works 100% Offline
            </div>
            
            <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-primary-600 via-secondary-600 to-primary-600 bg-clip-text text-transparent animate-gradient">
              Learn Anywhere,
              <br />
              <span className="text-slate-800">Anytime</span>
            </h1>
            
            <p className="text-xl text-slate-600 mb-8 max-w-2xl mx-auto">
              Your personal AI-powered learning platform that works completely offline.
              No internet? No problem! 📚
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/chat" className="btn-primary text-lg">
                Start Learning 🎓
              </Link>
              <Link to="/resources" className="btn-secondary text-lg">
                Browse Resources 📖
              </Link>
            </div>

            {/* Stats */}
            <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-8">
              {[
                { value: '100%', label: 'Offline' },
                { value: '7B+', label: 'AI Parameters' },
                { value: '0ms', label: 'Latency' },
                { value: '∞', label: 'Usage Limit' }
              ].map((stat, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 + 0.3 }}
                  className="card p-6"
                >
                  <div className="text-3xl font-bold bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
                    {stat.value}
                  </div>
                  <div className="text-sm text-slate-600 mt-1">{stat.label}</div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Gradient Orbs */}
        <div className="absolute top-20 left-10 w-72 h-72 bg-primary-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
        <div className="absolute top-40 right-10 w-72 h-72 bg-secondary-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute bottom-20 left-1/2 w-72 h-72 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4 bg-white/40">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold mb-4 text-slate-800">
              Everything You Need to Learn
            </h2>
            <p className="text-xl text-slate-600">
              Powerful features designed for offline learning
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.1 }}
                whileHover={{ scale: 1.05, y: -10 }}
                className="card p-8 group cursor-pointer"
              >
                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-200`}>
                  <feature.icon className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-xl font-bold mb-3 text-slate-800">{feature.title}</h3>
                <p className="text-slate-600">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="max-w-4xl mx-auto card p-12 text-center bg-gradient-to-br from-primary-600 to-secondary-600 text-white"
        >
          <h2 className="text-4xl font-bold mb-4">Ready to Start Learning?</h2>
          <p className="text-xl mb-8 text-white/90">
            Join thousands of students learning offline with AI
          </p>
          <Link to="/chat" className="inline-block bg-white text-primary-600 font-bold px-8 py-4 rounded-xl hover:bg-slate-50 transition-all duration-200 hover:shadow-2xl hover:-translate-y-1">
            Get Started Free →
          </Link>
        </motion.div>
      </section>

      <style jsx>{`
        @keyframes blob {
          0%, 100% { transform: translate(0, 0) scale(1); }
          25% { transform: translate(20px, -50px) scale(1.1); }
          50% { transform: translate(-20px, 20px) scale(0.9); }
          75% { transform: translate(50px, 50px) scale(1.05); }
        }
        .animate-blob {
          animation: blob 7s infinite;
        }
        .animation-delay-2000 {
          animation-delay: 2s;
        }
        .animation-delay-4000 {
          animation-delay: 4s;
        }
      `}</style>
    </div>
  )
}
