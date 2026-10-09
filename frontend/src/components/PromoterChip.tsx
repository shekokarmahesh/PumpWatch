import type { RegistryMatch } from '../api/client'
const labels = { registered: 'Registered name match', possible: 'Possible match', not_found: 'Not found', not_checked: 'Not checked' }
export function PromoterChip({ promoter }: { promoter: RegistryMatch }) {
  return <details className="promoter-item"><summary><strong>{promoter.name}</strong><span className={`promoter-status promoter-${promoter.status}`}>{labels[promoter.status]}</span></summary><div className="promoter-detail"><p>{promoter.note}</p>{promoter.registry_row && <dl>{Object.entries(promoter.registry_row).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{value}</dd></div>)}</dl>}</div></details>
}
