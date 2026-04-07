from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import CurrentUser, DBSession, require_roles
from app.core.enums import Role
from app.models.entities import User
from app.core.security import decode_token
from app.schemas.auth import AcceptInviteRequest, InviteDelegateRequest, LoginRequest, RefreshRequest, UserRegistration
from app.schemas.common import MessageResponse, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter()
service = AuthService()


@router.post("/register-owner", response_model=TokenResponse)
def register_owner(payload: UserRegistration, db: DBSession) -> TokenResponse:
    user = service.register_owner(db, payload)
    return TokenResponse(**service.issue_tokens(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DBSession) -> TokenResponse:
    user = service.authenticate(db, payload)
    return TokenResponse(**service.issue_tokens(user))


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: DBSession) -> TokenResponse:
    try:
        claims = decode_token(payload.refresh_token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc
    if claims.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = service.users.get(db, int(claims["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return TokenResponse(**service.issue_tokens(user))


@router.post("/invite-delegate", response_model=MessageResponse)
def invite_delegate(
    payload: InviteDelegateRequest,
    db: DBSession,
    current_user: User = Depends(require_roles(Role.OWNER, Role.OPS_ADMIN)),
) -> MessageResponse:
    delegate = service.invite_delegate(db, current_user, payload)
    return MessageResponse(message=f"Delegate invited. invite_token={delegate.invite_token}")


@router.post("/accept-invite", response_model=TokenResponse)
def accept_invite(payload: AcceptInviteRequest, db: DBSession) -> TokenResponse:
    user = service.accept_invite(db, payload)
    return TokenResponse(**service.issue_tokens(user))


@router.get("/me", response_model=dict)
def me(current_user: CurrentUser) -> dict:
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role.value}
