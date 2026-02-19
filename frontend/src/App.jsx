import { useState, useEffect, useCallback, useRef } from 'react'
import { supabase } from './supabase'
import './App.css'

// API Base URL
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ============== API Service ==============
const api = {
  // Get system status
  async getStatus() {
    const res = await fetch(`${API_URL}/api/status`)
    return res.json()
  },

  // Get dashboard stats
  async getStats() {
    const res = await fetch(`${API_URL}/api/stats`)
    return res.json()
  },

  // Get recent actions
  async getActions() {
    const res = await fetch(`${API_URL}/api/actions`)
    return res.json()
  },

  // Get latency data
  async getLatency() {
    const res = await fetch(`${API_URL}/api/latency`)
    return res.json()
  },

  // Create and start a new pipeline run
  async createRun(repoUrl, branch = 'main') {
    const res = await fetch(`${API_URL}/api/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_url: repoUrl, branch })
    })
    return res.json()
  },

  // Get all runs
  async getRuns() {
    const res = await fetch(`${API_URL}/api/runs`)
    return res.json()
  },

  // Get specific run
  async getRun(runId) {
    const res = await fetch(`${API_URL}/api/runs/${runId}`)
    return res.json()
  },

  // Get run status
  async getRunStatus(runId) {
    const res = await fetch(`${API_URL}/api/runs/${runId}/status`)
    return res.json()
  }
}

// ============== WebSocket Hook ==============
function useWebSocket(runId) {
  const [updates, setUpdates] = useState([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)

  useEffect(() => {
    if (!runId) return

    // Connect to WebSocket
    const ws = new WebSocket(`ws://localhost:8000/ws`)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      // Subscribe to run updates
      ws.send(JSON.stringify({ type: 'subscribe', run_id: runId }))
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setUpdates(prev => [...prev, data])
      } catch (e) {
        console.error('WebSocket message error:', e)
      }
    }

    ws.onclose = () => {
      setConnected(false)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    return () => {
      ws.close()
    }
  }, [runId])

  return { updates, connected }
}

