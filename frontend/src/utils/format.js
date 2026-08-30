/**
 * Format a number as Indian Rupees
 */
export function formatINR(amount, options = {}) {
  const { compact = false } = options
  if (amount === null || amount === undefined) return '—'
  
  if (compact) {
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`
  }
  
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount)
}

/**
 * Format a percentage
 */
export function formatPct(value) {
  if (value === null || value === undefined) return '—'
  return `${(value * 100).toFixed(1)}%`
}

/**
 * Format a datetime string
 */
export function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Format date relative (e.g., "2 hours ago")
 */
export function formatRelative(dateStr) {
  if (!dateStr) return '—'
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  const hours = Math.floor(mins / 60)
  const days = Math.floor(hours / 24)
  if (days > 0) return `${days}d ago`
  if (hours > 0) return `${hours}h ago`
  if (mins > 0) return `${mins}m ago`
  return 'just now'
}

/**
 * Get badge class for status
 */
export function getStatusBadge(status) {
  const map = {
    success: 'badge-success',
    captured: 'badge-success',
    approved: 'badge-info',
    executing: 'badge-info',
    pending: 'badge-warning',
    failed: 'badge-danger',
    blocked: 'badge-danger',
    stopped: 'badge-muted',
    unactioned: 'badge-muted',
    created: 'badge-muted',
  }
  return map[status?.toLowerCase()] || 'badge-muted'
}

/**
 * Get badge class for priority
 */
export function getPriorityBadge(priority) {
  const map = {
    HIGH: 'badge-danger',
    MEDIUM: 'badge-warning',
    LOW: 'badge-muted',
  }
  return map[priority] || 'badge-muted'
}

/**
 * Get color for recovery score
 */
export function getScoreColor(score) {
  if (score >= 0.75) return '#22c55e'
  if (score >= 0.50) return '#f59e0b'
  return '#ef4444'
}

/**
 * Get action type label
 */
export function getActionLabel(action) {
  const map = {
    RETRY_RECOVERY: 'Immediate Retry',
    DELAYED_RECOVERY: 'Delayed Recovery',
    CHECKOUT_RECOVERY: 'New Checkout',
    PAYMENT_REMINDER: 'Payment Reminder',
    ALTERNATE_PAYMENT_METHOD: 'Alternate Method',
    ESCALATE: 'Escalate',
    STOP: 'Stop Recovery',
  }
  return map[action] || action
}

/**
 * Failure type label
 */
export function getFailureLabel(type) {
  const map = {
    TEMPORARY_BANK_FAILURE: 'Bank Failure',
    NETWORK_TIMEOUT: 'Network Timeout',
    PAYMENT_METHOD_FAILURE: 'Method Failure',
    CUSTOMER_ACTION_REQUIRED: 'Customer Action',
    MULTIPLE_FAILED_ATTEMPTS: 'Multiple Failures',
    CHECKOUT_ABANDONMENT: 'Abandoned',
    UNKNOWN: 'Unknown',
  }
  return map[type] || type
}
