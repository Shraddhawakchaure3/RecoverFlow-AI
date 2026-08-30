import { useFetch } from '../hooks/useFetch'
import { evaluationApi } from '../services/api'
import { formatINR, formatPct } from '../utils/format'
import PageHeader from '../components/PageHeader'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  RadialBarChart, RadialBar, Cell, Legend
} from 'recharts'
import { TrendingUp, Target, Zap, Shield, AlertTriangle } from 'lucide-react'

function StatBox({ label, value, sub, color = 'var(--color-text)' }) {
  return (
    <div className="text-center p-4 rounded" style={{ background: 'var(--color-surface-2)' }}>
      <div className="text-xs text-[var(--color-text-muted)] mb-1">{label}</div>
      <div className="text-xl font-700 amount" style={{ fontWeight: 700, color }}>{value}</div>
      {sub && <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{sub}</div>}
    </div>
  )
}

export default function Evaluation() {
  const { data, loading, error, refetch } = useFetch(() => evaluationApi.get())

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="text-[var(--color-danger)] text-sm">{error}</div>
      </div>
    )
  }

  const d = data || {}
  const overview = d.overview || {}
  const baseline = d.baseline || {}
  const ai = d.recoverflow_ai || {}
  const comparison = d.comparison || {}
  const priority = d.priority_breakdown || {}
  const failureBreakdown = d.failure_type_breakdown || []

  // Comparison chart data
  const comparisonData = [
    {
      name: 'Recovered (INR)',
      Baseline: baseline.estimated_recovered_inr || 0,
      'RecoverFlow AI': ai.recovered_inr || 0,
    },
    {
      name: 'Recovery Rate %',
      Baseline: Math.round((baseline.estimated_recovery_rate || 0) * 100),
      'RecoverFlow AI': Math.round((ai.recovery_rate || 0) * 100),
    },
  ]

  const failureChart = failureBreakdown.map(f => ({
    name: f.failure_type?.replace(/_/g, ' ').slice(0, 18),
    attempts: f.attempts,
    recovered: f.recovered,
    rate: Math.round((f.recovery_rate || 0) * 100),
  }))

  return (
    <div className="fade-in">
      <PageHeader
        title="Batch Evaluation"
        subtitle={d.label || 'Synthetic evaluation results'}
        onRefresh={refetch}
        loading={loading}
      />

      {d.note && (
        <div className="mb-4 px-3 py-2 rounded text-xs text-[var(--color-info)] border border-[var(--color-info)]/20" style={{ background: 'rgba(56,189,248,0.06)' }}>
          ℹ {d.note}
        </div>
      )}

      {/* Overview */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatBox
          label="Total Transactions"
          value={overview.total_transactions?.toLocaleString() || '0'}
        />
        <StatBox
          label="Revenue at Risk"
          value={formatINR(overview.total_at_risk_inr || 0)}
          color="var(--color-danger)"
        />
        <StatBox
          label="Failed Payments"
          value={overview.failed_payments?.toLocaleString() || '0'}
          color="var(--color-warning)"
        />
        <StatBox
          label="Already Recovered"
          value={overview.captured_payments?.toLocaleString() || '0'}
          color="var(--color-success)"
        />
      </div>

      {/* Comparison */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Baseline */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-sm bg-[#6b7280]" />
            <span className="text-sm font-600" style={{ fontWeight: 600 }}>Baseline Strategy</span>
          </div>
          <div className="text-xs text-[var(--color-text-muted)] mb-3">{baseline.strategy}</div>
          <div className="grid grid-cols-3 gap-2">
            <StatBox label="Attempts" value={baseline.recovery_attempts?.toLocaleString() || '0'} />
            <StatBox
              label="Recovered"
              value={formatINR(baseline.estimated_recovered_inr || 0)}
              color="var(--color-warning)"
            />
            <StatBox
              label="Recovery Rate"
              value={`${Math.round((baseline.estimated_recovery_rate || 0) * 100)}%`}
            />
          </div>
        </div>

        {/* AI */}
        <div className="card p-4" style={{ borderColor: 'var(--color-primary)' }}>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-sm bg-[var(--color-primary)]" />
            <span className="text-sm font-600 text-[var(--color-primary)]" style={{ fontWeight: 600 }}>RecoverFlow AI</span>
            {comparison.improvement_pct > 0 && (
              <span className="badge badge-success">+{comparison.improvement_pct?.toFixed(1)}%</span>
            )}
          </div>
          <div className="text-xs text-[var(--color-text-muted)] mb-3">{ai.strategy}</div>
          <div className="grid grid-cols-3 gap-2">
            <StatBox label="Attempts" value={ai.recovery_attempts?.toLocaleString() || '0'} />
            <StatBox
              label="Recovered"
              value={formatINR(ai.recovered_inr || 0)}
              color="var(--color-success)"
            />
            <StatBox
              label="Recovery Rate"
              value={`${Math.round((ai.recovery_rate || 0) * 100)}%`}
              color="var(--color-success)"
            />
          </div>
        </div>
      </div>

      {/* Additional AI metrics */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <div className="card p-3 text-center">
          <div className="text-xs text-[var(--color-text-muted)]">Successful Recoveries</div>
          <div className="text-2xl font-700 text-[var(--color-success)] mt-1" style={{ fontWeight: 700 }}>
            {ai.successful_recoveries || 0}
          </div>
        </div>
        <div className="card p-3 text-center">
          <div className="text-xs text-[var(--color-text-muted)]">Policy Blocked</div>
          <div className="text-2xl font-700 text-[var(--color-purple)] mt-1" style={{ fontWeight: 700 }}>
            {ai.policy_blocked || 0}
          </div>
        </div>
        <div className="card p-3 text-center">
          <div className="text-xs text-[var(--color-text-muted)]">Stopped by AI</div>
          <div className="text-2xl font-700 text-[var(--color-text-muted)] mt-1" style={{ fontWeight: 700 }}>
            {ai.stopped_by_ai || 0}
          </div>
        </div>
        <div className="card p-3 text-center">
          <div className="text-xs text-[var(--color-text-muted)]">Interventions Saved</div>
          <div className="text-2xl font-700 text-[var(--color-info)] mt-1" style={{ fontWeight: 700 }}>
            {ai.unnecessary_interventions_avoided || 0}
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-4">
        {/* Baseline vs AI Recovery */}
        <div className="card p-4">
          <div className="text-sm font-600 mb-3" style={{ fontWeight: 600 }}>Baseline vs RecoverFlow AI</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={[{
              name: 'Recovered',
              Baseline: baseline.estimated_recovered_inr || 0,
              'RecoverFlow AI': ai.recovered_inr || 0,
            }]}>
              <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `₹${(v/1000).toFixed(0)}K`} />
              <Tooltip formatter={v => formatINR(v)} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="Baseline" fill="#4b5563" radius={[4, 4, 0, 0]} />
              <Bar dataKey="RecoverFlow AI" fill="#4f7fff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Failure type breakdown */}
        <div className="card p-4">
          <div className="text-sm font-600 mb-3" style={{ fontWeight: 600 }}>Recovery Rate by Failure Type</div>
          {failureChart.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={failureChart} layout="vertical">
                <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} unit="%" domain={[0, 100]} />
                <YAxis type="category" dataKey="name" tick={{ fill: '#9ca3af', fontSize: 9 }} axisLine={false} tickLine={false} width={120} />
                <Tooltip formatter={v => `${v}%`} />
                <Bar dataKey="rate" fill="#22c55e" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-40 flex items-center justify-center text-sm text-[var(--color-text-muted)]">
              No evaluation data yet
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
