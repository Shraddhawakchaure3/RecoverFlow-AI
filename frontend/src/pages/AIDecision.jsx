import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useFetch } from '../hooks/useFetch'
import { opportunitiesApi, recoveryApi } from '../services/api'
import {
  formatINR, formatDate, formatPct, getStatusBadge,
  getPriorityBadge, getActionLabel, getScoreColor
} from '../utils/format'
import PageHeader from '../components/PageHeader'
import RecoveryScoreBar from '../components/RecoveryScoreBar'
import PolicyChecklist from '../components/PolicyChecklist'
import AuditTimeline from '../components/AuditTimeline'
import {
  ArrowLeft, Brain, Zap, DollarSign, AlertTriangle,
  CheckCircle, XCircle, Play, Clock
} from 'lucide-react'

function Section({ title, children, className = '' }) {
  return (
    <div className={`card p-4 ${className}`}>
      <div className="text-sm font-600 mb-3 text-[var(--color-text)]" style={{ fontWeight: 600 }}>
        {title}
      </div>
      {children}
    </div>
  )
}

function KV({ label, value, mono, highlight }) {
  return (
    <div className="flex items-start justify-between py-1.5 border-b border-[var(--color-border)] last:border-b-0">
      <span className="text-xs text-[var(--color-text-muted)] flex-shrink-0 mr-4">{label}</span>
      <span
        className={`text-xs text-right ${mono ? 'font-mono' : ''}`}
        style={{ color: highlight || 'var(--color-text)', fontWeight: highlight ? 600 : 400 }}
      >
        {value || '—'}
      </span>
    </div>
  )
}

