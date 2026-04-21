"""
认证API端点
"""
import random
import string
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from redis.asyncio import Redis

from app.core.database import get_async_session
from app.core.redis_client import get_redis, CacheKeys, CacheExpire
from app.core.security import (
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user
)
from app.core.config import settings
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.auth import (
    SendCodeRequest,
    SendCodeResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    UserInfo
)

router = APIRouter(prefix="/auth", tags=["认证"])


def generate_verification_code() -> str:
    """生成6位数字验证码"""
    return "".join([str(random.randint(0, 9)) for _ in range(6)])


def generate_salt() -> str:
    """生成密码盐值"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=64))


@router.post("/send-code", response_model=ApiResponse[SendCodeResponse])
async def send_verification_code(
    request: SendCodeRequest,
    session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis)
):
    """发送手机验证码"""
    phone = request.phone
    
    # 生成验证码
    code = generate_verification_code()
    
    # 存储验证码到Redis，统一使用 "auth" 类型
    cache_key = CacheKeys.VERIFY_CODE.format(phone=phone, type="auth")
    await redis.setex(cache_key, CacheExpire.VERIFY_CODE, code)
    
    # TODO: 调用短信服务发送验证码
    # 这里只是模拟，实际需要调用阿里云短信API
    print(f"验证码: {code}")  # 开发环境打印验证码
    
    return ApiResponse(
        code=200,
        message="验证码发送成功",
        data=SendCodeResponse(expire_in=CacheExpire.VERIFY_CODE)
    )


@router.post("/login", response_model=ApiResponse[LoginResponse])
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis)
):
    """用户登录（支持自动注册）"""
    phone = request.phone
    code = request.code
    
    # 验证验证码，统一使用 "auth" 类型
    cache_key = CacheKeys.VERIFY_CODE.format(phone=phone, type="auth")
    saved_code = await redis.get(cache_key)
    
    if not saved_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码已过期，请重新获取"
        )
    
    if saved_code != code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="验证码错误"
        )
    
    # 查找用户
    result = await session.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()
    
    # 用户不存在时自动创建新用户
    if not user:
        new_user = User(
            phone=phone,
            role="investor",
            risk_preference="neutral"
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        user = new_user
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    await session.commit()
    
    # 生成令牌
    access_token = create_access_token({"sub": str(user.id), "phone": user.phone})
    refresh_token = create_refresh_token({"sub": str(user.id), "phone": user.phone})
    
    # 删除验证码
    await redis.delete(cache_key)
    
    return ApiResponse(
        code=200,
        message="登录成功",
        data=LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_token,
            user=UserInfo(
                id=str(user.id),
                phone=user.phone,
                username=user.username,
                email=user.email,
                role=user.role,
                risk_preference=user.risk_preference,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login_at=user.last_login_at
            )
        )
    )


@router.post("/refresh", response_model=ApiResponse[RefreshTokenResponse])
async def refresh_token(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """刷新访问令牌"""
    refresh_token = request.refresh_token
    
    # 解码刷新令牌
    payload = decode_token(refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌类型"
        )
    
    user_id = payload.get("sub")
    
    # 查找用户
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用"
        )
    
    # 生成新的访问令牌
    access_token = create_access_token({"sub": str(user.id), "phone": user.phone})
    
    return ApiResponse(
        code=200,
        message="令牌刷新成功",
        data=RefreshTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    )


@router.post("/logout", response_model=ApiResponse)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """用户登出"""
    # TODO: 将令牌加入黑名单
    return ApiResponse(code=200, message="登出成功")
