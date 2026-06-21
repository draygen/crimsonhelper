import { useEffect, useRef, useState, useCallback } from 'react'

export interface WSEvent {
  type: string
  ts?: string
  [key: string]: unknown
}

export function useWebSocket(onEvent: (e: WSEvent) => void) {
  const ws = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  const connect = useCallback(() => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${proto}://${location.host}/ws`
    const socket = new WebSocket(url)
    ws.current = socket

    socket.onopen = () => setConnected(true)

    socket.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data) as WSEvent
        onEventRef.current(data)
      } catch {
        // ignore parse errors
      }
    }

    socket.onclose = () => {
      setConnected(false)
      reconnectTimer.current = setTimeout(connect, 3000)
    }

    socket.onerror = () => {
      socket.close()
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      ws.current?.close()
    }
  }, [connect])

  const send = useCallback((data: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data))
    }
  }, [])

  return { connected, send }
}
