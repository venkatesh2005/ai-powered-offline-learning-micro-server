# 🚀 React + Tailwind Frontend Setup

Beautiful modern UI for the AI Learning Hub built with React, Tailwind CSS, and Framer Motion.

## 📦 Installation

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

## 🎨 Development

Run the development server:
```bash
npm run dev
```

The React app will run on **http://localhost:3000** and automatically proxy API requests to Flask at **http://localhost:5000**.

## 🏗️ Build for Production

Build the optimized production bundle:
```bash
npm run build
```

This will create a `static/dist` folder that Flask can serve.

## 🎯 Features

- ✅ Modern, clean UI with Tailwind CSS
- ✅ Smooth animations with Framer Motion
- ✅ Fully responsive design
- ✅ Beautiful gradients and color themes
- ✅ Icon library (Lucide React)
- ✅ React Router for navigation
- ✅ Axios for API calls

## 📂 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── Navbar.jsx          # Navigation component
│   ├── pages/
│   │   ├── Home.jsx            # Landing page
│   │   ├── Chat.jsx            # AI Chat interface
│   │   ├── Resources.jsx       # Resource browser
│   │   ├── Quizzes.jsx         # Quiz interface
│   │   ├── Admin.jsx           # Admin dashboard
│   │   └── Login.jsx           # Login page
│   ├── App.jsx                 # Main app component
│   ├── main.jsx                # Entry point
│   └── index.css               # Global styles
├── index.html
├── vite.config.js
├── tailwind.config.js
└── package.json
```

## 🎨 Color Theme

- **Primary:** Blue (Cyan to Sky Blue gradient)
- **Secondary:** Purple (Violet gradient)
- **Background:** Subtle gradient from Slate to Blue
- **Accent colors:** Green, Orange, Pink for various UI elements

## 🔗 API Integration

The frontend connects to Flask backend at `http://localhost:5000`:
- `/api/chat` - Chat with AI
- `/resources` - Get resources
- `/quizzes` - Get quizzes
- `/admin` - Admin operations

## 🚢 Production Deployment

After building, Flask will serve the React app from `static/dist`. Update your Flask app to serve the React build.
