import type { components } from './schema'

export type Analysis = components['schemas']['Analysis']
export type Ticker = components['schemas']['Ticker']
export type Signal = components['schemas']['Signal']
export type Evidence = components['schemas']['Evidence']
export type RegistryMatch = components['schemas']['RegistryMatch']
export type Call = components['schemas']['Call']
export type Health = components['schemas']['Health']
export type WatchItem = components['schemas']['WatchItem']
export type HistoryPoint = components['schemas']['HistoryPoint']
export type PastSearch = components['schemas']['PastSearch']
export type SnapshotResponse = components['schemas']['SnapshotResponse']

export async function request<T>(path: string, method = 'GET', body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method, headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    ...(signal ? { signal } : {}),
  })
  if (!response.ok) {
    let message = 'Something went wrong. Please try again.'
    try { const data = await response.json(); if (typeof data.detail === 'string') message = data.detail } catch { /* retain safe fallback */ }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export const tickerKey = (ticker: Ticker) => `${ticker.symbol}:${ticker.exchange}`
export const listingLabel = (ticker: Ticker) => `${ticker.exchange === 'BOM' ? 'BSE' : ticker.exchange} · ${ticker.symbol}`
export const searchTerm = (value: string) => value.trim().replace(/\s+/g, ' ').toLocaleLowerCase()
export const tickerBody = (key: string) => { const [symbol, exchange = 'NSE'] = key.split(':'); return { symbol, exchange } }
export const savedMatches = (query: string, items: PastSearch[]) => {
  const term = searchTerm(query)
  return term ? items.filter(item => searchTerm(tickerKey(item.ticker)).includes(term) || searchTerm(item.ticker.company_name).includes(term)) : items
}
export const api = {
  health: () => request<Health>('/health'),
  resolve: (query: string, signal?: AbortSignal) => request<Ticker[]>('/resolve', 'POST', { query }, signal),
  analyse: (key: string) => request<Analysis>('/analyse', 'POST', tickerBody(key)),
  latest: (key: string) => { const { symbol, exchange } = tickerBody(key); return request<Analysis>(`/tickers/${encodeURIComponent(symbol)}/latest?exchange=${exchange}`) },
  calls: (run: string) => request<Call[]>(`/runs/${run}/calls`),
  watchlist: () => request<WatchItem[]>('/watchlist'),
  searches: () => request<PastSearch[]>('/searches?limit=100'),
  watch: (key: string, add: boolean) => request<WatchItem[]>('/watchlist', add ? 'POST' : 'DELETE', tickerBody(key)),
  history: (key: string) => { const { symbol, exchange } = tickerBody(key); return request<HistoryPoint[]>(`/tickers/${encodeURIComponent(symbol)}/history?exchange=${exchange}`) },
  snapshot: () => request<SnapshotResponse>('/snapshot', 'POST', {}),
}
