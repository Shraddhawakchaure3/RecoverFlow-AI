import { ChevronDown, ShieldCheck } from 'lucide-react'

export default function TopHeader() {
  return (
    <header className="top-header">
      <div className="top-header-brand">
        <div className="top-header-title">RecoverFlow AI</div>
        <div className="top-header-subtitle">Autonomous Revenue Recovery</div>
      </div>
      <div className="top-header-actions">
        <span className="environment-pill"><ShieldCheck size={13} /> Razorpay Test Mode</span>
        <span className="synthetic-pill">Synthetic Data</span>
        <button className="merchant-switcher" type="button">
          Demo Merchant <ChevronDown size={14} />
        </button>
      </div>
    </header>
  )
}
