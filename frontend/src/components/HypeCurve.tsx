import { useQuery } from '@tanstack/react-query'
import { Area, CartesianGrid, ComposedChart, Line, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useReducedMotion } from 'motion/react'
import { useId, useState } from 'react'
import { api } from '../api/client'
import { ErrorNotice } from './shared'

const shortDate = (value: string) => new Date(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })

export function HypeCurve({ stockKey }: { stockKey: string }) {
  const history = useQuery({ queryKey: ['history', stockKey], queryFn: () => api.history(stockKey) })
  const reduce = useReducedMotion()
  const id = useId().replaceAll(':', '')
  const [showHype, setShowHype] = useState(true)
  const [showSupport, setShowSupport] = useState(true)
  if (history.isPending) return <div className="chart-skeleton" role="status">Loading recorded observations…</div>
  if (history.error) return <ErrorNotice error={history.error} />
  const data = history.data ?? []
  if (!data.length) return <div className="empty-inline">No history yet. Run an analysis or take a snapshot to start the curve.</div>
  return <div className="curve">
    <div className="chart-description"><div className="chart-legend"><button aria-pressed={showHype} onClick={() => setShowHype(!showHype)}><span className="legend-dot hype-dot" />Hype score</button><button aria-pressed={showSupport} onClick={() => setShowSupport(!showSupport)}><span className="legend-dot support-dot" />Support score</button></div><span>○ New promoter / ad</span></div>
    <div role="img" aria-label={`Score history for ${stockKey}: ${data.map(p => `${p.date}, hype ${p.hype_score ?? 'unknown'}, support ${p.support_score ?? 'unknown'}`).join('; ')}`}>
      <ResponsiveContainer width="100%" height={240}><ComposedChart data={data} margin={{ top: 20, right: 22, bottom: 8, left: -20 }}>
        <defs><linearGradient id={`fill-${id}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#a6f3c5" stopOpacity={0.14} /><stop offset="100%" stopColor="#a6f3c5" stopOpacity={0} /></linearGradient></defs>
        <CartesianGrid stroke="#ffffff0c" strokeDasharray="3 5" vertical={false} />
        <XAxis dataKey="date" tickFormatter={shortDate} tick={{ fill: '#87928e', fontSize: 11 }} axisLine={false} tickLine={false} tickMargin={12} />
        <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={{ fill: '#87928e', fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={{ background: '#19201e', border: '1px solid #35403b', borderRadius: 12, boxShadow: '0 12px 35px #0005', fontSize: 12 }} labelStyle={{ color: '#d9e6df', marginBottom: 8 }} labelFormatter={value => shortDate(String(value))} cursor={{ stroke: '#6a7971', strokeDasharray: '3 3' }} formatter={(value, name) => [value == null ? 'Unknown' : `${Math.round(Number(value))} / 100`, name]} />
        {showHype && <Area type="linear" dataKey="hype_score" name="Hype score" stroke="#a6f3c5" strokeWidth={2} fill={`url(#fill-${id})`} dot={{ r: 4, fill: '#111815', strokeWidth: 2 }} activeDot={{ r: 6, fill: '#a6f3c5', stroke: '#111815', strokeWidth: 3 }} connectNulls={false} isAnimationActive={!reduce} />}
        {showSupport && <Line type="linear" dataKey="support_score" name="Support score" stroke="#9daef4" strokeDasharray="4 4" strokeWidth={2} dot={{ r: 4, fill: '#111815', strokeWidth: 2 }} activeDot={{ r: 6, fill: '#9daef4', stroke: '#111815', strokeWidth: 3 }} connectNulls={false} isAnimationActive={!reduce} />}
        {showHype && data.filter(p => (p.new_promoter || p.new_ad) && p.hype_score != null).map(p => <ReferenceDot key={p.date} x={p.date} y={p.hype_score!} r={7} fill="#111815" stroke="#a6f3c5" strokeWidth={2} />)}
      </ComposedChart></ResponsiveContainer>
    </div>
    {data.length === 1 && <p className="chart-note"><span className="mode-dot" />One recorded day. Daily snapshots will build the curve.</p>}
    <details className="history-table"><summary>View recorded observations</summary><div className="table-scroll"><table><thead><tr><th>Date</th><th>Hype</th><th>Support</th><th>Markers</th></tr></thead><tbody>{data.map(p => <tr key={p.date}><td>{p.date}</td><td>{p.hype_score ?? 'Unknown'}</td><td>{p.support_score ?? 'Unknown'}</td><td>{[p.new_ad && 'New ad', p.new_promoter && 'New promoter', p.carried && 'Carried signals', p.synthetic && 'Synthetic'].filter(Boolean).join(' · ') || '—'}</td></tr>)}</tbody></table></div></details>
  </div>
}
