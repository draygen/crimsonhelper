import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Search, Trash2, ExternalLink, Youtube, ChevronDown } from 'lucide-react'
import { api, Quest, YTGuide } from '../lib/api'
import { formatDistanceToNow } from 'date-fns'

export default function Quests() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [guideData, setGuideData] = useState<{ quest: Quest; guide: YTGuide } | null>(null)
  const qc = useQueryClient()

  const { data: quests = [], isLoading } = useQuery({
    queryKey: ['quests', search, status],
    queryFn: () => api.quests.list({
      ...(search && { q: search }),
      ...(status && { status }),
    }),
  })

  const handleDelete = async (id: number) => {
    try {
      await api.quests.delete(id)
      qc.invalidateQueries({ queryKey: ['quests'] })
      qc.invalidateQueries({ queryKey: ['quests-recent'] })
    } catch {
      // delete failed — list stays unchanged
    }
  }

  const handleGuide = async (quest: Quest) => {
    try {
      const guide = await api.quests.guide(quest.id)
      setGuideData({ quest, guide })
    } catch {
      // guide lookup failed — nothing to show
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-100">Quest Memory</h1>
        <span className="text-xs text-slate-500">{quests.length} quests</span>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-slate-500" />
          <input
            className="input-dark pl-8"
            placeholder="Search quests…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select
          className="input-dark w-36"
          value={status}
          onChange={e => setStatus(e.target.value)}
        >
          <option value="">All status</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Guide modal */}
      {guideData && (
        <div className="card p-4 border-crimson-700/40 bg-crimson-950/20">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-crimson-300">
              Guides for: {guideData.quest.title}
            </span>
            <button onClick={() => setGuideData(null)} className="btn-ghost text-xs">✕</button>
          </div>
          <a
            href={guideData.guide.search_url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 text-xs text-crimson-400 hover:text-crimson-300 mb-3"
          >
            <Youtube className="w-3.5 h-3.5" /> Search YouTube <ExternalLink className="w-3 h-3" />
          </a>
          {guideData.guide.results.map(r => (
            <a
              key={r.url}
              href={r.url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 py-1.5 hover:text-slate-100 text-slate-400 text-xs"
            >
              {r.thumbnail && <img src={r.thumbnail} alt="" className="w-16 h-9 rounded object-cover" />}
              <div>
                <p className="text-slate-200 line-clamp-1">{r.title}</p>
                <p className="text-slate-500">{r.channel}</p>
              </div>
            </a>
          ))}
        </div>
      )}

      {/* Table */}
      {isLoading
        ? <div className="text-xs text-slate-500 py-4">Loading…</div>
        : (
          <div className="card divide-y divide-surface-700">
            {quests.length === 0
              ? <p className="text-xs text-slate-500 p-4 text-center">No quests found.</p>
              : quests.map(q => <QuestRow key={q.id} quest={q} onDelete={handleDelete} onGuide={handleGuide} />)
            }
          </div>
        )
      }
    </div>
  )
}

function QuestRow({ quest, onDelete, onGuide }: {
  quest: Quest
  onDelete: (id: number) => Promise<void>
  onGuide: (q: Quest) => Promise<void>
}) {
  const [expanded, setExpanded] = useState(false)
  const statusColor: Record<string, string> = {
    active: 'bg-crimson-700/30 text-crimson-300',
    completed: 'bg-emerald-700/30 text-emerald-300',
    failed: 'bg-red-700/30 text-red-300',
  }

  return (
    <div className="px-4 py-3">
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-slate-100 font-medium truncate">{quest.title}</span>
            <span className={`badge ${statusColor[quest.status] ?? 'bg-surface-600 text-slate-400'}`}>
              {quest.status}
            </span>
            {quest.zone && (
              <span className="badge bg-surface-600 text-slate-400">{quest.zone}</span>
            )}
          </div>
          {quest.description && (
            <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{quest.description}</p>
          )}
          <p className="text-[10px] text-slate-600 mt-1">
            {formatDistanceToNow(new Date(quest.captured_at))} ago
          </p>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button onClick={() => onGuide(quest)} className="btn-ghost" title="Find YouTube guide">
            <Youtube className="w-3.5 h-3.5" />
          </button>
          {quest.description && (
            <button onClick={() => setExpanded(v => !v)} className="btn-ghost">
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`} />
            </button>
          )}
          <button onClick={() => onDelete(quest.id)} className="btn-ghost text-red-500 hover:text-red-400">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      {expanded && quest.description && (
        <p className="text-xs text-slate-400 mt-2 pl-0 leading-relaxed">{quest.description}</p>
      )}
    </div>
  )
}
