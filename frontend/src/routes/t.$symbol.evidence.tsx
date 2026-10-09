import { createFileRoute } from '@tanstack/react-router'
import { EvidencePage } from '../components/EvidencePage'
export const Route = createFileRoute('/t/$symbol/evidence')({ component: Page })
function Page() { const { symbol } = Route.useParams(); return <EvidencePage stockKey={symbol} /> }
