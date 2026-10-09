import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { api } from '../api/client'
import type { PastSearch, Ticker } from '../api/client'
import { StockSearch } from './StockSearch'

afterEach(() => { cleanup(); vi.restoreAllMocks() })
const ticker: Ticker = { symbol: 'JSIPL', exchange: 'NSE', company_name: 'Jindal Supreme India', is_sme: false, listing_verified: false, synthetic: false }
const saved: PastSearch = { ticker, run_id: 'saved', run_at: '2026-10-08T00:00:00Z', hype_score: 52, support_score: 75, verdict: 'Insufficient data', signals_available: 2, support_available: 1, mode: 'cache-first', synthetic: false, run_count: 1 }

function setup(items: PastSearch[] = [saved]) {
  const onOpenReport = vi.fn(), onAnalyse = vi.fn()
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(<QueryClientProvider client={client}><StockSearch replay={false} saved={items} analysing={false} analysisError={null}
    onOpenReport={onOpenReport} onAnalyse={onAnalyse} onReset={vi.fn()} /></QueryClientProvider>)
  return { user: userEvent.setup(), onOpenReport, onAnalyse, input: screen.getByRole('combobox', { name: 'Which company are you researching?' }) }
}

it('offers local saved reports while typing and opens a keyboard selection without a provider request', async () => {
  const resolve = vi.spyOn(api, 'resolve')
  const { user, input, onOpenReport, onAnalyse } = setup()
  await user.type(input, 'jindal')
  expect(screen.getByRole('listbox', { name: 'Saved company reports' })).toBeVisible()
  await user.keyboard('{ArrowDown}{Enter}')
  expect(onOpenReport).toHaveBeenCalledWith('JSIPL:NSE')
  expect(resolve).not.toHaveBeenCalled()
  expect(onAnalyse).not.toHaveBeenCalled()
})

it('opens an exact saved symbol with one submission and keeps Escape distinct from selecting a report', async () => {
  const resolve = vi.spyOn(api, 'resolve')
  const { user, input, onOpenReport } = setup()
  await user.type(input, 'jsipl')
  await user.keyboard('{Escape}')
  expect(input).toHaveAttribute('aria-expanded', 'false')
  expect(onOpenReport).not.toHaveBeenCalled()
  await user.keyboard('{Enter}')
  expect(onOpenReport).toHaveBeenCalledTimes(1)
  expect(resolve).not.toHaveBeenCalled()
})

it('opens a clicked saved suggestion without losing it when the field blurs', async () => {
  const resolve = vi.spyOn(api, 'resolve')
  const { user, input, onOpenReport, onAnalyse } = setup()
  await user.type(input, 'jindal')
  await user.click(screen.getByRole('option', { name: /Jindal Supreme India/ }))
  expect(onOpenReport).toHaveBeenCalledOnce()
  expect(onOpenReport).toHaveBeenCalledWith('JSIPL:NSE')
  expect(onAnalyse).not.toHaveBeenCalled()
  expect(resolve).not.toHaveBeenCalled()
})

it('waits for explicit company confirmation before starting a new analysis', async () => {
  vi.spyOn(api, 'resolve').mockResolvedValue([ticker])
  const { user, input, onAnalyse } = setup([])
  await user.type(input, 'Jindal Supreme')
  await user.click(screen.getByRole('button', { name: 'Search' }))
  const choice = await screen.findByRole('button', { name: 'Analyse Jindal Supreme India' })
  expect(choice).toHaveFocus()
  expect(onAnalyse).not.toHaveBeenCalled()
  await user.click(choice)
  expect(onAnalyse).toHaveBeenCalledWith('JSIPL:NSE')
})

it('preserves a failed query and offers a retry that recovers to a company choice', async () => {
  const resolve = vi.spyOn(api, 'resolve').mockRejectedValueOnce(new Error('Company search took too long. Please try again.')).mockResolvedValue([ticker])
  const { user, input } = setup([])
  await user.type(input, 'Jindal Supreme')
  await user.click(screen.getByRole('button', { name: 'Search' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Company search took too long')
  expect(input).toHaveValue('Jindal Supreme')
  expect(input).toHaveAttribute('aria-invalid', 'true')
  expect(input).toHaveFocus()
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByRole('button', { name: 'Analyse Jindal Supreme India' })).toBeVisible()
  expect(resolve).toHaveBeenCalledTimes(2)
})

it('lets the user edit during lookup and discards a late result for the old query', async () => {
  let complete!: (data: Ticker[]) => void
  let requestSignal: AbortSignal | undefined
  const resolve = vi.spyOn(api, 'resolve').mockImplementation((_term, signal) => {
    requestSignal = signal
    return new Promise<Ticker[]>(done => { complete = done })
  })
  const { user, input } = setup([])
  await user.type(input, 'Jindal Supreme')
  await user.click(screen.getByRole('button', { name: 'Search' }))
  await waitFor(() => expect(resolve).toHaveBeenCalledTimes(1))
  expect(input).not.toBeDisabled()
  await user.clear(input)
  await user.type(input, 'Adroit Industries')
  expect(requestSignal?.aborted).toBe(true)
  await act(async () => { complete([ticker]) })
  expect(screen.queryByRole('button', { name: 'Analyse Jindal Supreme India' })).not.toBeInTheDocument()
  expect(input).toHaveValue('Adroit Industries')
  expect(screen.getByRole('button', { name: 'Search' })).toBeEnabled()
})

it('shows a recovery path for an empty lookup rather than leaving a blank result', async () => {
  vi.spyOn(api, 'resolve').mockResolvedValue([])
  const { user, input } = setup([])
  await user.type(input, 'Unknown company')
  await user.click(screen.getByRole('button', { name: 'Search' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Try a fuller name')
  expect(screen.getByRole('button', { name: 'Try again' })).toBeVisible()
})

it('clears a query without triggering an automatic paid lookup', async () => {
  const resolve = vi.spyOn(api, 'resolve')
  const { user, input } = setup()
  await user.type(input, 'Unknown')
  await user.click(screen.getByRole('button', { name: 'Clear company search' }))
  expect(input).toHaveValue('')
  expect(input).toHaveFocus()
  expect(resolve).not.toHaveBeenCalled()
})
