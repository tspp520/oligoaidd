import { useNavigate } from 'react-router-dom'
import { logout } from '../utils/auth'
import { MODULES } from '../data/modules'

const iconColor = ['#2563eb', '#7c3aed', '#0d9488', '#dc2626', '#ea580c', '#059669', '#0284c7']

export default function Home() {
  const navigate = useNavigate()
  return (
    <div style={{ minHeight: '100vh', padding: '40px 48px' }}>
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 32,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: '#2563eb',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 24,
              fontWeight: 700,
            }}
          >
            O
          </div>
          <div>
            <h1 style={{ fontSize: 24 }}>OligoLab · 小核酸药物研发平台</h1>
            <p style={{ color: '#6b7280', fontSize: 14 }}>
              公司内网 SaaS · 点击卡片在新标签页查看模块介绍
            </p>
          </div>
        </div>
        <button
          onClick={() => {
            logout()
            navigate('/login', { replace: true })
          }}
          style={{
            padding: '8px 18px',
            border: '1px solid #d1d5db',
            borderRadius: 8,
            background: '#fff',
            cursor: 'pointer',
          }}
        >
          退出登录
        </button>
      </header>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: 24,
        }}
      >
        {MODULES.map((m, i) => (
          <a
            key={m.slug}
            href={`/module/${m.slug}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              background: '#fff',
              borderRadius: 16,
              padding: 24,
              border: '1px solid #e5e7eb',
              boxShadow: '0 4px 16px rgba(0,0,0,.04)',
              display: 'flex',
              flexDirection: 'column',
              gap: 14,
              transition: 'transform .15s, box-shadow .15s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-4px)'
              e.currentTarget.style.boxShadow = '0 12px 28px rgba(0,0,0,.1)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = ''
              e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,.04)'
            }}
          >
            <div
              style={{
                width: 46,
                height: 46,
                borderRadius: 12,
                background: `${iconColor[i % iconColor.length]}16`,
                color: iconColor[i % iconColor.length],
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: 20,
              }}
            >
              {String(i + 1).padStart(2, '0')}
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                <h3 style={{ fontSize: 18 }}>{m.name}</h3>
                <span
                  style={{
                    fontSize: 12,
                    color: '#b45309',
                    background: '#fef3c7',
                    padding: '2px 8px',
                    borderRadius: 10,
                  }}
                >
                  {m.status}
                </span>
              </div>
              <p style={{ color: '#6b7280', fontSize: 14, lineHeight: 1.6 }}>{m.summary}</p>
            </div>
            <span style={{ color: '#2563eb', fontSize: 13 }}>点击查看 →</span>
          </a>
        ))}
      </div>
    </div>
  )
}
