# medkit — 技术架构分析 & 智能体改写参考

> 用途：① 供人阅读、理解整个项目的技术架构；② 供 AI 智能体（或协作者）在改写本仓库时遵循的约定与速查。
> 认知前提：这是一个 **浏览器端的 ER（急诊）+ 全科门诊（Polyclinic）临床培训模拟器**。玩家扮演医生，AI 扮演患者（实时语音），另一个 Claude 智能体（`medkit-attending`）在后台观察并按真实临床指南给玩家打分。项目为 3 天黑客松作品，案例为合成数据，不声称临床准确性。

---

## 0. 一分钟总览

| 维度 | 内容 |
|---|---|
| 前端 | React 18（更新为19） + TypeScript + Vite；Three.js（`@react-three/fiber` + `drei`）做 3D 诊室；`livekit-client` 接实时语音；单一 `Store` 类（`useSyncExternalStore`）做状态，无 Redux/Zustand |
| 后端 | **两个独立 Python 进程**：① FastAPI（`127.0.0.1:8787`）做 Managed Agents 代理 + LiveKit JWT 签发；② LiveKit `voice_agent.py` 语音 Worker（Deepgram STT → Haiku 4.5 → Cartesia TTS） |
| 部署 | 前端 + 边缘代理上 Vercel（`vercel.json` + `middleware.ts`）；FastAPI 上 Render（`grand-rounds-backend.onrender.com`） |
| LLM 路由 | 患者语音人格 = Haiku 4.5（快/便宜）；`medkit-attending` 打分 = **Opus 4.7**；ER 分诊分类器 = 另一条 Opus 4.7 直连推理 |
| 安全底线 | **所有 API Key 只在服务端**，浏览器永不持有。`VITE_*` 的 Anthropic Key 已被废弃，患者流式对话改走 `/agent/patient/stream` 后端代理 |

---

