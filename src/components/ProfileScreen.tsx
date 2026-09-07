import { useEffect } from 'react';
import { TopBar } from './primitives';
import { store, useGameState } from '../game/store';
import { fetchProfile } from '../game/auth';

/** 学生能力画像详情页：维度得分、薄弱项、下一轮推荐。 */
export function ProfileScreen() {
  const { skillProfile, authUser } = useGameState();

  useEffect(() => {
    if (authUser?.role === 'student' && !skillProfile) {
      fetchProfile()
        .then((p) => store.setSkillProfile(p))
        .catch(() => {});
    }
  }, [authUser, skillProfile]);

  const dims = Object.entries(skillProfile?.dimension_scores ?? {});

  return (
    <div className="screen" style={{ background: 'var(--cream)' }}>
      <TopBar here={0} steps={['主页', '能力画像']} />
      <div style={{ padding: '28px 36px', maxWidth: 900, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
          <h1 style={{ fontSize: 32 }}>我的能力画像</h1>
          <button
            type="button"
            className="btn-plush ghost"
            style={{ fontSize: 13, padding: '9px 14px' }}
            onClick={() => store.setScreen('home')}
          >
            ← 返回主页
          </button>
        </div>

        {dims.length === 0 ? (
          <div className="plush-lg" style={{ padding: 24, marginTop: 20 }}>
            <div style={{ fontWeight: 900, fontSize: 20 }}>还没有训练记录</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-2)', marginTop: 6 }}>
              完成一次入组沟通训练后，这里会展示各沟通维度的得分变化。
            </div>
          </div>
        ) : (
          <div className="plush-lg" style={{ padding: 24, marginTop: 20 }}>
            <div style={{ fontWeight: 800, marginBottom: 14 }}>各维度平均得分（0–100）</div>
            {dims.map(([dim, score]) => {
              const pct = Math.max(0, Math.min(100, score));
              const color = score < 75 ? 'var(--rose)' : score < 85 ? 'var(--butter)' : 'var(--mint)';
              return (
                <div key={dim} style={{ marginBottom: 12 }}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: 13,
                      fontWeight: 700,
                      marginBottom: 4,
                    }}
                  >
                    <span>{dim}</span>
                    <span>{score} 分</span>
                  </div>
                  <div
                    style={{
                      height: 14,
                      background: 'var(--cream)',
                      border: '2.5px solid var(--line)',
                      borderRadius: 999,
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        width: `${pct}%`,
                        background: color,
                        borderRadius: 999,
                        transition: 'width 500ms ease',
                      }}
                    />
                  </div>
                </div>
              );
            })}

            {skillProfile && (
              <div style={{ marginTop: 18, fontSize: 13, fontWeight: 600, color: 'var(--ink-2)', lineHeight: 1.7 }}>
                <div style={{ marginBottom: 6 }}>
                  累计训练 <b>{skillProfile.total_sessions}</b> 次
                  {skillProfile.avg_score != null && <> · 平均分 <b>{skillProfile.avg_score}</b></>}
                  {skillProfile.pass_rate != null && <> · 通过率 <b>{skillProfile.pass_rate}%</b></>}
                </div>
                {skillProfile.strengths.length > 0 && (
                  <div style={{ marginBottom: 6 }}>
                    ✅ 优势维度：{skillProfile.strengths.map((s) => `${s.dimension}（${s.score}）`).join('、')}
                  </div>
                )}
                {skillProfile.weaknesses.length > 0 && (
                  <div style={{ marginBottom: 10 }}>
                    ⚠ 需要强化：{skillProfile.weaknesses.map((s) => `${s.dimension}（${s.score}）`).join('、')}
                  </div>
                )}
                <button
                  type="button"
                  className="btn-plush primary"
                  style={{ fontSize: 15, padding: '12px 18px' }}
                  onClick={() => {
                    if (skillProfile.training_goal) store.setTrainingFocus(skillProfile.training_goal);
                    store.setScreen('mode');
                  }}
                >
                  ▶ 按推荐开始训练（{skillProfile.label || '推荐病例'}）
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
