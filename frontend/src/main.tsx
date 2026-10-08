import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/sora'
import '@fontsource-variable/inter'
import './index.css'
import App from './App.tsx'

// restore saved theme (default: light)
try {
  if (localStorage.getItem('theme') === 'dark') document.documentElement.classList.add('dark')
} catch { /* storage unavailable */ }

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
