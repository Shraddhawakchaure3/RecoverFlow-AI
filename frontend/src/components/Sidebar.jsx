import { NavLink } from 'react-router-dom'
import {
  BarChart3, Zap, Brain, FileText, FlaskConical, Play, Shield
} from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', icon: BarChart3, label: 'Command Center', end: true },
  { to: '/opportunities', icon: Zap, label: 'Revenue Opportunities' },
  { to: '/ai-decision', icon: Brain, label: 'AI Decision' },
  { to: '/audit', icon: FileText, label: 'Audit Trail' },
  { to: '/evaluation', icon: FlaskConical, label: 'Evaluation' },
  { to: '/demo', icon: Play, label: 'Demo Scenarios' },
  { to: '/policies', icon: Shield, label: 'Policies' },
]

export default function Sidebar() {
  return (
    <aside className="sidebar h-screen sticky top-0 flex flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)] overflow-y-auto">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-[var(--color-primary)] flex items-center justify-center">
            <Zap size={14} className="text-white" />
          </div>
          <div>
            <div className="text-[13px] font-700 text-[var(--color-text)] leading-none" style={{ fontWeight: 700 }}>RecoverFlow</div>
            <div className="text-[10px] text-[var(--color-text-muted)] leading-none mt-0.5">AI Revenue Recovery</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-0.5">
        <div className="text-[10px] font-600 text-[var(--color-text-muted)] uppercase tracking-widest px-3 py-2 mt-1" style={{ fontWeight: 600 }}>
          Navigation
        </div>
        {NAV_ITEMS.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `nav-item ${isActive ? 'active' : ''}`
            }
          >
            <Icon size={15} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-[var(--color-border)]">
        <div className="text-[10px] text-[var(--color-text-muted)]">
          Track 03 — Razorpay AI Buildathon 2026
        </div>
        <div className="text-[10px] text-[var(--color-primary)] mt-0.5">Test Mode Active</div>
      </div>
    </aside>
  )
}
