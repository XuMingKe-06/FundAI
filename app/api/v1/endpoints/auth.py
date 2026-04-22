"""
认证API端点
"""
import random
import secrets
import string
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
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
    UserInfo,
    TokenCheckResponse
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
    
    print(f"[Auth] Received request: send_verification_code")
    print(f"[Auth] Request params: phone={phone}")
    
    # 开发环境：使用固定验证码，无需短信服务
    if settings.DEBUG:
        code = "123456"
        cache_key = CacheKeys.VERIFY_CODE.format(phone=phone, type="auth")
        await redis.setex(cache_key, CacheExpire.VERIFY_CODE, code)
        print(f"[Auth] Processing result: code={code}, cache_key={cache_key}, stored=True, mode=debug")
        print(f"[开发模式] 手机号 {phone} 的验证码: {code}")
        return ApiResponse(
            code=200,
            message="验证码发送成功（开发模式）",
            data=SendCodeResponse(expire_in=CacheExpire.VERIFY_CODE)
        )
    
    # 生产环境：生成随机验证码并发送短信
    code = generate_verification_code()
    
    # 存储验证码到Redis，统一使用 "auth" 类型
    cache_key = CacheKeys.VERIFY_CODE.format(phone=phone, type="auth")
    await redis.setex(cache_key, CacheExpire.VERIFY_CODE, code)
    
    print(f"[Auth] Processing result: code={code}, cache_key={cache_key}, stored=True, mode=production")
    
    # TODO: 调用短信服务发送验证码
    # 实际需要调用阿里云短信API
    print(f"验证码: {code}")
    
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
    
    print(f"[Auth] Received request: login")
    print(f"[Auth] Request params: phone={phone}, code={code}")
    
    # 开发环境：接受固定验证码 "123456"
    if settings.DEBUG and code == "123456":
        print(f"[开发模式] 手机号 {phone} 使用固定验证码登录")
    else:
        # 生产环境：验证 Redis 中的验证码
        cache_key = CacheKeys.VERIFY_CODE.format(phone=phone, type="auth")
        saved_code = await redis.get(cache_key)
        
        if not saved_code:
            print(f"[Auth] Processing result: verification_code_expired=True, phone={phone}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码已过期，请重新获取"
            )
        
        if saved_code != code:
            print(f"[Auth] Processing result: verification_code_invalid=True, phone={phone}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="验证码错误"
            )
        
        # 验证成功后删除验证码
        await redis.delete(cache_key)
        print(f"[Auth] Processing result: verification_code_valid=True, phone={phone}")
    
    # 查找用户
    result = await session.execute(
        select(User).where(User.phone == phone)
    )
    user = result.scalar_one_or_none()
    print(f"[Auth] Processing result: user_exists={user is not None}, user_id={user.id if user else None}")
    
    # 用户不存在时自动创建新用户
    if not user:
        salt = generate_salt()
        new_user = User(
            phone=phone,
            password_hash=get_password_hash("placeholder_password"),
            salt=salt,
            role="investor",
            risk_preference="neutral"
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        user = new_user
        print(f"[Auth] Processing result: new_user_created=True, user_id={user.id}, phone={user.phone}")
    
    if not user.is_active:
        print(f"[Auth] Processing result: user_inactive=True, user_id={user.id}")
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
    
    print(f"[Auth] Processing result: login_success=True, user_id={user.id}, access_token_generated=True")
    
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


@router.get("/check-token", response_model=ApiResponse[TokenCheckResponse])
async def check_token(
    session: AsyncSession = Depends(get_async_session)
):
    """
    Token诊断接口
    
    检查请求头中的Authorization token是否有效，返回详细的诊断信息。
    用于排查认证问题。
    """
    from fastapi import Request
    from datetime import datetime
    
    # 从请求头获取token
    # 注意：这个接口不需要强制认证，我们手动解析token
    from fastapi import Header
    from typing import Optional
    
    # 重新定义一个不依赖Depends的版本
    return ApiResponse(
        code=200,
        message="请使用POST方法传递token",
        data=TokenCheckResponse(
            valid=False,
            error="请使用POST方法传递token"
        )
    )


@router.post("/check-token", response_model=ApiResponse[TokenCheckResponse])
async def check_token_post(
    session: AsyncSession = Depends(get_async_session),
    authorization: Optional[str] = Header(default=None)
):
    """
    Token诊断接口（POST方法）
    
    检查请求头中的Authorization token是否有效，返回详细的诊断信息。
    用于排查认证问题。
    """
    from datetime import datetime
    
    # 检查Authorization头是否存在
    if not authorization:
        return ApiResponse(
            code=200,
            message="未提供Authorization头",
            data=TokenCheckResponse(
                valid=False,
                error="未提供Authorization头"
            )
        )
    
    # 解析Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return ApiResponse(
            code=200,
            message="Authorization头格式错误",
            data=TokenCheckResponse(
                valid=False,
                error="Authorization头格式错误，应为: Bearer <token>"
            )
        )
    
    token = parts[1]
    
    # 解码token
    payload = decode_token(token)
    
    if payload is None:
        return ApiResponse(
            code=200,
            message="Token无效或已过期",
            data=TokenCheckResponse(
                valid=False,
                error="Token无效或已过期（JWT解码失败）"
            )
        )
    
    # 提取token信息
    user_id = payload.get("sub")
    phone = payload.get("phone")
    token_type = payload.get("type")
    exp = payload.get("exp")
    iat = payload.get("iat")
    
    # 转换时间戳
    expires_at = datetime.fromtimestamp(exp) if exp else None
    issued_at = datetime.fromtimestamp(iat) if iat else None
    
    # 检查token类型
    if token_type != "access":
        return ApiResponse(
            code=200,
            message="Token类型错误",
            data=TokenCheckResponse(
                valid=False,
                user_id=user_id,
                phone=phone,
                token_type=token_type,
                expires_at=expires_at,
                issued_at=issued_at,
                error=f"Token类型错误，期望'access'，实际为'{token_type}'"
            )
        )
    
    # 检查用户是否存在
    user_exists = False
    user_active = False
    
    if user_id:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user_exists = True
            user_active = user.is_active
    
    # 构建响应
    is_valid = user_exists and user_active
    
    return ApiResponse(
        code=200,
        message="Token诊断完成",
        data=TokenCheckResponse(
            valid=is_valid,
            user_id=user_id,
            phone=phone,
            token_type=token_type,
            expires_at=expires_at,
            issued_at=issued_at,
            user_exists=user_exists,
            user_active=user_active,
            error=None if is_valid else ("用户不存在" if not user_exists else "用户已被禁用")
        )
    )
