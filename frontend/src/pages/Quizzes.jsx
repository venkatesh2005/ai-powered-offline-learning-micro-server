import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Brain, Trophy, Clock, ChevronLeft, ChevronRight, Check, Plus, Trash2, Edit3, BarChart3, RefreshCw, Save } from 'lucide-react'
import axios from '../api/axios'

export default function Quizzes() {
  const user = JSON.parse(localStorage.getItem('user') || 'null')
  const isAdmin = user?.is_admin === true

  /* ───── state ───────────────────────────────────────────────── */
  const [view, setView] = useState('list')
  const [quizzes, setQuizzes] = useState([])
  const [categories, setCategories] = useState([])
  const [filterCat, setFilterCat] = useState('')
  const [loading, setLoading] = useState(true)

  // taking a quiz
  const [currentQuiz, setCurrentQuiz] = useState(null)
  const [questions, setQuestions] = useState([])
  const [qIndex, setQIndex] = useState(0)
  const [answers, setAnswers] = useState({})
  const [resultData, setResultData] = useState(null)

  // admin generate
  const [showGenerate, setShowGenerate] = useState(false)
  const [genForm, setGenForm] = useState({ title: 'Auto Quiz', num_questions: 10, category: 'General', difficulty: 'medium', topic: '' })
  const [generating, setGenerating] = useState(false)
  const [genMsg, setGenMsg] = useState('')

  // admin manual create / edit
  const [editQuiz, setEditQuiz] = useState(null)
  const [editQuestions, setEditQuestions] = useState([])
  const [editMeta, setEditMeta] = useState({ title: '', description: '', category: '', difficulty: 'medium' })

  // admin analytics
  const [analytics, setAnalytics] = useState(null)

  /* ───── load quizzes ────────────────────────────────────────── */
  const loadQuizzes = useCallback(async () => {
    setLoading(true)
    try {
      const url = filterCat ? `/api/quizzes?category=${encodeURIComponent(filterCat)}` : '/api/quizzes'
      const res = await axios.get(url)
      setQuizzes(res.data.quizzes || [])
      setCategories(res.data.categories || [])
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [filterCat])

  useEffect(() => { loadQuizzes() }, [loadQuizzes])

  /* ───── student: start / select / submit ────────────────────── */
  const startQuiz = async (quizId) => {
    try {
      const res = await axios.get(`/api/quiz/${quizId}`)
      setCurrentQuiz({ id: quizId, title: res.data.title })
      setQuestions(res.data.questions || [])
      setQIndex(0)
      setAnswers({})
      setResultData(null)
      setView('take')
    } catch { alert('Could not load quiz') }
  }

  const selectOption = (label) => {
    const qid = String(questions[qIndex]?.id)
    setAnswers(prev => ({ ...prev, [qid]: label }))
  }

  const submitQuiz = async () => {
    const unanswered = questions.filter(q => !answers[String(q.id)])
    if (unanswered.length > 0 && !window.confirm(`You have ${unanswered.length} unanswered question(s). Submit anyway?`)) return
    try {
      const res = await axios.post(`/api/quiz/${currentQuiz.id}/submit`, { answers })
      setResultData(res.data)
      setView('result')
    } catch { alert('Submit failed') }
  }

  /* ───── admin: generate ─────────────────────────────────────── */
  const openGenerateForm = () => {
    setShowGenerate(prev => !prev)
  }

  const handleGenerate = async () => {
    if (!genForm.topic.trim()) { setGenMsg('Please enter a topic.'); return }
    setGenerating(true); setGenMsg('')
    try {
      const res = await axios.post('/api/quiz/generate', genForm)
      setGenMsg(`Generated ${res.data.num_questions} questions!`)
      setShowGenerate(false)
      loadQuizzes()
    } catch (e) {
      setGenMsg(e.response?.data?.error || e.message)
    } finally { setGenerating(false) }
  }

  /* ───── admin: editor ───────────────────────────────────────── */
  const openEditor = async (quizId) => {
    if (quizId) {
      try {
        const res = await axios.get(`/api/quiz/${quizId}/admin`)
        const q = res.data
        setEditQuiz(quizId)
        setEditMeta({ title: q.title, description: q.description || '', category: q.category || '', difficulty: q.difficulty || 'medium' })
        setEditQuestions(q.questions || [])
      } catch { alert('Failed to load quiz') }
    } else {
      setEditQuiz(null)
      setEditMeta({ title: 'New Quiz', description: '', category: 'General', difficulty: 'medium' })
      setEditQuestions([{ id: 1, question: '', optionA: '', optionB: '', optionC: '', optionD: '', correctAnswer: 'A', topic: '', sourceDocument: 'Manual' }])
    }
    setView('admin-edit')
  }

  const updateEditQ = (idx, field, val) => setEditQuestions(prev => prev.map((q, i) => i === idx ? { ...q, [field]: val } : q))
  const addEditQ = () => {
    const nextId = editQuestions.length > 0 ? Math.max(...editQuestions.map(q => q.id || 0)) + 1 : 1
    setEditQuestions(prev => [...prev, { id: nextId, question: '', optionA: '', optionB: '', optionC: '', optionD: '', correctAnswer: 'A', topic: '', sourceDocument: 'Manual' }])
  }
  const removeEditQ = (idx) => setEditQuestions(prev => prev.filter((_, i) => i !== idx))

  const saveQuiz = async () => {
    for (const q of editQuestions) {
      if (!q.question || !q.optionA || !q.optionB || !q.optionC || !q.optionD) {
        alert('All questions must have text and 4 options.'); return
      }
    }
    try {
      if (editQuiz) {
        await axios.put(`/api/quiz/${editQuiz}/edit`, { ...editMeta, questions: editQuestions })
      } else {
        await axios.post('/api/quiz/create', { ...editMeta, questions: editQuestions })
      }
      setView('list'); loadQuizzes()
    } catch (e) { alert('Save failed: ' + (e.response?.data?.error || e.message)) }
  }

  const deleteQuiz = async (id) => {
    if (!window.confirm('Delete this quiz and all its results?')) return
    try { await axios.delete(`/api/quiz/${id}/delete`); loadQuizzes() }
    catch { alert('Delete failed') }
  }

  /* ───── admin: analytics ────────────────────────────────────── */
  const openAnalytics = async (quizId) => {
    try {
      const res = await axios.get(`/api/quiz/${quizId}/analytics`)
      setAnalytics(res.data)
      setView('admin-analytics')
    } catch { alert('Could not load analytics') }
  }

  /* ───── render helpers ──────────────────────────────────────── */
  const q = questions[qIndex] || {}
  const labels = ['A', 'B', 'C', 'D']
  const optKeys = ['optionA', 'optionB', 'optionC', 'optionD']
  const selected = answers[String(q.id)]

  /* ================================================================
     QUIZ LIST VIEW
     ================================================================ */
  if (view === 'list') return (
    <div className="min-h-screen p-3 md:p-6">
      <div className="max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6 md:mb-8">
          <h1 className="text-2xl md:text-4xl font-bold mb-2 text-slate-800">Interactive Quizzes</h1>
          <p className="text-sm md:text-base text-slate-600">Test your knowledge and track your progress</p>
        </motion.div>

        {/* Admin controls */}
        {isAdmin && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card p-4 md:p-6 mb-6">
            <h3 className="font-bold text-lg text-slate-800 mb-3">Admin Controls</h3>
            <div className="flex flex-wrap gap-3">
              <button onClick={openGenerateForm}
                className="btn-primary flex items-center gap-2 text-sm">
                <RefreshCw className="w-4 h-4" /> Generate with AI
              </button>
              <button onClick={() => openEditor(null)}
                className="btn-secondary flex items-center gap-2 text-sm">
                <Plus className="w-4 h-4" /> Create Manually
              </button>
            </div>

            {/* Generate form */}
            <AnimatePresence>
              {showGenerate && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden mt-4 p-4 bg-slate-50 rounded-xl space-y-3">
                  <div className="grid sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-semibold text-slate-600">Title</label>
                      <input className="w-full border rounded-lg p-2 text-sm" value={genForm.title}
                        onChange={e => setGenForm(f => ({ ...f, title: e.target.value }))} />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-600">Topic *</label>
                      <input className="w-full border rounded-lg p-2 text-sm" placeholder="e.g. Python Variables, OOP Concepts"
                        value={genForm.topic}
                        onChange={e => setGenForm(f => ({ ...f, topic: e.target.value }))} />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-600">Category</label>
                      <input className="w-full border rounded-lg p-2 text-sm" value={genForm.category}
                        onChange={e => setGenForm(f => ({ ...f, category: e.target.value }))} />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-600">Questions</label>
                      <select className="w-full border rounded-lg p-2 text-sm" value={genForm.num_questions}
                        onChange={e => setGenForm(f => ({ ...f, num_questions: Number(e.target.value) }))}>
                        {[5, 10, 15, 20].map(n => <option key={n} value={n}>{n}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-600">Difficulty</label>
                      <select className="w-full border rounded-lg p-2 text-sm" value={genForm.difficulty}
                        onChange={e => setGenForm(f => ({ ...f, difficulty: e.target.value }))}>
                        {['easy', 'medium', 'hard'].map(d => <option key={d} value={d}>{d}</option>)}
                      </select>
                    </div>
                  </div>
                  <div className="flex gap-3 items-center">
                    <button onClick={handleGenerate} disabled={generating}
                      className="btn-primary text-sm disabled:opacity-50">
                      {generating ? 'Generating...' : 'Generate'}
                    </button>
                    <button onClick={() => setShowGenerate(false)} className="btn-secondary text-sm">Cancel</button>
                  </div>
                  {genMsg && <p className={`text-sm ${genMsg.startsWith('Generated') ? 'text-green-600' : 'text-red-600'}`}>{genMsg}</p>}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}

        {/* Category filter */}
        {categories.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            <button onClick={() => setFilterCat('')}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition ${!filterCat ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>All</button>
            {categories.map(c => (
              <button key={c} onClick={() => setFilterCat(c)}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition ${filterCat === c ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>{c}</button>
            ))}
          </div>
        )}

        {/* Quiz cards */}
        {loading ? (
          <div className="flex justify-center items-center h-64"><div className="loading-spinner w-12 h-12" /></div>
        ) : quizzes.length === 0 ? (
          <div className="card p-8 text-center text-slate-500">
            No quizzes available yet.{isAdmin ? ' Generate one using the admin controls above!' : ''}
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
            {quizzes.map((quiz, idx) => (
              <motion.div key={quiz.id}
                initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="card p-5 md:p-6 group"
              >
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                  <Brain className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-bold mb-1 text-slate-800">{quiz.title}</h3>
                {quiz.description && <p className="text-xs text-slate-500 mb-2 line-clamp-2">{quiz.description}</p>}

                <div className="space-y-1 mb-3 text-xs text-slate-600">
                  <div className="flex items-center"><Trophy className="w-3 h-3 mr-2" />{quiz.question_count || (quiz.questions||[]).length} Questions</div>
                  {quiz.category && <div className="flex items-center"><Clock className="w-3 h-3 mr-2" />{quiz.category}</div>}
                </div>

                <span className={`inline-block px-2 py-1 rounded-full text-xs font-semibold mb-3 ${
                  quiz.difficulty === 'easy' ? 'bg-green-100 text-green-700' :
                  quiz.difficulty === 'hard' ? 'bg-purple-100 text-purple-700' :
                  'bg-blue-100 text-blue-700'
                }`}>{quiz.difficulty}</span>

                <div className="flex flex-wrap gap-2 mt-auto">
                  <button onClick={() => startQuiz(quiz.id)} className="btn-primary text-xs flex-1">Take Quiz</button>
                  {isAdmin && <>
                    <button onClick={() => openEditor(quiz.id)} title="Edit"
                      className="p-2 rounded-lg bg-amber-50 text-amber-600 hover:bg-amber-100 transition"><Edit3 className="w-4 h-4" /></button>
                    <button onClick={() => openAnalytics(quiz.id)} title="Analytics"
                      className="p-2 rounded-lg bg-indigo-50 text-indigo-600 hover:bg-indigo-100 transition"><BarChart3 className="w-4 h-4" /></button>
                    <button onClick={() => deleteQuiz(quiz.id)} title="Delete"
                      className="p-2 rounded-lg bg-red-50 text-red-600 hover:bg-red-100 transition"><Trash2 className="w-4 h-4" /></button>
                  </>}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  )

  /* ================================================================
     TAKE QUIZ VIEW
     ================================================================ */
  if (view === 'take') return (
    <div className="min-h-screen p-3 md:p-6">
      <div className="max-w-3xl mx-auto">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card p-5 md:p-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-slate-800">{currentQuiz?.title}</h2>
            <button onClick={() => setView('list')} className="text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1"><ChevronLeft className="w-4 h-4" />Back</button>
          </div>

          {/* Progress */}
          <p className="text-xs text-slate-500 mb-1">Question {qIndex + 1} of {questions.length}</p>
          <div className="w-full h-2 bg-slate-200 rounded-full mb-6">
            <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${((qIndex + 1) / questions.length) * 100}%` }} />
          </div>

          {/* Question */}
          <p className="text-base md:text-lg font-semibold text-slate-800 mb-6 leading-relaxed">{q.question}</p>

          {/* Options */}
          <div className="space-y-3 mb-6">
            {labels.map((label, i) => {
              const text = q[optKeys[i]] || ''
              const isSel = selected === label
              return (
                <button key={label} onClick={() => selectOption(label)}
                  className={`w-full flex items-start gap-3 p-3 md:p-4 rounded-xl border-2 text-left transition
                    ${isSel ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-slate-300 bg-white'}`}>
                  <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0
                    ${isSel ? 'bg-blue-500 text-white' : 'bg-slate-100 text-slate-600'}`}>{label}</span>
                  <span className="pt-1 text-sm text-slate-700 leading-relaxed">{text}</span>
                </button>
              )
            })}
          </div>

          {q.sourceDocument && <p className="text-xs text-slate-400 italic mb-4">Source: {q.sourceDocument}</p>}

          {/* Nav */}
          <div className="flex justify-between">
            <button onClick={() => setQIndex(i => Math.max(0, i - 1))} disabled={qIndex === 0}
              className="btn-secondary text-sm disabled:opacity-40 flex items-center gap-1"><ChevronLeft className="w-4 h-4" /> Prev</button>
            {qIndex < questions.length - 1
              ? <button onClick={() => setQIndex(i => i + 1)} className="btn-primary text-sm flex items-center gap-1">Next <ChevronRight className="w-4 h-4" /></button>
              : <button onClick={submitQuiz} className="bg-green-600 hover:bg-green-700 text-white font-semibold px-5 py-2 rounded-xl text-sm flex items-center gap-1"><Check className="w-4 h-4" /> Submit</button>
            }
          </div>
        </motion.div>
      </div>
    </div>
  )

  /* ================================================================
     RESULT VIEW
     ================================================================ */
  if (view === 'result' && resultData) {
    const pct = Math.round(resultData.percentage || 0)
    return (
      <div className="min-h-screen p-3 md:p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="card p-6 md:p-8 text-center">
            <div className={`w-32 h-32 mx-auto rounded-full border-4 flex flex-col items-center justify-center mb-4
              ${pct >= 80 ? 'border-green-500' : pct >= 50 ? 'border-amber-500' : 'border-red-500'}`}>
              <span className={`text-4xl font-bold ${pct >= 80 ? 'text-green-600' : pct >= 50 ? 'text-amber-600' : 'text-red-600'}`}>{pct}%</span>
              <span className="text-xs text-slate-500">{resultData.correct}/{resultData.total}</span>
            </div>
            <h2 className="text-2xl font-bold text-slate-800">{pct >= 80 ? 'Excellent!' : pct >= 50 ? 'Good Job!' : 'Keep Studying!'}</h2>
            <p className="text-slate-500 mt-1 text-sm">You answered {resultData.correct} out of {resultData.total} correctly.</p>
            <div className="flex justify-center gap-3 mt-4">
              <button onClick={() => setView('list')} className="btn-secondary text-sm">All Quizzes</button>
              <button onClick={() => startQuiz(currentQuiz.id)} className="btn-primary text-sm">Retake</button>
            </div>
          </motion.div>

          {/* Detail */}
          <div className="card p-5 md:p-6">
            <h3 className="font-bold text-lg text-slate-800 mb-4">Detailed Results</h3>
            <div className="space-y-3">
              {(resultData.results || []).map((r, idx) => {
                const optMap = { A: r.optionA, B: r.optionB, C: r.optionC, D: r.optionD }
                return (
                  <div key={idx} className={`p-3 rounded-xl border-l-4 ${r.is_correct ? 'border-green-500 bg-green-50' : 'border-red-500 bg-red-50'}`}>
                    <p className="font-semibold text-sm text-slate-800 mb-1">{idx + 1}. {r.question}</p>
                    <p className="text-xs text-slate-600">
                      Your answer: <span className={r.is_correct ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}>
                        {r.user_answer ? `${r.user_answer}: ${optMap[r.user_answer] || ''}` : 'Not answered'}
                      </span>
                    </p>
                    {!r.is_correct && <p className="text-xs text-green-700 mt-0.5">Correct: {r.correct_answer}: {optMap[r.correct_answer] || ''}</p>}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    )
  }

  /* ================================================================
     ADMIN EDIT VIEW
     ================================================================ */
  if (view === 'admin-edit') return (
    <div className="min-h-screen p-3 md:p-6">
      <div className="max-w-4xl mx-auto space-y-5">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-slate-800">{editQuiz ? 'Edit Quiz' : 'Create Quiz'}</h2>
          <button onClick={() => setView('list')} className="btn-secondary text-sm flex items-center gap-1"><ChevronLeft className="w-4 h-4" />Back</button>
        </div>

        {/* Meta */}
        <div className="card p-5 grid sm:grid-cols-2 gap-3">
          <div><label className="text-xs font-semibold text-slate-600">Title</label>
            <input className="w-full border rounded-lg p-2 text-sm" value={editMeta.title}
              onChange={e => setEditMeta(m => ({ ...m, title: e.target.value }))} /></div>
          <div><label className="text-xs font-semibold text-slate-600">Category</label>
            <input className="w-full border rounded-lg p-2 text-sm" value={editMeta.category}
              onChange={e => setEditMeta(m => ({ ...m, category: e.target.value }))} /></div>
          <div><label className="text-xs font-semibold text-slate-600">Description</label>
            <input className="w-full border rounded-lg p-2 text-sm" value={editMeta.description}
              onChange={e => setEditMeta(m => ({ ...m, description: e.target.value }))} /></div>
          <div><label className="text-xs font-semibold text-slate-600">Difficulty</label>
            <select className="w-full border rounded-lg p-2 text-sm" value={editMeta.difficulty}
              onChange={e => setEditMeta(m => ({ ...m, difficulty: e.target.value }))}>
              {['easy', 'medium', 'hard'].map(d => <option key={d} value={d}>{d}</option>)}
            </select></div>
        </div>

        {/* Questions */}
        {editQuestions.map((eq, idx) => (
          <motion.div key={eq.id || idx} layout className="card p-4 space-y-2 relative">
            <div className="flex justify-between items-start">
              <span className="text-xs font-bold text-slate-400">Q{idx + 1}</span>
              <button onClick={() => removeEditQ(idx)} className="text-red-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
            </div>
            <div><label className="text-xs font-semibold text-slate-600">Question</label>
              <textarea className="w-full border rounded-lg p-2 text-sm" rows={2} value={eq.question}
                onChange={e => updateEditQ(idx, 'question', e.target.value)} /></div>
            <div className="grid sm:grid-cols-2 gap-2">
              {['A', 'B', 'C', 'D'].map(l => (
                <div key={l}><label className="text-xs font-semibold text-slate-600">Option {l}</label>
                  <input className="w-full border rounded-lg p-2 text-sm" value={eq[`option${l}`] || ''}
                    onChange={e => updateEditQ(idx, `option${l}`, e.target.value)} /></div>
              ))}
            </div>
            <div className="grid sm:grid-cols-2 gap-2">
              <div><label className="text-xs font-semibold text-slate-600">Correct Answer</label>
                <select className="w-full border rounded-lg p-2 text-sm" value={eq.correctAnswer || 'A'}
                  onChange={e => updateEditQ(idx, 'correctAnswer', e.target.value)}>
                  {['A', 'B', 'C', 'D'].map(l => <option key={l} value={l}>{l}</option>)}
                </select></div>
              <div><label className="text-xs font-semibold text-slate-600">Topic</label>
                <input className="w-full border rounded-lg p-2 text-sm" value={eq.topic || ''}
                  onChange={e => updateEditQ(idx, 'topic', e.target.value)} /></div>
            </div>
          </motion.div>
        ))}

        <div className="flex gap-3">
          <button onClick={addEditQ} className="btn-secondary text-sm flex items-center gap-1"><Plus className="w-4 h-4" /> Add Question</button>
          <button onClick={saveQuiz} className="btn-primary text-sm flex items-center gap-1"><Save className="w-4 h-4" /> Save Quiz</button>
        </div>
      </div>
    </div>
  )

  /* ================================================================
     ADMIN ANALYTICS VIEW
     ================================================================ */
  if (view === 'admin-analytics' && analytics) return (
    <div className="min-h-screen p-3 md:p-6">
      <div className="max-w-4xl mx-auto space-y-5">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-slate-800">Analytics: {analytics.title}</h2>
          <button onClick={() => setView('list')} className="btn-secondary text-sm flex items-center gap-1"><ChevronLeft className="w-4 h-4" />Back</button>
        </div>

        {analytics.attempts === 0 ? (
          <div className="card p-8 text-center text-slate-500">No attempts yet.</div>
        ) : <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { label: 'Attempts', value: analytics.attempts, cls: 'text-blue-600' },
              { label: 'Avg Score', value: `${analytics.average_score}%`, cls: 'text-indigo-600' },
              { label: 'Highest', value: `${analytics.highest_score}%`, cls: 'text-green-600' },
              { label: 'Lowest', value: `${analytics.lowest_score}%`, cls: 'text-red-600' },
              { label: 'Pass', value: analytics.pass_count, cls: 'text-emerald-600' },
              { label: 'Fail', value: analytics.fail_count, cls: 'text-rose-600' },
            ].map(s => (
              <div key={s.label} className="card p-4 text-center">
                <p className="text-xs text-slate-500">{s.label}</p>
                <p className={`text-xl font-bold ${s.cls}`}>{s.value}</p>
              </div>
            ))}
          </div>

          {/* Question accuracy */}
          <div className="card p-5">
            <h3 className="font-bold text-lg text-slate-800 mb-4">Question-wise Accuracy</h3>
            <div className="space-y-3">
              {(analytics.question_accuracy || []).map((qa, idx) => (
                <div key={qa.question_id} className="flex items-center gap-3">
                  <span className="text-xs text-slate-400 w-8 shrink-0">Q{idx + 1}</span>
                  <div className="flex-1">
                    <p className="text-xs text-slate-700 mb-1 truncate">{qa.question}</p>
                    <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${qa.accuracy >= 70 ? 'bg-green-500' : qa.accuracy >= 40 ? 'bg-amber-500' : 'bg-red-500'}`}
                        style={{ width: `${qa.accuracy}%` }} />
                    </div>
                  </div>
                  <span className="text-xs font-bold text-slate-600 w-14 text-right">{qa.accuracy}%</span>
                </div>
              ))}
            </div>
          </div>
        </>}
      </div>
    </div>
  )

  /* fallback */
  return <div className="p-8 text-center"><button onClick={() => setView('list')} className="btn-primary">Back to Quizzes</button></div>
}
