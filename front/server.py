"""CRC 入组前对话 — 简易前端 API。

启动：
  python front/server.py
  浏览器打开 http://127.0.0.1:8790
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from service.agent.evaluation import (  # noqa: E402
    EvalConfig,
    EvaluationAgent,
)
from service.agent.opening_question import (  # noqa: E402
    OpeningConfig,
    OpeningQuestionAgent,
)
from service.agent.patient_turn import (  # noqa: E402
    DialogueSession,
    PatientTurnAgent,
    PatientTurnConfig,
    load_json,
    save_json,
)
from service.agent.personality import sample_persona  # noqa: E402
from service.agent.study_paths import resolve_study  # noqa: E402

FRONT_DIR = Path(__file__).resolve().parent
SESSIONS_BASE = _ROOT / "service" / "acknowledge" / "dialogue_sessions"

app = FastAPI(title="CRC Dialogue Front")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartSessionBody(BaseModel):
    study: str = Field(..., min_length=1)
    random_persona: bool = False


class ReplyBody(BaseModel):
    message: str = Field(..., min_length=1)


def _list_ready_studies() -> list[dict[str, Any]]:
    opening_dir = _ROOT / "service" / "acknowledge" / "opening_state"
    if not opening_dir.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for p in sorted(opening_dir.glob("*.opening.json")):
        stem = p.name[: -len(".opening.json")]
        paths = resolve_study(stem)
        ready = (
            paths.background.is_file()
            and paths.concerns.is_file()
            and (p.is_file() or (paths.background.is_file() and paths.concerns.is_file()))
        )
        items.append({"stem": stem, "label": stem, "ready": ready})
    # Also include studies that have bg+concerns but no opening (random persona can generate)
    for stem in {
        p.name[: -len(".background.json")]
        for p in (_ROOT / "service" / "acknowledge" / "relative_experiment").glob(
            "*.background.json"
        )
    }:
        if any(x["stem"] == stem for x in items):
            continue
        paths = resolve_study(stem)
        if paths.background.is_file() and paths.concerns.is_file():
            items.append({"stem": stem, "label": stem, "ready": True})
    items.sort(key=lambda x: x["stem"])
    return items


def _new_session_dir() -> Path:
    SESSIONS_BASE.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SESSIONS_BASE / f"session_{stamp}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def _persona_summary(persona: dict[str, Any] | None) -> str:
    if not persona:
        return ""
    from service.agent.personality import Persona

    try:
        constraints = persona.get("life_constraints") or ()
        if isinstance(constraints, list):
            constraints = tuple(constraints)
        return Persona(
            age_band=str(persona.get("age_band", "mid")),
            education=str(persona.get("education", "mid")),
            trial_experience=str(persona.get("trial_experience", "naive")),
            emotion_base=str(persona.get("emotion_base", "hesitant")),
            decision_role=str(persona.get("decision_role", "self")),
            companion=str(persona.get("companion", "alone")),
            life_constraints=tuple(constraints),
            pressure=str(persona.get("pressure", "mid")),
            seed=persona.get("seed") if isinstance(persona.get("seed"), int) else None,
        ).render()
    except Exception:  # noqa: BLE001
        return json.dumps(persona, ensure_ascii=False)


def _session_payload(
    session: DialogueSession,
    detail: dict[str, Any] | None = None,
    *,
    evaluation: dict[str, Any] | None = None,
    persona: dict[str, Any] | None = None,
    persona_text: str | None = None,
) -> dict[str, Any]:
    patient_line = ""
    if session.dialogue:
        last = session.dialogue[-1]
        if last.get("role") == "patient":
            patient_line = str(last.get("content", "") or "")
    if not patient_line:
        patient_line = session.last_line

    if detail is None:
        detail = {
            "患者画像": session.portrait,
            "状态": session.state,
            "患者台词": patient_line,
            "是否结束": session.ended,
        }
        if session.last_action:
            detail["动作"] = session.last_action
        if session.end_reason:
            detail["结束原因"] = session.end_reason

    if persona is None or persona_text is None:
        loaded_persona, loaded_text = _load_persona_bundle(session)
        if persona is None:
            persona = loaded_persona
        if persona_text is None:
            persona_text = loaded_text

    eval_path = session.root / "evaluation.json"
    if evaluation is None and eval_path.is_file():
        try:
            evaluation = load_json(eval_path)
        except Exception:  # noqa: BLE001
            evaluation = None

    return {
        "session_id": session.root.name,
        "study": session.study_stem,
        "patient_line": patient_line,
        "ended": session.ended,
        "end_reason": session.end_reason,
        "action": session.last_action,
        "detail": detail,
        "persona": persona,
        "persona_text": persona_text,
        "evaluation": evaluation,
        "messages": [
            {"role": m["role"], "content": m["content"]} for m in session.dialogue
        ],
    }


def _load_session(session_id: str) -> DialogueSession:
    session_dir = SESSIONS_BASE / session_id
    if not session_dir.is_dir() or not (session_dir / "state.json").is_file():
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

    meta_path = session_dir / "meta.json"
    meta = load_json(meta_path) if meta_path.is_file() else {}
    stem = str(meta.get("study_stem") or "")
    if not stem:
        raise HTTPException(status_code=400, detail="会话缺少 study_stem")

    paths = resolve_study(stem)
    bg_path = Path(meta["background_path"]) if meta.get("background_path") else paths.background
    concerns_path = (
        Path(meta["concerns_path"]) if meta.get("concerns_path") else paths.concerns
    )
    if not bg_path.is_file() or not concerns_path.is_file():
        raise HTTPException(status_code=400, detail="会话关联的背景/顾虑池文件缺失")

    background = load_json(bg_path)
    concerns = load_json(concerns_path)
    if not isinstance(background, dict) or not isinstance(concerns, list):
        raise HTTPException(status_code=400, detail="背景或顾虑池格式无效")

    return DialogueSession.load(session_dir, background=background, concerns=concerns)


def _attach_persona_meta(
    session: DialogueSession,
    *,
    persona: dict[str, Any] | None,
    persona_text: str,
    random_persona: bool,
) -> None:
    payload = {
        "random_persona": random_persona,
        "persona": persona,
        "persona_text": persona_text,
    }
    save_json(session.root / "persona.json", payload)


def _load_persona_bundle(session: DialogueSession) -> tuple[dict[str, Any] | None, str]:
    path = session.root / "persona.json"
    if not path.is_file():
        meta_path = session.root / "meta.json"
        meta = load_json(meta_path) if meta_path.is_file() else {}
        if isinstance(meta, dict):
            persona = meta.get("persona") if isinstance(meta.get("persona"), dict) else None
            text = str(meta.get("persona_text") or "") or _persona_summary(persona)
            return persona, text
        return None, ""
    data = load_json(path)
    if not isinstance(data, dict):
        return None, ""
    persona = data.get("persona") if isinstance(data.get("persona"), dict) else None
    text = str(data.get("persona_text") or "") or _persona_summary(persona)
    return persona, text


async def _run_evaluation(session: DialogueSession) -> dict[str, Any]:
    config = EvalConfig.from_env(trust_env=False)
    config.require_api_key()
    async with EvaluationAgent(config) as agent:
        report = await agent.evaluate(
            session.dialogue,
            scenario=f"临床试验入组前知情沟通 · {session.study_stem}",
        )
    payload = report.to_dict()
    save_json(session.root / "evaluation.json", payload)
    return payload


@app.get("/api/studies")
def list_studies() -> dict[str, Any]:
    return {"studies": _list_ready_studies()}


@app.post("/api/persona/sample")
def sample_persona_api() -> dict[str, Any]:
    persona = sample_persona()
    return {
        "persona": persona.to_dict(),
        "persona_text": persona.render(),
    }


@app.post("/api/sessions")
async def start_session(body: StartSessionBody) -> dict[str, Any]:
    paths = resolve_study(body.study.strip())
    if not paths.background.is_file() or not paths.concerns.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"研究「{paths.stem}」缺少研究背景或顾虑池",
        )

    background = load_json(paths.background)
    concerns = load_json(paths.concerns)
    if not isinstance(background, dict) or not isinstance(concerns, list):
        raise HTTPException(status_code=400, detail="背景须为对象，顾虑池须为数组")

    persona: dict[str, Any] | None = None
    persona_text = ""
    opening_path_str = ""

    if body.random_persona:
        ocfg = OpeningConfig.from_env(trust_env=False)
        try:
            ocfg.require_api_key()
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        try:
            async with OpeningQuestionAgent(ocfg) as agent:
                result = await agent.generate(
                    background=background,
                    concerns=concerns,
                )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"随机人设开局失败: {exc}") from exc
        opening = result.to_dict()
        persona = result.persona if isinstance(result.persona, dict) else None
        persona_text = _persona_summary(persona)
        opening_path_str = "(generated)"
    else:
        if not paths.opening.is_file():
            raise HTTPException(
                status_code=400,
                detail=f"研究「{paths.stem}」缺少开局文件；请改用「随机人设开局」",
            )
        opening = load_json(paths.opening)
        if not isinstance(opening, dict):
            raise HTTPException(status_code=400, detail="开局文件须为对象")
        opening_path_str = str(paths.opening.resolve())
        portrait = opening.get("患者画像")
        if isinstance(portrait, dict):
            persona_text = (
                f"固定开局画像：{portrait.get('年龄', '?')}岁 / "
                f"{portrait.get('学历', '')} / {portrait.get('交流特点', '')} / "
                f"{portrait.get('试验经历', '')}"
            )

    session_dir = _new_session_dir()
    session = DialogueSession.create_from_opening(
        session_dir=session_dir,
        background=background,
        concerns=concerns,
        opening=opening,
        background_path=str(paths.background.resolve()),
        concerns_path=str(paths.concerns.resolve()),
        opening_path=opening_path_str,
        study_stem=paths.stem,
    )
    _attach_persona_meta(
        session,
        persona=persona,
        persona_text=persona_text,
        random_persona=body.random_persona,
    )
    return _session_payload(
        session,
        persona=persona,
        persona_text=persona_text,
    )


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    return _session_payload(_load_session(session_id))


@app.post("/api/sessions/{session_id}/reply")
async def reply(session_id: str, body: ReplyBody) -> dict[str, Any]:
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="CRC 回答不能为空")

    session = _load_session(session_id)
    if session.ended:
        raise HTTPException(status_code=400, detail="会话已结束")

    config = PatientTurnConfig.from_env(trust_env=False)
    try:
        config.require_api_key()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        async with PatientTurnAgent(config) as agent:
            result = await agent.apply_crc_reply(session, message)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    evaluation: dict[str, Any] | None = None
    if result.ended:
        try:
            evaluation = await _run_evaluation(session)
        except Exception as exc:  # noqa: BLE001
            evaluation = {
                "error": str(exc),
                "summary": "自动评分失败，可稍后重试",
                "overall_score": None,
                "passed": False,
                "dimensions": [],
            }

    return _session_payload(
        session,
        detail=result.to_dict(),
        evaluation=evaluation,
    )


@app.post("/api/sessions/{session_id}/evaluate")
async def evaluate_session(session_id: str) -> dict[str, Any]:
    session = _load_session(session_id)
    if not session.dialogue:
        raise HTTPException(status_code=400, detail="对话为空，无法评分")
    try:
        evaluation = await _run_evaluation(session)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _session_payload(session, evaluation=evaluation)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONT_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONT_DIR), name="static")


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8790, reload=False)


if __name__ == "__main__":
    main()
