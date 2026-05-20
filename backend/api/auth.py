"""
API Router — Authentication
POST /auth/register
POST /auth/login
GET  /auth/me
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

from typing import Dict, Any
from backend.db.session import get_db
from backend.models.user import User
from backend.schemas.auth import RegisterRequest, LoginRequest, GoogleLoginRequest, TokenResponse, UserResponse
from backend.config.settings import get_settings
from backend.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def _hash(password: str) -> str:
    return await run_in_threadpool(pwd_ctx.hash, password)

async def _verify(plain: str, hashed: str) -> bool:
    return await run_in_threadpool(pwd_ctx.verify, plain, hashed)

def _create_token(user_id, lang: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "lang": lang, "exp": expire},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Duplicate check
    conditions = []
    if payload.phone:
        conditions.append(User.phone == payload.phone)
    if payload.email:
        conditions.append(User.email == payload.email)
    
    if conditions:
        result = await db.execute(select(User).where(or_(*conditions)))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Phone or email already registered.")

    user = User(
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        hashed_password=await _hash(payload.password),
        preferred_lang=payload.preferred_lang or "en",
    )
    db.add(user)
    try:
        await db.commit()
        # Removed db.refresh(user) to reduce round-trips
        token = _create_token(user.id, user.preferred_lang)
        logger.info(f"[auth] New user registered: id={user.id} phone={user.phone}")
        return TokenResponse(access_token=token, user_id=user.id, preferred_lang=user.preferred_lang)
    except Exception as e:
        await db.rollback()
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"[auth] Registration CRITICAL FAILURE:\n{error_trace}")
        raise HTTPException(
            status_code=500, 
            detail=f"Database Error: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Robust identifier matching
    ident = payload.identifier.strip().lower()
    result = await db.execute(
        select(User).where(
            or_(User.phone == ident, User.email == ident)
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.warning(f"[auth] Login failed: User not found for {ident}")
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    
    if not await _verify(payload.password, user.hashed_password):
        logger.warning(f"[auth] Login failed: Password mismatch for {ident}")
        raise HTTPException(status_code=401, detail="Invalid credentials.")


    token = _create_token(user.id, user.preferred_lang)
    return TokenResponse(access_token=token, user_id=user.id, preferred_lang=user.preferred_lang)

@router.post("/google", response_model=TokenResponse)
async def google_login(payload: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email == payload.email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Create a new user if one doesn't exist
        user = User(
            name=payload.name,
            phone="Google-" + payload.google_id[:8], # Temporary safe phone filler
            email=payload.email,
            hashed_password=await _hash(payload.google_id),  # Use google id as hash
            preferred_lang="en", # Default
        )
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
            logger.info(f"[auth] New Google user registered: email={user.email}")
        except Exception as e:
            await db.rollback()
            logger.error(f"[auth] Google Registration failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to persist Google user")

    token = _create_token(user.id, user.preferred_lang)
    return TokenResponse(access_token=token, user_id=user.id, preferred_lang=user.preferred_lang)


from backend.app.dependencies import get_current_user

@router.get("/me", response_model=UserResponse)
async def get_me(current_user = Depends(get_current_user)):
    return current_user


from fastapi import Path

@router.patch("/preference/{uid}")
async def update_preference(uid: str = Path(..., title="The ID of the user to update"), payload: dict = {}, db: AsyncSession = Depends(get_db)):
    """Updates user's preferred language."""
    new_lang = payload.get("preferred_lang")
    if not new_lang or new_lang not in ("en", "kn", "hi", "te"):
        raise HTTPException(status_code=400, detail="Invalid language code")
        
    import uuid
    try:
        uuid_obj = uuid.UUID(str(uid))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format.")
    
    result = await db.execute(select(User).where(User.id == uuid_obj))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.preferred_lang = new_lang
    await db.commit()
    logger.info(f"[auth] Updated preference for {uid}: lang={new_lang}")
    return {"status": "success", "preferred_lang": new_lang}

@router.get("/ping")
async def ping():
    return {"status": "ok", "message": "AquaSol Backend is Reachable!"}
@router.put("/profile")
async def update_profile(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user profile details."""
    if "name" in payload:
        current_user.name = payload["name"]
    if "email" in payload:
        current_user.email = payload["email"]
    if "preferred_lang" in payload:
        current_user.preferred_lang = payload["preferred_lang"]
    if "avatar_url" in payload:
        current_user.avatar_url = payload["avatar_url"]
        
    await db.commit()
    return {"status": "success", "user": {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
        "preferred_lang": current_user.preferred_lang,
        "avatar_url": current_user.avatar_url
    }}
