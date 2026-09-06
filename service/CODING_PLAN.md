# CRC Agent 工作流修复 Coding Plan

## 目标

把「多 CLI 文件流水线」收成可复现的闭环：同一研究 stem 贯通背景 → 顾虑池 → 开局 → 多轮 → 评分，并修掉已知一致性 bug。

## 范围（本次）

| 优先级 | 项 | 做法 |
|--------|----|------|
| P0 | 默认研究不一致 | 统一默认 stem；共享 `study_paths` |
| P0 | 无编排器 | 新增 `run_pipeline.py`（`--study` + `--stages`） |
| P0 | 评测角色映射反了 | 与 `patient_turn` 对齐：`user`→CRC，`assistant`→患者 |
| P0 | 评测未接 session | `evaluation --session` 读 `dialogue.jsonl` |
| P1 | CRS 缺安慰剂话题 | 直接补一条顾虑池条目 |
| P1 | 人设锁不完整 | `normalize_opening` 强制学历/情绪/交流特点 |
| P1 | session 未钉路径 / ended 短暂丢 | `meta.json` 记路径；`save()` 保留 ended |
| P2 | 培训材料偏薄 | `concern_pool` 默认改用 `crc_pre_enrollment_dialogue.md` |
| P2 | 双轨问题生成 | `questions_generate` 标注 legacy |

## 不在本次

- LangGraph / FastAPI 产品化
- TTS/ASR 接入多轮
- 重跑 LLM 重新生成整份 CRS 顾虑池（仅手工补关键条目）
- 全面单测套件（可后续补 normalize / role-map 单测）

## 验收

1. 各 agent 无参默认指向同一研究（CRS with nasal polyps）
2. `python service/agent/run_pipeline.py --study "..." --stages prep` 能串背景/顾虑/开局路径
3. `evaluation.py --session <dir>` 能评分；角色映射与 `patient_turn` 一致
4. CRS `concerns.json` 含安慰剂/随机分组话题
5. 新 session 的 `meta.json` 含 artifact 路径；结束后 `state.json` 的 `是否结束` 不被 `save()` 抹掉
