from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import clock
from app.db.session import get_db, uow
from app.models.notify import Notification
from app.models.user import User
from app.services import audit

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    subject: str
    body: str
    related_type: str | None
    related_id: str | None
    read_at: datetime | None
    created_at: datetime


@router.get("", response_model=list[NotificationOut])
def list_notifications(unread: bool = False, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    q = select(Notification).where(Notification.user_id == user.id,
                                   Notification.channel == "IN_APP")
    if unread:
        q = q.where(Notification.read_at.is_(None))
    return db.scalars(q.order_by(Notification.created_at.desc())).all()


@router.get("/unread-count")
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"count": db.scalar(select(func.count()).select_from(Notification).where(
        Notification.user_id == user.id, Notification.channel == "IN_APP",
        Notification.read_at.is_(None)))}


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: str, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.id or n.channel != "IN_APP":
        raise HTTPException(404, "Notification not found")  # never reveal other users' ids
    with uow(db):
        n.read_at = clock.now()
        audit.append(db, actor_id=user.id, actor_role=user.role, action="NOTIFICATION.READ",
                     entity_type="notification", entity_id=n.id)
    return n
