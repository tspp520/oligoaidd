import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../api/client'

interface DocItem {
  name: string
  updated?: string
}

/** 把 md 内的相对资源路径解析为可访问 URL：
 *  - 相对路径（如 `./x.png`、`x.png`）→ `/literature/assets/<docName>/x.png`
 *  - 绝对 http(s)、data: 等原样保留
 */
function resolveAssetUrl(src: string, docName: string): string {
  if (/^(https?:|data:|blob:)/i.test(src)) return src
  if (src.startsWith('/literature/assets/')) return src
  const path = src.replace(/^\.\//, '')
  // 兼容平台挂在子路径下（BASE）
  const base =
    typeof window !== 'undefined' && location.pathname.indexOf('/offtarget') > 0
      ? '/offtarget'
      : ''
  return `${base}/literature/assets/${encodeURIComponent(docName)}/${path}`
}

export default function Literature() {
  const [docs, setDocs] = useState<DocItem[]>([])
  const [current, setCurrent] = useState<string | null>(null)
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 载入文档列表，默认选中第一篇
  useEffect(() => {
    api
      .get('/literature/docs')
      .then((res) => {
        const d: DocItem[] = res.data.docs || []
        setDocs(d)
        if (d.length) setCurrent(d[0].name)
      })
      .catch((e) => setError('文档列表加载失败：' + (e?.response?.data?.detail || e.message)))
  }, [])

  // 选中文档变化时拉取 md 原文
  useEffect(() => {
    if (!current) return
    setLoading(true)
    setError(null)
    api
      .get(`/literature/docs/${encodeURIComponent(current)}`)
      .then((res) => setContent(res.data.content || ''))
      .catch((e) => setError('文档加载失败：' + (e?.response?.data?.detail || e.message)))
      .finally(() => setLoading(false))
  }, [current])

  return (
    <div style={{ minHeight: '100vh', background: '#f4f6fb' }}>
      {/* 顶栏 */}
      <header
        style={{
          padding: '16px 32px',
          background: '#fff',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <a href="/" style={{ color: '#2563eb', textDecoration: 'none' }}>
          ← 返回
        </a>
        <h1 style={{ fontSize: 20, margin: 0 }}>📚 文献与知识库</h1>
        <span style={{ color: '#6b7280', fontSize: 13 }}>小核酸药物 · 内部知识文档</span>
      </header>

      <div style={{ display: 'flex', minHeight: 'calc(100vh - 61px)' }}>
        {/* 左侧：文档栏目（文件名 = 栏目名） */}
        <aside
          style={{
            width: 240,
            borderRight: '1px solid #e5e7eb',
            background: '#fff',
            overflowY: 'auto',
            flexShrink: 0,
          }}
        >
          <div style={{ padding: '12px 16px', fontSize: 13, color: '#6b7280' }}>文档列表</div>
          {docs.map((d) => {
            const active = d.name === current
            return (
              <button
                key={d.name}
                onClick={() => setCurrent(d.name)}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '12px 16px',
                  border: 'none',
                  borderLeft: active ? '3px solid #2563eb' : '3px solid transparent',
                  background: active ? '#eff6ff' : 'transparent',
                  cursor: 'pointer',
                  fontSize: 14,
                  color: active ? '#1d4ed8' : '#1f2937',
                  fontWeight: active ? 600 : 400,
                }}
              >
                {d.name}
              </button>
            )
          })}
          {!docs.length && (
            <div style={{ padding: 16, color: '#9ca3af', fontSize: 13 }}>暂无文档</div>
          )}
        </aside>

        {/* 右侧：Markdown 渲染 */}
        <main style={{ flex: 1, padding: '32px 40px', minWidth: 0 }}>
          {current && (
            <h2 style={{ fontSize: 16, color: '#6b7280', margin: '0 0 16px', fontWeight: 500 }}>
              {current}
            </h2>
          )}
          {error && (
            <div
              style={{
                background: '#fef2f2',
                border: '1px solid #fecaca',
                color: '#dc2626',
                borderRadius: 8,
                padding: 12,
                marginBottom: 16,
              }}
            >
              {error}
            </div>
          )}
          {loading && <div style={{ color: '#6b7280' }}>加载中…</div>}
          {!loading && content && (
            <article
              style={{
                background: '#fff',
                borderRadius: 12,
                border: '1px solid #e5e7eb',
                padding: '28px 36px',
                lineHeight: 1.8,
              }}
            >
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                urlTransform={(url) => resolveAssetUrl(url, current || '')}
              >
                {content}
              </ReactMarkdown>
            </article>
          )}
        </main>
      </div>
    </div>
  )
}
