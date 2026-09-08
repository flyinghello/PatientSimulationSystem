import { useState } from 'react';
import { Doodle, DoodleScatter } from './primitives';
import { store } from '../game/store';
import { authLogin, authRegister } from '../game/auth';

type Mode = 'login' | 'register';

const ROLE_HINTS: Array<{ label: string; value: string }> = [
  { label: '学生', value: 'student / student123' },
  { label: '工作人员', value: 'staff / staff123' },
  { label: '管理员', value: 'admin / admin123' },
];

export function LoginScreen() {
  const [mode, setMode] = useState<Mode>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError('');
    if (!username.trim() || !password) {
      setError('请输入用户名和密码');
      return;
    }
    setBusy(true);
    try {
      const res =
        mode === 'login'
          ? await authLogin(username.trim(), password)
          : await authRegister(username.trim(), password, displayName.trim());
      store.setAuth(res.token, res.user);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="screen bg-peach-soft"
      style={{ position: 'relative' }}
    >
      <DoodleScatter
        items={[
          { kind: 'cloud', x: 60, y: 70, size: 100, color: '#fff' },
          { kind: 'cloud', x: 720, y: 110, size: 130, color: '#fff' },
          { kind: 'sparkle', x: 180, y: 200, size: 32, color: '#FFD86B' },
          { kind: 'pill', x: 830, y: 500, size: 70, anim: 'wobble' },
          { kind: 'heart', x: 120, y: 600, size: 40, color: '#F47A92' },
        ]}
      />

      <div
        style={{
          position: 'relative',
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 24,
        }}
      >
        <div
          className="plush-lg popin"
          style={{
            width: 420,
            maxWidth: '100%',
            background: 'white',
            padding: 28,
            position: 'relative',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
            <Doodle kind="cross" size={34} color="#F47A92" />
            <div style={{ fontWeight: 900, fontSize: 26, letterSpacing: '-0.02em' }}>
              受试者沟通训练
            </div>
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink-2)', marginBottom: 18 }}>
            {mode === 'login' ? '登录后继续你的训练与能力画像' : '注册一个新学生账号（默认角色：学生）'}
          </div>

          {/* 模式切换 */}
          <div
            style={{
              display: 'flex',
              background: 'var(--cream)',
              borderRadius: 999,
              border: '3px solid var(--line)',
              padding: 4,
              marginBottom: 18,
            }}
          >
            {(['login', 'register'] as Mode[]).map((m) => (
              <button
                key={m}
                type="button"
                className={mode === m ? 'btn-plush primary' : ''}
                style={{
                  flex: 1,
                  fontSize: 14,
                  padding: '10px 0',
                  borderRadius: 999,
                  background: mode === m ? undefined : 'transparent',
                  boxShadow: mode === m ? undefined : 'none',
                }}
                onClick={() => {
                  setMode(m);
                  setError('');
                }}
              >
                {m === 'login' ? '登录' : '注册'}
              </button>
            ))}
          </div>

          {mode === 'register' && (
            <label style={{ display: 'block', marginBottom: 12 }}>
              <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--ink-2)' }}>昵称（可选）</span>
              <input
                className="auth-input"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="你的称呼"
                style={{ display: 'block', width: '100%', marginTop: 4 }}
              />
            </label>
          )}

          <label style={{ display: 'block', marginBottom: 12 }}>
            <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--ink-2)' }}>用户名</span>
            <input
              className="auth-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="至少 3 个字符"
              autoComplete="username"
              style={{ display: 'block', width: '100%', marginTop: 4 }}
            />
          </label>

          <label style={{ display: 'block', marginBottom: 14 }}>
            <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--ink-2)' }}>密码</span>
            <input
              className="auth-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === 'register' ? '至少 6 位' : '输入密码'}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              onKeyDown={(e) => {
                if (e.key === 'Enter') submit();
              }}
              style={{ display: 'block', width: '100%', marginTop: 4 }}
            />
          </label>

          {error && (
            <div
              style={{
                fontSize: 13,
                fontWeight: 700,
                color: '#B3261E',
                background: '#FFEDEA',
                border: '2px solid #F2B8B5',
                borderRadius: 10,
                padding: '8px 12px',
                marginBottom: 12,
              }}
            >
              {error}
            </div>
          )}

          <button
            type="button"
            className="btn-plush primary"
            disabled={busy}
            style={{ width: '100%', fontSize: 17, padding: '14px 0' }}
            onClick={submit}
          >
            {busy ? '请稍候…' : mode === 'login' ? '登录 →' : '注册并进入 →'}
          </button>

          <button
            type="button"
            className="btn-plush ghost"
            style={{ width: '100%', fontSize: 13, padding: '10px 0', marginTop: 10 }}
            onClick={() => store.enterAsGuest()}
          >
            游客体验（不保存训练记录）
          </button>

          <div
            className="plush-tiny"
            style={{
              marginTop: 16,
              background: 'var(--cream-2)',
              borderRadius: 12,
              padding: '10px 12px',
              fontSize: 12,
              fontWeight: 600,
              color: 'var(--ink-2)',
            }}
          >
            <div style={{ fontWeight: 800, marginBottom: 4 }}>演示账号</div>
            {ROLE_HINTS.map((r) => (
              <div key={r.value}>
                {r.label}：<b>{r.value}</b>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
