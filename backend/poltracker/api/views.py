"""Local personalization storage: saved views and the last-used screen. WRITES, so this router is mounted only in the desktop app (same-origin, single user) or when
POLTRACKER_LOCAL_VIEWS=1; never on the public read-only API. It stores user preferences only and never touches `trade_context`.
"""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..context_rules import PRESETS, ContextRule
from ..models import AppPreference, ContextView
from ..trade_screen import MAX_FILTERS, FilterSpec
from .main import get_session

router = APIRouter(prefix="/context")

MAX_VIEWS = 100
ACTIVE_KEY = "active_screen"


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _clean_name(value: str) -> str:
    name = " ".join(value.split())
    if not 1 <= len(name) <= 80:
        raise ValueError("a view name is 1 to 80 characters")
    return name


def _check_preset(value: str | None) -> str | None:
    if value is not None and value != "custom" and value not in PRESETS:
        raise ValueError(f"unknown preset {value!r}")
    return value


class ViewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    rule: ContextRule = Field(default_factory=ContextRule)
    filters: list[FilterSpec] = Field(default_factory=list, max_length=MAX_FILTERS)
    preset: str | None = None

    _name = field_validator("name")(lambda cls, v: _clean_name(v))
    _preset = field_validator("preset")(lambda cls, v: _check_preset(v))


class ViewPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    rule: ContextRule | None = None
    filters: list[FilterSpec] | None = Field(default=None, max_length=MAX_FILTERS)
    preset: str | None = None

    _name = field_validator("name")(lambda cls, v: None if v is None else _clean_name(v))
    _preset = field_validator("preset")(lambda cls, v: _check_preset(v))


class ViewOut(BaseModel):
    id: int
    name: str
    preset: str | None
    rule: ContextRule
    filters: list[FilterSpec]
    created_at: datetime
    updated_at: datetime


class ActiveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule: ContextRule = Field(default_factory=ContextRule)
    filters: list[FilterSpec] = Field(default_factory=list, max_length=MAX_FILTERS)
    preset: str | None = "balanced"  # a built-in preset key, 'custom', or None
    view_id: int | None = None  # the saved view this started from, if any

    _preset = field_validator("preset")(lambda cls, v: _check_preset(v))


class ActiveOut(ActiveIn):
    saved: bool  # False until the user has changed something: the screen is the default methodology


def _view_out(v: ContextView) -> ViewOut:
    return ViewOut(id=v.id, name=v.name, preset=v.preset, rule=ContextRule.model_validate_json(v.rule_json),
                   filters=[FilterSpec.model_validate(f) for f in json.loads(v.filters_json)], created_at=v.created_at, updated_at=v.updated_at)


def _dump_filters(filters: list[FilterSpec]) -> str:
    return json.dumps([f.model_dump(mode="json") for f in filters])


def _name_taken(session: Session, name: str, except_id: int | None = None) -> bool:
    q = select(ContextView.id).where(func.lower(ContextView.name) == name.lower())
    if except_id is not None:
        q = q.where(ContextView.id != except_id)
    return session.scalar(q) is not None


@router.get("/views", response_model=list[ViewOut])
def list_views(session: Session = Depends(get_session)) -> list[ViewOut]:
    return [_view_out(v) for v in session.scalars(select(ContextView).order_by(func.lower(ContextView.name), ContextView.id))]


@router.post("/views", response_model=ViewOut, status_code=201)
def create_view(body: ViewIn, session: Session = Depends(get_session)) -> ViewOut:
    if (session.scalar(select(func.count()).select_from(ContextView)) or 0) >= MAX_VIEWS:
        raise HTTPException(409, f"at most {MAX_VIEWS} saved views")
    if _name_taken(session, body.name):
        raise HTTPException(409, f"a view named {body.name!r} already exists")
    now = _now()
    view = ContextView(name=body.name, preset=body.preset, rule_json=body.rule.model_dump_json(), filters_json=_dump_filters(body.filters), created_at=now, updated_at=now)
    session.add(view)
    session.commit()
    return _view_out(view)


@router.patch("/views/{view_id}", response_model=ViewOut)
def update_view(view_id: int, body: ViewPatch, session: Session = Depends(get_session)) -> ViewOut:
    view = session.get(ContextView, view_id)
    if view is None:
        raise HTTPException(404, "View not found")
    fields = body.model_fields_set
    if "name" in fields and body.name is not None:
        if _name_taken(session, body.name, view_id):
            raise HTTPException(409, f"a view named {body.name!r} already exists")
        view.name = body.name
    if "rule" in fields and body.rule is not None:
        view.rule_json = body.rule.model_dump_json()
    if "filters" in fields and body.filters is not None:
        view.filters_json = _dump_filters(body.filters)
    if "preset" in fields:
        view.preset = body.preset
    view.updated_at = _now()
    session.commit()
    return _view_out(view)


@router.delete("/views/{view_id}", status_code=204)
def delete_view(view_id: int, session: Session = Depends(get_session)) -> Response:
    view = session.get(ContextView, view_id)
    if view is None:
        raise HTTPException(404, "View not found")
    session.delete(view)
    session.commit()
    return Response(status_code=204)


@router.get("/active", response_model=ActiveOut)
def get_active(session: Session = Depends(get_session)) -> ActiveOut:
    row = session.get(AppPreference, ACTIVE_KEY)
    if row is not None:
        try:
            return ActiveOut(**ActiveIn.model_validate_json(row.value_json).model_dump(), saved=True)
        except ValidationError:
            pass  # an unreadable stored value falls back to the default rather than breaking the page
    return ActiveOut(saved=False)


@router.put("/active", response_model=ActiveOut)
def put_active(body: ActiveIn, session: Session = Depends(get_session)) -> ActiveOut:
    if body.view_id is not None and session.get(ContextView, body.view_id) is None:
        body = body.model_copy(update={"view_id": None})  # the saved view was deleted since: remember the screen, not the dangling link
    row = session.get(AppPreference, ACTIVE_KEY)
    payload = body.model_dump_json()
    if row is None:
        session.add(AppPreference(key=ACTIVE_KEY, value_json=payload, updated_at=_now()))
    else:
        row.value_json, row.updated_at = payload, _now()
    session.commit()
    return ActiveOut(**body.model_dump(), saved=True)


@router.delete("/active", response_model=ActiveOut)
def reset_active(session: Session = Depends(get_session)) -> ActiveOut:
    row = session.get(AppPreference, ACTIVE_KEY)
    if row is not None:
        session.delete(row)
        session.commit()
    return ActiveOut(saved=False)
