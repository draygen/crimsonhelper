import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Search, Trash2, X } from 'lucide-react'
import { api, Screenshot } from '../lib/api'
import { formatDistanceToNow } from 'date-fns'

const CATEGORIES = ['', 'quest', 'loot', 'npc', 'general']

export default function Screenshots() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [selected, setSelected] = useState<Screenshot | null>(null)
  const qc = useQueryClient()

  const { data: shots = [], isLoading } = useQuery({
    queryKey: ['screenshots', search, category],
    queryFn: () => api.screenshots.list({
      ...(search   && { q: search }),
      ...(category && { category }),
    }),
  })

  const handleDelete = async (id: number) => {
    try {
      await api.screenshots.delete(id)
      qc.invalidateQueries({ queryKey: ['screenshots'] })
      qc.invalidateQueries({ queryKey: ['shots-recent'] })
      if (selected?.id === id) setSelected(null)
    } catch {
      // delete failed — selection and list stay unchanged
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-100">Screenshot Archive</h1>
        <span className="text-xs text-slate-500">{shots.length} screenshots</span>
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-slate-500" />
          <input
            className="input-dark pl-8"
            placeholder="Search OCR text…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select
          className="input-dark w-36"
          value={category}
          onChange={e => setCategory(e.target.value)}
        >
          {CATEGORIES.map(c => (
            <option key={c} value={c}>{c || 'All types'}</option>
          ))}
        </select>
      </div>

      {/* Lightbox */}
      {selected && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-6"
          onClick={() => setSelected(null)}
        >
          <div
            className="card max-w-4xl w-full max-h-[90vh] overflow-auto p-4"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-3">
              <div>
                <span className="text-sm font-medium text-slate-200">{selected.filename}</span>
                <div className="flex gap-2 mt-1">
                  <span className="badge bg-surface-600 text-slate-400 capitalize">{selected.category}</span>
                  {selected.zone && <span className="badge bg-surface-600 text-slate-400">{selected.zone}</span>}
                </div>
              </div>
              <button onClick={() => setSelected(null)} className="btn-ghost">
                <X className="w-4 h-4" />
              </button>
            </div>
            <img
              src={api.screenshots.url(selected.filename)}
              alt={selected.filename}
              className="w-full rounded"
              loading="lazy"
            />
            {selected.ocr_text && (
              <div className="mt-3">
                <p className="text-xs text-slate-500 mb-1">OCR Text</p>
                <pre className="text-xs text-slate-400 bg-surface-900 rounded p-3 overflow-auto max-h-40 whitespace-pre-wrap">
                  {selected.ocr_text}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Grid */}
      {isLoading
        ? <div className="text-xs text-slate-500 py-4">Loading…</div>
        : (
          <div className="grid grid-cols-3 gap-3">
            {shots.length === 0
              ? <p className="col-span-3 text-xs text-slate-500 text-center py-8">No screenshots yet.</p>
              : shots.map(s => (
                <div
                  key={s.id}
                  className="card overflow-hidden cursor-pointer group hover:border-crimson-700/50 transition-colors"
                  onClick={() => setSelected(s)}
                >
                  <div className="aspect-video bg-surface-700 relative">
                    {s.thumbnail
                      ? <img src={api.screenshots.thumb(s.thumbnail)} alt="" className="w-full h-full object-cover" loading="lazy" />
                      : <div className="w-full h-full flex items-center justify-center text-slate-600 text-xs">No preview</div>
                    }
                    <div className="absolute top-1 left-1">
                      <span className="badge bg-black/70 text-slate-300 capitalize">{s.category}</span>
                    </div>
                  </div>
                  <div className="px-2 py-1.5 flex items-center justify-between">
                    <span className="text-[10px] text-slate-500 truncate">
                      {formatDistanceToNow(new Date(s.captured_at))} ago
                    </span>
                    <button
                      onClick={e => { e.stopPropagation(); handleDelete(s.id) }}
                      className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-400 transition-opacity p-0.5"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))
            }
          </div>
        )
      }
    </div>
  )
}
