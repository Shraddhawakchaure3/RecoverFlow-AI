import { useState, useEffect } from 'react'

/**
 * Generic data fetching hook
 */
export function useFetch(fetchFn, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetch = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchFn()
      setData(res.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetch()
  }, deps) // eslint-disable-line

  return { data, loading, error, refetch: fetch }
}

/**
 * Auto-refreshing fetch hook
 */
export function useAutoRefetch(fetchFn, intervalMs = 30000, deps = []) {
  const result = useFetch(fetchFn, deps)

  useEffect(() => {
    const interval = setInterval(result.refetch, intervalMs)
    return () => clearInterval(interval)
  }, [intervalMs]) // eslint-disable-line

  return result
}
