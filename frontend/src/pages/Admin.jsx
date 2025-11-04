import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Users, FileText, MessageSquare, Activity, TrendingUp, BookOpen, CheckCircle } from 'lucide-react'
import axios from '../api/axios'

export default function Admin() {
  const [stats, setStats] = useState({
    user_count: 0,
    resource_count: 0,
    quiz_count: 0,
    chat_count: 0,
    notifications: [],
    recent_resources: []
  })
  const [loading, setLoading] = useState(true)
  const [indexing, setIndexing] = useState(false)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const response = await axios.get('/api/stats')
      setStats(response.data)
    } catch (error) {
      console.error('Error fetching stats:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleIndexResources = async (forceReindex = false) => {
    setIndexing(true)
    try {
      const response = await axios.post('/api/index-resources', {
        force_reindex: forceReindex
      })
      
      const data = response.data
      let message = `Resources indexed successfully!\n\n`
      message += `📊 Processed: ${data.count || 0} PDFs\n`
      message += `📦 Generated: ${data.chunks || 0} chunks\n`
      
      if (data.debug_file) {
        message += `\n🔍 Debug file created: ${data.debug_file}\n`
        message += `Check the backend folder for detailed chunk analysis.`
      }
      
      if (data.stats) {
        message += `\n\n📈 Index Stats:\n`
        message += `• Total documents: ${data.stats.total_documents}\n`
        message += `• Index loaded: ${data.stats.index_loaded ? '✅' : '❌'}\n`
        message += `• Model loaded: ${data.stats.model_loaded ? '✅' : '❌'}`
      }
      
      alert(message)
      fetchStats() // Refresh stats
    } catch (error) {
      console.error('Indexing error:', error)
      let errorMsg = 'Indexing failed!'
      
      if (error.response?.data?.debug_file) {
        errorMsg += `\n\nDebug file created: ${error.response.data.debug_file}`
        errorMsg += `\nCheck the backend folder for error details.`
      }
      
      if (error.response?.data?.error) {
        errorMsg += `\n\nError: ${error.response.data.error}`
      }
      
      alert(errorMsg)
    } finally {
      setIndexing(false)
    }
  }

  const statsCards = [
    { label: 'Total Students', value: stats.user_count, icon: Users, color: 'from-blue-500 to-cyan-500' },
    { label: 'Resources Uploaded', value: stats.resource_count, icon: FileText, color: 'from-purple-500 to-pink-500' },
    { label: 'Chat Interactions', value: stats.chat_count, icon: MessageSquare, color: 'from-green-500 to-emerald-500' },
    { label: 'Quizzes Available', value: stats.quiz_count, icon: BookOpen, color: 'from-orange-500 to-red-500' },
  ]

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold mb-2 text-slate-800">Teacher Dashboard</h1>
          <p className="text-slate-600">Manage your learning platform and monitor student activity</p>
        </motion.div>

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="loading-spinner w-12 h-12"></div>
          </div>
        ) : (
          <>
            {/* Stats Grid */}
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {statsCards.map((stat, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className="card p-6"
                >
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center mb-4`}>
                    <stat.icon className="w-6 h-6 text-white" />
                  </div>
                  <div className="text-3xl font-bold text-slate-800 mb-1">{stat.value}</div>
                  <div className="text-sm text-slate-600">{stat.label}</div>
                </motion.div>
              ))}
            </div>

            {/* Recent Resources */}
            {stats.recent_resources && stats.recent_resources.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="card p-6 mb-8"
              >
                <h3 className="text-xl font-bold mb-4 text-slate-800">Recently Uploaded Resources</h3>
                <div className="space-y-3">
                  {stats.recent_resources.map((resource) => (
                    <div key={resource.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                      <div>
                        <p className="font-semibold text-slate-800">{resource.title}</p>
                        <p className="text-sm text-slate-600">{resource.category}</p>
                      </div>
                      <span className="text-xs text-slate-500">
                        {new Date(resource.uploaded_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Actions */}
            <div className="grid md:grid-cols-2 gap-6">
              <motion.div
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                className="card p-8"
              >
                <h3 className="text-xl font-bold mb-4 text-slate-800">Index Resources for AI</h3>
                <p className="text-slate-600 mb-6">Process uploaded PDFs and create embeddings for AI-powered chat</p>
                
                <div className="space-y-3">
                  <button 
                    onClick={() => handleIndexResources(false)}
                    disabled={indexing}
                    className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {indexing ? 'Indexing...' : 'Index New Resources'}
                  </button>
                  
                  <button 
                    onClick={() => handleIndexResources(true)}
                    disabled={indexing}
                    className="btn-secondary w-full disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {indexing ? 'Indexing...' : '🔄 Force Re-index All (Debug)'}
                  </button>
                </div>
                
                <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                  <p className="text-xs text-blue-600">
                    <strong>Normal:</strong> Index only new PDFs<br/>
                    <strong>Force:</strong> Re-index all PDFs with debug output
                  </p>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                className="card p-8"
              >
                <h3 className="text-xl font-bold mb-4 text-slate-800">System Status</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-600">AI Model</span>
                    <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-semibold flex items-center">
                      <CheckCircle className="w-4 h-4 mr-1" />
                      Active
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-600">Database</span>
                    <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-semibold flex items-center">
                      <CheckCircle className="w-4 h-4 mr-1" />
                      Connected
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-600">Resources Indexed</span>
                    <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-semibold">
                      {stats.recent_resources?.filter(r => r.indexed).length || 0} / {stats.resource_count}
                    </span>
                  </div>
                </div>
              </motion.div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
