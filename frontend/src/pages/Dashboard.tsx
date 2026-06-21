import { useQuery } from '@tanstack/react-query'
import { ScrollText, Package, Image, Users, Zap } from 'lucide-react'
import { api, Quest, LootEntry, Screenshot } from '../lib/api'
import { WSEvent } from '../hooks/useWebSocket'
import { formatDistanceToNow } from 'date-fns'

interface Props { events: WSEvent[] }

export default function Dashboard({ events }: Props) {
  const { data: quests }   = useQuery({ queryKey: ['quests-recent'], queryFn: () => api.quests.list({ limit: '5' }) })
  const { data: loot }     = useQuery({ queryKey: ['loot-recent'],   queryFn: () => api.loot.list({ limit: '5' }) })
  const { data: shots }    = useQuery({ queryKey: ['shots-recent'],  queryFn: () => api.screenshots.list({ limit: '6' }) })
  const { data: summary }  = useQuery({ queryKey: ['loot-summary'],  queryFn: api.loot.summary })
  const { data: npcCount } = useQuery({ queryKey: ['npc-count'],     queryFn: api.npcs.count })
  const { data: status }   = useQuery({ queryKey: ['status'],        queryFn: api.status })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-100">Dashboard</h1>
        <p className="text-sm text-slate-500">Game memory overview</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard icon={ScrollText} label="Quests" value={quests?.length ?? 0} color="crimson" />
        <StatCard icon={Package}    label="Loot entries" value={loot?.length ?? 0} color="amber" />
        <StatCard icon={Image}      label="Screenshots" value={shots?.length ?? 0} color="sky" />
        <StatCard icon={Users}      label="NPCs" value={npcCount?.count ?? 0} color="violet" />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Recent quests */}
        <section className="card p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <ScrollText className="w-4 h-4 text-crimson-400" /> Recent Quests
          </h2>
          <div className="space-y-2">
            {quests?.map(q => <QuestRow key={q.id} quest={q} />) ?? <Empty hotkey={status?.hotkey} />}
          </div>
        </section>

        {/* Top loot */}
        <section className="card p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <Package className="w-4 h-4 text-amber-400" /> Top Loot
          </h2>
          <div className="space-y-1.5">
            {summary?.slice(0, 5).map((row: { item_name: string; total: number }) => (
              <div key={row.item_name} className="flex items-center justify-between">
                <span className="text-xs text-slate-300 truncate">{row.item_name}</span>
                <span className="text-xs text-amber-400 font-medium ml-2">×{row.total}</span>
              </div>
            )) ?? <Empty />}
          </div>
        </section>
      </div>

      {/* Screenshot grid */}
      <section className="card p-4">
        <h2 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
          <Image className="w-4 h-4 text-sky-400" /> Recent Screenshots
        </h2>
        <div className="grid grid-cols-3 gap-2">
          {shots?.map(s => (
            <div key={s.id} className="relative aspect-video bg-surface-700 rounded overflow-hidden group">
              {s.thumbnail && (
                <img
                  src={api.screenshots.thumb(s.thumbnail)}
                  alt={s.filename}
                  className="w-full h-full object-cover"
                />
              )}
              <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity
                              flex items-end p-1.5">
                <span className="text-[10px] text-slate-300 truncate">{s.category}</span>
              </div>
            </div>
          )) ?? <Empty />}
        </div>
      </section>

      {/* Live events */}
      {events.length > 0 && (
        <section className="card p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <Zap className="w-4 h-4 text-yellow-400" /> Recent Events
          </h2>
          <div className="space-y-1">
            {events.slice(0, 8).map((e, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-slate-400">
                <span className="text-slate-600">{e.ts ? new Date(e.ts as string).toLocaleTimeString() : ''}</span>
                <span className="text-slate-300 capitalize">{e.type.replace(/_/g, ' ')}</span>
                {e.quest_title && <span className="text-crimson-400">{e.quest_title as string}</span>}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function StatCard({ icon: Icon, label, value, color }: {
  icon: typeof ScrollText; label: string; value: number; color: string
}) {
  const colors: Record<string, string> = {
    crimson: 'text-crimson-400', amber: 'text-amber-400',
    sky: 'text-sky-400', violet: 'text-violet-400',
  }
  return (
    <div className="card px-4 py-3">
      <div className={`${colors[color]} mb-1`}><Icon className="w-4 h-4" /></div>
      <div className="text-2xl font-semibold text-slate-100">{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  )
}

function QuestRow({ quest }: { quest: Quest }) {
  const statusColor: Record<string, string> = {
    active: 'bg-crimson-700/30 text-crimson-300',
    completed: 'bg-emerald-700/30 text-emerald-300',
    failed: 'bg-red-700/30 text-red-300',
  }
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-xs text-slate-300 truncate flex-1">{quest.title}</span>
      <span className={`badge ${statusColor[quest.status] ?? 'bg-surface-600 text-slate-400'}`}>
        {quest.status}
      </span>
    </div>
  )
}

function Empty({ hotkey }: { hotkey?: string }) {
  return <p className="text-xs text-slate-600 py-2">Nothing yet — press {hotkey ?? 'F6'} to capture</p>
}
