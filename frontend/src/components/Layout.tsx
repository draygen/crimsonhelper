import { ReactNode, useCallback } from 'react'
import { NavLink } from 'react-router-dom'
import {
  Sword, ScrollText, Image, Package, Users, Radio,
  Wifi, WifiOff, Camera,
} from 'lucide-react'
import { useWebSocket, WSEvent } from '../hooks/useWebSocket'
import { api } from '../lib/api'
import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'

interface Props {
  children: ReactNode
  onWsEvent: (e: WSEvent) => void
  liveEvents: WSEvent[]
}

const NAV = [
  { to: '/',            label: 'Dashboard',   icon: Sword },
  { to: '/quests',      label: 'Quests',      icon: ScrollText },
  { to: '/screenshots', label: 'Archive',     icon: Image },
  { to: '/loot',        label: 'Loot',        icon: Package },
  { to: '/npcs',        label: 'NPCs',        icon: Users },
]

export default function Layout({ children, onWsEvent, liveEvents }: Props) {
  const { connected, send } = useWebSocket(onWsEvent)
  const { data: status } = useQuery({ queryKey: ['status'], queryFn: api.status, refetchInterval: 5_000 })

  const handleCapture = useCallback(async () => {
    await api.capture()
  }, [])

  const handleVoiceToggle = useCallback(() => {
    send({ action: 'voice_toggle' })
  }, [send])

  return (
    <div className="flex h-screen overflow-hidden bg-surface-950">
      {/* Sidebar */}
      <aside className="w-52 flex-shrink-0 bg-surface-900 border-r border-surface-700 flex flex-col">
        {/* Logo */}
        <div className="px-4 py-4 border-b border-surface-700">
          <div className="flex items-center gap-2">
            <Sword className="w-5 h-5 text-crimson-500" />
            <span className="text-sm font-semibold text-slate-100 tracking-wide">CrimsonHelper</span>
          </div>
          <div className="mt-1 flex items-center gap-1.5">
            {connected
              ? <Wifi className="w-3 h-3 text-emerald-400" />
              : <WifiOff className="w-3 h-3 text-slate-500" />}
            <span className={clsx('text-xs', connected ? 'text-emerald-400' : 'text-slate-500')}>
              {connected ? 'Live' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-2.5 px-3 py-2 rounded text-sm transition-colors',
                  isActive
                    ? 'bg-crimson-700/30 text-crimson-300 border border-crimson-700/40'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-surface-700',
                )
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Status / actions */}
        <div className="px-3 py-3 border-t border-surface-700 space-y-2">
          {status && (
            <div className="text-xs text-slate-500 space-y-1">
              <div>Game: <span className={status.game_running ? 'text-emerald-400' : 'text-red-400'}>
                {status.game_running ? 'Running' : 'Not detected'}
              </span></div>
              <div>Hotkey: <span className="text-slate-300">{status.hotkey}</span></div>
              <div>OCR: <span className={status.ocr_available ? 'text-emerald-400' : 'text-red-400'}>
                {status.ocr_available ? 'Ready' : 'Not found'}
              </span></div>
            </div>
          )}
          <button
            onClick={handleCapture}
            disabled={status?.game_running === false}
            title={status?.game_running === false ? `${status.game_process} not running` : undefined}
            className={clsx(
              'w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs rounded transition-colors',
              status?.game_running === false
                ? 'bg-surface-700 text-slate-500 cursor-not-allowed'
                : 'bg-crimson-700 hover:bg-crimson-600 text-white',
            )}
          >
            <Camera className="w-3.5 h-3.5" />
            Capture Now
          </button>
          {status?.voice_available && (
            <button
              onClick={handleVoiceToggle}
              className={clsx(
                'w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs rounded transition-colors',
                status.voice_active
                  ? 'bg-emerald-700/40 text-emerald-300 border border-emerald-700/40'
                  : 'bg-surface-700 text-slate-400 hover:text-slate-100',
              )}
            >
              <Radio className="w-3.5 h-3.5" />
              {status.voice_active ? 'Voice On' : 'Voice Off'}
            </button>
          )}
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto p-6">
        {children}
      </main>

      {/* Live feed rail */}
      <aside className="w-64 flex-shrink-0 bg-surface-900 border-l border-surface-700 flex flex-col">
        <div className="px-3 py-3 border-b border-surface-700">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Live Feed</span>
        </div>
        <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1.5">
          {liveEvents.length === 0
            ? <p className="text-xs text-slate-600 text-center pt-4">Waiting for captures…</p>
            : liveEvents.map((e, i) => <EventCard key={i} event={e} />)
          }
        </div>
      </aside>
    </div>
  )
}

function EventCard({ event }: { event: WSEvent }) {
  const color: Record<string, string> = {
    ocr_complete:   'border-crimson-700/50 bg-crimson-950/30',
    capture_started:'border-surface-600 bg-surface-800/50',
    voice_command:  'border-blue-700/50 bg-blue-950/30',
    collab_message: 'border-purple-700/50 bg-purple-950/30',
    pipeline_error: 'border-red-700/50 bg-red-950/30',
  }
  const cls = color[event.type] ?? 'border-surface-600 bg-surface-800/50'

  const label: Record<string, string> = {
    ocr_complete:    event.category as string ?? 'OCR',
    capture_started: 'Capturing',
    voice_command:   'Voice',
    collab_message:  'Collab',
    pipeline_error:  'Error',
  }

  return (
    <div className={`border rounded px-2 py-1.5 animate-slide-in ${cls}`}>
      <div className="flex items-center justify-between mb-0.5">
        <span className="text-xs font-medium text-slate-300 capitalize">
          {label[event.type] ?? event.type}
        </span>
        {event.ts && (
          <span className="text-[10px] text-slate-600">
            {new Date(event.ts as string).toLocaleTimeString()}
          </span>
        )}
      </div>
      {event.quest_title && (
        <p className="text-xs text-crimson-300 truncate">{event.quest_title as string}</p>
      )}
      {event.items && (
        <p className="text-xs text-slate-400 truncate">
          {(event.items as string[]).join(', ')}
        </p>
      )}
      {event.command && (
        <p className="text-xs text-blue-300 truncate">"{event.command as string}"</p>
      )}
      {event.error && (
        <p className="text-xs text-red-400 truncate">{event.error as string}</p>
      )}
    </div>
  )
}
