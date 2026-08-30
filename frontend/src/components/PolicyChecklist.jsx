import { CheckCircle, XCircle } from 'lucide-react'

export default function PolicyChecklist({ checks, status, reason }) {
  const approved = status === 'APPROVED'

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-600" style={{ fontWeight: 600 }}>Policy Check</span>
        <span className={`badge ${approved ? 'badge-success' : 'badge-danger'}`}>
          {approved ? '✓ APPROVED' : '✗ DENIED'}
        </span>
      </div>

      {checks && checks.length > 0 ? (
        <div>
          {checks.map((check, i) => (
            <div key={i} className="check-item">
              {check.passed ? (
                <CheckCircle size={14} className="text-[var(--color-success)] mt-0.5 shrink-0" />
              ) : (
                <XCircle size={14} className="text-[var(--color-danger)] mt-0.5 shrink-0" />
              )}
              <div>
                <div className="text-[var(--color-text)] text-xs font-500" style={{ fontWeight: 500 }}>
                  {check.check}
                </div>
                <div className="text-[var(--color-text-muted)] text-xs mt-0.5">
                  {check.detail}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {reason && !approved && (
        <div className="mt-3 p-2 rounded" style={{ background: 'rgba(239,68,68,0.08)' }}>
          <p className="text-xs text-[var(--color-danger)]">
            <strong>Denial reason:</strong> {reason}
          </p>
        </div>
      )}
    </div>
  )
}
