import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useFetch } from '../hooks/useFetch'
import { auditApi } from '../services/api'
import { formatDate, getStatusBadge } from '../utils/format'
import PageHeader from '../components/PageHeader'
import AuditTimeline from '../components/AuditTimeline'
import { Search } from 'lucide-react'

export default function AuditTrail() {
  const [searchParams] = useSearchParams()
  const initialPaymentId = searchParams.get('payment_id') || ''
  const [paymentFilter, setPaymentFilter] = useState(initialPaymentId)
  const [applied, setApplied] = useState(initialPaymentId)

  const { data, loading, error, refetch } = useFetch(
    () => auditApi.getLogs({ payment_id: applied || undefined, limit: 100 }),
    [applied]
  )

  const handleSearch = (e) => {
    e.preventDefault()
    setApplied(paymentFilter.trim())
  }

  return (
    <div className="fade-in">
      <PageHeader
        title="Audit Trail"
        subtitle={`${data?.total || 0} events recorded`}
        onRefresh={refetch}
        loading={loading}
      />

      {/* Search */}
      <form className="flex items-center gap-2 mb-5" onSubmit={handleSearch}>
        <div className="relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input
            className="pl-8 pr-3 py-1.5 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-primary)] w-64"
            placeholder="Filter by Payment ID…"
            value={paymentFilter}
            onChange={e => setPaymentFilter(e.target.value)}
          />
        </div>
        <button type="submit" className="btn btn-primary btn-sm">Filter</button>
        {applied && (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => { setPaymentFilter(''); setApplied('') }}
          >
            Clear
          </button>
        )}
      </form>

      <div className="grid grid-cols-5 gap-4">
        {/* Timeline */}
        <div className="col-span-3 card p-4">
          {loading ? (
            <div className="flex items-center justify-center h-40"><div className="spinner" /></div>
          ) : error ? (
            <div className="text-sm text-[var(--color-danger)]">{error}</div>
          ) : (
            <AuditTimeline entries={data?.entries || []} />
          )}
        </div>

        {/* Raw log table */}
        <div className="col-span-2 card">
          <div className="p-4 border-b border-[var(--color-border)]">
            <div className="text-sm font-600" style={{ fontWeight: 600 }}>Raw Log</div>
          </div>
          {loading ? (
            <div className="flex items-center justify-center h-40"><div className="spinner" /></div>
          ) : (
            <div className="table-container" style={{ maxHeight: 600, overflowY: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th>Event</th>
                    <th>Payment</th>
                    <th>Result</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.entries || []).map((e, i) => (
                    <tr key={e.log_id || i}>
                      <td>
                        <div className="text-xs font-mono text-[var(--color-primary)] leading-tight">
                          {e.event?.replace(/_/g, '\u200b_')}
                        </div>
                      </td>
                      <td className="font-mono text-[10px] text-[var(--color-text-muted)]">
                        {e.payment_id ? (
                          <Link className="text-[var(--color-primary)]" to={`/opportunities/${e.payment_id}`}>
                            {e.payment_id.slice(0, 12)}…
                          </Link>
                        ) : '—'}
                      </td>
                      <td className="text-xs text-[var(--color-text-muted)]">
                        {e.result?.slice(0, 30) || e.action || '—'}
                      </td>
                      <td className="text-[10px] text-[var(--color-text-muted)] whitespace-nowrap">
                        {formatDate(e.timestamp)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
