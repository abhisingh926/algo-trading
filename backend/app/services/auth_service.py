from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import AuthenticationError, ConflictError, PermissionDeniedError
from app.core.logging import get_logger, log_event
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import AuthStatus, AuthToken, UserRead

logger = get_logger(__name__)


class AuthService:
    def __init__(self, users: UserRepository, settings: Settings) -> None:
        self.users = users
        self.settings = settings

    async def status(self) -> AuthStatus:
        has_users = await self.users.count() > 0
        return AuthStatus(
            auth_enabled=self.settings.auth_enabled,
            registration_open=self.settings.auth_enabled
            and (not has_users or self.settings.allow_registration),
            has_users=has_users,
        )

    def _token(self, user: User) -> AuthToken:
        token, expires_in = create_access_token(user.id, self.settings)
        return AuthToken(access_token=token, expires_in=expires_in, user=UserRead.model_validate(user))

    async def register(self, email: str, password: str, full_name: str) -> AuthToken:
        first_user = await self.users.count() == 0
        if not first_user and not self.settings.allow_registration:
            raise PermissionDeniedError(
                "Registration is closed. Ask an administrator or set ALLOW_REGISTRATION=true."
            )
        if await self.users.get_by_email(email) is not None:
            raise ConflictError("An account with this email already exists")
        user = await self.users.create(
            User(
                email=email.lower(),
                full_name=full_name,
                hashed_password=hash_password(password),
                is_admin=first_user,
            )
        )
        log_event(logger, "user_registered", user_id=user.id, is_admin=first_user)
        return self._token(user)

    async def login(self, email: str, password: str) -> AuthToken:
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Incorrect email or password")
        if not user.is_active:
            raise AuthenticationError("This account is disabled")
        return self._token(user)

    async def authenticate(self, token: str) -> User:
        payload = decode_access_token(token, self.settings)
        user = await self.users.get_by_id(str(payload.get("sub", "")))
        if user is None or not user.is_active:
            raise AuthenticationError("User no longer exists or is disabled")
        return user