## 1. 分层架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│  Browser (React + Vite, localhost:5173 或 Vercel)                      │
│                                                                        │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  ┌─────────────┐  │
│  │ Store     │  │ 3D Scenes    │  │ Voice Client   │  │ Agent Client │  │
│  │(single)   │  │(R3F/Three)  │  │(livekit-client)│  │(/agent/* SSE)│  │
│  └────┬─────┘  └──────┬───────┘  └──────┬────────┘  └──────┬──────┘  │
│       │                │                 │                   │          │
│       └────────────────┴────────┬────────┴───────────────────┘          │
│                         Vite dev/preview 代理（/agent/*、/voice/*）       │
└────────────────────────────────┼──────────────────────────────────────┘
                                  │ HTTP (localhost:8787 或 Render)
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│  FastAPI backend (server.py) — 127.0.0.1:8787                          │
│   · /agent/*  → Claude Managed Agents 代理（medkit-attending 打分）      │
│   · /voice/token → 创建 LiveKit 房间 + 签发 JWT                         │
│   · /agent/patient/stream → Haiku 4.5 患者对话流式（SSE）               │
│   · /agent/triage/classify → Opus 4.7 一次性 ESI 分诊                    │
│   · /agent/vault/ehr/lookup → 凭据保险库演示（EHR_API_TOKEN 不出后端）   │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │ LiveKit Cloud (WebRTC)
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  LiveKit voice worker (voice_agent.py) — 独立进程                       │
│   Browser mic → Deepgram Nova-3 STT → Haiku 4.5 → Cartesia Sonic-2 TTS │
└──────────────────────────────────────────────────────────────────────┘
```

**关键点**：浏览器只与 FastAPI 通信，绝不直接调 Anthropic。语音链路上，浏览器把麦克风推到 LiveKit 房间，Python Worker 在房间内做 STT→LLM→TTS 再把音频推回浏览器。前端**不加载任何 STT/TTS 模型**。

---

## 2. 前端架构

### 2.1 技术栈与依赖
- `react@18` / `react-dom@18`、`typescript@5`、`vite@5`
- `three@0.170` + `@react-three/fiber@8` + `@react-three/drei@9`（3D 场景）
- `livekit-client@2`（浏览器端 WebRTC + 转录事件）
- `zod@3`（自定义工具入参校验）
- 运行时依赖里**没有** 状态库、没有 STT/TTS SDK——这是刻意设计。

`package.json` 里的脚本特意用 `node node_modules/<pkg>/bin/<entry>.js` 而非 `.bin` 可执行包装器（Windows 组策略会拦截 `.exe` 包装器）。**新增脚本时保持这个模式，不要引入 `tsx`**。

### 2.2 目录结构（src/）
```
src/
  game/         Store、类型、单一事实来源
    store.ts    单一 Store 类 + useSyncExternalStore 绑定
    types.ts    PatientCase / ActivePatient / GameState / Rubric 类型
    clinic.ts   诊所 id 枚举 + DEFAULT_CLINIC
  data/         纯数据（无逻辑）
    cases.ts           卡通风格病例目录（首屏/选案入口，含 clinic 归属）
    patients.ts        完整 medkit PatientCase（主诉/anamnesis/vitals/诊断/治疗）
    polyclinicPatients.ts  门诊患者（儿科主诉写成第三人称，父母代述）
    tests.ts treatments.ts medications.ts guidelines.ts  检验/治疗/用药/指南注册表
    autoRubric.ts radiologyImages.ts avatarModels.ts evalHistory.ts ...
  components/   React UI
    *.tsx       各屏幕 + primitives.tsx（通用按钮/顶栏）
    three/      Three.js 场景
      Polyclinic.tsx  门诊 3D 诊室（当前重点开发区域）
      Player.tsx      第一人称控制器（指针锁定 + 交互）
      StylizedCharacter.tsx 卡通角色
      createStore.ts interactions.ts FloatingVoicePanel.tsx
  voice/        实时语音层
    conversation.ts     Conversation 类：LiveKit 房间、麦克风、转录、口型振幅
    conversationStore.ts 按 bedIndex 缓存的对话实例（含单人床哨兵 -10）
    patientPersona.ts   系统提示构建（成人 vs 儿科父母代述）
    claude.ts           后端 Haiku 流式对话的 SSE 解析器（/agent/patient/stream）
  agents/       Managed Agent（medkit-attending）集成
    managedAgent.ts     浏览器端 Agent 客户端（bootstrap/session/stream）
    customTools.ts      7 个自定义工具的 Zod schema + 权限策略（auto/confirm）
    eventStreamRenderer.tsx  工具名 → 组件 映射（*待读以补全*）
    useAttendingDebrief.ts    问诊结束后的复盘流程 hook
    debriefRequest.ts         复盘请求体构建
  App.tsx       屏幕路由（基于 store.screen 的条件渲染，非 react-router）
  main.tsx      入口
  styles/       global.css、palettes.ts（主题调色板 + intensity 应用）
```

### 2.3 状态管理（核心约定）
- **单一 `Store` 类**（`src/game/store.ts`）持有整个 `GameState`，通过 `useSyncExternalStore` 暴露 `useStore<T>(selector)`。
- `store` 是模块级单例（`export const store = new Store()`）。
- **不要引入 Redux/Zustand**。需要派生状态就写 selector 或在组件里算。
- 关键状态切片：
  - `screen`：13 个屏幕枚举之一（`splash → onboarding → mode → brief → encounter → endConfirm → debrief` 等）
  - `polyclinic`：`{ clinic, patient }`——3D 场景与语音面板消费的切片
  - `lastEncounter`：患者离场瞬间的快照（用于复盘，因为 `polyclinic.patient` 离场后被清空做走路动画）
- `POLYCLINIC_BED_INDEX = -10`：**门诊用这个哨兵值**作为 bedIndex 贯穿 Store、会话缓存、3D 场景。改三处要同步。
- `attemptedCaseIds`：`pickNextCaseId` 用它避免重复抽到同一患者；reload 清空（刻意，单次轮班非数据库）。

### 2.4 屏幕路由
`App.tsx` 用 `screen === 'x' && <XScreen/>` 条件渲染，**不是** react-router。`/agentic-rounds`、`/agent-topology` 两条路径在 `App` 的 `useEffect` 里直接 `store.setScreen(...)` 做深链。`AgenticRoundsScreen` / `AgentTopologyScreen` 是架构展示页。

### 2.5 3D 场景（Three.js / R3F）
- `Polyclinic.tsx` 是主要活动区。地板/墙有固定尺寸约束，新 mesh 必须遵守地面平面、不与现有家具包围盒重叠（由 `scripts/verify/three-scene.ts` 校验）。
- `Player.tsx`：第一人称控制器，指针锁定（PointerLock）+ 交互总线 `interactionBus`。`EncounterScreen.tsx` 管相机 FOV 自适应、E 检查、T 静音、Esc 释放锁定等。
- 语音口型同步：`Conversation.getMouthAmplitude()` 从远端音频轨道的 `AnalyserNode` 读数（RMS × 3.2），喂给 3D 角色，不连接 destination（只读 tap）。

### 2.6 语音层（关键交互）
- `Conversation` 类（`conversation.ts`）是语音会话的门面：
  - `init()`：请求 `/voice/token` → 连 LiveKit 房间 → 开麦克风 → 等患者开场白
  - 转录来自 LiveKit `TranscriptionReceived` 事件，按 `participant.identity` 区分"你/患者"
  - `getMouthAmplitude()` 驱动口型；`detectEmotion()` 用正则推断 patient 情绪（pain/fear/relief/confused）
  - `sayFarewell()`：通过 LiveKit RPC（`performRpc` method `"farewell"`）让 Worker 用 `session.say` 直接 TTS 一句再见，再轮询 status 直到说完
  - `sendTextMessage()`：走旧 `/agent/patient/stream` 文本路径，与语音并行不冲突
- `conversationStore.ts`：按 `bedIndex` 缓存 `Conversation`。**换患者必须 dispose 旧的**（否则新患者继承旧姓名/病史/声音）。`clearAllConversationStorage()` 清 localStorage 历史。
- `patientPersona.ts`：系统提示构建。**儿科（age<14）由父母代述**，父母性别用 FNV-1a 哈希 caseId 决定，3D 场景与语音端必须一致（见 `parentGenderForId`）。
- `claude.ts` 的 `hasClaudeKey()` 现在恒为 `true`（密钥后端持有），保留函数是为让调用方不动。

### 2.7 Managed Agent 客户端（打分智能体）
- `managedAgent.ts`：浏览器端封装，所有调用走 `/agent/*` 后端代理。核心是 `openEventStream()`——**带 reconnect+backfill+去重**的 SSE 消费器（按 event id 去重，断线后用 `GET /events?limit=1000` 回填未收事件）。
- `customTools.ts`：**后端 `MEDKIT_CUSTOM_TOOLS` 的浏览器孪生**。每个工具：Zod schema + 权限（`auto` 立即 ack / `confirm` 等用户确认）。两端 schema **必须一致**，改一处改两处。
- `useAttendingDebrief.ts`：复盘流程 hook——`bootstrap → createSession → sendUserMessage([debrief request]) → openEventStream`；流式里自动 ack 所有 `auto` 工具，把 `render_case_evaluation` 作为最终打分结果。

---

## 3. 后端架构

后端是 **两个独立 Python 进程**，各有独立虚拟环境（依赖树不兼容）。

### 3.1 进程 A：FastAPI（`backend/server.py`）
监听 `127.0.0.1:8787`，三类职责：

**(a) Claude Managed Agents 代理（medkit-attending 打分）**
- `POST /agent/bootstrap`：幂等，首次创建 Agent + Environment，返回 `agent_id`/`environment_id`（用 `threading.Lock` 防并发双创建），之后要持久化到 `.env.local`
- `POST /agent/refresh`：把当前系统提示 + 自定义工具推上去，产生新版本（现有 session 用旧版本，新 session 用最新）
- `POST /agent/sessions`、`GET/POST /agent/sessions/{id}/events`、`GET /agent/sessions/{id}/stream`（SSE 代理）
- SSE 用 **异步 Anthropic 客户端**（`AsyncAnthropic`），否则同步生成器会占满线程池导致所有端点（含 `/health`）失活。`asyncio.wait_for` 包 `anext` 做 15s keepalive，避免代理/浏览器静默断流。

**(b) LiveKit 房间与令牌**
- `POST /voice/token`：前端传 persona payload（systemPrompt/initialLine/gender），后端用 `livekit-api` **预创建房间**（metadata 携带 persona），`RoomAgentDispatch(agent_name="medkit-voice")` 显式按名派单（解决 Render Oregon 与 Worker EU 跨云自动派单失败问题），返回 JWT。

**(c) 两条直连 Opus/Haiku 推理**
- `POST /agent/patient/stream`：Haiku 4.5 患者对话流式（SSE，带 `cache_control: ephemeral`）。**替代了原来浏览器直连 Anthropic 的危险做法**。
- `POST /agent/triage/classify`：**独立**的 Opus 4.7 一次性 ESI 三级分诊（critical/urgent/stable），`run_triage_reasoning` 是纯函数便于单测 mock。与 Managed Agent 是两条不同代码路径。

**(d) 凭据保险库演示**
- `POST /agent/vault/ehr/lookup`：响应 `lookup_ehr_history` 工具。后端附 `EHR_API_TOKEN`（仅进程内环境变量，从不进 Claude 上下文、不进响应、不进日志），返回假 EHR 记录。`backend/tests/test_vault.py` 断言 token 不泄露。

**安全中间件**（顺序：auth 最内 → slowapi → CORS 最外）：
- `require_shared_secret`：除 `/health` 和 OPTIONS 外，DEV_ORIGINS 放行；其余需 `x-medkit-auth` 头等于 `BACKEND_SHARED_SECRET`，否则 401。Vercel 边缘 `middleware.ts` 为浏览器流量注入该头。
- `slowapi` 限流 120/min/IP（SSE 计一次请求）。
- 所有密钥：`ANTHROPIC_API_KEY`、`LIVEKIT_*`、`DEEPGRAM_API_KEY`、`CARTESIA_API_KEY`、`EHR_API_TOKEN`——**服务端 only，浏览器永不持有**。

### 3.2 进程 B：LiveKit 语音 Worker（`backend/voice_agent.py`）
- 独立进程/venv（`voice_agent_requirements.txt`：livekit-agents 全家桶）。
- `entrypoint(ctx)`：`ctx.connect()` → 读房间 metadata（persona 来自前端 TS，Python 不重复逻辑）→ `AgentSession(stt=Deepgram Nova-3, llm=Haiku 4.5, tts=Cartesia Sonic-2, vad=Silero)`。
- 注册 RPC 方法 `"farewell"`：`session.say()` 直接 TTS 一句再见（不绕 LLM），对应前端的 `sayFarewell()`。
- `agent_name="medkit-voice"` + `RoomAgentDispatch` 显式派单。
- 语音 ID 按 `pick_voice(caseId, gender)`（FNV-1a 哈希，与前端 `patientPersona.ts` 相同算法）确定性选择同一音色。
- **需要 FastAPI + Worker 都在线语音才能用**；只有 FastAPI 时前端仍可文本聊天。

### 3.3 部署拓扑
- 本地：`npm run dev`（Vite 5173，代理 `/agent/*`、`/voice/*` 到 8787）+ 两个后端进程。
- 生产：Vercel 托管前端 + 边缘 `middleware.ts`（把 `/agent/*`、`/voice/*` 转发到 Render 后端，注入共享密钥）；`vercel.json` rewrites 兜底。Render 上 `Procfile` 拉起 FastAPI。

---

## 4. 两条核心数据流（改写时必读）

### 4.1 实时语音问诊
```
用户说话 → 浏览器麦克风(WebRTC) → LiveKit 房间
  → Worker: Deepgram STT → Haiku 4.5（patientPersona 提示）→ Cartesia TTS
  → 音频回传浏览器（远端轨道 + 转录事件）
  → Conversation 更新字幕/情绪/口型，Store 不变（语音不写游戏状态）
```
注意：语音**不写** `GameState`。病史/检验/诊断等"游戏动作"走 `ExamineOverlay` → Store（见 `EncounterScreen` 的 `openExamine`）。

### 4.2 问诊复盘打分（medkit-attending）
```
End consultation → store.finishPolyclinicCase() 拍快照到 lastEncounter
  → DebriefScreen / useAttendingDebrief
  → bootstrap → createSession → sendUserMessage(debriefRequest JSON)
     JSON 含：correctDiagnosisId + rubric + registry_slice(指南子集) + encounter_log
  → openEventStream: 自动 ack render_*；遇到 render_case_evaluation 即最终打分
  → <CaseEvaluationCard> 用 guideline_ref 在 src/data/guidelines.ts 解析引用
```
**硬规则（来自系统提示）**：每个 clinical_management 准则的 `guideline_ref` 必须出现在 `registry_slice` 中；引用不存在就**丢弃该准则**，绝不编造（避免评分"幻造"来源）。

---

## 5. 智能体改写参考（Conventions）

> 给后续 AI 智能体/协作者：编辑本仓库时务必遵守以下约定，避免破坏既有架构。

1. **改动最小化**：修 bug 就只修 bug，不要顺手重构相邻代码。"Don't refactor adjacent code while you're there."
2. **数据即数据**：新增病例/检验/药物 → 编辑 `src/data/*` 对应文件。除非游戏机制真变了，否则不要把新形状塞进 Store。
3. **不新增状态库**：`Store` 类管一切。派生状态用 selector 或组件内计算。**不要加 Redux/Zustand**。
4. **不引入 `tsx` 依赖**：新脚本用 `node node_modules/<pkg>/bin/<entry>.js` 模式（组策略拦截 `.exe` 包装器）。
5. **前后端自定义工具 schema 必须同步**：改 `src/agents/customTools.ts` 的 Zod 时，同步改 `backend/server.py` 的 `MEDKIT_CUSTOM_TOOLS` JSON Schema，反之亦然。测试 `scripts/test/custom-tools.test.ts` 会强制两边工具集合一致。
6. **密钥永不在前端**：新增任何要用 Anthropic/LiveKit/Deepgram/Cartesia 的功能，**必须走后端代理**，禁止 `VITE_*`。Vite 仅代理 `/agent/*` 和 `/voice/*`。
7. **Prompt 缓存**：新增 Claude 调用（尤其 `claude.ts` / `server.py` 的 patient stream）在 system 提示上加 `cache_control: { type: 'ephemeral' }`。
8. **儿科父母代述**：改 persona/3D/语音任何一端时，`parentGenderForId` 的哈希算法两端必须一致，否则可见父母与发声父母不一致。
9. **会话生命周期**：换患者/离场必须 `disposePatientConversation(POLYCLINIC_BED_INDEX)`（或对应 bedIndex）。`POLYCLINIC_BED_INDEX=-10` 哨兵贯穿三处。
10. **3D 场景约束**：新增 mesh 遵守地面平面、不与家具包围盒重叠；改后用 dev server 转相机验证，别靠数字脑补。由 `scripts/verify/three-scene.ts` 校验。
11. **不要创建专家子 agent**（triage-expert 等）。用 `agent/skills/` 里的 skill，让 Claude 组合调用（见 `agent/skills/README.md`）。
12. **勿提交**：`.env.local`、>1MB 的语音样本、`node_modules/`、`backend/.venv/`、`dist/`。
13. **指南注册表需人工核验**：`src/data/guidelines.ts` 条目默认 `verificationStatus:"auto-fetched"`，**不要**用代码把它翻成 `"verified"`——那是临床医生人工签字。

### 关键文件速查（改写入口）
| 想改什么 | 改这里 |
|---|---|
| 全局状态/导航/诊室流程 | `src/game/store.ts`、`src/game/types.ts` |
| 病例/检验/治疗/用药/指南 | `src/data/*.ts` |
| 3D 诊室/角色/相机 | `src/components/three/*.tsx` |
| 实时语音/口型/情绪 | `src/voice/conversation.ts`、`conversationStore.ts`、`patientPersona.ts` |
| 打分智能体客户端/工具/复盘 | `src/agents/*.ts`、`src/components/DebriefScreen.tsx` |
| 患者对话模型(Haiku) | `backend/server.py` `PATIENT_MODEL` + `patient_stream` |
| 打分系统提示/工具定义 | `backend/server.py` `MEDKIT_ATTENDING_SYSTEM_PROMPT` + `MEDKIT_CUSTOM_TOOLS` |
| 分诊分类器(Opus) | `backend/server.py` `ESI_TRIAGE_SYSTEM_PROMPT` + `run_triage_reasoning` |
| 语音 Worker 链路 | `backend/voice_agent.py` |
| 后端安全/代理/部署 | `backend/server.py` 中间件、`vercel.json`、`middleware.ts` |

---

## 6. 模型路由表（新增 Claude 功能时对照）

| 调用 | 模型 | 原因 |
|---|---|---|
| 患者语音人格（LiveKit Worker 内） | Haiku 4.5 | 快、便宜，角色对话足够 |
| 患者文本对话（`/agent/patient/stream`） | Haiku 4.5 | 同上 |
| `medkit-attending` 打分（Managed Agent） | **Opus 4.7** | 临床推理精度优先 |
| ER 分诊分类（`/agent/triage/classify`） | **Opus 4.7** | 一次性 ESI 推理，最强模型 |

---

## 7. 验证与测试

- `npm run verify`（`scripts/verify/run-all.ts`，Node 22+ 原生跑 `.ts`）：
  - `simulation-state.ts`、`three-scene.ts`、`triage-priority.ts`、`data-integrity.ts`、`rubric-smoke.ts`
  - 任一失败非零退出。**每次改 `src/data/*`、类型、Store 后必跑**。
- `npm test`（`scripts/test/run-all.ts`）：自定义工具、工具分发、分诊客户端、loop 命令等单测；每个测试还会端到端跑一次 `scripts/loop/verify-loop.ts`。
- 后端：`backend/.venv/Scripts/python -m unittest discover backend/tests`（`test_triage.py` 用 mock Anthropic 测分诊；`test_vault.py` 断言 `EHR_API_TOKEN` 不泄露）。
- 两套测试均 < 2 秒、无需联网。
- `/loop` 用法（`loop/keep-thinking.md`、`loop/babysit-simulation.md`）：`/loop 20m /medkit-verify-simulation` 周期性校验并写 `verify.log`。

---

## 8. 已知范围与边界（Out of scope）

- 不做多 agent 交接（研究预览阶段）。
- 不做持久用户账户——单玩家、单班次。
- 不声称临床准确性；药物剂量经过简化。
- 不做移动端/触屏——仅桌面演示。
- 后端 `server.py` 顶部 TODO：提交前需按 `platform.claude.com/docs/managed-agents/` 核对 β 版 SDK 字段名（`beta.agents/sessions/environments`），字段可能漂移。

---

## 9. 给智能体的"不要做"清单

- 不要把 `useSyncExternalStore` 换成 Redux/Zustand。
- 不要把 `livekit-client` 的 STT/TTS 往前端搬（应留在 Worker）。
- 不要在 `package.json` 加 `tsx` 或 `.bin` 包装器调用。
- 不要在前端新增 `VITE_ANTHROPIC_API_KEY` 或任何密钥。
- 不要单边改 `customTools.ts` / `MEDKIT_CUSTOM_TOOLS`。
- 不要把 `guidelines.ts` 条目标 `verified`（需人工）。
- 不要创建新的专家子 agent，用 `agent/skills/`。
