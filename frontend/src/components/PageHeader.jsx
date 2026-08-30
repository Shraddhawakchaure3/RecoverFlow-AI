import { RefreshCw } from 'lucide-react'

export default function PageHeader({ title, subtitle, action, onRefresh, loading }) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h1 className="text-xl font-700 text-[var(--color-text)]" style={{ fontWeight: 700 }}>{title}</h1>
        {subtitle && (
          <p className="text-sm text-[var(--color-text-muted)] mt-0.5">{subtitle}</p>
        )}
      </div>
      <div className="flex items-center gap-2">
        {onRefresh && (
          <button
            className="btn btn-secondary btn-sm"
            onClick={onRefresh}
            disabled={loading}
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        )}
        {action}
      </div>
    </div>
  )
}
