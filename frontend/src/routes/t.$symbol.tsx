import { createFileRoute, Outlet, useMatchRoute } from '@tanstack/react-router'
import { Overview } from '../components/Overview'

export const Route = createFileRoute('/t/$symbol')({ component: TickerPage })
function TickerPage() {
  const matchRoute = useMatchRoute()
  const { symbol } = Route.useParams()
  return matchRoute({ to: '/t/$symbol/evidence', params: { symbol } }) ? <Outlet /> : <Overview stockKey={symbol} />
}