export default function AIDecision() {
  const { paymentId } = useParams()
  const [analyzing, setAnalyzing] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [executeResult, setExecuteResult] = useState(null)
  const [actionError, setActionError] = useState(null)

  const { data, loading, error, refetch } = useFetch(
    () => opportunitiesApi.get(paymentId),
    [paymentId]
  )

  const handleAnalyze = async () => {
    setAnalyzing(true)
    setActionError(null)
    setAnalysisResult(null)
    try {
      const res = await recoveryApi.analyze(paymentId)
      setAnalysisResult(res.data)
    } catch (e) {
      setActionError(e.message)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleExecute = async () => {
    setExecuting(true)
    setActionError(null)
    try {
      const res = await recoveryApi.execute(paymentId)
      setExecuteResult(res.data)
      refetch()
    } catch (e) {
      setActionError(e.message)
    } finally {
      setExecuting(false)
    }
  }

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
        <Link to="/opportunities" className="btn btn-secondary btn-sm mt-2">
          <ArrowLeft size={13} /> Back
        </Link>
      </div>
    )
  }

  const opp = data || {}
  const payment = opp.payment || {}
  const customer = opp.customer || {}
  const analysis = analysisResult?.analysis || opp
  const aiDecision = analysisResult?.ai_decision
  const policyDecision = analysisResult?.policy_decision
  const latestAction = opp.recovery_actions?.[0]

  const displayScore = analysisResult ? analysis.recovery_score : opp.recovery_score
  const displayBreakdown = analysisResult
    ? analysis.score_breakdown?.feature_scores
    : opp.score_breakdown?.feature_scores

  return (
    <div className="fade-in">
      <PageHeader
        title="AI Decision Center"
        subtitle={`Analyzing payment ${paymentId}`}
        action={
          <Link to="/ai-decision" className="btn btn-secondary btn-sm">
            <ArrowLeft size={13} /> All Opportunities
          </Link>
        }
      />

      <div className="grid grid-cols-3 gap-4">
        {/* Left col — payment + customer */}
        <div className="space-y-4">
          <Section title="Payment Details">
            <KV label="Payment ID" value={payment.payment_id} mono />
            <KV label="Order ID" value={payment.order_id} mono />
            <KV label="Amount" value={formatINR(payment.amount / 100)} highlight="var(--color-warning)" />
            <KV label="Method" value={payment.method} />
            <KV label="Bank" value={payment.bank} />
            <KV label="Status" value={
              <span className={`badge ${getStatusBadge(payment.status)}`}>{payment.status}</span>
            } />
            <KV label="Failure" value={payment.failure_reason} />
            <KV label="Failure Type" value={
              <span className="badge badge-danger">{opp.failure_type}</span>
            } />
          </Section>

          <Section title="Customer">
            <KV label="Name" value={customer.name} />
            <KV label="Email" value={customer.email} />
            <KV label="Total Payments" value={customer.total_payments} />
            <KV label="Successful" value={customer.successful_payments} />
            <KV label="Failed" value={customer.failed_payments} />
            <KV label="Opted Out" value={customer.opted_out ? 'Yes' : 'No'} />
          </Section>
        </div>

        {/* Middle col — score + AI decision */}
        <div className="space-y-4">
          <Section title="Recovery Analysis">
            <RecoveryScoreBar
              score={displayScore}
              breakdown={displayBreakdown}
            />
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="text-center p-3 rounded" style={{ background: 'var(--color-surface-2)' }}>
                <div className="text-xs text-[var(--color-text-muted)]">Recovery Prob.</div>
                <div className="text-lg font-700 mt-1" style={{ fontWeight: 700, color: getScoreColor(displayScore) }}>
                  {Math.round((displayScore || 0) * 100)}%
                </div>
              </div>
              <div className="text-center p-3 rounded" style={{ background: 'var(--color-surface-2)' }}>
                <div className="text-xs text-[var(--color-text-muted)]">Expected Recovery</div>
                <div className="text-sm font-700 mt-1" style={{ fontWeight: 700, color: 'var(--color-success)' }}>
                  {formatINR(opp.expected_recovery_inr || 0)}
                </div>
              </div>
            </div>
            <div className="mt-3 p-3 rounded text-xs" style={{ background: 'var(--color-surface-2)' }}>
              <div className="text-[var(--color-text-muted)] mb-1">Root Cause</div>
              <div className="font-500 text-[var(--color-warning)]" style={{ fontWeight: 500 }}>
                {opp.failure_label}
              </div>
              <div className="text-[var(--color-text-muted)] mt-1 leading-relaxed">
                {opp.failure_explanation}
              </div>
            </div>
          </Section>

          {/* AI Decision Result */}
          {aiDecision ? (
            <Section title="AI Recommendation">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[var(--color-text-muted)]">Recommended Action</span>
                  <span className="badge badge-primary">{getActionLabel(aiDecision.recommended_action)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[var(--color-text-muted)]">Priority</span>
                  <span className={`badge ${getPriorityBadge(aiDecision.priority)}`}>{aiDecision.priority}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[var(--color-text-muted)]">Confidence</span>
                  <span className="text-xs font-600" style={{ fontWeight: 600 }}>
                    {Math.round((aiDecision.confidence || 0) * 100)}%
                  </span>
                </div>
                {aiDecision.delay_minutes > 0 && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[var(--color-text-muted)]">Delay</span>
                    <span className="text-xs">{aiDecision.delay_minutes} min</span>
                  </div>
                )}
                <div className="mt-2 p-2 rounded text-xs leading-relaxed" style={{ background: 'var(--color-surface-2)' }}>
                  <span className="text-[var(--color-text-muted)]">Reasoning: </span>
                  {aiDecision.reason}
                </div>
                <div className="text-[10px] text-[var(--color-text-muted)]">
                  {analysisResult?.used_ai ? '🤖 AI-generated decision' : '⚙ Deterministic fallback used'}
                </div>
              </div>
            </Section>
          ) : (
            <div className="card p-4 text-center">
              <Brain size={24} className="mx-auto mb-2 text-[var(--color-text-muted)]" />
              <div className="text-xs text-[var(--color-text-muted)] mb-3">
                Run analysis to get AI recommendation
              </div>
              <button
                className="btn btn-primary btn-sm w-full"
                onClick={handleAnalyze}
                disabled={analyzing}
              >
                {analyzing ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Analyzing…</> : <><Brain size={13} /> Analyze with AI</>}
              </button>
            </div>
          )}

          {/* Policy check */}
          {policyDecision && (
            <PolicyChecklist
              checks={policyDecision.checks}
              status={policyDecision.status}
              reason={policyDecision.reason}
            />
          )}

          {/* Execute button */}
          {analysisResult && (
            <div className="space-y-2">
              {!executeResult ? (
                <button
                  className="btn btn-success w-full"
                  onClick={handleExecute}
                  disabled={executing || !policyDecision?.approved}
                  style={{ opacity: policyDecision?.approved ? 1 : 0.5 }}
                >
                  {executing
                    ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Executing…</>
                    : <><Play size={13} /> Execute Recovery</>
                  }
                </button>
              ) : (
                <div className="card p-3">
                  {executeResult.success ? (
                    <div className="flex items-start gap-2">
                      <CheckCircle size={16} className="text-[var(--color-success)] mt-0.5" />
                      <div>
                        <div className="text-sm font-600 text-[var(--color-success)]" style={{ fontWeight: 600 }}>
                          Recovery Initiated
                        </div>
                        <div className="text-xs text-[var(--color-text-muted)] mt-1">
                          {executeResult.result?.result}
                        </div>
                        {executeResult.result?.razorpay_order_id && (
                          <div className="text-xs font-mono mt-1 text-[var(--color-primary)]">
                            Order: {executeResult.result.razorpay_order_id}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-start gap-2">
                      <XCircle size={16} className="text-[var(--color-danger)] mt-0.5" />
                      <div>
                        <div className="text-sm font-600 text-[var(--color-danger)]" style={{ fontWeight: 600 }}>
                          {executeResult.stopped ? 'Stopped' : 'Failed'}
                        </div>
                        <div className="text-xs text-[var(--color-text-muted)] mt-1">
                          {executeResult.reason}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {actionError && (
                <div className="text-xs text-[var(--color-danger)] p-2 rounded" style={{ background: 'rgba(239,68,68,0.08)' }}>
                  {actionError}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right col — audit trail */}
        <div className="space-y-4">
          <Section title="Audit Trail">
            <AuditTimeline entries={opp.audit_trail || []} />
          </Section>

          {opp.recovery_actions?.length > 0 && (
            <Section title="Recovery Actions">
              {opp.recovery_actions.map((action, i) => (
                <div key={i} className="check-item">
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-500" style={{ fontWeight: 500 }}>
                        #{action.attempt_number} {getActionLabel(action.action_type)}
                      </span>
                      <span className={`badge ${getStatusBadge(action.status)}`}>{action.status}</span>
                    </div>
                    <div className="text-xs text-[var(--color-text-muted)] mt-0.5">
                      Policy: {action.policy_status}
                    </div>
                    {action.amount_recovered && (
                      <div className="text-xs text-[var(--color-success)] mt-0.5">
                        Recovered: {formatINR(action.amount_recovered / 100)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </Section>
          )}
        </div>
      </div>
    </div>
  )
}
