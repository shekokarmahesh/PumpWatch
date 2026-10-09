import { useMutation } from '@tanstack/react-query'
import { ArrowRight, Clock3, LoaderCircle, Search, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { api, listingLabel, savedMatches, searchTerm, tickerKey } from '../api/client'
import type { PastSearch, Ticker } from '../api/client'
import { ErrorNotice } from './shared'
import { Button } from './ui/motion'

type Props = {
  replay: boolean
  saved: PastSearch[]
  analysing: boolean
  analysisError: unknown
  onAnalyse: (key: string) => void
  onOpenReport: (key: string) => void
  onReset: () => void
}

export function StockSearch({ replay, saved, analysing, analysisError, onAnalyse, onOpenReport, onReset }: Props) {
  const [query, setQuery] = useState('')
  const [candidates, setCandidates] = useState<Ticker[]>([])
  const [expanded, setExpanded] = useState(false)
  const [active, setActive] = useState(-1)
  const input = useRef<HTMLInputElement>(null)
  const firstCandidate = useRef<HTMLButtonElement>(null)
  const currentRequest = useRef<AbortController | null>(null)
  const selectedKey = useRef<string | null>(null)
  const recent = saved.filter(item => item.synthetic === replay)
  const suggestions = savedMatches(query, recent).slice(0, 5)
  const showSuggestions = expanded && suggestions.length > 0 && !candidates.length && !analysing
  const resolve = useMutation({
    mutationFn: async ({ term, controller }: { term: string; controller: AbortController }) => {
      const data = await api.resolve(term, controller.signal)
      if (!data.length) throw new Error('No Indian company matched this search. Try a fuller name.')
      return data
    },
    onSuccess: (data, variables) => {
      if (!variables.controller.signal.aborted) { setCandidates(data); setExpanded(false) }
    },
    onError: (_error, variables) => { if (!variables.controller.signal.aborted) input.current?.focus() },
  })
  useEffect(() => () => currentRequest.current?.abort(), [])
  useEffect(() => { if (candidates.length) firstCandidate.current?.focus() }, [candidates])
  useEffect(() => {
    if (showSuggestions && active >= 0) document.getElementById(`saved-stock-option-${active}`)?.scrollIntoView?.({ block: 'nearest' })
  }, [active, showSuggestions])

  function edit(value: string) {
    currentRequest.current?.abort()
    resolve.reset(); onReset()
    setQuery(value); setCandidates([]); setExpanded(true); setActive(-1)
  }
  function open(item: PastSearch) {
    currentRequest.current?.abort(); setExpanded(false)
    onOpenReport(tickerKey(item.ticker))
  }
  function search() {
    const term = searchTerm(query)
    if (!term || analysing || resolve.isPending) return
    const exact = recent.filter(item => [item.ticker.company_name, item.ticker.symbol, tickerKey(item.ticker)].some(name => searchTerm(name) === term))
    if (exact.length === 1) { open(exact[0]); return }
    currentRequest.current?.abort()
    const controller = new AbortController(); currentRequest.current = controller
    setCandidates([]); setExpanded(false); onReset()
    resolve.mutate({ term: query.trim(), controller })
  }
  function keydown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') { setExpanded(false); setActive(-1); return }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      if (!suggestions.length) return
      event.preventDefault(); setExpanded(true)
      setActive(value => event.key === 'ArrowDown' ? (value + 1) % suggestions.length : (value <= 0 ? suggestions.length - 1 : value - 1))
    }
    if (event.key === 'Enter' && showSuggestions && active >= 0) {
      event.preventDefault(); open(suggestions[active])
    }
  }
  function select(ticker: Ticker) {
    const key = tickerKey(ticker)
    const existing = recent.find(item => tickerKey(item.ticker) === key)
    if (existing) open(existing)
    else { selectedKey.current = key; onAnalyse(key) }
  }
  const error = resolve.error || analysisError
  return <section className="stock-search" id="stock-search" aria-label="Search Indian stocks">
    <label htmlFor="stock-query" className="search-label">Which company are you researching?</label>
    <div className="search-field-wrap">
      <form className="search-box" onSubmit={event => { event.preventDefault(); search() }} aria-busy={resolve.isPending || analysing}>
        <Search size={20} aria-hidden="true" />
        <input id="stock-query" ref={input} value={query} onChange={event => edit(event.target.value)}
          onFocus={() => setExpanded(true)} onBlur={() => { setExpanded(false); setActive(-1) }} onKeyDown={keydown}
          role="combobox" aria-autocomplete="list" aria-expanded={showSuggestions} aria-controls={showSuggestions ? 'saved-stock-suggestions' : undefined}
          aria-activedescendant={showSuggestions && active >= 0 ? `saved-stock-option-${active}` : undefined}
          aria-invalid={Boolean(error)} aria-describedby={error ? 'stock-search-hint stock-search-error' : 'stock-search-hint'}
          placeholder={replay ? 'Try Pulse or Aster…' : 'Company name or symbol'} autoComplete="off" maxLength={120} readOnly={analysing} enterKeyHint="search" />
        {query && !analysing && <button type="button" className="search-clear" aria-label="Clear company search" onClick={() => { edit(''); input.current?.focus() }}><X size={18} aria-hidden="true" /></button>}
        <Button type="submit" className="primary" disabled={!query.trim() || resolve.isPending || analysing}>
          {resolve.isPending || analysing ? <LoaderCircle size={17} className="spin" aria-hidden="true" /> : <ArrowRight size={17} aria-hidden="true" />}
          <span>{analysing ? 'Analysing…' : resolve.isPending ? 'Finding…' : 'Search'}</span>
        </Button>
      </form>
      {showSuggestions && <div className="saved-suggestions"><div className="suggestion-label">{query.trim() ? 'Matching saved reports' : 'Recent reports'}<span>Open instantly</span></div>
        <ul id="saved-stock-suggestions" role="listbox" aria-label="Saved company reports">{suggestions.map((item, index) => <li
          role="option" id={`saved-stock-option-${index}`} key={tickerKey(item.ticker)} aria-selected={active === index}
          onPointerDown={event => event.preventDefault()} onClick={() => open(item)} onPointerMove={() => setActive(index)}>
          <Clock3 size={17} aria-hidden="true" /><span><strong>{item.ticker.company_name}</strong><small>{listingLabel(item.ticker)}{item.synthetic && ' · Fictional demo'}</small></span><span className="suggestion-action">Open report <ArrowRight size={15} aria-hidden="true" /></span>
        </li>)}</ul>
      </div>}
    </div>
    <p className="search-hint" id="stock-search-hint">{replay ? 'Explore fictional demo companies. All data is simulated.' : 'Use a company name. We’ll find its NSE or BSE listing.'}</p>
    {Boolean(error) && <div id="stock-search-error"><ErrorNotice error={error} onRetry={() => analysisError && selectedKey.current ? onAnalyse(selectedKey.current) : search()} />
      {!analysisError && <p className="search-recovery">{replay ? 'Try Pulse, Aster or Northstar from the demo collection.' : 'Try the full company name, or choose a saved report above.'}</p>}</div>}
    {resolve.isPending && <p role="status" className="inline-status">Finding Indian listings. You can edit your search while we look.</p>}
    {candidates.length > 0 && !analysing && <div className="candidate-list"><div className="candidate-heading" role="status">{candidates.length === 1 ? 'Company found' : `${candidates.length} matching listings`}<span>Choose the company to continue</span></div>
      {candidates.map((ticker, index) => <button type="button" className="company-choice" key={tickerKey(ticker)} ref={index === 0 ? firstCandidate : undefined}
        onClick={() => select(ticker)} aria-label={`${recent.some(item => tickerKey(item.ticker) === tickerKey(ticker)) ? 'Open report for' : 'Analyse'} ${ticker.company_name}`}>
        <span><strong>{ticker.company_name}</strong><small>{listingLabel(ticker)}{ticker.synthetic && ' · Fictional demo'}</small></span><span className="choice-action">{recent.some(item => tickerKey(item.ticker) === tickerKey(ticker)) ? 'Open report' : 'Analyse'} <ArrowRight size={17} aria-hidden="true" /></span>
      </button>)}</div>}
    {analysing && <p role="status" className="inline-status">Checking the signals. Your report will be saved automatically.</p>}
    {!query && recent.length > 0 && <div className="recent-shortcuts"><span>Continue researching</span><div>{recent.slice(0, 3).map(item => <button type="button" key={tickerKey(item.ticker)} onClick={() => open(item)} disabled={analysing} aria-label={`Open saved report for ${item.ticker.company_name}`}><Clock3 size={14} aria-hidden="true" />{item.ticker.company_name}<ArrowRight size={14} aria-hidden="true" /></button>)}</div></div>}
  </section>
}
