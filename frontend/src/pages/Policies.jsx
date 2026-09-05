import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useFetch } from '../hooks/useFetch'
import { policiesApi } from '../services/api'
import PageHeader from '../components/PageHeader'
import { Save, Shield } from 'lucide-react'

function PolicyField({ label, description, value, onChange, type = 'number', step }) {
  return (
    <div className="py-3 border-b border-[var(--color-border)] last:border-b-0">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="text-sm font-500" style={{ fontWeight: 500 }}>{label}</div>
          <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{description}</div>
        </div>
        {type === 'boolean' ? (
          <label className="flex items-center gap-2 cursor-pointer">
            <div
              className="w-10 h-5 rounded-full relative transition-colors"
              style={{ background: value ? 'var(--color-primary)' : 'var(--color-border)' }}
              onClick={() => onChange(!value)}
            >
              <div
                className="w-3.5 h-3.5 rounded-full bg-white absolute top-[3px] transition-transform"
                style={{ left: value ? '22px' : '3px' }}
              />
            </div>
            <span className="text-xs text-[var(--color-text-muted)]">{value ? 'Enabled' : 'Disabled'}</span>
          </label>
        ) : (
          <input
            type={type}
            step={step}
            value={value}
            onChange={e => onChange(type === 'number' ? parseFloat(e.target.value) : e.target.value)}
            className="w-28 px-2 py-1 rounded text-sm text-right bg-[var(--color-surface-2)] border border-[var(--color-border)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-primary)]"
          />
        )}
      </div>
    </div>
  )
}

export default function Policies() {
  const [searchParams] = useSearchParams()
  const paymentId = searchParams.get('payment_id')
  const { data, loading, error, refetch } = useFetch(() => policiesApi.get())
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [form, setForm] = useState(null)

  const policy = form || data || {}

  const set = (key, val) => setForm(prev => ({ ...(prev || data), [key]: val }))

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    try {
      await policiesApi.update(form || data)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
      refetch()
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fade-in">
      <PageHeader
        title="Policy Engine"
        subtitle="Configure guardrails that gate AI recovery recommendations"
        onRefresh={refetch}
        loading={loading}
        action={
          <div className="flex items-center gap-2">
            <Link to={paymentId ? `/ai-decision/${paymentId}` : '/opportunities'} className="btn btn-secondary btn-sm">
              {paymentId ? 'Back to AI Decision →' : 'View Recovery Opportunities →'}
            </Link>
            <button
              className={`btn btn-sm ${saved ? 'btn-success' : 'btn-primary'}`}
              onClick={handleSave}
              disabled={saving || !form}
            >
              {saving ? <div className="spinner" style={{ width: 13, height: 13 }} /> : <Save size={13} />}
              {saved ? 'Saved!' : 'Save Policy'}
            </button>
          </div>
        }
      />

      <div className="policy-context-note">
        These rules govern whether an AI-generated recovery recommendation can be executed.
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Left: Guardrail limits */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-4">
            <Shield size={16} className="text-[var(--color-primary)]" />
            <div className="text-sm font-600" style={{ fontWeight: 600 }}>Guardrail Limits</div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-40"><div className="spinner" /></div>
          ) : error ? (
            <div className="text-sm text-[var(--color-danger)]">{error}</div>
          ) : (
            <>
              <PolicyField
                label="Max Retries"
                description="Maximum number of recovery retry attempts per payment"
                value={policy.max_retries ?? 2}
                onChange={v => set('max_retries', Math.round(v))}
              />
              <PolicyField
                label="Max Recovery Actions"
                description="Maximum total recovery actions per payment"
                value={policy.max_recovery_actions ?? 3}
                onChange={v => set('max_recovery_actions', Math.round(v))}
              />
              <PolicyField
                label="Min Recovery Score"
                description="Minimum score required to attempt recovery (0–1)"
                value={policy.min_recovery_score ?? 0.4}
                onChange={v => set('min_recovery_score', v)}
                step="0.05"
              />
              <PolicyField
                label="Max Transaction Amount (₹)"
                description="Recovery is blocked for payments above this amount"
                value={policy.max_transaction_amount ?? 1000000}
                onChange={v => set('max_transaction_amount', v)}
              />
            </>
          )}
        </div>

        {/* Right: Stop conditions */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-4">
            <Shield size={16} className="text-[var(--color-danger)]" />
            <div className="text-sm font-600" style={{ fontWeight: 600 }}>Stopping Rules</div>
          </div>

          <PolicyField
            label="Stop on Payment Success"
            description="Immediately stop recovery when payment is captured"
            value={policy.stop_if_payment_success ?? true}
            onChange={v => set('stop_if_payment_success', v)}
            type="boolean"
          />
          <PolicyField
            label="Stop on Customer Opt-Out"
            description="Never contact customers who have opted out"
            value={policy.stop_if_customer_optout ?? true}
            onChange={v => set('stop_if_customer_optout', v)}
            type="boolean"
          />

          <div className="mt-4 p-3 rounded text-xs" style={{ background: 'var(--color-surface-2)' }}>
            <div className="font-600 text-[var(--color-text)] mb-2" style={{ fontWeight: 600 }}>Additional stopping rules (hardcoded)</div>
            <ul className="space-y-1 text-[var(--color-text-muted)]">
              <li>✓ Stop if duplicate successful recovery exists</li>
              <li>✓ Stop if retry limit reached</li>
              <li>✓ Stop if recovery score below threshold</li>
              <li>✓ Stop if transaction amount exceeds max</li>
              <li>✓ Escalate after configured failure threshold</li>
              <li>✓ AI recommendation "STOP" is always honored</li>
            </ul>
          </div>

          <div className="mt-4 p-3 rounded border border-[var(--color-warning)]/20" style={{ background: 'rgba(245,158,11,0.06)' }}>
            <div className="text-xs font-600 text-[var(--color-warning)] mb-1" style={{ fontWeight: 600 }}>
              Policy Principle
            </div>
            <div className="text-xs text-[var(--color-text-muted)] leading-relaxed">
              The AI can <strong className="text-[var(--color-text)]">recommend</strong> any action,
              but the policy engine <strong className="text-[var(--color-text)]">decides</strong> what
              is actually executed. No financial action bypasses the policy engine.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
