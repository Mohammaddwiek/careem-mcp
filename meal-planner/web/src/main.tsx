import '@fontsource-variable/plus-jakarta-sans'
import '@fontsource-variable/inter'
import '@fontsource/jetbrains-mono/500.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './styles/tokens.css'
import './styles/app.css'
import './styles/wizard.css'
import './styles/phone.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
