import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Search, Trash2, Users, ChevronDown } from 'lucide-react'
import { api, NPC } from '../lib/api'
import { formatDistanceToNow } from 'date-fns'

export default function NPCs() {
  const [search, setSearch] = useState('')
  const qc = useQueryClient()

  const { data: npcs = [], isLoading } = useQuery({
    queryKey: ['npcs', search],
    queryFn: () => api.npcs.list({ ...(search && { q: search }) }),
  })

  const handleDelete = async (id: number) => {
    try {
      await api.npcs.delete(id)
      qc.invalidateQueries({ queryKey: ['npcs'] })
      qc.invalidateQueries({ queryKey: ['npc-count'] })
    } catch {
      // delete failed — list stays unchanged
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-100">NPC Memory</h1>
        <span className="text-xs text-slate-500">{npcs.length} NPCs</span>
      </div>

      <div className="relative">
        <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-slate-500" />
        <input
          className="input-dark pl-8"
          placeholder="Search NPCs or dialogue…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {isLoading
        ? <div className="text-xs text-slate-500 py-4">Loading…</div>
        : (
          <div className="card divide-y divide-surface-700">
            {npcs.length === 0
              ? <p className="text-xs text-slate-500 p-4 text-center">No NPCs recorded yet.</p>
              : npcs.map(n => <NPCRow key={n.id} npc={n} onDelete={handleDelete} />)
            }
          </div>
        )
      }
    </div>
  )
}

function NPCRow({ npc, onDelete }: { npc: NPC; onDelete: (id: number) => Promise<void> }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="px-4 py-3">
      <div className="flex items-start gap-3">
        <div className="w-7 h-7 rounded-full bg-violet-700/30 border border-violet-700/40
                        flex items-center justify-center flex-shrink-0 mt-0.5">
          <Users className="w-3.5 h-3.5 text-violet-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-slate-100">{npc.name || 'Unknown NPC'}</span>
            {npc.zone && <span className="badge bg-surface-600 text-slate-400">{npc.zone}</span>}
          </div>
          {npc.dialogue && !expanded && (
            <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{npc.dialogue}</p>
          )}
          <p className="text-[10px] text-slate-600 mt-1">
            Last seen {formatDistanceToNow(new Date(npc.last_seen))} ago
          </p>
        </div>
        <div className="flex items-center gap-1">
          {npc.dialogue && (
            <button onClick={() => setExpanded(v => !v)} className="btn-ghost">
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`} />
            </button>
          )}
          <button onClick={() => onDelete(npc.id)} className="btn-ghost text-red-500 hover:text-red-400">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      {expanded && npc.dialogue && (
        <div className="mt-2 ml-10 text-xs text-slate-400 bg-surface-900 rounded p-2 leading-relaxed">
          {npc.dialogue}
        </div>
      )}
    </div>
  )
}
