import { Navigate, useParams } from 'react-router-dom'
import { MODULES } from '../data/modules'
import Literature from './Literature'

export default function Module() {
  const { slug } = useParams()
  const m = MODULES.find((x) => x.slug === slug)
  if (!m) return <Navigate to="/" replace />
  // 文献与知识库：直接渲染 Markdown 文档库（左侧文档栏目 + 右侧渲染）
  if (slug === 'literature') return <Literature />
  return (
    <div style={{ minHeight: '100vh', padding: '48px 56px', maxWidth: 880, margin: '0 auto' }}>
      <a href="/" style={{ color: '#2563eb' }}>
        ← 返回首页
      </a>
      <div
        style={{
          marginTop: 20,
          background: '#fff',
          borderRadius: 16,
          padding: 40,
          border: '1px solid #e5e7eb',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <h1 style={{ fontSize: 28 }}>{m.name}</h1>
          <span
            style={{
              fontSize: 13,
              color: '#b45309',
              background: '#fef3c7',
              padding: '3px 10px',
              borderRadius: 12,
            }}
          >
            {m.status}
          </span>
        </div>
        <p style={{ color: '#4b5563', fontSize: 16, lineHeight: 1.8, marginBottom: 24 }}>
          {m.summary}
        </p>
        <h3 style={{ marginBottom: 12, color: '#111827' }}>功能规划</h3>
        <ul style={{ paddingLeft: 22, lineHeight: 2, color: '#374151' }}>
          {m.features.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
        {m.url ? (
          <>
            <a
              href={m.url}
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'inline-block',
                marginTop: 24,
                padding: '10px 22px',
                background: '#2563eb',
                color: '#fff',
                borderRadius: 8,
                textDecoration: 'none',
                fontWeight: 600,
              }}
            >
              打开工具（新标签页）
            </a>
          </>
        ) : (
          <p style={{ marginTop: 24, color: '#9ca3af', fontSize: 13 }}>
            当前为占位页面，具体功能开发中，敬请期待。
          </p>
        )}
      </div>
    </div>
  )
}
