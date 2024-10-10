import ipaddress
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.api import limiter
from app.api.constants import ONLY_FOR_INTERNAL_USAGE
from app.api.models import Invitation, APIKey

router = APIRouter()


def generate_token():
    return secrets.token_urlsafe(32)


def is_local_network(request: Request):
    if not request.client:
        return False

    client_ip = request.client.host
    ip = ipaddress.ip_address(client_ip)
    if ip.is_loopback or ip.is_private:
        return True

    return False


@router.post("/create/invitation")
@limiter.limit("5/minute")
def create_invitation(request: Request):
    if not is_local_network(request):
        raise HTTPException(
            status_code=403,
            detail=ONLY_FOR_INTERNAL_USAGE,
        )

    inv = Invitation(
        code=generate_token(),
    )
    inv.save()
    return {"code": inv.code, "expires_at": inv.expires_at}


@router.post("/create/token")
@limiter.limit("5/minute")
def generate_api_key(request: Request, invitation_code: str):
    inv: Optional[Invitation] = (
        Invitation.select().where(Invitation.code == invitation_code).first()
    )
    if not inv:
        raise HTTPException(
            status_code=400, detail="Invalid invitation code"
        )

    if not inv.active:
        raise HTTPException(
            status_code=400, detail="Invitation code already used"
        )

    if inv.expires_at < datetime.now():
        inv.active = False
        inv.save()
        raise HTTPException(
            status_code=400,
            detail=f"Invitation expired at {inv.expires_at.to_value().strftime('%d/%m/%Y %H:%M:%S')}",
        )

    key: APIKey = APIKey.create(token=generate_token(), invitation_id=inv.id)
    key.save()

    inv.active = False
    inv.used_at = datetime.now()
    inv.save()
    return {"token": key.token}
