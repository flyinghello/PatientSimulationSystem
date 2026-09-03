import { TopBar } from './primitives';
import { store } from '../game/store';

interface HistoryCase {
  day: string;
  name: string;
  cond: string;
  verdict: string;
  color: string;
}

const CASES: HistoryCase[] = [
  { day: '4月25日 周二', name: 'Aisha Rahman', cond: '高血压', verdict: '合格', color: 'var(--mint)' },
  { day: '4月24日 周一', name: 'Tom Whitford', cond: '心力衰竭', verdict: '勉强合格', color: 'var(--butter)' },
  { day: '4月24日 周一', name: 'Leila Haddad', cond: '扁桃体炎', verdict: '良好', color: 'var(--mint)' },
  { day: '4月21日 周五', name: 'Davy Chen', cond: '消化不良', verdict: '合格', color: 'var(--mint)' },
  { day: '4月20日 周四', name: 'Mei Tan', cond: '2型糖尿病', verdict: '良好', color: 'var(--mint)' },
  { day: '4月19日 周三', name: 'Priya Iyer', cond: '头痛', verdict: '勉强合格', color: 'var(--butter)' },
  { day: '4月18日 周二', name: 'Henrik Solberg', cond: '房颤', verdict: '明显不合格', color: 'var(--rose)' },
];

