import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { api } from '../api/client'
import { ErrorNotice, Loading, ResultHeader } from './shared'
import { SignalCard } from './SignalCard'
import { DebugTable } from './DebugTable'

export function EvidencePage({ stockKey }: { stockKey: string }) {
  const query = useQuery({ queryKey: ['analysis', stockKey], queryFn: () => api.latest(stockKey) })
  if (query.isPending) return <Loading />
  if (query.isError) return <div className="page"><ErrorNotice error={query.error} onRetry={() => query.refetch()} /><Link to="/">Search another company</Link></div>
  const result = query.data
  return <div className="page evidence-page"><ResultHeader result={result} /><div className="section-heading"><div><h2>The evidence, in full</h2><p>Inspect each measurement, its rule, and the observations behind it.</p></div></div>
    <nav className="signal-jump" aria-label="Jump to a signal">{result.signals.map(s => <a href={`#${s.name}`} key={s.name}>{s.label}</a>)}</nav>
    <div className="signal-grid">{result.signals.map(s => <SignalCard signal={s} key={s.name} />)}</div><DebugTable runId={result.run_id} /></div>
}
