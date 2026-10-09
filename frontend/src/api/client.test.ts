import { afterEach, expect, it, vi } from 'vitest'
import { api, request, savedMatches } from './client'
import type { PastSearch } from './client'
afterEach(() => vi.unstubAllGlobals())

it('sends the ticker and exchange unchanged to the backend scorer', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ verdict: 'Low' }), { status: 200 }))
  vi.stubGlobal('fetch', fetch)
  await api.analyse('ORBIT:BOM')
  expect(fetch).toHaveBeenCalledWith('/api/analyse', expect.objectContaining({ method: 'POST', body: '{"symbol":"ORBIT","exchange":"BOM"}' }))
})

it('surfaces the API error without attempting to render invalid data', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'No fixture found' }), { status: 400 })))
  await expect(request('/analyse')).rejects.toThrow('No fixture found')
})

it('finds saved reports locally by company or symbol and reads history without a paid request', async () => {
  const items: PastSearch[] = [{ ticker: { symbol: 'ORIENTCABL', exchange: 'NSE', company_name: 'Orient Cables (India) Ltd', is_sme: false, listing_verified: false, synthetic: false }, run_id: 'saved', run_at: '2026-10-08T00:00:00Z', hype_score: 80, support_score: 100, verdict: 'Insufficient data', signals_available: 2, support_available: 1, mode: 'cache-first', synthetic: false, run_count: 2 }]
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(items), { status: 200 }))
  vi.stubGlobal('fetch', fetch)
  expect(savedMatches(' orient cable ', items)).toEqual(items)
  expect(savedMatches('orientcabl:nse', items)).toEqual(items)
  expect(savedMatches('TCS', items)).toEqual([])
  expect(fetch).not.toHaveBeenCalled()
  expect(await api.searches()).toEqual(items)
  expect(fetch).toHaveBeenCalledWith('/api/searches?limit=100', expect.objectContaining({ method: 'GET' }))
})
