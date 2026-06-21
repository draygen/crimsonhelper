import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Search, Trash2, Youtube, ExternalLink, BarChart3 } from 'lucide-react'
import { api, LootEntry, YTGuide } from '../lib/api'
import { formatDistanceToNow } from 'date-fns'

export default function Loot() {
  const [search, setSearch] = useState('')
  const [view, setView] = useState<'list' | 'summary'>('list')
  const [guide, setGuide] = useState<{ item: string; data: YTGuide } | null>(null)
  const qc = useQueryClient()

  const { data: loot = [], isLoading: listLoading } = useQuery({
    queryKey: ['loot', search],
    queryFn: () => api.loot.list({ ...(search && { q: search }) }),
    enabled: view === 'list',
  })

  const { data: summary = [] } = useQuery({
    queryKey: ['loot-summary'],
    queryFn: api.loot.summary,
    enabled: view === 'summary',
  })

  const handleDelete = async (id: number) => {
    try {
      await api.loot.delete(id)
      qc.invalidateQueries({ queryKey: ['loot'] })
      qc.invalidateQueries({ queryKey: ['loot-summary'] })
      qc.invalidateQueries({ queryKey: ['loot-recent'] })
    } catch {
      // delete failed — list stays unchanged
    }
  }

  const handleGuide = async (item: string) => {
    try {
      const data = await api.loot.guide(item)
      setGuide({ item, data })
    } catch {
      // guide lookup failed
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-100">Loot Tracker</h1>
        <div className="flex gap-1">
          <button
            onClick={() => setView('list')}
            className={`btn-ghost ${view === 'list' ? 'text-slate-100 bg-surface-700' : ''}`}
          >
            List
          </button>
          <button
            onClick={() => setView('summary')}
            className={`btn-ghost flex items-center gap-1 ${view === 'summary' ? 'text-slate-100 bg-surface-700' : ''}`}
          >
            <BarChart3 className="w-3.5 h-3.5" /> Summary
          </button>
        </div>
      </div>

      {view === 'list' && (
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-slate-500" />
          <input
            className="input-dark pl-8"
            placeholder="Search items…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      )}

      {/* Guide panel */}
      {guide && (
        <div className="card p-4 border-amber-700/40 bg-amber-950/20">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-amber-300">Guides: {guide.item}</span>
            <button onClick={() => setGuide(null)} className="btn-ghost text-xs">✕</button>
          </div>
          <a href={guide.data.search_url} target="_blank" rel="noreferrer"
             className="flex items-center gap-1.5 text-xs text-amber-400 hover:text-amber-300 mb-2">
            <Youtube className="w-3.5 h-3.5" /> Search YouTube <ExternalLink className="w-3 h-3" />
          </a>
          {guide.data.results.map(r => (
            <a key={r.url} href={r.url} target="_blank" rel="noreferrer"
               className="flex items-center gap-2 py-1.5 text-xs text-slate-400 hover:text-slate-200">
              {r.thumbnail && <img src={r.thumbnail} alt="" className="w-14 h-8 rounded object-cover" />}
              <div>
                <p className="text-slate-200 line-clamp-1">{r.title}</p>
                <p className="text-slate-500">{r.channel}</p>
              </div>
            </a>
          ))}
        </div>
      )}

      {view === 'list' && listLoading && <div className="text-xs text-slate-500 py-4">Loading…</div>}

      {view === 'summary' && (
        <div className="card divide-y divide-surface-700">
          {summary.length === 0
            ? <p className="text-xs text-slate-500 p-4 text-center">No loot tracked yet.</p>
            : summary.map(row => (
              <div key={row.item_name} className="px-4 py-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-200">{row.item_name}</span>
                  <button
                    onClick={() => handleGuide(row.item_name)}
                    className="btn-ghost text-amber-500 hover:text-amber-400 py-0.5 px-1"
                  >
                    <Youtube className="w-3.5 h-3.5" />
                  </button>
                </div>
                <span className="text-sm font-semibold text-amber-400">×{row.total}</span>
              </div>
            ))
          }
        </div>
      )}

      {view === 'list' && !listLoading && (
        <div className="card divide-y divide-surface-700">
          {loot.length === 0
            ? <p className="text-xs text-slate-500 p-4 text-center">No loot recorded yet.</p>
            : loot.map(entry => <LootRow key={entry.id} entry={entry} onDelete={handleDelete} onGuide={handleGuide} />)
          }
        </div>
      )}
    </div>
  )
}

function LootRow({ entry, onDelete, onGuide }: {
  entry: LootEntry
  onDelete: (id: number) => Promise<void>
  onGuide: (item: string) => Promise<void>
}) {
  return (
    <div className="px-4 py-2.5 flex items-center gap-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-200 font-medium truncate">{entry.item_name}</span>
          <span className="badge bg-amber-700/30 text-amber-300">×{entry.quantity}</span>
          {entry.zone && <span className="badge bg-surface-600 text-slate-400">{entry.zone}</span>}
        </div>
        <p className="text-[10px] text-slate-600 mt-0.5">
          {formatDistanceToNow(new Date(entry.captured_at))} ago
        </p>
      </div>
      <div className="flex items-center gap-1">
        <button onClick={() => onGuide(entry.item_name)} className="btn-ghost text-amber-500">
          <Youtube className="w-3.5 h-3.5" />
        </button>
        <button onClick={() => onDelete(entry.id)} className="btn-ghost text-red-500 hover:text-red-400">
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )
}
