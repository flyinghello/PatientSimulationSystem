import { useCallback, useEffect, useState } from 'react';
import { PatientFace, TopBar } from './primitives';
import { store, useGameState } from '../game/store';
import {
  apiFetch,
  fetchProfile,
  type SkillProfile,
  type TrainingRecord,
} from '../game/auth';

const ROLE_LABEL: Record<string, string> = {
  admin: '管理员',
  staff: '工作人员',
  student: '学生',
  guest: '游客',
};

const ROLE_COLOR: Record<string, string> = {
  admin: 'var(--rose)',
  staff: 'var(--sky)',
  student: 'var(--mint)',
  guest: 'var(--butter)',
};

interface AdminStats {
  total_users: number;
  by_role: Record<string, number>;
  total_records: number;
  avg_score: number | null;
  pass_rate: number | null;
  by_study: Record<string, number>;
}

export function RoleHomeScreen() {
  const { authUser, skillProfile } = useGameState();
  const [records, setRecords] = useState<TrainingRecord[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(false);

  const role = authUser?.role ?? 'guest';

  const loadProfile = useCallback(async () => {
    if (!authUser || role === 'guest') return;
    if (authUser.role === 'student') {
      setLoadingProfile(true);
      try {
        const profile = await fetchProfile();
        store.setSkillProfile(profile);
      } catch {
        /* backend offline — keep stored profile */
      } finally {
        setLoadingProfile(false);
      }
    }
  }, [authUser, role]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  // 学生：拉取自己的训练记录；工作人员：拉取整体统计（只读）
  useEffect(() => {
    if (!authUser) return;
    if (authUser.role === 'student') {
      import('../game/auth').then((m) =>
        m.fetchMyRecords().then((rs) => setRecords(rs)).catch(() => {}),
      );
    } else if (authUser.role === 'staff' || authUser.role === 'admin') {
      apiFetch<AdminStats>('/api/admin/stats')
        .then(setStats)
        .catch(() => {});
    }
  }, [authUser]);

  const startTraining = () => {
    if (skillProfile?.training_goal) {
      store.setTrainingFocus(skillProfile.training_goal);
    }
    store.setScreen('mode');
  };

  return (
    <div className="screen" style={{ background: 'var(--cream)' }}>
      <TopBar here={0} steps={['主页']} />

      <div
        style={{
          padding: '28px 36px',
          minHeight: 'calc(100vh - 67px)',
          maxWidth: 1080,
          margin: '0 auto',
        }}
      >
        {/* 欢迎头 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
          <div className="floaty">
            <PatientFace
              style="portrait"
              skin="#E8B68F"
              hair="#3B2A1F"
              size={84}
              mood="neutral"
            />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <h1 style={{ fontSize: 34, lineHeight: 1.1 }}>{authUser?.display_name || '欢迎'}</h1>
              <span className="chip" style={{ background: ROLE_COLOR[role] }}>
                {ROLE_LABEL[role] ?? role}
              </span>
            </div>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-2)', marginTop: 4 }}>
              {role === 'guest'
                ? '游客模式：可体验完整训练，但不会保存训练记录。'
                : role === 'student'
                  ? '每次训练后都会更新你的能力画像，下一轮会针对性推荐。'
                  : role === 'staff'
                    ? '带教视图：可开始训练并查看学员整体训练情况。'
                    : '管理视图：管理用户、查看统计与病例目录。'}
            </div>
          </div>
          <button
            type="button"
            className="btn-plush ghost"
            style={{ fontSize: 13, padding: '10px 14px' }}
            onClick={() => store.logout()}
          >
            退出登录
          </button>
        </div>

        {/* 开始训练 */}
        <button
          type="button"
          className="btn-plush mint"
          style={{ width: '100%', fontSize: 22, padding: '20px 0', marginBottom: 24 }}
          onClick={startTraining}
        >
          ▶ 开始一次入组沟通训练
        </button>

        <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: 24, alignItems: 'start' }}>
          {/* 左列：能力画像 / 推荐 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {role === 'student' && (
              <ProfileCard profile={skillProfile} loading={loadingProfile} />
            )}
            {role === 'student' && records.length > 0 && (
              <HistoryCard records={records} onOpen={() => store.setScreen('history')} />
            )}
            {role === 'staff' && stats && <StaffStatsCard stats={stats} />}
            {role === 'admin' && (
              <>
                <button
                  type="button"
                  className="btn-plush primary"
                  style={{ fontSize: 17, padding: '16px 0' }}
                  onClick={() => store.setScreen('admin')}
                >
                  ⚙ 进入管理后台
                </button>
                {stats && <StaffStatsCard stats={stats} />}
              </>
            )}
            {(role === 'guest' || role === 'staff') && (
              <div className="plush" style={{ padding: 18 }}>
                <div style={{ fontWeight: 800, fontSize: 15, marginBottom: 6 }}>为什么登录？</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-2)', lineHeight: 1.6 }}>
                  {role === 'guest'
                    ? '登录后每次训练都会被评估，系统会记录你的薄弱维度并在下一轮推荐针对性的病例与训练目标。'
                    : '作为工作人员，你可以在学员端看到每位学生的训练记录与统计，帮助带教。'}
                </div>
              </div>
            )}
          </div>

          {/* 右列：快捷入口 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <QuickLink
              icon="🧾"
              title="训练记录"
              sub="查看历史评估与复盘"
              onClick={() => store.setScreen('history')}
            />
            <QuickLink
              icon="📚"
              title="病例库"
              sub="按专科浏览可选病例"
              onClick={() => store.setScreen('library')}
            />
            <QuickLink
              icon="🎓"
              title="智能体评分机制"
              sub="了解评分规则与引用"
              onClick={() => store.setScreen('agenticRounds')}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function ProfileCard({ profile, loading }: { profile: SkillProfile | null; loading: boolean }) {
  if (loading) {
    return (
      <div className="plush-lg" style={{ padding: 20 }}>
        <div style={{ fontWeight: 800 }}>能力画像加载中…</div>
      </div>
    );
  }
  if (!profile) {
    return (
      <div className="plush-lg" style={{ padding: 20, position: 'relative' }}>
        <div style={{ position: 'absolute', top: -12, left: 22 }} className="chip butter">
          ★ 首次训练
        </div>
        <div style={{ fontWeight: 900, fontSize: 20 }}>完成一次训练，建立你的能力基线</div>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-2)', marginTop: 6 }}>
          训练结束后会生成评估报告，并据此推荐下一轮的针对性练习。
        </div>
      </div>
    );
  }

  const weak = profile.weaknesses[0];
  return (
    <div className="plush-lg" style={{ padding: 20, position: 'relative' }}>
      <div style={{ position: 'absolute', top: -12, left: 22 }} className="chip butter">
        {profile.total_sessions === 0 ? '★ 首次训练' : '★ 为你推荐'}
      </div>

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 14 }}>
        <div style={{ fontWeight: 900, fontSize: 22 }}>下一轮：{profile.label || '—'}</div>
      </div>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-2)', marginBottom: 12 }}>
        {profile.reason}
      </div>

      {weak && (
        <div
          className="plush"
          style={{
            padding: 12,
            background: 'var(--peach)',
            borderRadius: 12,
            marginBottom: 12,
            fontSize: 13,
            fontWeight: 700,
          }}
        >
          需要强化：<b>{weak.dimension}</b>（平均 {weak.score} 分）
        </div>
      )}
      <div
        className="plush"
        style={{
          padding: 12,
          background: 'var(--cream-2)',
          borderRadius: 12,
          fontSize: 13,
          fontWeight: 600,
          lineHeight: 1.6,
        }}
      >
        <div style={{ fontWeight: 800, marginBottom: 4 }}>本回合训练目标</div>
        {profile.training_goal || '（训练目标将在开始后注入患者扮演提示）'}
      </div>

      <div
        style={{
          display: 'flex',
          gap: 8,
          flexWrap: 'wrap',
          marginTop: 14,
          fontSize: 12,
          fontWeight: 700,
          color: 'var(--ink-2)',
        }}
      >
        <span className="chip">累计训练 {profile.total_sessions} 次</span>
        {profile.avg_score != null && <span className="chip">平均 {profile.avg_score} 分</span>}
        {profile.pass_rate != null && <span className="chip">通过率 {profile.pass_rate}%</span>}
        {profile.strengths.length > 0 && (
          <span className="chip mint">
            优势：{profile.strengths.map((s) => s.dimension).join('、')}
          </span>
        )}
      </div>
    </div>
  );
}

function HistoryCard({
  records,
  onOpen,
}: {
  records: TrainingRecord[];
  onOpen: () => void;
}) {
  const recent = records[0];
  return (
    <div className="plush" style={{ padding: 16 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          marginBottom: 10,
        }}
      >
        <div
          style={{
            fontWeight: 800,
            fontSize: 12,
            color: 'var(--ink-2)',
            letterSpacing: '.06em',
            textTransform: 'uppercase',
          }}
        >
          最近训练
        </div>
        <span
          style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink-2)', cursor: 'pointer' }}
          onClick={onOpen}
        >
          查看全部 →
        </span>
      </div>
      {recent ? (
        <div style={{ fontSize: 13, fontWeight: 700 }}>
          {recent.study}
          <span style={{ color: 'var(--ink-2)', fontWeight: 600 }}>
            {' '}
            · {recent.overall_score ?? '—'} 分 · {recent.created_at?.slice(0, 10)}
          </span>
        </div>
      ) : (
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-2)' }}>暂无记录</div>
      )}
    </div>
  );
}

function StaffStatsCard({ stats }: { stats: AdminStats }) {
  return (
    <div className="plush-lg" style={{ padding: 20, position: 'relative' }}>
      <div style={{ position: 'absolute', top: -12, left: 22 }} className="chip sky">
        📊 学员训练概览
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <Stat big={String(stats.total_users)} sub="注册用户" />
        <Stat big={String(stats.total_records)} sub="训练次数" />
        <Stat big={stats.avg_score != null ? `${stats.avg_score}` : '—'} sub="平均分" />
        <Stat big={stats.pass_rate != null ? `${stats.pass_rate}%` : '—'} sub="通过率" />
      </div>
      {Object.keys(stats.by_study).length > 0 && (
        <div style={{ marginTop: 12, fontSize: 12, fontWeight: 600, color: 'var(--ink-2)' }}>
          病例分布：
          {Object.entries(stats.by_study)
            .map(([k, v]) => `${k} ×${v}`)
            .join('，')}
        </div>
      )}
    </div>
  );
}

function Stat({ big, sub }: { big: string; sub: string }) {
  return (
    <div>
      <div style={{ fontWeight: 900, fontSize: 26, lineHeight: 1 }}>{big}</div>
      <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink-2)', marginTop: 4 }}>{sub}</div>
    </div>
  );
}

function QuickLink({
  icon,
  title,
  sub,
  onClick,
}: {
  icon: string;
  title: string;
  sub: string;
  onClick: () => void;
}) {
  return (
    <div className="plush tap" style={{ padding: 16, display: 'flex', gap: 14, alignItems: 'center' }} onClick={onClick}>
      <div style={{ fontSize: 26, width: 44, textAlign: 'center' }}>{icon}</div>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 800, fontSize: 15 }}>{title}</div>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-2)' }}>{sub}</div>
      </div>
      <div style={{ fontWeight: 800, color: 'var(--ink-2)' }}>→</div>
    </div>
  );
}
