"""FastAPI dependency providers. Routers depend on services only - never on sessions or models."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.container import AppContainer
from app.core.exceptions import AuthenticationError
from app.models.user import User
from app.services.factory import Services

_bearer = HTTPBearer(auto_error=False, description="JWT from POST /api/v1/auth/login")


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


async def get_session(
    container: Annotated[AppContainer, Depends(get_container)],
) -> AsyncIterator[AsyncSession]:
    async for session in container.db.session():
        yield session


def get_services(
    session: Annotated[AsyncSession, Depends(get_session)],
    container: Annotated[AppContainer, Depends(get_container)],
) -> Services:
    return Services(session, container)


ServicesDep = Annotated[Services, Depends(get_services)]


async def get_current_user(
    services: ServicesDep, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> User | None:
    """Authenticated user, or None when AUTH_ENABLED=false (single-operator dev mode)."""
    if not services.settings.auth_enabled:
        return None
    if credentials is None:
        raise AuthenticationError("Missing bearer token")
    return await services.auth.authenticate(credentials.credentials)


CurrentUser = Annotated[User | None, Depends(get_current_user)]


def user_id_of(user: User | None) -> str | None:
    return user.id if user else None
