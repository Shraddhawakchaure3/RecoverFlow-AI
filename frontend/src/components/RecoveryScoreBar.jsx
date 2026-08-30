import { getScoreColor } from '../utils/format'

export default function RecoveryScoreBar({ score, probability, breakdown }) {
  const pct = Math.round((score || 0) * 100)
  const color = getScoreColor(score)

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-[var(--color-text-muted)]">Recovery Score</span>
        <span className="text-sm font-700" style={{ color, fontWeight: 700 }}>{pct}%</span>
      </div>
      <div className="progress mb-3">
        <div
          className="progress-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>

      {breakdown && (
        <div className="space-y-1.5 mt-3">
          {Object.entries(breakdown).map(([key, val]) => {
            const label = {
              customer_history: 'Customer History (30%)',
              failure_type: 'Failure Type (25%)',
              retry_history: 'Retry History (20%)',
              transaction_value: 'Transaction Value (15%)',
              recency: 'Recency / Engagement (10%)',
            }[key] || key
            const pctVal = Math.round(val * 100)
            return (
              <div key={key}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-[var(--color-text-muted)]">{label}</span>
                  <span className="text-[var(--color-text)]">{pctVal}%</span>
                </div>
                <div className="progress" style={{ height: 3 }}>
                  <div
                    className="progress-fill"
                    style={{
                      width: `${pctVal}%`,
                      background: getScoreColor(val),
                    }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
