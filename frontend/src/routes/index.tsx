import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, ArrowUpRight, AudioLines, CircleHelp, FileSearch, Layers, ShieldCheck, ScanLine } from 'lucide-react'
import { api, tickerKey } from '../api/client'
import { ErrorNotice } from '../components/shared'
import { Reveal, TiltCard } from '../components/ui/motion'
import { PastSearches } from '../components/PastSearches'
import { SignalOrbit } from '../components/SignalOrbit'
import { StockSearch } from '../components/StockSearch'

export const Route = createFileRoute('/')({ component: SearchPage })
const scenarioText: Record<string, { label: string; description: string }> = {
  PULSE: { label: 'Rapid attention', description: 'A surge in videos, tip groups and paid promotion.' },
  ASTER: { label: 'Mixed signals', description: 'Growing attention with limited supporting coverage.' },
  NORTHSTAR: { label: 'Steady control', description: 'Measured attention and stronger supporting signals.' },
  ORBIT: { label: 'Quiet control', description: 'Low public attention with regular news coverage.' },
  SPARROW: { label: 'Thin coverage', description: 'Explore how the model handles missing data.' },
}

function SearchPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const health = useQuery({ queryKey: ['health'], queryFn: api.health })
  const past = useQuery({ queryKey: ['past-searches'], queryFn: api.searches })
  const analyse = useMutation({ mutationFn: api.analyse, onSuccess: result => {
    queryClient.setQueryData(['analysis', tickerKey(result.ticker)], result)
    queryClient.invalidateQueries({ queryKey: ['health'] })
    queryClient.invalidateQueries({ queryKey: ['past-searches'] })
    queryClient.invalidateQueries({ queryKey: ['history', tickerKey(result.ticker)] })
    navigate({ to: '/t/$symbol', params: { symbol: tickerKey(result.ticker) } })
  } })
  return <div className="page search-page">
    <div className="page-kicker"><span className="eyebrow">PUBLIC SIGNALS. CLEARER PERSPECTIVE.</span><span className="edition mono">RESEARCH DESK / 01</span></div>
    <Reveal className="hero"><div className="hero-content"><div className="hero-label"><span className="mode-dot" /> YOUR EDGE IS THE EVIDENCE</div>
      <h1>Beyond the hype.<br /><span>Into the evidence.</span></h1><p>A stock tip is just the start. See what’s driving the attention<br className="desktop-break" /> and whether the substance keeps up.</p>
      <StockSearch replay={health.data?.mode === 'replay'} saved={past.data ?? []} analysing={analyse.isPending} analysisError={analyse.error}
        onAnalyse={key => analyse.mutate(key)} onOpenReport={key => navigate({ to: '/t/$symbol', params: { symbol: key } })} onReset={analyse.reset} />
      <div className="hero-features"><span><ScanLine size={14} /> 8 transparent signals</span><span><ShieldCheck size={14} /> Every source linked</span></div></div>
      <SignalOrbit />
    </Reveal>
    <PastSearches />
    {health.data?.mode === 'replay' && <section className="examples"><div className="section-heading"><div><h2>Start with a second look</h2><p>Five fictional scenarios. The same analysis pipeline.</p></div><span className="neutral-chip"><Layers size={13} /> REPLAY COLLECTION</span></div>
      <div className="example-grid">{health.data.fixture_tickers.map((ticker, i) => <TiltCard className={i === 0 ? 'featured-example' : ''} key={ticker.symbol}><button className="example-card" disabled={analyse.isPending} onClick={() => analyse.mutate(tickerKey(ticker))}>
        <div className="example-top"><span className="company-monogram">{ticker.company_name.split(' ').map(w => w[0]).join('').slice(0,2)}</span><ArrowUpRight size={18} /></div>
        <h3>{ticker.company_name}</h3><div className="example-symbol mono">{tickerKey(ticker)} {ticker.is_sme && <span>· SME demo</span>}</div><p>{scenarioText[ticker.symbol]?.description}</p><div className="example-bottom"><span>{scenarioText[ticker.symbol]?.label ?? 'Captured scenario'}</span><span className="mono">0{i+1}</span></div>
        {i === 0 && <div className="example-feature-footer"><span>Explore this scenario</span><span className="round-arrow"><ArrowRight size={18} /></span></div>}
      </button></TiltCard>)}</div>
      <div className="fixture-caption"><CircleHelp size={13} /> Simulated observations and links. These examples do not describe real listed companies.</div></section>}
    {health.isError && <ErrorNotice error={new Error('Unable to connect to the research service. Please try again.')} onRetry={() => health.refetch()} />}
    <section className="methodology" id="methodology"><div className="section-heading"><div><h2>Follow the attention. Inspect the substance.</h2><p>Transparent rules, linked evidence, and no hidden model.</p></div><span className="eyebrow">THE METHODOLOGY</span></div>
      <div className="method-grid"><article><AudioLines size={24} strokeWidth={1.4} /><span className="eyebrow">01 / COLLECT</span><h3>Six surfaces, one view</h3><p>Videos, search interest, indexed tip groups, ads, prices and news — brought into the same research trail.</p></article>
        <article><FileSearch size={24} strokeWidth={1.4} /><span className="eyebrow">02 / COMPARE</span><h3>Attention meets support</h3><p>Five hype signals are weighed against news coverage, financial trends and promoter name matches.</p></article>
        <article><ShieldCheck size={24} strokeWidth={1.4} /><span className="eyebrow">03 / VERIFY</span><h3>Every finding has a source</h3><p>Open the evidence, inspect the scoring rule, and export the complete report. Missing data stays unknown.</p></article></div>
      <details className="scoring-details"><summary>View scoring and verdict rules <ArrowUpRight size={14} /></summary><p>Available signals form a weighted mean. Hype weights: video velocity 30%, search spike 25%, tip groups 20%, ads 15%, price-volume 10%. Support weights: news 40%, financial trend 35%, registered names 25%.</p><p>High: hype ≥ 60 and support ≤ 40. Elevated: hype ≥ 40 with a gap ≥ 20, or one hype signal at 100 and support below 50. Low otherwise. Fewer than three hype signals, or unknown support, gives insufficient data. News and registry name matches do not establish legitimacy.</p></details>
      <div className="source-strip"><span className="eyebrow">POWERED BY SERPAPI</span><span>Google Finance</span><span>YouTube</span><span>Google Trends</span><span>Google Search</span><span>Google News</span><span>Ads Transparency</span></div>
    </section>
  </div>
}
