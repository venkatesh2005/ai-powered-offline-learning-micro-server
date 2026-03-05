import axios from 'axios'

// Configure axios to send credentials (cookies/session) with every request
axios.defaults.withCredentials = true

// Use relative base URL so requests go to whatever host the page was loaded from.
//
// Dev mode  : Vite proxy (/api → localhost:5000) handles it server-side,
//             so phones connecting to http://<server-ip>:3000 work correctly.
// Prod mode : Flask serves both the frontend (port 5000) and the API on the
//             same origin, so relative paths resolve directly.
//
// Override via .env:  VITE_API_URL=http://192.168.1.x:5000  (only needed
// when frontend and backend run on different origins in production)
const apiURL = import.meta.env.VITE_API_URL || ''
axios.defaults.baseURL = apiURL

export default axios
