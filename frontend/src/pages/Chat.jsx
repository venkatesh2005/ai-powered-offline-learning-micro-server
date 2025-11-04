import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Bot, User, Loader, BookOpen } from 'lucide-react'
import axios from '../api/axios'
import ChatSidebar from '../components/ChatSidebar'

export default function Chat() {
  const [conversations, setConversations] = useState([])
  const [currentConversationId, setCurrentConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Load conversations on mount
  useEffect(() => {
    loadConversations()
  }, [])

  // Load messages when conversation changes
  useEffect(() => {
    if (currentConversationId) {
      loadConversationMessages(currentConversationId)
    } else {
      setMessages([])
    }
  }, [currentConversationId])

  const loadConversations = async () => {
    try {
      const response = await axios.get('/api/conversations')
      setConversations(response.data.conversations)
      
      // Auto-select first conversation only on initial load
      if (response.data.conversations.length > 0 && !currentConversationId) {
        setCurrentConversationId(response.data.conversations[0].id)
      }
    } catch (error) {
      console.error('Failed to load conversations:', error)
      // If not authenticated, clear state
      if (error.response?.status === 401) {
        setConversations([])
        setCurrentConversationId(null)
        setMessages([])
      }
    }
  }

  const loadConversationMessages = async (convId) => {
    try {
      const response = await axios.get(`/api/conversations/${convId}/messages`)
      const msgs = response.data.messages.map(m => ([
        { role: 'user', content: m.question },
        { role: 'assistant', content: m.answer }
      ])).flat()
      setMessages(msgs)
    } catch (error) {
      console.error('Failed to load messages:', error)
      setMessages([])
    }
  }

  const handleNewConversation = async () => {
    try {
      const response = await axios.post('/api/conversations', {
        title: 'New Conversation'
      })
      
      const newConv = response.data
      setConversations([newConv, ...conversations])
      setCurrentConversationId(newConv.id)
      setMessages([])
    } catch (error) {
      console.error('Failed to create conversation:', error)
      // Show user-friendly error
      if (error.response?.status === 401) {
        alert('Please login to create conversations')
      } else {
        alert('Failed to create conversation. Please try again.')
      }
    }
  }

  const handleDeleteConversation = async (convId) => {
    if (!window.confirm('Delete this conversation?')) return
    
    try {
      await axios.delete(`/api/conversations/${convId}`)
      
      setConversations(conversations.filter(c => c.id !== convId))
      if (currentConversationId === convId) {
        setCurrentConversationId(null)
        setMessages([])
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error)
    }
  }

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    // Create conversation if none exists
    let convId = currentConversationId
    if (!convId) {
      try {
        const response = await axios.post('/api/conversations', {
          title: input.substring(0, 50)
        })
        convId = response.data.id
        setCurrentConversationId(convId)
        setConversations([response.data, ...conversations])
      } catch (error) {
        console.error('Failed to create conversation:', error)
        return
      }
    }

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      const response = await axios.post('/api/chat', { 
        question: userMessage,
        conversation_id: convId
      })
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: response.data.answer,
        sources: response.data.sources,
        generation_time: response.data.generation_time,
        total_time: response.data.total_time
      }])
      
      // Refresh conversation list
      loadConversations()
    } catch (error) {
      console.error('Chat error:', error)
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: '❌ Sorry, I encountered an error. Please make sure the Flask server is running!' 
      }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Sidebar */}
      <ChatSidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={setCurrentConversationId}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-primary-600 to-secondary-600 p-6 text-white">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
              <Bot className="w-7 h-7" />
            </div>
            <div>
              <h2 className="text-2xl font-bold">AI Learning Assistant</h2>
              <p className="text-sm text-white/80">Powered by Orca Mini 3B - Running Offline</p>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center text-slate-500">
              <BookOpen size={64} className="mb-4 opacity-50" />
              <p className="text-lg font-medium">Start a conversation!</p>
              <p className="text-sm mt-2">Ask me anything about your uploaded resources 🎓</p>
            </div>
          )}
          <AnimatePresence>
            {messages.map((message, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex items-start space-x-3 max-w-[80%] ${
                  message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                }`}>
                  {/* Avatar */}
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                    message.role === 'user' 
                      ? 'bg-gradient-to-br from-primary-500 to-primary-600' 
                      : 'bg-gradient-to-br from-secondary-500 to-secondary-600'
                  }`}>
                    {message.role === 'user' ? (
                      <User className="w-5 h-5 text-white" />
                    ) : (
                      <Bot className="w-5 h-5 text-white" />
                    )}
                  </div>

                  {/* Message Content */}
                  <div className={`rounded-2xl px-5 py-3 ${
                    message.role === 'user'
                      ? 'bg-gradient-to-br from-primary-500 to-primary-600 text-white'
                      : 'bg-white border-2 border-slate-100 text-slate-800'
                  }`}>
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    
                    {/* Timing Information */}
                    {message.role === 'assistant' && (message.generation_time || message.total_time) && (
                      <div className="mt-2 pt-2 border-t border-slate-200">
                        <p className="text-xs text-slate-500">
                          ⏱️ Response time: {message.generation_time?.toFixed(2)}s
                          {message.total_time && message.total_time !== message.generation_time && 
                            ` (Total: ${message.total_time?.toFixed(2)}s)`
                          }
                        </p>
                      </div>
                    )}
                    
                    {/* Sources */}
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-200">
                        <p className="text-xs font-semibold text-slate-500 mb-2">📚 Sources:</p>
                        {message.sources.map((source, i) => (
                          <div key={i} className="text-xs text-slate-600 mb-1">
                            • {typeof source === 'string' ? source : source.source || `Chunk ${source.chunk_id}`}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Loading Indicator */}
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-start space-x-3"
            >
              <div className="w-10 h-10 bg-gradient-to-br from-secondary-500 to-secondary-600 rounded-xl flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="bg-white border-2 border-slate-100 rounded-2xl px-5 py-3">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-slate-200 p-4 bg-white/50 backdrop-blur-sm">
          <form onSubmit={sendMessage} className="flex space-x-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me anything about your learning materials..."
              className="input flex-1"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="btn-primary px-6 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {isLoading ? (
                <Loader className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
              <span>Send</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
