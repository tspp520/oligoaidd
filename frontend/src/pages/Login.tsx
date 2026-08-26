import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Dna, Eye, EyeOff, Loader2 } from 'lucide-react'
import { api } from '../api/client'
import { isAuthenticated, setToken, setUser } from '../utils/auth'

interface LoginData {
  success: boolean
  code?: string
  message?: string
  token?: string
  user?: { username: string; display_name: string; department: string; email: string }
  attempts_left?: number
  locked_until?: number
}

export default function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isAuthenticated()) navigate('/', { replace: true })
  }, [navigate])

  const fmtError = (d: LoginData): string => {
    if (d.code === 'USER_LOCKED' && d.locked_until) {
      const r = Math.max(0, Math.round((d.locked_until * 1000 - Date.now()) / 1000))
      return `账号已锁定，请 ${Math.floor(r / 60)}分${Math.floor(r % 60)}秒后重试`
    }
    if (d.code === 'WRONG_PASSWORD' && d.attempts_left != null)
      return `密码错误，还可尝试 ${d.attempts_left} 次`
    if (d.code === 'WRONG_PASSWORD_LAST_ATTEMPT') return '密码错误，仅剩最后 1 次机会'
    if (d.code === 'USER_LOCKED') return '账号已锁定，请稍后重试'
    if (d.code === 'AUTH_MISSING_CREDENTIALS') return '请输入工号和密码'
    if (d.message) return d.message === d.code ? '登录失败，请检查工号和密码' : d.message
    return '登录失败，请检查工号和密码'
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password) {
      setError('请输入工号和密码')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await api.post<LoginData>('/auth/login', {
        username: username.trim(),
        password,
      })
      const data = res.data
      if (data.success && data.token) {
        setToken(data.token)
        if (data.user) setUser(data.user)
        navigate('/', { replace: true })
      } else {
        setError(fmtError(data))
      }
    } catch {
      setError('网络错误，无法连接服务器')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg,#0f172a,#1e3a8a)',
      }}
    >
      <form
        onSubmit={submit}
        style={{
          width: 380,
          padding: 40,
          background: '#fff',
          borderRadius: 16,
          boxShadow: '0 20px 60px rgba(0,0,0,.3)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            justifyContent: 'center',
            marginBottom: 8,
          }}
        >
          <Dna color="#2563eb" size={30} />
          <h1 style={{ fontSize: 22 }}>OligoLab</h1>
        </div>
        <p style={{ textAlign: 'center', color: '#6b7280', marginBottom: 24 }}>
          小核酸药物研发平台 · 域账号登录
        </p>
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="工号（如 cp12398）"
          style={inp}
          autoFocus
        />
        <div style={{ position: 'relative' }}>
          <input
            type={show ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="AD 域密码"
            style={inp}
          />
          <button
            type="button"
            onClick={() => setShow(!show)}
            style={{
              position: 'absolute',
              right: 12,
              top: 12,
              background: 'none',
              border: 'none',
              cursor: 'pointer',
            }}
            aria-label="显示/隐藏密码"
          >
            {show ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
        {error && <p style={{ color: '#dc2626', fontSize: 13, margin: '8px 0' }}>{error}</p>}
        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%',
            padding: 12,
            marginTop: 16,
            background: '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontSize: 15,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
          }}
        >
          {loading && <Loader2 size={16} className="spin" />} 登 录
        </button>
      </form>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}.spin{animation:spin 1s linear infinite}`}</style>
    </div>
  )
}

const inp: React.CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  margin: '8px 0',
  border: '1px solid #d1d5db',
  borderRadius: 8,
  fontSize: 14,
}
