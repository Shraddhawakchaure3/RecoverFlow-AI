import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAutoRefetch } from '../hooks/useFetch'
import { dashboardApi } from '../services/api'
import { formatINR, formatPct, getScoreColor } from '../utils/format'
import PageHeader from '../components/PageHeader'
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import {
  TrendingUp, AlertTriangle, CheckCircle, Shield, Zap, RefreshCw, Clock
} from 'lucide-react'

const COLORS = ['#4f7fff', '#22c55e', '#f59e0b', '#ef4444', '#a78bfa', '#38bdf8']

function MetricCard({ label, value, sub, icon: Icon, color = 'var(--color-primary)', delta }) {
  return (
    <div className="metric-card">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="metric-label">{label}</div>
          <div className="metric-value mt-1 amount" style={{ color }}>
            {value}
          </div>
          {sub && <div className="text-xs text-[var(--color-text-muted)] mt-1">{sub}</div>}
        </div>
        {Icon && (
          <div className="p-2 rounded-md ml-3 shrink-0" style={{ background: `${color}18` }}>
            <Icon size={18} style={{ color }} />
          </div>
        )}
      </div>
    </div>
  )
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="card p-2 text-xs">
      <div className="text-[var(--color-text-muted)] mb-1">{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color }}>
          {p.name}: {formatINR(p.value)}
        </div>
      ))}
    </div>
  )
}

function Pipeline({ data }) {
  const processed = (data.active_recovery_actions || 0) + (data.successful_recoveries || 0) +
    (data.policy_blocked_actions || 0) + (data.stopped_actions || 0)
  const stages = [
    { label: 'Failed Payments', value: data.payments_at_risk || 0, tone: 'danger', to: '/opportunities' },
    { label: 'Analyzed', value: processed, tone: 'primary' },
    { label: 'Recovery Opportunities', value: data.active_recovery_actions || 0, tone: 'info', to: '/opportunities' },
    { label: 'Policy Approved', value: (data.active_recovery_actions || 0) + (data.successful_recoveries || 0), tone: 'warning', to: '/policies' },
    { label: 'Recovered', value: data.successful_recoveries || 0, tone: 'success', to: '/audit' },
  ]

  return (
    <section className="pipeline-section">
      <div className="section-kicker">Revenue Recovery Pipeline</div>
      <div className="pipeline-track">
        {stages.map((stage, index) => (
          <div className="pipeline-stage" key={stage.label}>
            {stage.to ? (
              <Link to={stage.to} className="pipeline-link" title={`Open ${stage.label}`}>
                <div className={`pipeline-node ${stage.tone}`}><span>{stage.value.toLocaleString()}</span></div>
                <div className="pipeline-label">{stage.label}</div>
              </Link>
            ) : (
              <><div className={`pipeline-node ${stage.tone}`}><span>{stage.value.toLocaleString()}</span></div><div className="pipeline-label">{stage.label}</div></>
            )}
            {index < stages.length - 1 && <div className="pipeline-connector" />}
          </div>
        ))}
      </div>
    </section>
  )
}

