"""
认证相关Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class SendCodeRequest(BaseModel):
    """发送验证码请求"""
    phone: str = Field(..., description="手机号", min_length=11, max_length=11)
    type: str = Field(..., description="验证码类型：login/register")
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v
    
    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in ["login", "register"]:
            raise ValueError("验证码类型必须为login或register")
        return v


class SendCodeResponse(BaseModel):
    """发送验证码响应"""
    expire_in: int = Field(default=300, description="验证码有效期（秒）")


class LoginRequest(BaseModel):
    """登录请求"""
    phone: str = Field(..., description="手机号", min_length=11, max_length=11)
    code: str = Field(..., description="验证码", min_length=6, max_length=6)
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v
    
    @field_validator("code")
    @classmethod
    def validate_code(cls, v):
        if not re.match(r"^\d{6}$", v):
            raise ValueError("验证码必须为6位数字")
        return v


class UserInfo(BaseModel):
    """用户信息"""
    id: str = Field(..., description="用户ID")
    phone: str = Field(..., description="手机号")
    username: Optional[str] = Field(default=None, description="用户名")
    email: Optional[str] = Field(default=None, description="邮箱")
    role: str = Field(..., description="用户角色")
    risk_preference: str = Field(..., description="风险偏好")
    is_active: bool = Field(default=True, description="是否激活")
    created_at: datetime = Field(..., description="创建时间")
    last_login_at: Optional[datetime] = Field(default=None, description="最后登录时间")
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    refresh_token: str = Field(..., description="刷新令牌")
    user: UserInfo = Field(..., description="用户信息")


class RegisterRequest(BaseModel):
    """注册请求"""
    phone: str = Field(..., description="手机号", min_length=11, max_length=11)
    code: str = Field(..., description="验证码", min_length=6, max_length=6)
    password: str = Field(..., description="密码", min_length=6, max_length=20)
    confirm_password: str = Field(..., description="确认密码", min_length=6, max_length=20)
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v
    
    @field_validator("code")
    @classmethod
    def validate_code(cls, v):
        if not re.match(r"^\d{6}$", v):
            raise ValueError("验证码必须为6位数字")
        return v
    
    @field_validator("confirm_password")
    @classmethod
    def validate_passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("两次输入的密码不一致")
        return v


class RegisterResponse(BaseModel):
    """注册响应"""
    user_id: str = Field(..., description="用户ID")
    phone: str = Field(..., description="手机号")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class RefreshTokenResponse(BaseModel):
    """刷新令牌响应"""
    access_token: str = Field(..., description="新的访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
