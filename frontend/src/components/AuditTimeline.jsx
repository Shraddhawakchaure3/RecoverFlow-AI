import { formatDate } from '../utils/format'
import { CheckCircle, AlertCircle, Clock, XCircle, Zap, Shield, BarChart3, Play } from 'lucide-react'

const EVENT_ICONS = {
  RECOVERY_WORKFLOW_STARTED: Play,
  ROOT_CAUSE_ANALYZED: Zap,
  RECOVERY_SCORE_COMPUTED: BarChart3,
  AI_DECISION_GENERATED: Zap,
  POLICY_CHECKED: Shield,
  RECOVERY_ACTION_EXECUTED: CheckCircle,
  RECOVERY_SUCCESS: CheckCircle,
  RECOVERY_STOPPED: XCircle,
  RECOVERY_BLOCKED_BY_POLICY: XCircle,
  RECOVERY_STOPPED_BY_AI: XCircle,
  RECOVERY_PAYMENT_FAILED: AlertCircle,
}

const EVENT_COLORS = {
  RECOVERY_SUCCESS: '#22c55e',
  RECOVERY_STOPPED: '#ef4444',
  RECOVERY_BLOCKED_BY_POLICY: '#ef4444',
  RECOVERY_STOPPED_BY_AI: '#9ca3af',
  RECOVERY_PAYMENT_FAILED: '#ef4444',
  POLICY_CHECKED: '#a78bfa',
  AI_DECISION_GENERATED: '#4f7fff',
}

function getEventStyle(event) {
  return {
    color: EVENT_COLORS[event] || '#6b7280',
    Icon: EVENT_ICONS[event] || Clock,
  }
}

export default function AuditTimeline({ entries }) {
  if (!entries || entries.length === 0) {
    return (
      <div className="text-center py-8 text-[var(--color-text-muted)] text-sm">
        No audit entries found
      </div>
    )
  }

  return (
    <div className="relative">
      {/* Vertical line */}
      <div
        className="absolute left-[17px] top-0 bottom-0 w-px"
        style={{ background: 'var(--color-border)' }}
      />

      <div className="space-y-4">
        {entries.map((entry, i) => {
          const { color, Icon } = getEventStyle(entry.event)
          return (
            <div key={entry.log_id || i} className="flex gap-4 relative fade-in">
              {/* Icon */}
              <div
                className="w-[34px] h-[34px] rounded-full flex items-center justify-center shrink-0 z-10 border"
                style={{
                  background: 'var(--color-surface)',
                  borderColor: color,
                  color,
                }}
              >
                <Icon size={13} />
              </div>

              {/* Content */}
              <div className="flex-1 pb-2">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="text-[13px] font-500 text-[var(--color-text)]" style={{ fontWeight: 500 }}>
                      {entry.event?.replace(/_/g, ' ')}
                    </div>
                    {entry.result && (
                      <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{entry.result}</div>
                    )}
                    {entry.action && (
                      <div className="text-xs mt-0.5" style={{ color: 'var(--color-primary)' }}>
                        Action: {entry.action}
                      </div>
                    )}
                    {entry.amount_recovered && (
                      <div className="text-xs mt-0.5" style={{ color: 'var(--color-success)' }}>
                        Recovered: ₹{(entry.amount_recovered / 100).toLocaleString('en-IN')}
                      </div>
                    )}
                  </div>
                  <div className="text-[11px] text-[var(--color-text-muted)] whitespace-nowrap shrink-0">
                    {formatDate(entry.timestamp)}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
