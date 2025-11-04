import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FileText, Search, Filter, Upload, Download, X, Loader, Eye, ExternalLink, Trash2 } from 'lucide-react'
import axios from '../api/axios'

export default function Resources() {
  const [resources, setResources] = useState([])
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(true)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showViewerModal, setShowViewerModal] = useState(false)
  const [selectedResource, setSelectedResource] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadData, setUploadData] = useState({
    title: '',
    description: '',
    category: 'pdf',
    file: null
  })

  const user = JSON.parse(localStorage.getItem('user') || 'null')

  useEffect(() => {
    fetchResources()
  }, [search, category])

  const fetchResources = async () => {
    try {
      const response = await axios.get(`/api/resources?search=${search}&category=${category}`)
      setResources(response.data.resources || [])
    } catch (error) {
      console.error('Error fetching resources:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!uploadData.file) {
      alert('Please select a file')
      return
    }

    setUploading(true)
    const formData = new FormData()
    formData.append('file', uploadData.file)
    formData.append('title', uploadData.title || uploadData.file.name)
    formData.append('description', uploadData.description)
    formData.append('category', uploadData.category)

    try {
      await axios.post('/api/admin/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      
      setShowUploadModal(false)
      setUploadData({ title: '', description: '', category: 'pdf', file: null })
      fetchResources() // Refresh list
      alert('Resource uploaded successfully!')
    } catch (error) {
      console.error('Upload error:', error)
      alert(error.response?.data?.error || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleResourceClick = (resource) => {
    setSelectedResource(resource)
    setShowViewerModal(true)
  }

  const handleDownload = (resource, e) => {
    e.stopPropagation()
    window.open(`http://localhost:5000/api/resources/${resource.id}/download`, '_blank')
  }

  const handleDelete = async (resource, e) => {
    e.stopPropagation()
    if (!confirm(`Are you sure you want to delete "${resource.title}"?`)) {
      return
    }

    try {
      await axios.delete(`/api/admin/resource/${resource.id}/delete`)
      alert('Resource deleted successfully!')
      fetchResources() // Refresh list
    } catch (error) {
      console.error('Delete error:', error)
      alert(error.response?.data?.error || 'Delete failed')
    }
  }

  const categories = ['All', 'PDF', 'Video', 'Document', 'Presentation']

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold mb-2 text-slate-800">Learning Resources</h1>
          <p className="text-slate-600">Browse and search through your learning materials</p>
        </motion.div>

        {/* Search and Filter */}
        <div className="card p-6 mb-8">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search resources..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input pl-12"
              />
            </div>
            
            <div className="flex gap-2">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCategory(cat === 'All' ? '' : cat.toLowerCase())}
                  className={`px-4 py-2 rounded-lg font-medium transition-all ${
                    (cat === 'All' && !category) || category === cat.toLowerCase()
                      ? 'bg-primary-600 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Upload Button - Only for Teachers */}
        {user?.is_admin && (
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowUploadModal(true)}
            className="btn-primary mb-8 flex items-center space-x-2"
          >
            <Upload className="w-5 h-5" />
            <span>Upload New Resource</span>
          </motion.button>
        )}

        {/* Upload Modal */}
        <AnimatePresence>
          {showUploadModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
              onClick={() => !uploading && setShowUploadModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="card p-8 max-w-md w-full"
              >
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-bold text-slate-800">Upload Resource</h2>
                  <button
                    onClick={() => !uploading && setShowUploadModal(false)}
                    className="text-slate-400 hover:text-slate-600"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>

                <form onSubmit={handleUpload} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">File</label>
                    <input
                      type="file"
                      accept=".pdf,.doc,.docx,.ppt,.pptx,.txt"
                      onChange={(e) => setUploadData({ ...uploadData, file: e.target.files[0] })}
                      className="input"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Title (Optional)</label>
                    <input
                      type="text"
                      value={uploadData.title}
                      onChange={(e) => setUploadData({ ...uploadData, title: e.target.value })}
                      className="input"
                      placeholder="Leave empty to use filename"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Description</label>
                    <textarea
                      value={uploadData.description}
                      onChange={(e) => setUploadData({ ...uploadData, description: e.target.value })}
                      className="input"
                      rows="3"
                      placeholder="Describe this resource..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Category</label>
                    <select
                      value={uploadData.category}
                      onChange={(e) => setUploadData({ ...uploadData, category: e.target.value })}
                      className="input"
                    >
                      <option value="pdf">PDF</option>
                      <option value="document">Document</option>
                      <option value="presentation">Presentation</option>
                      <option value="video">Video</option>
                    </select>
                  </div>

                  <button
                    type="submit"
                    disabled={uploading || !uploadData.file}
                    className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {uploading ? (
                      <span className="flex items-center justify-center">
                        <Loader className="animate-spin mr-2 w-5 h-5" />
                        Uploading...
                      </span>
                    ) : (
                      'Upload Resource'
                    )}
                  </button>
                </form>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Resources Grid */}
        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="loading-spinner w-12 h-12"></div>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {resources.map((resource, idx) => (
              <motion.div
                key={resource.id}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                whileHover={{ y: -5 }}
                onClick={() => handleResourceClick(resource)}
                className="card p-6 cursor-pointer group"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                    <FileText className="w-6 h-6 text-white" />
                  </div>
                  <span className="px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-xs font-semibold">
                    {resource.category}
                  </span>
                </div>
                
                <h3 className="font-bold text-lg mb-2 text-slate-800 group-hover:text-primary-600 transition-colors">
                  {resource.title}
                </h3>
                <p className="text-sm text-slate-600 mb-4">{resource.description}</p>
                
                <div className="flex items-center justify-between text-sm text-slate-500">
                  <span>{resource.uploaded_at}</span>
                  <div className="flex items-center space-x-2">
                    <Eye className="w-4 h-4" />
                    <button
                      onClick={(e) => handleDownload(resource, e)}
                      className="p-1 hover:bg-slate-100 rounded transition-colors"
                      title="Download"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                    {user?.is_admin && (
                      <button
                        onClick={(e) => handleDelete(resource, e)}
                        className="p-1 hover:bg-red-100 hover:text-red-600 rounded transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* PDF Viewer Modal */}
        <AnimatePresence>
          {showViewerModal && selectedResource && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"
              onClick={() => setShowViewerModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-white rounded-2xl w-full max-w-6xl h-[90vh] flex flex-col"
              >
                <div className="flex justify-between items-center p-6 border-b border-slate-200">
                  <div>
                    <h2 className="text-2xl font-bold text-slate-800">{selectedResource.title}</h2>
                    <p className="text-sm text-slate-600">{selectedResource.description}</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={(e) => handleDownload(selectedResource, e)}
                      className="btn-secondary flex items-center space-x-2"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download</span>
                    </button>
                    <button
                      onClick={() => setShowViewerModal(false)}
                      className="text-slate-400 hover:text-slate-600 p-2"
                    >
                      <X className="w-6 h-6" />
                    </button>
                  </div>
                </div>

                <div className="flex-1 overflow-hidden">
                  {selectedResource.category === 'pdf' ? (
                    <iframe
                      src={`http://localhost:5000/api/resources/${selectedResource.id}/view`}
                      className="w-full h-full"
                      title={selectedResource.title}
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center">
                        <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                        <p className="text-slate-600 mb-4">Preview not available for this file type</p>
                        <button
                          onClick={(e) => handleDownload(selectedResource, e)}
                          className="btn-primary flex items-center space-x-2 mx-auto"
                        >
                          <Download className="w-4 h-4" />
                          <span>Download to View</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {!loading && resources.length === 0 && (
          <div className="text-center py-20">
            <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-slate-600 mb-2">No resources found</h3>
            <p className="text-slate-500">Upload your first learning resource to get started!</p>
          </div>
        )}
      </div>
    </div>
  )
}
