import { Routes, Route } from 'react-router-dom'
import { useState, useCallback } from 'react'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Quests from './pages/Quests'
import Screenshots from './pages/Screenshots'
import Loot from './pages/Loot'
import NPCs from './pages/NPCs'
import { WSEvent } from './hooks/useWebSocket'

export default function App() {
  const [events, setEvents] = useState<WSEvent[]>([])

  const handleEvent = useCallback((e: WSEvent) => {
    setEvents(prev => [e, ...prev].slice(0, 50))
  }, [])

  return (
    <Layout onWsEvent={handleEvent} liveEvents={events}>
      <Routes>
        <Route path="/"            element={<Dashboard events={events} />} />
        <Route path="/quests"      element={<Quests />} />
        <Route path="/screenshots" element={<Screenshots />} />
        <Route path="/loot"        element={<Loot />} />
        <Route path="/npcs"        element={<NPCs />} />
      </Routes>
    </Layout>
  )
}
