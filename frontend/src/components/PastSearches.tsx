import { Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { ArrowUpRight, Clock3, History, Search, X } from 'lucide-react'
import { useState } from 'react'
import { api, listingLabel, savedMatches, tickerKey } from '../api/client'
import { dateLabel, ErrorNotice, scoreLabel, VerdictBadge } from './shared'

export function PastSearches() {
  const searches = useQuery({ queryKey: ['past-searches'], queryFn: api.searches })
  const [filter, setFilter] = useState('')
  const [showAll, setShowAll] = useState(false)
  const items = savedMatches(filter, searches.data ?? [])
  const visible = showAll || filter.trim() ? items : items.slice(0, 5)
  return <section className="past-searches" id="past-searches" aria-labelledby="past-searches-title">
    <div className="section-heading"><div><h2 id="past-searches-title"><History size={20} strokeWidth={1.5} /> Past searches</h2><p>Your saved reports. Open one to pick up where you left off.</p></div><span className="neutral-chip"><Clock3 size={12} /> SAVED AUTOMATICALLY</span></div>
    {searches.isError ? <ErrorNotice error={searches.error} onRetry={() => searches.refetch()} /> : searches.isPending ? <p className="empty-inline" role="status">Loading your saved searches…</p> : !searches.data?.length ? <div className="past-empty"><History size={23} aria-hidden="true" /><div><h3>Your research starts here.</h3><p>After an analysis, the report appears here and stays available when you return.</p><a href="#stock-query" className="text-link">Search your first company <ArrowUpRight size={16} aria-hidden="true" /></a></div></div> : <>
      <div className="past-toolbar"><div className="past-filter-field"><label htmlFor="past-report-filter">Filter saved reports</label><div className="past-filter"><Search size={17} aria-hidden="true" /><input id="past-report-filter" value={filter} onChange={e => setFilter(e.target.value)} placeholder="Company name or symbol" />{filter && <button className="filter-clear" aria-label="Clear saved-report filter" onClick={() => setFilter('')}><X size={17} aria-hidden="true" /></button>}</div></div><span role="status">{items.length} saved {items.length === 1 ? 'stock' : 'stocks'}</span></div>
      <div className="past-list" id="saved-report-list">{visible.map(item => <Link key={tickerKey(item.ticker)} to="/t/$symbol" params={{ symbol: tickerKey(item.ticker) }} className="past-row" aria-label={`Open saved report for ${item.ticker.company_name}`}>
        <span className="company-monogram">{item.ticker.company_name.split(' ').map(w => w[0]).join('').slice(0, 2)}</span>
        <div className="past-company"><h3>{item.ticker.company_name}</h3><span className="mono">{listingLabel(item.ticker)}{item.synthetic && ' · FICTIONAL DEMO'}</span><span className="past-date">{dateLabel(item.run_at)} · {item.run_count} saved {item.run_count === 1 ? 'run' : 'runs'}</span></div>
        <div className="past-score"><span>Hype</span><strong>{scoreLabel(item.hype_score)}<small>/100</small></strong></div>
        <div className="past-score"><span>Support</span><strong>{scoreLabel(item.support_score)}<small>/100</small></strong></div>
        <div className="past-verdict"><VerdictBadge verdict={item.verdict} /><span>{item.signals_available}/5 hype · {item.support_available}/3 support signals</span></div>
        <ArrowUpRight className="past-arrow" size={17} />
      </Link>)}</div>
      {!items.length && <div className="empty-inline"><p>No saved report for “{filter}”.</p><div className="empty-actions"><button className="button secondary" onClick={() => setFilter('')}>Clear filter</button><a href="#stock-query" className="button secondary">Search a new company</a></div></div>}
      {!filter.trim() && items.length > 5 && <button className="button secondary saved-disclosure" aria-expanded={showAll} aria-controls="saved-report-list" onClick={() => setShowAll(!showAll)}>{showAll ? 'Show recent 5' : `View all ${items.length} saved stocks`}</button>}
      <p className="past-caption">Opening a saved report uses no search credits. Choose “Analyse again” inside a report to collect an updated sample.</p>
    </>}
  </section>
}
