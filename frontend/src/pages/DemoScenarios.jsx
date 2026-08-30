import { useState } from 'react'
import { useFetch } from '../hooks/useFetch'
import { demoApi } from '../services/api'
import PageHeader from '../components/PageHeader'
import { formatINR, getStatusBadge } from '../utils/format'
import {
  Play, CheckCircle, XCircle, AlertTriangle, Zap, Shield, Copy, RefreshCw
} from 'lucide-react'

const SCENARIO_ICONS = {
  high_recovery_success: CheckCircle,
  low_recovery_stop: XCircle,
  retry_limit_reached: AlertTriangle,
  checkout_abandonment: Zap,
  duplicate_webhook: Copy,
  payment_success_stop: CheckCircle,
  policy_block: Shield,
}

const SCENARIO_COLORS = {
  high_recovery_success: 'var(--color-success)',
  low_recovery_stop: 'var(--color-danger)',
  retry_limit_reached: 'var(--color-warning)',
  checkout_abandonment: 'var(--color-info)',
  duplicate_webhook: 'var(--color-purple)',
  payment_success_stop: 'var(--color-success)',
  policy_block: 'var(--color-danger)',
}

export default function DemoScenarios() {
  const [running, setRunning] = useState(null)
  const [results, setResults] = useState({})
  const [errors, setErrors] = useState({})

  const { data, loading } = useFetch(() => demoApi.listScenarios())
  const scenarios = data?.scenarios || []

  const runScenario = async (id) => {
    setRunning(id)
    setErrors(prev => ({ ...prev, [id]: null }))
    try {
      const res = await demoApi.runScenario(id)
      setResults(prev => ({ ...prev, [id]: res.data }))
    } catch (e) {
      setErrors(prev => ({ ...prev, [id]: e.message }))
    } finally {
      setRunning(null)
    }
  }

  return (
    <div className="fade-in">
      <PageHeader
        title="Demo Scenarios"
        subtitle="Controlled scenarios that run through the real backend workflow"
      />

      <div className="mb-4 px-3 py-2 rounded text-xs text-[var(--color-warning)] border border-[var(--color-warning)]/20" style={{ background: 'rgba(245,158,11,0.06)' }}>
        ⚡ Each scenario creates real synthetic data and executes the full DETECT → DIAGNOSE → SCORE → DECIDE → POLICY → EXECUTE pipeline.
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="spinner" /></div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {scenarios.map(scenario => {
            const Icon = SCENARIO_ICONS[scenario.id] || Play
            const color = SCENARIO_COLORS[scenario.id] || 'var(--color-primary)'
            const result = results[scenario.id]
            const err = errors[scenario.id]
            const isRunning = running === scenario.id

            return (
              <div key={scenario.id} className="card p-4">
                <div className="flex items-start gap-3 mb-3">
                  <div className="p-2 rounded" style={{ background: `${color}18` }}>
                    <Icon size={16} style={{ color }} />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-600" style={{ fontWeight: 600 }}>{scenario.name}</div>
                    <div className="text-xs text-[var(--color-text-muted)] mt-0.5 leading-relaxed">
                      {scenario.description}
                    </div>
                  </div>
                </div>

                <button
                  className="btn btn-secondary btn-sm w-full mb-3"
                  onClick={() => runScenario(scenario.id)}
                  disabled={isRunning}
                >
                  {isRunning
                    ? <><div className="spinner" style={{ width: 13, height: 13 }} /> Running…</>
                    : <><Play size={12} /> Run Scenario</>
                  }
                </button>

                {err && (
                  <div className="text-xs text-[var(--color-danger)] p-2 rounded mb-2" style={{ background: 'rgba(239,68,68,0.08)' }}>
                    ✗ {err}
                  </div>
                )}

                {result && (
                  <div className="rounded overflow-hidden border border-[var(--color-border)]">
                    {/* Header */}
                    <div
                      className="px-3 py-2 flex items-center justify-between"
                      style={{ background: result.success ? 'rgba(34,197,94,0.08)' : result.stopped ? 'rgba(107,114,128,0.08)' : 'rgba(239,68,68,0.08)' }}
                    >
                      <div className="flex items-center gap-1.5 text-xs font-500" style={{ fontWeight: 500 }}>
                        {result.success ? (
                          <><CheckCircle size={12} className="text-[var(--color-success)]" /> Recovery Initiated</>
                        ) : result.stopped ? (
                          <><AlertTriangle size={12} className="text-[var(--color-warning)]" /> Stopped</>
                        ) : (
                          <><XCircle size={12} className="text-[var(--color-danger)]" /> Blocked/Failed</>
                        )}
                      </div>
                      {result.payment_id && (
                        <span className="text-[10px] font-mono text-[var(--color-text-muted)]">
                          {result.payment_id}
                        </span>
                      )}
                    </div>

                    {/* Result details */}
                    <div className="p-3 text-xs space-y-1">
                      {result.reason && (
                        <div><span className="text-[var(--color-text-muted)]">Reason: </span>{result.reason}</div>
                      )}
                      {result.result?.result && (
                        <div><span className="text-[var(--color-text-muted)]">Action: </span>{result.result.result}</div>
                      )}
                      {result.result?.razorpay_order_id && (
                        <div><span className="text-[var(--color-text-muted)]">Order: </span>
                          <span className="font-mono text-[var(--color-primary)]">{result.result.razorpay_order_id}</span>
                        </div>
                      )}
                      {result.result?.status && (
                        <div className="flex items-center gap-1.5">
                          <span className="text-[var(--color-text-muted)]">Status: </span>
                          <span className={`badge ${getStatusBadge(result.result.status)}`}>{result.result.status}</span>
                        </div>
                      )}
                      {/* Policy checks */}
                      {result.result?.policy_checks?.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-[var(--color-border)]">
                          <div className="text-[var(--color-text-muted)] mb-1">Policy checks:</div>
                          {result.result.policy_checks.map((c, i) => (
                            <div key={i} className="flex items-center gap-1">
                              {c.passed
                                ? <CheckCircle size={10} className="text-[var(--color-success)]" />
                                : <XCircle size={10} className="text-[var(--color-danger)]" />
                              }
                              <span className={c.passed ? '' : 'text-[var(--color-danger)]'}>
                                {c.check}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                      {/* Duplicate webhook special */}
                      {result.duplicate_detected !== undefined && (
                        <div className={`font-500 ${result.duplicate_detected ? 'text-[var(--color-success)]' : 'text-[var(--color-danger)]'}`} style={{ fontWeight: 500 }}>
                          Idempotency: {result.duplicate_detected ? '✓ Duplicate correctly rejected' : '✗ Duplicate not detected'}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
