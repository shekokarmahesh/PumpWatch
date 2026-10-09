import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import type { Signal } from '../api/client'
import { PromoterChip } from './PromoterChip'
import { SignalCard } from './SignalCard'

afterEach(cleanup)
const sample: Signal = { name: 'video_velocity', label: 'Video velocity', side: 'hype', window: 'Last 30 days',
  weight: .3, rule: '100 × log2(ratio) / 3', explanation: 'A dated sample of matching videos.',
  value: 8, unit: '× velocity', score: 100, has_data: true, carried: false, inputs: { recent_videos: 15 },
  evidence: Array.from({ length: 4 }, (_, i) => ({ url: `https://example.com/video/${i}`, title: `Source ${i}`,
    source: 'YouTube', published_at: '2026-10-08T00:00:00Z', synthetic: true })) }

describe('evidence disclosure', () => {
  it('opens the full source list and exposes the scoring inputs', async () => {
    const user = userEvent.setup()
    render(<SignalCard signal={sample} />)
    expect(screen.getAllByRole('link')).toHaveLength(3)
    await user.click(screen.getByRole('button', { name: 'Show all 4 sources' }))
    expect(screen.getAllByRole('link')).toHaveLength(4)
    expect(screen.getByRole('link', { name: 'Source 3' })).toHaveAttribute('href', 'https://example.com/video/3')
    await user.click(screen.getByText('Scoring rule & inputs'))
    expect(screen.getByText(/"recent_videos": 15/)).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Show fewer sources' }))
    expect(screen.getAllByRole('link')).toHaveLength(3)
  })

  it('shows unavailable measurements as unknown rather than zero', () => {
    render(<SignalCard signal={{ ...sample, score: null, value: null, has_data: false, evidence: [] }} />)
    expect(screen.getByText('NO DATA')).toBeVisible()
    expect(screen.queryAllByRole('link')).toHaveLength(0)
    expect(screen.getByText(/does not contribute/)).toBeVisible()
  })

  it('reveals a possible registry row with its identity caveat', async () => {
    const user = userEvent.setup()
    render(<PromoterChip promoter={{ name: 'Similar Channel', status: 'possible', note: 'Identity is not confirmed.',
      registry_row: { name: 'Similar Analyst', registration_number: 'DEMO-001' } }} />)
    expect(screen.getByText('Possible match')).toBeVisible()
    await user.click(screen.getByText('Similar Channel'))
    expect(screen.getByText('DEMO-001')).toBeVisible()
    expect(screen.getByText('Identity is not confirmed.')).toBeVisible()
  })
})
