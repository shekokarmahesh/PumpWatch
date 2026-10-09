import { Link } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, ArrowUpRight, Bookmark, Check, ChevronDown, Download, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/client'
import { ErrorNotice, Loading, ResultHeader, scoreLabel } from './shared'
import { PromoterChip } from './PromoterChip'
import { AnimatedNumber, Button, Reveal } from './ui/motion'
import { HypeCurve } from './HypeCurve'
import { motion, useReducedMotion } from 'motion/react'

export function Overview({ stockKey }: { stockKey: string }) {
  const reduce = useReducedMotion()
  const [showHistory, setShowHistory] = useState(false)
  const client = useQueryClient()
  const analysis = useQuery({ queryKey: ['analysis', stockKey], queryFn: () => api.latest(stockKey) })
  const watchlist = useQuery({ queryKey: ['watchlist'], queryFn: api.watchlist })
  const watched = watchlist.data?.some(w => `${w.ticker.symbol}:${w.ticker.exchange}` === stockKey)
  const watch = useMutation({ mutationFn: () => api.watch(stockKey, !watched), onSuccess: list => client.setQueryData(['watchlist'], list) })
  const refresh = useMutation({ mutationFn: () => api.analyse(stockKey), onSuccess: result => {
    client.setQueryData(['analysis', stockKey], result); client.invalidateQueries({ queryKey: ['health'] }); client.invalidateQueries({ queryKey: ['watchlist'] }); client.invalidateQueries({ queryKey: ['history', stockKey] }); client.invalidateQueries({ queryKey: ['past-searches'] })
  } })
  if (analysis.isPending) return <Loading />
  if (analysis.isError) return <div className="page"><ErrorNotice error={analysis.error} onRetry={() => analysis.refetch()} /><Link to="/" className="button secondary">Search another company</Link></div>
  const result = analysis.data
  return <div className="page result-page"><ResultHeader result={result} />
    {(result.signals_available < 5 || result.support_available < 3) && <div className="coverage-notice"><div><strong>{result.verdict === 'Insufficient data' ? 'Partial coverage — a verdict is unavailable.' : 'This report has partial coverage.'}</strong><p>{result.signals_available} of 5 hype signals and {result.support_available} of 3 support signals have usable evidence. Scores use those signals only; unavailable measurements stay unknown.</p></div><Link className="text-link" to="/t/$symbol/evidence" params={{ symbol: stockKey }}>Inspect sources <ArrowRight size={14} /></Link></div>}
    <Reveal className="overview-grid"><section className="verdict-card panel"><div className="section-heading"><span className="eyebrow">THE ATTENTION PICTURE</span><span className="neutral-chip">RULE-BASED</span></div>
      <h2>{result.verdict === 'High' ? 'Attention is outrunning support.' : result.verdict === 'Elevated' ? 'The attention deserves a closer look.' : result.verdict === 'Low' ? 'Attention is broadly in step.' : 'There’s more to learn here.'}</h2>
      <p className="verdict-description">{result.verdict === 'Insufficient data' ? 'There isn’t enough usable evidence to establish an attention-risk verdict.' : 'A comparison of public hype and supporting signals. Read the sources before drawing a conclusion.'}</p>
      {([{ side: 'hype', label: 'Hype score', value: result.hype_score, note: 'How quickly public attention is building' },
        { side: 'support', label: 'Fundamentals & support', value: result.support_score, note: 'News, financial trends and registered names' }] as const).map(m => <Link key={m.side} to="/t/$symbol/evidence" params={{ symbol: stockKey }} hash={m.side === 'hype' ? 'video_velocity' : 'news_coverage'} className={`score-meter score-${m.side}`}><div className="score-top"><span>{m.label} <ArrowUpRight size={12} /></span><span className={`score-number ${m.value == null ? 'score-unknown' : ''}`}>{m.value == null ? 'Unknown' : <><AnimatedNumber value={m.value} /><small>/100</small></>}</span></div><div className="meter-track"><motion.span style={{ transformOrigin: 'left', width: '100%' }} initial={reduce ? false : { scaleX: 0 }} animate={{ scaleX: (m.value ?? 0) / 100 }} transition={{ duration: reduce ? 0 : 0.9, ease: [0.16, 1, 0.3, 1] }} /></div><p>{m.note}</p></Link>)}
      <div className="coverage"><span>{result.signals_available} of 5 hype signals</span><span>{result.support_available} of 3 support signals</span></div>
    </section><aside className="research-card panel"><span className="eyebrow">YOUR RESEARCH TRAIL</span><span className="research-icon"><Bookmark size={24} strokeWidth={1.4} /></span><h3>Keep the stock in view.</h3><p>Save it to your watchlist. Daily snapshots help you see attention change over time.</p><Button className={watched ? 'secondary watch-toggle' : 'primary watch-toggle'} onClick={() => watch.mutate()} disabled={watch.isPending} aria-pressed={Boolean(watched)}>{watch.isPending ? 'Updating watchlist…' : watched ? <><Check size={16} aria-hidden="true" />Remove from watchlist</> : <><Bookmark size={16} aria-hidden="true" />Add to watchlist</>}</Button>
      {watch.isSuccess && <span className="watch-feedback" role="status">{watched ? 'Saved to your watchlist.' : 'Removed from your watchlist.'}</span>}
      <details className="export-actions"><summary><Download size={17} aria-hidden="true" /> Download report <ChevronDown size={16} aria-hidden="true" /></summary><a href={`/api/runs/${result.run_id}/export?format=md`} className="export-link">Markdown report <ArrowUpRight size={15} /></a><a href={`/api/runs/${result.run_id}/export?format=json`} className="export-link">JSON data <ArrowUpRight size={15} /></a></details>
      <Button className="text-button" onClick={() => refresh.mutate()} disabled={refresh.isPending}><RefreshCw size={14} className={refresh.isPending ? 'spin' : ''} />{refresh.isPending ? 'Analysing…' : 'Analyse again'}</Button></aside></Reveal>
    {(watch.error || refresh.error) && <ErrorNotice error={watch.error || refresh.error} />}
    <section className="reasons-section"><div className="section-heading"><div><h2>What’s driving the attention</h2><p>The highest scoring hype signals, with their sources attached.</p></div><Link className="text-link" to="/t/$symbol/evidence" params={{ symbol: stockKey }}>All evidence <ArrowRight size={15} /></Link></div>
      {result.reasons.length ? <div className="reason-list">{result.reasons.map((reason, i) => <Link to="/t/$symbol/evidence" params={{ symbol: stockKey }} hash={reason.signal_name} key={reason.signal_name} className="reason-row"><span className="reason-index mono">0{i+1}</span><div><h3>{reason.title}</h3><p>{reason.explanation}</p></div><div className="reason-value"><strong>{scoreLabel(reason.score)}<small>/100</small></strong><span>{reason.evidence.length} sources</span></div><ArrowUpRight size={18} /></Link>)}</div> : <div className="empty-inline">No supported hype reasons were found.</div>}</section>
    <section className="history-panel panel"><button className="history-toggle" aria-expanded={showHistory} aria-controls="report-history" onClick={() => setShowHistory(!showHistory)}><span><strong>Attention over time</strong><small>View saved observations and the 30-day history</small></span><ChevronDown size={19} aria-hidden="true" /></button><div id="report-history" hidden={!showHistory}>{showHistory && <HypeCurve stockKey={stockKey} />}</div></section>
    <section className="promoter-section"><div className="section-heading"><div><h2>Names behind the attention</h2><p>Registry name matching is a research lead. It does not confirm identity or conduct.</p></div><span className="neutral-chip">{result.synthetic ? 'DEMO REGISTRY' : 'SEBI NAME CHECK'}</span></div>
      <div className="promoter-grid">{result.promoters.map(p => <PromoterChip key={p.name} promoter={p} />)}{!result.promoters.length && <p>No promoter names found in the available evidence.</p>}</div></section>
    <details className="analysis-notes"><summary>Data coverage & limitations</summary><ul>{result.warnings.map(w => <li key={w}>{w}</li>)}</ul><p>Run recorded: {new Date(result.run_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })} IST. Low attention risk does not mean a stock is safe.</p></details>
  </div>
}
