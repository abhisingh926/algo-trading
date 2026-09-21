from fastapi import APIRouter

from app.core.dependencies import CurrentUser, ServicesDep
from app.core.exceptions import AuthenticationError
from app.schemas.common import ApiResponse, ok
from app.schemas.user import AuthStatus, AuthToken, UserLogin, UserRead, UserRegister

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/status", response_model=ApiResponse[AuthStatus])
async def auth_status(services: ServicesDep):
    return ok(await services.auth.status(), "Auth status")


@router.post("/register", response_model=ApiResponse[AuthToken], status_code=201)
async def register(body: UserRegister, services: ServicesDep):
    token = await services.auth.register(body.email, body.password, body.full_name)
    return ok(token, "Account created successfully", 201, "User registered")


@router.post("/login", response_model=ApiResponse[AuthToken])
async def login(body: UserLogin, services: ServicesDep):
    return ok(await services.auth.login(body.email, body.password), "Logged in successfully")


@router.get("/me", response_model=ApiResponse[UserRead])
async def me(user: CurrentUser):
    if user is None:
        raise AuthenticationError("Authentication is disabled; there is no current user")
    return ok(UserRead.model_validate(user), "Current user")
