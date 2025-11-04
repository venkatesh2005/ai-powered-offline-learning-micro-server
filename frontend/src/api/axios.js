import axios from 'axios'

// Configure axios to send credentials (cookies/session) with every request
axios.defaults.withCredentials = true

// Use environment variable or detect if on local network
// For mobile access, use your computer's IP: 10.50.173.74
const apiURL = import.meta.env.VITE_API_URL || 'http://10.50.173.74:5000'
axios.defaults.baseURL = apiURL

export default axios
