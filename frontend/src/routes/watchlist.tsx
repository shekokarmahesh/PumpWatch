import { createFileRoute, Link } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, ArrowUpRight, Bookmark, Camera, ChevronDown, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { api, listingLabel, tickerKey } from '../api/client'
import type { Ticker } from '../api/client'
import { HypeCurve } from '../components/HypeCurve'
import { ErrorNotice, Loading, scoreLabel, VerdictBadge } from '../components/shared'
import { Button, Reveal } from '../components/ui/motion'

export const Route = createFileRoute('/watchlist')({ component: WatchlistPage })
function WatchlistPage() {
  const client = useQueryClient()
  const list = useQuery({ queryKey: ['watchlist'], queryFn: api.watchlist })
  const [removed, setRemoved] = useState<Ticker | null>(null)
  const remove = useMutation({ mutationFn: (key: string) => api.watch(key, false), onSuccess: (data, key) => {
    setRemoved(list.data?.find(item => tickerKey(item.ticker) === key)?.ticker ?? null)
    client.setQueryData(['watchlist'], data)
  } })
  const undo = useMutation({ mutationFn: (key: string) => api.watch(key, true), onSuccess: data => {
    client.setQueryData(['watchlist'], data); setRemoved(null)
  } })
  const snapshot = useMutation({ mutationFn: api.snapshot, onSuccess: () => {
    for (const key of ['watchlist', 'history', 'analysis', 'health', 'past-searches']) client.invalidateQueries({ queryKey: [key] })
  } })
  if (list.isPending) return <Loading text="Opening your watchlist…" />
  return <div className="page watchlist-page"><div className="page-kicker"><span className="eyebrow">YOUR RESEARCH TRAIL</span><span className="edition mono">SAVED LOCALLY</span></div><Reveal className="watchlist-heading"><div><h1>Your watchlist.<br /><span>A clearer pattern.</span></h1><p>Watch public attention change, one day at a time.</p></div><Button className="primary" onClick={() => snapshot.mutate()} disabled={snapshot.isPending || !list.data?.length}><Camera size={16} />{snapshot.isPending ? 'Taking snapshot…' : 'Take daily snapshot'}</Button></Reveal>
    {(list.error || remove.error || undo.error || snapshot.error) && <ErrorNotice error={list.error || remove.error || undo.error || snapshot.error} onRetry={list.error ? () => list.refetch() : undefined} />}
    {removed && <div className="undo-notice"><span role="status">Removed {removed.company_name} from your watchlist.</span><Button className="secondary" disabled={undo.isPending || remove.isPending} onClick={() => undo.mutate(tickerKey(removed))}>{undo.isPending ? 'Restoring…' : 'Undo removal'}</Button></div>}
    {snapshot.data && <div className="demo-notice" role="status">{snapshot.data.rows_written} snapshots recorded. {snapshot.data.skipped > 0 && `${snapshot.data.skipped} already recorded today.`}</div>}
    {!list.data?.length ? <div className="empty-watchlist panel"><Bookmark size={32} strokeWidth={1.3} /><h2>Your research starts with one stock.</h2><p>Add a stock from its analysis to begin tracking the attention.</p><Link to="/" className="button primary">Research a stock <ArrowRight size={16} /></Link></div> : <div className="watchlist-items">{list.data.map(item => <article className="watchlist-card panel" key={tickerKey(item.ticker)}><div className="watch-stock-top"><Link to="/t/$symbol" params={{ symbol: tickerKey(item.ticker) }}><span className="company-monogram">{item.ticker.company_name[0]}</span><span><h2>{item.ticker.company_name} <ArrowUpRight size={15} /></h2><span className="mono muted">{listingLabel(item.ticker)} {item.ticker.synthetic && '· FICTIONAL DEMO'}</span></span></Link><button className="icon-button" aria-label={`Remove ${item.ticker.company_name} from watchlist`} onClick={() => remove.mutate(tickerKey(item.ticker))} disabled={remove.isPending || undo.isPending}><Trash2 size={17} /></button></div>
      {item.latest && <div className="watch-stock-stats"><VerdictBadge verdict={item.latest.verdict} /><Link to="/t/$symbol/evidence" params={{ symbol: tickerKey(item.ticker) }}>Hype <strong>{scoreLabel(item.latest.hype_score)}</strong> /100</Link><Link to="/t/$symbol/evidence" params={{ symbol: tickerKey(item.ticker) }} hash="news_coverage">Support <strong>{scoreLabel(item.latest.support_score)}</strong> /100</Link></div>}
      <details className="curve-details" open><summary>Attention over time <ChevronDown size={15} /></summary><HypeCurve stockKey={tickerKey(item.ticker)} /></details></article>)}</div>}
    <p className="watchlist-footnote">Snapshots collect three search responses per stock. Repeated snapshots on the same day are skipped. Carried observations are marked in the history.</p>
  </div>
}
