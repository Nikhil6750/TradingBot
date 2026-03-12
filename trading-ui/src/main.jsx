import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { StrategyProvider } from './context/StrategyContext'
import './index.css'
import App from './App'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <StrategyProvider>
      <App />
    </StrategyProvider>
  </StrictMode>,
)
