import { Link, useRouterState } from '@tanstack/react-router'
import { ArrowLeft, ArrowUpRight, CircleHelp, LoaderCircle } from 'lucide-react'
import { motion } from 'motion/react'
import type { Analysis } from '../api/client'
import { listingLabel } from '../api/client'
import { springLayout } from './ui/motion'

export function VerdictBadge({ verdict }: { verdict: string }) {
  return <span className={`verdict verdict-${verdict.toLowerCase().replaceAll(' ', '-')}`}><span className="verdict-dot" />{verdict === 'Insufficient data' ? verdict : `${verdict} attention risk`}</span>
}

export function ErrorNotice({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return <div className="error-notice" role="alert"><CircleHelp size={18} aria-hidden="true" /><span>{error instanceof Error ? error.message : 'Unable to load data. Please try again.'}</span>{onRetry && <button type="button" className="button secondary" onClick={onRetry}>Try again</button>}</div>
}

export function Loading({ text = 'Reading the signals…' }: { text?: string }) {
  return <div className="loading-state" role="status"><LoaderCircle className="spin" size={26} /><h2>{text}</h2><p>Collecting public attention. Keeping the evidence.</p></div>
}

export const dateLabel = (value: string) => new Date(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata' })
export const scoreLabel = (value?: number | null) => value == null ? '—' : Math.round(value).toString()

export function ResultHeader({ result }: { result: Analysis }) {
  const evidenceActive = useRouterState({ select: state => state.location.pathname.endsWith('/evidence') })
  return <>
    <Link to="/" hash="stock-query" className="back-link"><ArrowLeft size={16} aria-hidden="true" /> Search another company</Link>
    <div className="result-heading"><div><div className="eyebrow">STOCK RESEARCH <span>/</span> {result.ticker.exchange === 'BOM' ? 'BSE' : result.ticker.exchange}</div><h1>{result.ticker.company_name}</h1>
      <div className="stock-meta"><span className="mono">{listingLabel(result.ticker)}</span>{result.ticker.is_sme && <span className="neutral-chip">{result.synthetic ? 'Demo SME' : 'SME listing'}</span>}
      <span>Data as of {dateLabel(result.data_as_of)}</span></div></div><VerdictBadge verdict={result.verdict} /></div>
    {result.synthetic && <div className="demo-notice"><CircleHelp size={16} /><span>Fictional demo scenario. Observations, registry matches and evidence links are simulated.</span><span className="mono">REPLAY</span></div>}
    <nav className="result-tabs" aria-label="Analysis views"><Link to="/t/$symbol" params={{ symbol: `${result.ticker.symbol}:${result.ticker.exchange}` }} activeOptions={{ exact: true }}>{!evidenceActive && <motion.span className="tab-indicator" layoutId="report-tabs" transition={springLayout} />}<span>Overview</span></Link>
      <Link to="/t/$symbol/evidence" params={{ symbol: `${result.ticker.symbol}:${result.ticker.exchange}` }}>{evidenceActive && <motion.span className="tab-indicator" layoutId="report-tabs" transition={springLayout} />}<span>Evidence</span> <ArrowUpRight size={13} /></Link></nav>
  </>
}
