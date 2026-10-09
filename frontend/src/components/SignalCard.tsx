import { ArrowUpRight, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import type { Signal } from '../api/client'
import { dateLabel, scoreLabel } from './shared'
import { PromoterChip } from './PromoterChip'

export function SignalCard({ signal }: { signal: Signal }) {
  const [expanded, setExpanded] = useState(false)
  const allEvidence = signal.evidence ?? []
  const items = expanded ? allEvidence : allEvidence.slice(0, 3)
  return <article className="signal-card panel" id={signal.name}><div className="signal-heading"><div><div className="eyebrow">{signal.side} SIGNAL {signal.carried && '· CARRIED'}</div><h2>{signal.label}</h2></div><div className="signal-score"><strong>{signal.has_data ? scoreLabel(signal.score) : '—'}</strong><span>{signal.has_data ? '/100' : 'NO DATA'}</span></div></div>
    <div className="signal-measure"><span>{signal.value == null ? 'Unknown' : Number(signal.value.toFixed(2)).toLocaleString('en-IN')} {signal.unit}</span><span>{signal.window}</span></div><p className="signal-explanation">{signal.explanation}</p>
    <details className="rule-details"><summary>Scoring rule & inputs <ChevronDown size={14} /></summary><p className="mono">{signal.rule}</p><p>Weight: {(signal.weight * 100).toFixed(0)}% of the {signal.side} side. Unavailable signals drop out of the weighted mean.</p><pre>{JSON.stringify(signal.inputs, null, 2)}</pre></details>
    <div className="evidence-items"><div className="eyebrow">SOURCE EVIDENCE</div>{items.map(item => <div className="evidence-item" key={item.url}><a href={item.url} target="_blank" rel="noreferrer"><span>{item.title}</span><ArrowUpRight size={15} /></a><div className="source-meta"><span>{item.source}</span><span>{item.published_at ? dateLabel(item.published_at) : 'Date unavailable'}</span>{item.synthetic && <span>Simulated link</span>}</div>{item.promoter && <PromoterChip promoter={item.promoter} />}</div>)}
      {!allEvidence.length && <p className="muted">No usable evidence was returned. This signal does not contribute to the score.</p>}
      {allEvidence.length > 3 && <button className="text-button" onClick={() => setExpanded(!expanded)}>{expanded ? 'Show fewer sources' : `Show all ${allEvidence.length} sources`}<ChevronDown size={14} /></button>}</div>
  </article>
}