// ============== Main App Component ==============
function App() {
  const [session, setSession] = useState(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  
  // Dashboard state
  const [systemStatus, setSystemStatus] = useState(null)
  const [stats, setStats] = useState(null)
  const [recentActions, setRecentActions] = useState([])
  const [latencyData, setLatencyData] = useState([])
  const [activeView, setActiveView] = useState('overview')
  const [searchQuery, setSearchQuery] = useState('')

  // Pipeline state
  const [showPipelineModal, setShowPipelineModal] = useState(false)
  const [repoUrl, setRepoUrl] = useState('')
  const [branch, setBranch] = useState('main')
  const [currentRun, setCurrentRun] = useState(null)
  const [runProgress, setRunProgress] = useState(null)
  const [pipelineLogs, setPipelineLogs] = useState([])
  const [isRunning, setIsRunning] = useState(false)

  // WebSocket for real-time updates
  const { updates, connected } = useWebSocket(currentRun?.id)

  // Process WebSocket updates
  useEffect(() => {
    if (updates.length > 0) {
      const latest = updates[updates.length - 1]
      
      if (latest.type === 'pipeline_update') {
        setRunProgress({
          status: latest.status,
          progress: latest.progress,
          current_step: latest.current_step,
          iteration: latest.iteration,
          failures_detected: latest.failures_detected || [],
          fixes_applied: latest.fixes_applied || [],
        })
        setPipelineLogs(latest.logs || [])
      } else if (latest.type === 'pipeline_complete') {
        setIsRunning(false)
        setRunProgress({
          status: latest.status,
          progress: latest.progress,
          current_step: latest.current_step,
          score: latest.score,
          total_time_seconds: latest.total_time_seconds,
          total_failures: latest.total_failures,
          total_fixes: latest.total_fixes,
        })
      } else if (latest.type === 'pipeline_error') {
        setIsRunning(false)
        setRunProgress({
          status: 'FAILED',
          current_step: latest.error,
        })
      }
    }
  }, [updates])

  // Auth check
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => subscription.unsubscribe()
  }, [])

  // Fetch dashboard data
  useEffect(() => {
    if (session) {
      fetchDashboardData()
      const interval = setInterval(fetchDashboardData, 5000)
      return () => clearInterval(interval)
    }
  }, [session])

  const fetchDashboardData = async () => {
    try {
      const [statusData, statsData, actionsData, latency] = await Promise.all([
        api.getStatus(),
        api.getStats(),
        api.getActions(),
        api.getLatency()
      ])
      
      setSystemStatus(statusData)
      setStats(statsData)
      setRecentActions(actionsData)
      setLatencyData(latency.regions || [])
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err)
      // Use mock data
      setSystemStatus({ status: 'Autonomous Agent Active', active_nodes: 142, uptime: 99.99, region: 'US-EAST-1' })
      setStats({ active_deployments: 12, ai_confidence: 98.4, error_rate: 0.02, infra_cost: 2450 })
      setLatencyData([
        { name: 'US-EAST-1', latency: 12, percentage: 85 },
        { name: 'EU-WEST-1', latency: 42, percentage: 45 },
        { name: 'AP-SOUTH-1', latency: 68, percentage: 30 }
      ])
      setRecentActions([
        { id: '1', type: 'Kubernetes Auto-scaled', description: 'Traffic spike detected in US-West cluster.', timestamp: new Date().toISOString(), status: 'success' },
        { id: '2', type: 'Security Vulnerability Patched', description: 'Identified CVE-2024-5120 in base image.', timestamp: new Date().toISOString(), status: 'success' },
        { id: '3', type: 'Node Health Remediation', description: 'Node i-0a2f1b unresponsive. Restarted.', timestamp: new Date().toISOString(), status: 'success' }
      ])
    }
  }

  // Auth handlers
  const handleSignUp = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    const { error } = await supabase.auth.signUp({ email, password })
    if (error) setError(error.message)
    else setMessage('Check your email for verification!')
    setLoading(false)
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) setError(error.message)
    setLoading(false)
  }

  const handleGoogleLogin = async () => {
    setLoading(true)
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin }
    })
    if (error) setError(error.message)
    setLoading(false)
  }

  const handleLogout = async () => {
    await supabase.auth.signOut()
  }

  // Pipeline handlers
  const handleStartPipeline = async (e) => {
    e.preventDefault()
    if (!repoUrl) return

    setLoading(true)
    try {
      const run = await api.createRun(repoUrl, branch)
      setCurrentRun(run)
      setIsRunning(true)
      setPipelineLogs(run.logs || [])
      setRunProgress({
        status: run.status,
        progress: 0,
        current_step: run.current_step
      })
      setShowPipelineModal(false)
    } catch (err) {
      setError('Failed to start pipeline: ' + err.message)
    }
    setLoading(false)
  }

  const formatTimeAgo = (date) => {
    const diff = Date.now() - new Date(date)
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    if (minutes < 60) return `${minutes} min ago`
    if (hours < 24) return `${hours} hours ago`
    return `${Math.floor(hours / 24)} days ago`
  }

  // Login Screen
  if (!session) {
    return (
      <div className="login-container">
        <div className="login-card">
          <div className="login-header">
            <div className="logo-container">
              <span className="material-symbols-outlined logo-icon">bolt</span>
            </div>
            <h1>NEURAL OPS</h1>
            <p className="login-subtitle">DevOps AI Command Center</p>
          </div>
          
          {message && <div className="message success">{message}</div>}
          {error && <div className="message error">{error}</div>}

          <form onSubmit={handleLogin}>
            <div className="form-group">
              <input type="email" placeholder="Your email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="form-group">
              <input type="password" placeholder="Your password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            <div className="button-group">
              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? 'Loading...' : 'Sign In'}
              </button>
              <button onClick={handleSignUp} disabled={loading} type="button" className="btn-secondary">
                Sign Up
              </button>
            </div>
          </form>

          <div className="divider"><span>or</span></div>

          <button onClick={handleGoogleLogin} disabled={loading} className="btn-google">
            <span className="material-symbols-outlined">account_circle</span>
            Sign in with Google
          </button>
        </div>
      </div>
    )
  }

  // Dashboard
  return (
    <div className="dashboard">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo-icon-container">
            <span className="material-symbols-outlined">bolt</span>
          </div>
          <span className="logo-text">NEURAL OPS</span>
        </div>
        
        <nav className="sidebar-nav">
          <a className={`nav-item ${activeView === 'overview' ? 'active' : ''}`} onClick={() => setActiveView('overview')}>
            <span className="material-symbols-outlined">grid_view</span>
            <span>Overview</span>
          </a>
          <a className={`nav-item ${activeView === 'pipelines' ? 'active' : ''}`} onClick={() => setActiveView('pipelines')}>
            <span className="material-symbols-outlined">account_tree</span>
            <span>Pipelines</span>
          </a>
          <a className={`nav-item ${activeView === 'health' ? 'active' : ''}`} onClick={() => setActiveView('health')}>
            <span className="material-symbols-outlined">analytics</span>
            <span>Agent Health</span>
          </a>
          <a className={`nav-item ${activeView === 'infra' ? 'active' : ''}`} onClick={() => setActiveView('infra')}>
            <span className="material-symbols-outlined">database</span>
            <span>Infrastructure</span>
          </a>
          <a className={`nav-item ${activeView === 'settings' ? 'active' : ''}`} onClick={() => setActiveView('settings')}>
            <span className="material-symbols-outlined">settings</span>
            <span>Settings</span>
          </a>
        </nav>
        
        <div className="sidebar-footer">
          <div className="node-region glass-card">
            <p className="label">NODE REGION</p>
            <div className="region-info">
              <div className="pulse-dot"></div>
              <span>{systemStatus?.region || 'US-EAST-1'}</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {/* Header */}
        <header className="header glass-card">
          <div className="search-container">
            <span className="material-symbols-outlined search-icon">search</span>
            <input type="text" placeholder="Search clusters, logs, or neural tasks..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
          </div>
          
          <div className="header-right">
            <div className="status-badge">
              <span className="pulse-dot"></span>
              <span>System Online</span>
            </div>
            
            <div className="user-section">
              <div className="user-info">
                <p className="user-name">{session.user.email?.split('@')[0] || 'User'}</p>
                <p className="user-role">Lead DevOps</p>
              </div>
              <div className="user-avatar gradient-border">
                <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuCUFEICIRiQt-xfmhFErOalZfpNEIsrsLvkUVVzvojPooI94j1iwt3fbPro4x3lzHtjVmTx-8bH2egXXQJeD01NW9d9gD18Ypww0bM92ZjS2VeCN_8JUatWCCDUBM0-ALui4CJOpOSZh5Y8ahE2xyTgHATsd4hSfNjhZ24LrZWEBO2f34SuWdYGcsU_mUlz_S9sW76bejnH30iCGjf8tuKr8nMw6ePe1avfTaE7sNV9QNsAhAdrRaR8byOoxb-xF-r-QDtkzT51clg" alt="User" />
              </div>
              <button onClick={handleLogout} className="logout-btn">
                <span className="material-symbols-outlined">logout</span>
              </button>
            </div>
          </div>
        </header>

        {/* Dashboard Content */}
        <div className="dashboard-content">
          {/* Hero Section */}
          <section className="gradient-border neon-shadow-blue">
            <div className="hero-card">
              <div className="hero-bg-effect"></div>
              <div className="hero-content">
                <div className="hero-text">
                  <div className="hero-title">
                    <span className="material-symbols-outlined hero-icon">verified_user</span>
                    <h2>Autonomous Agent Active</h2>
                  </div>
                  <p className="hero-description">
                    Neural engine is currently monitoring <span className="highlight-primary">{systemStatus?.active_nodes || 142} nodes</span> across 3 global regions. Uptime remains optimal at <span className="highlight-white">{systemStatus?.uptime || 99.99}%</span>.
                  </p>
                  <div className="hero-buttons">
                    <button className="btn-primary" onClick={() => setShowPipelineModal(true)}>
                      <span className="material-symbols-outlined">play_arrow</span>
                      Run Pipeline
                    </button>
                    <button className="btn-outline">
                      <span className="material-symbols-outlined">visibility</span>
                      Cluster Map
                    </button>
                  </div>
                </div>
                <div className="hero-stats glass-card">
                  <div className="uptime-display">
                    <div className="uptime-value">{systemStatus?.uptime || 99.9}<span className="uptime-unit">%</span></div>
                    <div className="uptime-label">REAL-TIME UPTIME</div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Stats Grid */}
          <section className="stats-grid">
            <div className="stat-card glass-card">
              <div className="stat-header">
                <div className="stat-icon primary"><span className="material-symbols-outlined">rocket_launch</span></div>
                <div className="pulse-dot"></div>
              </div>
              <h3 className="stat-label">Active Deployments</h3>
              <div className="stat-value">{stats?.active_deployments || 12} <span className="stat-change">+2 Today</span></div>
            </div>

            <div className="stat-card glass-card">
              <div className="stat-header">
                <div className="stat-icon secondary"><span className="material-symbols-outlined">psychology</span></div>
                <span className="stat-badge secondary">+0.5%</span>
              </div>
              <h3 className="stat-label">AI Confidence</h3>
              <div className="stat-value confidence">
                <div className="circular-progress">
                  <svg viewBox="0 0 36 36">
                    <circle className="circular-bg" cx="18" cy="18" r="16" />
                    <circle className="circular-progress-bar" cx="18" cy="18" r="16" strokeDasharray={`${stats?.ai_confidence || 98.4}, 100`} />
                  </svg>
                  <span className="progress-text">{stats?.ai_confidence || 98}%</span>
                </div>
                <div className="confidence-value">{stats?.ai_confidence || 98.4}<span className="unit secondary">%</span></div>
              </div>
            </div>

            <div className="stat-card glass-card">
              <div className="stat-header">
                <div className="stat-icon success"><span className="material-symbols-outlined">analytics</span></div>
                <span className="stat-badge success">-12%</span>
              </div>
              <h3 className="stat-label">Error Rates</h3>
              <div className="stat-value">{stats?.error_rate || 0.02}<span className="unit success">%</span></div>
              <div className="progress-bar"><div className="progress-fill success"></div></div>
            </div>

            <div className="stat-card glass-card">
              <div className="stat-header">
                <div className="stat-icon primary"><span className="material-symbols-outlined">payments</span></div>
                <span className="stat-badge primary">Optimal</span>
              </div>
              <h3 className="stat-label">Infra Monthly Cost</h3>
              <div className="stat-value">${stats?.infra_cost || 2450} <span className="stat-sub">est.</span></div>
            </div>
          </section>

          {/* Pipeline Progress (when running) */}
          {isRunning && runProgress && (
            <section className="pipeline-progress">
              <div className="progress-card glass-card">
                <div className="progress-header">
                  <h3>
                    <span className="material-symbols-outlined">autorenew</span>
                    Pipeline Running
                  </h3>
                  <div className="progress-status">
                    <span className="pulse-dot"></span>
                    {runProgress.status}
                  </div>
                </div>
                
                <div className="progress-bar-container">
                  <div className="progress-bar-fill" style={{ width: `${runProgress.progress}%` }}></div>
                </div>
                
                <div className="progress-info">
                  <span className="progress-step">{runProgress.current_step}</span>
                  <span className="progress-percent">{Math.round(runProgress.progress)}%</span>
                </div>

                {runProgress.iteration && (
                  <div className="iteration-info">
                    <span>Iteration: {runProgress.iteration}</span>
                  </div>
                )}

                {runProgress.failures_detected?.length > 0 && (
                  <div className="failures-detected">
                    <h4>Failures Detected ({runProgress.failures_detected.length})</h4>
                    {runProgress.failures_detected.map((f, i) => (
                      <div key={i} className="failure-item">
                        <span className="file">{f.file}:{f.line}</span>
                        <span className="type">{f.type}</span>
                        <span className="message">{f.message}</span>
                      </div>
                    ))}
                  </div>
                )}

                {runProgress.fixes_applied?.length > 0 && (
                  <div className="fixes-applied">
                    <h4>Fixes Applied ({runProgress.fixes_applied.length})</h4>
                    {runProgress.fixes_applied.map((f, i) => (
                      <div key={i} className="fix-item">
                        <span className="file">{f.file}:{f.line}</span>
                        <span className="type success">{f.type}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Completed Pipeline Results */}
          {!isRunning && runProgress?.score && (
            <section className="pipeline-results">
              <div className="results-card glass-card">
                <div className="results-header">
                  <span className="material-symbols-outlined success-icon">check_circle</span>
                  <h3>Pipeline Completed</h3>
                </div>
                
                <div className="results-grid">
                  <div className="result-item">
                    <span className="result-label">Score</span>
                    <span className="result-value success">{runProgress.score}%</span>
                  </div>
                  <div className="result-item">
                    <span className="result-label">Time</span>
                    <span className="result-value">{runProgress.total_time_seconds}s</span>
                  </div>
                  <div className="result-item">
                    <span className="result-label">Failures</span>
                    <span className="result-value">{runProgress.total_failures}</span>
                  </div>
                  <div className="result-item">
                    <span className="result-label">Fixes</span>
                    <span className="result-value success">{runProgress.total_fixes}</span>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Main Content Grid */}
          <section className="content-grid">
            {/* Actions Section */}
            <div className="actions-section">
              <div className="section-header">
                <h3><span className="material-symbols-outlined">dynamic_feed</span>Recent AI Actions</h3>
                <a href="#" className="view-all">View All</a>
              </div>

              {recentActions.map((action) => (
                <div key={action.id} className={`action-card ${action.status === 'success' ? 'primary' : action.status === 'error' ? 'secondary' : 'success'}`}>
                  <div className="action-icon">
                    {action.type.includes('Kubernetes') && <span className="material-symbols-outlined">compress</span>}
                    {action.type.includes('Security') && <span className="material-symbols-outlined">security</span>}
                    {action.type.includes('Node') && <span className="material-symbols-outlined">dns</span>}
                    {!action.type.includes('Kubernetes') && !action.type.includes('Security') && !action.type.includes('Node') && <span className="material-symbols-outlined">auto_fix_high</span>}
                  </div>
                  <div className="action-content">
                    <div className="action-header">
                      <h4>{action.type}</h4>
                      <span className="action-time">{formatTimeAgo(action.timestamp)}</span>
                    </div>
                    <p className="action-description">"{action.description}"</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Right Column */}
            <div className="right-column">
              <div className="latency-card glass-card">
                <h3>Latency Distribution</h3>
                <div className="latency-list">
                  {latencyData.map((region) => (
                    <div key={region.name} className="latency-item">
                      <div className="latency-header">
                        <span className="region-name">{region.name}</span>
                        <span className="lat className={`latency-value ${region.name.includes('WEST') ? 'secondary' : 'primary'}`}>{region.latency}ms</span>
                      </div>
                      <div className="latency-bar">
                        <div className={`latency-fill ${region.name.includes('WEST') ? 'secondary' : 'primary'}`} style={{ width: `${region.percentage}%` }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="scan-card glass-card">
                <h3>Neural Scan</h3>
                <p className="scan-status">Scanning for infrastructure drifts...</p>
                <div className="scan-animation">
                  <div className="scanner">
                    <div className="scanner-ring"></div>
                    <span className="material-symbols-outlined">hub</span>
                  </div>
                </div>
                <button className="btn-outline full-width" onClick={() => setShowPipelineModal(true)}>Run Scan</button>
              </div>
            </div>
          </section>
        </div>

        {/* Terminal */}
        <footer className="terminal">
          <div className="terminal-header">
            <div className="terminal-info">
              <span className="material-symbols-outlined">terminal</span>
              <span>Neural Console v4.2.0</span>
              <span className="connection-status">
                <span className="dot success"></span>
                {connected ? 'CONNECTED' : 'DISCONNECTED'}
              </span>
            </div>
            <div className="terminal-actions">
              <button><span className="material-symbols-outlined">close_fullscreen</span></button>
              <button><span className="material-symbols-outlined">settings_ethernet</span></button>
            </div>
          </div>
          <div className="terminal-content">
            {(pipelineLogs.length > 0 ? pipelineLogs : [
              '[14:22:01] [INFO] AI Agent initializing neural pattern matching',
              '[14:22:05] [INFO] Monitoring ingress traffic peaks...',
              '[14:23:12] [SUCCESS] Node synchronization complete',
              '[14:24:45] [NEURAL] Predictive model suggests 15% increase',
              '[14:25:01] [INFO] Pre-warming pods...'
            ]).map((log, i) => (
              <div key={i} className="log-line">
                {log.includes('[SUCCESS]') && <span className="log-time">{log.split(']')[0]}]</span>}
                {log.includes('[SUCCESS]') && <span className="log-level success">[SUCCESS]</span>}
                {!log.includes('[SUCCESS]') && !log.includes('[INFO]') && !log.includes('[NEURAL]') && <span className="log-time">[{new Date().toLocaleTimeString()}]</span>}
                {!log.includes('[SUCCESS]') && !log.includes('[INFO]') && !log.includes('[NEURAL]') && <span className="log-level info">[INFO]</span>}
                {log.includes('[INFO]') && <span className="log-time">{log.split(']')[0]}]</span>}
                {log.includes('[INFO]') && <span className="log-level success">[INFO]</span>}
                {log.includes('[NEURAL]') && <span className="log-time">{log.split(']')[0]}]</span>}
                {log.includes('[NEURAL]') && <span className="log-level neural">[NEURAL]</span>}
                <span>{log.split('] ')[1] || log}</span>
              </div>
            ))}
            <div className="log-line cursor-line">
              <span className="log-time">[{new Date().toLocaleTimeString()}]</span>
              <span className="cursor pulse">_</span>
            </div>
          </div>
        </footer>
      </main>

      {/* Pipeline Modal */}
      {showPipelineModal && (
        <div className="modal-overlay" onClick={() => setShowPipelineModal(false)}>
          <div className="modal glass-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3><span className="material-symbols-outlined">rocket_launch</span>Run Pipeline</h3>
              <button className="close-btn" onClick={() => setShowPipelineModal(false)}>
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            
            <form onSubmit={handleStartPipeline}>
              <div className="form-group">
                <label>Repository URL</label>
                <input 
                  type="text" 
                  placeholder="https://github.com/owner/repo"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Branch</label>
                <input 
                  type="text" 
                  placeholder="main"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-outline" onClick={() => setShowPipelineModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? 'Starting...' : 'Start Pipeline'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Map Background */}
      <div className="map-background">
        <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuDZWV8kV-Ro00q49u2TiSzh8oiFh8Y2mvSAlLsyD0N_vKNhZ-JPzSNMJsyxrv02XalFf0XfV5iDJ0UvR-kazN8W12LJO2u2Dgadg1Tm3ZAcltB2CBOUVGbvLE-XfpvidbPEOh6ipDDJ-BD2cDGU7R3lvKfVEk6TRzwWaQJpmDDDp5JpxfPhXWJt-qk06nwRDOtICiD69byNzSmO-FCMAnioSrCngxY9_-LqFxU8sDv0eZ8aBcEjUX_WdRSwqdV_bcZruesINU3JzSw" alt="" />
      </div>
    </div>
  )
}

export default App
