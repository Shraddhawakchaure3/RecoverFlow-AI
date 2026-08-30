import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFetch } from '../hooks/useFetch'
import { opportunitiesApi } from '../services/api'
import { formatINR, formatRelative, getPriorityBadge, getScoreColor } from '../utils/format'
import PageHeader from '../components/PageHeader'
import { ChevronRight } from 'lucide-react'

export default function AIDecisionList() {
  const navigate = useNavigate()
  const { data, loading, error, refetch } = useFetch(() => opportunitiesApi.list({ limit: 50 }))

  const opportunities = (data?.opportunities || []).filter(
    o => o.action_status === 'unactioned' || o.action_status === 'pending'
  )

  return (
    <div className="fade-in">
      <PageHeader
        title="AI Decision"
        subtitle="Select a payment to analyze and execute recovery"
        onRefresh={refetch}
        loading={loading}
      />

      {loading && !data ? (
        <div className="flex items-center justify-center h-40"><div className="spinner" /></div>
      ) : error ? (
        <div className="text-sm text-[var(--color-danger)] p-4">{error}</div>
      ) : opportunities.length === 0 ? (
        <div className="card p-12 text-center text-sm text-[var(--color-text-muted)]">
          No unactioned opportunities. Seed the database or check the Opportunities page.
        </div>
      ) : (
        <div className="space-y-2">
          {opportunities.map(opp => (
            <div
              key={opp.payment_id}
              className="card card-hover p-4 cursor-pointer flex items-center gap-4"
              onClick={() => navigate(`/ai-decision/${opp.payment_id}`)}
            >
              <div
                className="score-ring shrink-0"
                style={{
                  background: `${getScoreColor(opp.recovery_score)}18`,
                  color: getScoreColor(opp.recovery_score),
                }}
              >
                {Math.round(opp.recovery_score * 100)}%
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="font-mono text-[11px] text-[var(--color-primary)]">
                    {opp.payment_id}
                  </span>
                  <span className={`badge ${getPriorityBadge(opp.priority)}`}>{opp.priority}</span>
                </div>
                <div className="text-sm font-500" style={{ fontWeight: 500 }}>{opp.customer_name}</div>
                <div className="text-xs text-[var(--color-text-muted)]">{opp.failure_label}</div>
              </div>
              <div className="text-right shrink-0">
                <div className="text-sm font-700 amount" style={{ fontWeight: 700 }}>
                  {formatINR(opp.amount_inr)}
                </div>
                <div className="text-xs text-[var(--color-success)]">
                  exp. {formatINR(opp.expected_recovery_inr)}
                </div>
                <div className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  {formatRelative(opp.created_at)}
                </div>
              </div>
              <ChevronRight size={16} className="text-[var(--color-text-muted)] shrink-0" />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