export default function CommandCenter() {
  const { data, loading, error, refetch } = useAutoRefetch(
    () => dashboardApi.getSummary(),
    30000
  )

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="spinner mx-auto mb-3" />
          <div className="text-sm text-[var(--color-text-muted)]">Loading dashboard…</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="card p-4 border-red-500/30">
          <div className="text-[var(--color-danger)] text-sm font-500" style={{ fontWeight: 500 }}>
            ⚠ Backend unavailable: {error}
          </div>
          <button className="btn btn-secondary btn-sm mt-2" onClick={refetch}>
            <RefreshCw size={12} /> Retry
          </button>
        </div>
      </div>
    )
  }

  const d = data || {}
  const recoveryRatePct = d.recovery_rate ? Math.round(d.recovery_rate * 100) : 0

  // Prepare chart data
  const trendData = (d.revenue_trend || []).map(t => ({
    date: t.date?.slice(5), // MM-DD
    'At Risk': Math.round(t.at_risk),
  }))

  const failureData = (d.failure_type_breakdown || []).map(f => ({
    name: f.type?.replace(/_/g, ' ').replace('FAILURE', '').trim(),
    value: f.count,
    amount: f.amount_inr,
  }))

  const recoveryData = [
    { name: 'Recovered', value: d.revenue_recovered_inr || 0, color: '#22c55e' },
    { name: 'Unrecovered', value: Math.max(0, (d.revenue_at_risk_inr || 0) - (d.revenue_recovered_inr || 0)), color: '#1e2230' },
  ]

  return (
    <div className="fade-in">
      <PageHeader
        title="Command Center"
        subtitle="Live revenue recovery overview"
        onRefresh={refetch}
        loading={loading}
      />

      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <MetricCard
          label="Revenue at Risk"
          value={formatINR(d.revenue_at_risk_inr || 0)}
          sub={`${d.payments_at_risk || 0} failed payments`}
          icon={AlertTriangle}
          color="var(--color-danger)"
        />
        <MetricCard
          label="Expected Recoverable"
          value={formatINR(d.expected_recoverable_inr || 0)}
          sub="Based on recovery probability"
          icon={TrendingUp}
          color="var(--color-warning)"
        />
        <MetricCard
          label="Revenue Recovered"
          value={formatINR(d.revenue_recovered_inr || 0)}
          sub={`${d.successful_recoveries || 0} successful recoveries`}
          icon={CheckCircle}
          color="var(--color-success)"
        />
        <MetricCard
          label="Recovery Rate"
          value={`${recoveryRatePct}%`}
          sub="Of all recovery attempts"
          icon={TrendingUp}
          color={getScoreColor(d.recovery_rate || 0)}
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <MetricCard
          label="Active Recoveries"
          value={d.active_recovery_actions ?? '—'}
          icon={Zap}
          color="var(--color-info)"
        />
        <MetricCard
          label="Policy Blocked"
          value={d.policy_blocked_actions ?? '—'}
          sub="Actions denied by policy"
          icon={Shield}
          color="var(--color-purple)"
        />
        <MetricCard
          label="Stopped Actions"
          value={d.stopped_actions ?? '—'}
          sub="AI recommended STOP"
          icon={Clock}
          color="var(--color-text-muted)"
        />
        <MetricCard
          label="Checkout Abandonments"
          value={d.checkout_abandonments ?? '—'}
          icon={AlertTriangle}
          color="var(--color-warning)"
        />
      </div>

      <Pipeline data={d} />

      {/* Charts Row 1 */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        {/* Revenue at Risk Trend */}
        <div className="card p-4 col-span-2">
          <div className="text-sm font-600 mb-4" style={{ fontWeight: 600 }}>Revenue at Risk — Last 30 Days</div>
          {trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `₹${(v/1000).toFixed(0)}K`} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="At Risk" stroke="#ef4444" fill="url(#riskGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-40 flex items-center justify-center text-sm text-[var(--color-text-muted)]">
              No trend data yet — seed the database to see charts
            </div>
          )}
        </div>

        {/* Recovered vs Unrecovered */}
        <div className="card p-4">
          <div className="text-sm font-600 mb-4" style={{ fontWeight: 600 }}>Recovery Status</div>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie
                data={recoveryData}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={65}
                paddingAngle={2}
                dataKey="value"
              >
                {recoveryData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => formatINR(v)} />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-2 space-y-1">
            {recoveryData.map((item, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-sm" style={{ background: item.color }} />
                  <span className="text-[var(--color-text-muted)]">{item.name}</span>
                </div>
                <span className="amount">{formatINR(item.value)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Charts Row 2 */}
      {failureData.length > 0 && (
        <div className="card p-4">
          <div className="text-sm font-600 mb-4" style={{ fontWeight: 600 }}>Revenue at Risk by Failure Type</div>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={failureData} layout="vertical">
              <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `₹${(v/1000).toFixed(0)}K`} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#9ca3af', fontSize: 10 }} axisLine={false} tickLine={false} width={110} />
              <Tooltip formatter={(v) => formatINR(v)} />
              <Bar dataKey="amount" radius={[0, 4, 4, 0]}>
                {failureData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Empty State */}
      {!data && (
        <div className="card p-8 text-center mt-4">
          <div className="text-[var(--color-text-muted)] text-sm">
            No data yet. Run the dataset generator to populate the dashboard.
          </div>
          <div className="mt-2 text-xs text-[var(--color-text-muted)] font-mono">
            cd data && python generate_dataset.py
          </div>
        </div>
      )}
    </div>
  )
}
