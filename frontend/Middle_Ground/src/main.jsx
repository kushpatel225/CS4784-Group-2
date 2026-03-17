import React, { useState } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import PersonScreen from './pages/PersonScreen.jsx'
import OmniscientScreen from './pages/OmniscientScreen.jsx'
import './index.css'

function Root() {
  const [page, setPage] = useState('home')

  if (page === 'a') return <PersonScreen person="a" onBack={() => setPage('home')} />
  if (page === 'b') return <PersonScreen person="b" onBack={() => setPage('home')} />
  if (page === 'omniscient') return <OmniscientScreen onBack={() => setPage('home')} />
  return <App onNavigate={setPage} />
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
)