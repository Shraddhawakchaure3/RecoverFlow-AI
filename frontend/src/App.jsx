import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import CommandCenter from './pages/CommandCenter'
import Opportunities from './pages/Opportunities'
import AIDecisionList from './pages/AIDecisionList'
import AIDecision from './pages/AIDecision'
import AuditTrail from './pages/AuditTrail'
import Evaluation from './pages/Evaluation'
import DemoScenarios from './pages/DemoScenarios'
import Policies from './pages/Policies'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden" style={{ background: 'var(--color-bg)' }}>
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6">
          <Routes>
            <Route path="/" element={<CommandCenter />} />
            <Route path="/opportunities" element={<Opportunities />} />
            <Route path="/opportunities/:paymentId" element={<AIDecision />} />
            <Route path="/ai-decision" element={<AIDecisionList />} />
            <Route path="/ai-decision/:paymentId" element={<AIDecision />} />
            <Route path="/audit" element={<AuditTrail />} />
            <Route path="/evaluation" element={<Evaluation />} />
            <Route path="/demo" element={<DemoScenarios />} />
            <Route path="/policies" element={<Policies />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
