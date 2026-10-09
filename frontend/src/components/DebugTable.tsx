import { useQuery } from '@tanstack/react-query'
import { Check, CodeXml, Copy } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/client'
import { ErrorNotice } from './shared'

export function DebugTable({ runId }: { runId: string }) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState<string | null>(null)
  const [copyError, setCopyError] = useState(false)
  const calls = useQuery({ queryKey: ['calls', runId], queryFn: () => api.calls(runId), enabled: open })
  async function copy(id: string, params: object) {
    try { await navigator.clipboard.writeText(JSON.stringify(params, null, 2)); setCopied(id); setCopyError(false) } catch { setCopyError(true) }
  }
  return <details className="debug-panel panel" onToggle={e => setOpen(e.currentTarget.open)}><summary><CodeXml size={18} /><span>Under the hood</span><span className="muted">SerpApi requests & credit trail</span></summary><div className="debug-body"><p>Requests are cached on disk before parsing. Credit spend is a conservative local estimate.</p>
    {calls.error && <ErrorNotice error={calls.error} />}{copyError && <p role="alert">Clipboard is unavailable. Select and copy the parameters below.</p>}
    <div className="table-scroll"><table><thead><tr><th>Engine / parameters</th><th>Source</th><th>Status</th><th>Credits</th></tr></thead><tbody>{calls.data?.map(call => <tr key={call.id}><td><div className="debug-engine"><strong>{call.engine}</strong><button aria-label={`Copy ${call.engine} parameters`} onClick={() => copy(call.id, call.params)}>{copied === call.id ? <Check size={14} /> : <Copy size={14} />}</button></div><pre>{JSON.stringify(call.params, null, 2)}</pre><small>Fetched: {call.fetched_at}</small></td><td>{call.mode}<small>{call.cache_hit ? 'Cache hit' : 'Cache miss'}</small></td><td>{call.status}{call.error && <small>{call.error}</small>}</td><td className="mono">{call.credits_spent}</td></tr>)}</tbody></table></div>
  </div></details>
}
