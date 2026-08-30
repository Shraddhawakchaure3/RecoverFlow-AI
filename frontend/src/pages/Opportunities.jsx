import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFetch } from '../hooks/useFetch'
import { opportunitiesApi } from '../services/api'
import {
  formatINR, formatRelative, getStatusBadge, getPriorityBadge,
  getActionLabel, getFailureLabel, getScoreColor
} from '../utils/format'
import PageHeader from '../components/PageHeader'
import { ChevronRight, Search, Filter } from 'lucide-react'

const PRIORITIES = ['ALL', 'HIGH', 'MEDIUM', 'LOW']

export default function Opportunities() {
  const navigate = useNavigate()
  const [priority, setPriority] = useState('ALL')
  const [search, setSearch] = useState('')

  const { data, loading, error, refetch } = useFetch(
    () => opportunitiesApi.list({ priority: priority === 'ALL' ? undefined : priority }),
    [priority]
  )

  const opportunities = (data?.opportunities || []).filter(o => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      o.payment_id?.toLowerCase().includes(q) ||
      o.customer_name?.toLowerCase().includes(q) ||
      o.failure_label?.toLowerCase().includes(q)
    )
  })

  return (
    <div className="fade-in">
      <PageHeader
        title="Revenue Opportunities"
        subtitle={`${data?.total || 0} failed payments requiring attention`}
        onRefresh={refetch}
        loading={loading}
      />

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-xs">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input
            className="w-full pl-8 pr-3 py-1.5 rounded-md text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-primary)]"
            placeholder="Search payment ID, customer…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-1.5">
          <Filter size={13} className="text-[var(--color-text-muted)]" />
          {PRIORITIES.map(p => (
            <button
              key={p}
              onClick={() => setPriority(p)}
              className={`btn btn-sm ${priority === p ? 'btn-primary' : 'btn-secondary'}`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="card">
        {loading && !data ? (
          <div className="flex items-center justify-center h-40">
            <div className="spinner" />
          </div>
        ) : error ? (
          <div className="p-6 text-center text-sm text-[var(--color-danger)]">{error}</div>
        ) : opportunities.length === 0 ? (
          <div className="p-12 text-center text-sm text-[var(--color-text-muted)]">
            No opportunities found. Seed the database to see data.
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Payment ID</th>
                  <th>Customer</th>
                  <th>Amount</th>
                  <th>Failure</th>
                  <th>Score</th>
                  <th>Priority</th>
                  <th>Recommended Action</th>
                  <th>Status</th>
                  <th>Age</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {opportunities.map(opp => (
                  <tr
                    key={opp.payment_id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/opportunities/${opp.payment_id}`)}
                  >
                    <td>
                      <span className="font-mono text-[11px] text-[var(--color-primary)]">
                        {opp.payment_id}
                      </span>
                    </td>
                    <td>
                      <div className="font-500" style={{ fontWeight: 500 }}>{opp.customer_name}</div>
                      <div className="text-xs text-[var(--color-text-muted)]">{opp.customer_email}</div>
                    </td>
                    <td>
                      <div className="amount font-600" style={{ fontWeight: 600 }}>
                        {formatINR(opp.amount_inr)}
                      </div>
                      <div className="text-xs text-[var(--color-text-muted)]">
                        exp. {formatINR(opp.expected_recovery_inr)}
                      </div>
                    </td>
                    <td>
                      <div className="text-xs">{opp.failure_label}</div>
                      <div className="text-[11px] text-[var(--color-text-muted)]">
                        {opp.failure_reason}
                      </div>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div
                          className="text-sm font-700 amount"
                          style={{ color: getScoreColor(opp.recovery_score), fontWeight: 700 }}
                        >
                          {Math.round(opp.recovery_score * 100)}%
                        </div>
                        <div className="w-14 progress">
                          <div
                            className="progress-fill"
                            style={{
                              width: `${opp.recovery_score * 100}%`,
                              background: getScoreColor(opp.recovery_score),
                            }}
                          />
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${getPriorityBadge(opp.priority)}`}>
                        {opp.priority}
                      </span>
                    </td>
                    <td>
                      <span className="text-xs text-[var(--color-text-muted)]">
                        {opp.latest_action
                          ? getActionLabel(opp.latest_action.action_type)
                          : '—'}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${getStatusBadge(opp.action_status)}`}>
                        {opp.action_status}
                      </span>
                    </td>
                    <td className="text-xs text-[var(--color-text-muted)]">
                      {formatRelative(opp.created_at)}
                    </td>
                    <td>
                      <ChevronRight size={14} className="text-[var(--color-text-muted)]" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {data && (
        <div className="mt-3 text-xs text-[var(--color-text-muted)]">
          Showing {opportunities.length} of {data.total} opportunities
        </div>
      )}
    </div>
  )
}
