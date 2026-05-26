"""LLM Profile endpoints。"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.application.settings_service import SettingsService
from app.domain.models import LlmProfile

from .dependencies import get_settings_service
from .schemas import (
    LlmProfileIn,
    LlmProfileOut,
    ProfileImportIn,
    ProfileTestStartIn,
)

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings/llm-profiles", tags=["settings"])


def _out(p: LlmProfile) -> LlmProfileOut:
    return LlmProfileOut(
        id=p.id, name=p.name, provider=p.provider, model=p.model,
        api_key=p.api_key, base_url=p.base_url, auth_type=p.auth_type,
        max_tokens=p.max_tokens, temperature=p.temperature,
        extra_headers=dict(p.extra_headers or {}),
        verified_at=p.verified_at,
    )


def _domain_from_in(body: LlmProfileIn) -> LlmProfile:
    p = LlmProfile(
        name=body.name, provider=body.provider, model=body.model,
        api_key=body.api_key, base_url=body.base_url, auth_type=body.auth_type,
        max_tokens=body.max_tokens, temperature=body.temperature,
        extra_headers=dict(body.extra_headers or {}),
    )
    if body.id:
        p.id = body.id
    return p


def _sse(event: str, data: dict) -> bytes:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


@router.get("", response_model=list[LlmProfileOut])
async def list_profiles(svc: SettingsService = Depends(get_settings_service)):
    return [_out(p) for p in await svc.list()]


@router.post("", response_model=LlmProfileOut)
async def upsert_profile(
    body: LlmProfileIn,
    svc: SettingsService = Depends(get_settings_service),
):
    profile = LlmProfile(
        name=body.name, provider=body.provider, model=body.model,
        api_key=body.api_key, base_url=body.base_url, auth_type=body.auth_type,
        max_tokens=body.max_tokens, temperature=body.temperature,
        extra_headers=dict(body.extra_headers or {}),
    )
    if body.id:
        profile.id = body.id
    try:
        return _out(await svc.upsert(profile))
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(profile_id: str, svc: SettingsService = Depends(get_settings_service)):
    await svc.delete(profile_id)


@router.get("/active", response_model=LlmProfileOut | None)
async def get_active(svc: SettingsService = Depends(get_settings_service)):
    p = await svc.get_active()
    return _out(p) if p else None


@router.post("/{profile_id}/activate", status_code=204)
async def activate(profile_id: str, svc: SettingsService = Depends(get_settings_service)):
    await svc.set_active(profile_id)


@router.post("/import", response_model=LlmProfileOut)
async def import_profile(
    body: ProfileImportIn,
    svc: SettingsService = Depends(get_settings_service),
):
    """解析任意来源(env JSON / curl)文本为未保存的 draft profile。
    前端拿到 draft 后,显示在表单里给用户校对,再走 POST 保存。
    """
    try:
        draft = await svc.import_from_text(body.text, body.fallback_name)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return _out(draft)


@router.post("/test")
async def test_profile_stream(
    body: ProfileTestStartIn,
    svc: SettingsService = Depends(get_settings_service),
):
    """SSE:实测一个未保存的 profile。
    若 body.profile.id 非空且对应到已存在记录,成功后写 verified_at。
    """
    profile = _domain_from_in(body.profile)
    persist_id = body.profile.id

    async def gen():
        try:
            async for ev in svc.test_profile(profile, persist_id=persist_id):
                event_name = ev.pop("event")
                yield _sse(event_name, ev)
        except Exception as e:  # noqa: BLE001
            _log.exception("profile test failed")
            yield _sse("error", {"title": "测试失败", "detail": str(e)})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
