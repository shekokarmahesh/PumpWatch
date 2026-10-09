import { createRootRouteWithContext, Link, Outlet, useRouterState } from '@tanstack/react-router'
import type { QueryClient } from '@tanstack/react-query'
import { useQuery } from '@tanstack/react-query'
import { Activity, ArrowUpRight, Bookmark, CircleHelp, Search, ShieldCheck, Radio, History } from 'lucide-react'
import { motion, MotionConfig } from 'motion/react'
import { api } from '../api/client'
import { springLayout } from '../components/ui/motion'

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: Shell,
  notFoundComponent: () => <div className="loading-state"><h1>Page not found</h1><Link to="/">Return to research</Link></div>,
  errorComponent: ({ error }) => <div className="loading-state"><h1>Unable to open this page</h1><p>{error instanceof Error ? error.message : 'Please try again.'}</p><a href="/">Return to research</a></div>,
})

function Shell() {
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, refetchInterval: 30_000 })
  const watchlist = useQuery({ queryKey: ['watchlist'], queryFn: api.watchlist })
  const pathname = useRouterState({ select: state => state.location.pathname })
  const hash = useRouterState({ select: state => state.location.hash })
  const pastActive = pathname === '/' && hash === 'past-searches'
  const researchActive = pathname !== '/watchlist' && !pastActive
  const dataMode = health.isError ? 'Offline' : health.data?.mode === 'replay' ? 'Demo data' : health.data ? 'Live sources' : 'Connecting…'
  return <MotionConfig reducedMotion="user"><div className="app-shell">
    <a href="#main" className="skip-link">Skip to content</a>
    <aside className="sidebar">
      <Link to="/" className="brand"><span className="brand-icon"><Activity size={21} strokeWidth={1.8} /></span><span>PumpWatch<span className="brand-caption">LOOK BEYOND THE TIP</span></span></Link>
      <div className="sidebar-label">WORKSPACE</div>
      <nav className="primary-nav" aria-label="Main navigation"><Link to="/" aria-label="Stock research" activeOptions={{ exact: true, includeHash: true }} className={researchActive ? 'active' : ''}>{researchActive && <motion.span className="nav-indicator" layoutId="navigation-pill" transition={springLayout} />}<Search size={18} aria-hidden="true" /><span>Research</span><span className="nav-shortcut">01</span></Link>
        <Link to="/" hash="past-searches" activeOptions={{ exact: true, includeHash: true }} className={pastActive ? 'active' : ''}>{pastActive && <motion.span className="nav-indicator" layoutId="navigation-pill" transition={springLayout} />}<History size={18} aria-hidden="true" /><span>Past searches</span></Link>
        <Link to="/watchlist">{pathname === '/watchlist' && <motion.span className="nav-indicator" layoutId="navigation-pill" transition={springLayout} />}<Bookmark size={18} aria-hidden="true" /><span>Watchlist</span><span className="nav-count">{watchlist.data?.length ?? 0}</span></Link></nav>
      <div className="sidebar-divider" /><a href="/#methodology" className="sidebar-help"><CircleHelp size={17} /> How scoring works <ArrowUpRight size={12} /></a>
      <div className="sidebar-bottom"><div className="mode-card"><div className="eyebrow">DATA MODE</div><div className="mode-title"><span className="mode-dot" />{dataMode}</div>
        <p>{health.data?.mode === 'replay' ? 'Explore five fictional scenarios. No API key needed.' : 'Local estimates; billed usage is in your SerpApi dashboard.'}</p>
        <div className="mode-credits"><span>This month · estimated</span><span className="mono">{health.data?.credits_spent_this_month ?? '—'} / {health.data?.credit_budget ?? 250}</span></div>
        {health.data?.mode !== 'replay' && <div className="mode-credits"><span>Past hour · estimated</span><span className="mono">{health.data?.credits_spent_this_hour ?? '—'} / {health.data?.hourly_credit_budget ?? '—'}</span></div>}</div>
        <div className="sidebar-footer"><ShieldCheck size={15} /><span>Evidence before enthusiasm.</span></div></div>
    </aside>
    <div className="workspace"><header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <strong>{pathname === '/watchlist' ? 'Watchlist' : pastActive ? 'Past searches' : 'Stock research'}</strong></div><span className="topbar-right"><span className="connection-status"><Radio size={13} aria-hidden="true" />{dataMode}</span><span className="market-pill">NSE + BSE</span></span></header>
      <main id="main"><Outlet /></main>
      <footer className="disclaimer"><ShieldCheck size={15} /><span>This tool measures public attention, not value. It is not investment advice.</span></footer>
    </div>
  </div></MotionConfig>
}