function TrendChart() {
  const series = [
    { color: 'var(--peach-deep)', pts: [40, 42, 38, 44, 46, 48, 52, 50, 55, 58, 54, 60] },
    { color: 'var(--mint-deep)', pts: [55, 58, 60, 58, 62, 64, 66, 68, 68, 70, 72, 74] },
    { color: 'var(--sky-deep)', pts: [60, 62, 65, 64, 68, 70, 72, 74, 75, 76, 78, 76] },
  ];
  const W = 980;
  const H = 180;
  const P = 16;
  const x = (i: number) => P + (i / 11) * (W - 2 * P);
  const y = (v: number) => H - P - (v / 100) * (H - 2 * P);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 180 }}>
      {[0, 25, 50, 75, 100].map((g, i) => (
        <g key={i}>
          <line
            x1={P}
            y1={y(g)}
            x2={W - P}
            y2={y(g)}
            stroke="rgba(43,30,22,0.08)"
            strokeWidth="1.5"
            strokeDasharray="3 5"
          />
          <text x={4} y={y(g) + 4} fontSize="9" fontFamily="Nunito" fontWeight="800" fill="var(--ink-2)">
            {g}
          </text>
        </g>
      ))}
      {series.map((s, si) => (
        <g key={si}>
          <path
            d={s.pts.map((v, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(v)}`).join(' ')}
            fill="none"
            stroke={s.color}
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {s.pts.map((v, i) => (
            <circle key={i} cx={x(i)} cy={y(v)} r="4" fill="white" stroke={s.color} strokeWidth="2.5" />
          ))}
        </g>
      ))}
    </svg>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <span style={{ width: 14, height: 14, borderRadius: 4, background: color, border: '2px solid var(--line)' }} />
      {label}
    </span>
  );
}

export function HistoryScreen() {
  return (
    <div className="screen" style={{ background: 'var(--cream)', overflowY: 'auto' }}>
      <TopBar here={1} steps={['主页', '训练记录']} />
      <div style={{ padding: '28px 36px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            justifyContent: 'space-between',
            marginBottom: 18,
          }}
        >
          <div>
            <h1 style={{ fontSize: 36 }}>你的训练记录</h1>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-2)', marginTop: 4 }}>
              趋势才是故事，而非任何单一病例。
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <span className="chip butter">最近 30 天</span>
            <span className="chip">全部病种 ▾</span>
            <button
              type="button"
              className="btn-plush ghost"
              style={{ fontSize: 13, padding: '8px 14px' }}
              onClick={() => store.setScreen('home')}
            >
              ← 个人主页
            </button>
          </div>
        </div>

        <div className="plush" style={{ padding: 16, marginBottom: 18, background: 'white' }}>
          <div
            style={{
              fontWeight: 800,
              fontSize: 11,
              color: 'var(--ink-2)',
              letterSpacing: '.06em',
              textTransform: 'uppercase',
              marginBottom: 12,
            }}
          >
            领域趋势 · 最近 30 天
          </div>
          <TrendChart />
          <div
            style={{
              display: 'flex',
              gap: 14,
              marginTop: 12,
              justifyContent: 'center',
              fontSize: 12,
              fontWeight: 700,
            }}
          >
            <Legend color="var(--peach-deep)" label="信息采集" />
            <Legend color="var(--mint-deep)" label="临床处理" />
            <Legend color="var(--sky-deep)" label="医患沟通" />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 18 }}>
          <div className="plush" style={{ padding: 16 }}>
            <div
              style={{
                fontWeight: 800,
                fontSize: 11,
                color: 'var(--ink-2)',
                letterSpacing: '.06em',
                textTransform: 'uppercase',
                marginBottom: 12,
              }}
            >
              病例时间线
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {CASES.map((c, i) => (
                <div
                  key={`${c.day}-${c.name}`}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '90px 28px 1fr 110px 30px',
                    gap: 10,
                    alignItems: 'center',
                    padding: '8px 8px',
                    borderBottom: i < CASES.length - 1 ? '2px dashed rgba(43,30,22,0.15)' : 'none',
                  }}
                >
                  <span style={{ fontSize: 11, fontWeight: 800, color: 'var(--ink-2)' }}>{c.day}</span>
                  <div
                    style={{
                      width: 22,
                      height: 22,
                      borderRadius: '50%',
                      background: c.color,
                      border: '2.5px solid var(--line)',
                      boxShadow: '0 2px 0 var(--line)',
                    }}
                  />
                  <div>
                    <div style={{ fontWeight: 800, fontSize: 14 }}>{c.name}</div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--ink-2)' }}>{c.cond}</div>
                  </div>
                  <span className="chip" style={{ background: c.color, fontSize: 11 }}>
                    {c.verdict}
                  </span>
                  <span style={{ fontSize: 16, fontWeight: 900, color: 'var(--ink-2)' }}>›</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="plush" style={{ padding: 16, background: 'var(--peach)' }}>
              <div className="chip" style={{ background: 'white', marginBottom: 10 }}>
                🎯 重点提升区
              </div>
              <div style={{ fontSize: 22, fontWeight: 900, lineHeight: 1.1 }}>信息采集</div>
              <div style={{ fontSize: 13, fontWeight: 600, marginTop: 6 }}>
                你最近 10 例中有 6 例遗漏了 ICE（想法、顾虑、期望）。明天的推荐病例将围绕它展开。
              </div>
            </div>

            <div className="plush" style={{ padding: 16 }}>
              <div
                style={{
                  fontWeight: 800,
                  fontSize: 11,
                  color: 'var(--ink-2)',
                  letterSpacing: '.06em',
                  textTransform: 'uppercase',
                  marginBottom: 10,
                }}
              >
                你接触过的指南
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {['NICE NG136', 'NICE NG28', 'GINA 2025', 'ESC 2023', 'BSG 2024', 'NICE NG209', 'NICE CG69', 'NICE NG217'].map(
                  (g) => (
                    <span key={g} className="chip" style={{ fontSize: 11 }}>
                      📖 {g}
                    </span>
                  ),
                )}
              </div>
            </div>

            <div className="plush" style={{ padding: 16, background: 'var(--rose)' }}>
              <div className="chip" style={{ background: 'white', marginBottom: 10 }}>
                🚩 红旗病例
              </div>
              <div style={{ fontSize: 32, fontWeight: 900, lineHeight: 1 }}>3 / 7</div>
              <div style={{ fontSize: 12, fontWeight: 700, marginTop: 4 }}>已尝试的红旗病例</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
