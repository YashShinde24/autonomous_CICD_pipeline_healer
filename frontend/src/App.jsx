import { useState, useEffect } from 'react'
import { supabase } from './supabase'
import './App.css'

function App() {
  const [session, setSession] = useState(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [message, setMessage] = useState(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => subscription.unsubscribe()
  }, [])

  const handleSignUp = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setMessage(null)
    const { error } = await supabase.auth.signUp({
      email,
      password,
    })
    if (error) setError(error.message)
    else setMessage('Check your email for the verification link!')
    setLoading(false)
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setMessage(null)
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    if (error) setError(error.message)
    setLoading(false)
  }

  const handleGoogleLogin = async () => {
    setLoading(true)
    setError(null)
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: 'http://localhost:5173',
      },
    })
    if (error) setError(error.message)
    setLoading(false)
  }

  const handleLogout = async () => {
    setLoading(true)
    const { error } = await supabase.auth.signOut()
    if (error) setError(error.message)
    setLoading(false)
  }

  if (session) {
    return (
      <div className="container">
        <h1>Welcome!</h1>
        <p>You are logged in as: <strong>{session.user.email}</strong></p>
        <div className="protected-section">
          <h2>Protected Content</h2>
          <p>This content is only visible to authenticated users.</p>
        </div>
        <button onClick={handleLogout} disabled={loading}>
          {loading ? 'Logging out...' : 'Logout'}
        </button>
      </div>
    )
  }

  return (
    <div className="container">
      <h1>Supabase Auth</h1>
      <form>
        <div>
          <label>Email:</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Your email"
          />
        </div>
        <div>
          <label>Password:</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Your password"
          />
        </div>
        <div className="button-group">
          <button onClick={handleLogin} disabled={loading}>
            {loading ? 'Loading...' : 'Login'}
          </button>
          <button onClick={handleSignUp} disabled={loading}>
            {loading ? 'Loading...' : 'Sign Up'}
          </button>
        </div>
      </form>
      <div className="oauth-section">
        <p>Or sign in with:</p>
        <button onClick={handleGoogleLogin} disabled={loading} className="google-btn">
          Sign in with Google
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {message && <p className="message">{message}</p>}
    </div>
  )
}

export default App
