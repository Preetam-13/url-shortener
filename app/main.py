from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime, timedelta
from jose import jwt, JWTError
import secrets
import string
import json
import os

from argon2 import PasswordHasher

from .database import engine, Base, SessionLocal
from .models import URL
from .user_models import User
from .redis_client import redis_client


# ==========================================
# DATABASE SETUP
# ==========================================

Base.metadata.create_all(bind=engine)


# ==========================================
# FASTAPI APPLICATION
# ==========================================

app = FastAPI(
    title="URL Shortener API",
    description="A URL shortening and analytics platform",
    version="1.0.0"
)


# ==========================================
# PASSWORD HASHING
# ==========================================

password_hasher = PasswordHasher()

security = HTTPBearer()

# ==========================================
# JWT CONFIGURATION
# ==========================================

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "change-this-secret-key"
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60

# ==========================================
# REQUEST MODELS
# ==========================================

class URLRequest(BaseModel):

    original_url: HttpUrl

    custom_alias: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$"
    )

    expires_in_hours: Optional[int] = Field(
        default=None,
        gt=0
    )


class UserRegister(BaseModel):

    username: str = Field(
        min_length=3,
        max_length=50
    )

    email: str

    password: str = Field(
        min_length=8,
        max_length=100
    )

class UserLogin(BaseModel):
    username: str
    password: str


# ==========================================
# JWT AUTHENTICATION
# ==========================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    token = credentials.credentials

    try:

        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        user_id = payload.get("user_id")
        username = payload.get("username")

        if user_id is None or username is None:

            raise HTTPException(
                status_code=401,
                detail="Invalid token payload."
            )

        return {
            "user_id": user_id,
            "username": username
        }

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid JWT token."
        )

# ==========================================
# GENERATE RANDOM SHORT CODE
# ==========================================

def generate_short_code(length=6):

    characters = string.ascii_letters + string.digits

    return "".join(
        secrets.choice(characters)
        for _ in range(length)
    )


# ==========================================
# HOME
# ==========================================

@app.get("/")
def home():

    return {
        "message": "URL Shortener API is running"
    }


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/health")
def health():

    return {
        "status": "healthy"
    }


# ==========================================
# USER REGISTRATION
# ==========================================

@app.post("/auth/register")
def register_user(request: UserRegister):

    db = SessionLocal()

    try:

        # Check username
        existing_username = db.query(User).filter(
            User.username == request.username
        ).first()

        if existing_username:

            raise HTTPException(
                status_code=409,
                detail="Username already exists."
            )

        # Check email
        existing_email = db.query(User).filter(
            User.email == request.email
        ).first()

        if existing_email:

            raise HTTPException(
                status_code=409,
                detail="Email already exists."
            )

        # Hash password using Argon2
        password_hash = password_hasher.hash(
            request.password
        )

        # Create user
        new_user = User(
            username=request.username,
            email=request.email,
            password_hash=password_hash
        )

        db.add(new_user)

        db.commit()

        db.refresh(new_user)

        return {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "created_at": new_user.created_at
        }

    finally:

        db.close()

# ==========================================
# USER LOGIN
# ==========================================

@app.post("/auth/login")
def login_user(request: UserLogin):

    db = SessionLocal()

    try:

        # Find user
        user = db.query(User).filter(
            User.username == request.username
        ).first()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password."
            )

        # Verify password
        try:

            password_hasher.verify(
                user.password_hash,
                request.password
            )

        except Exception:

            raise HTTPException(
                status_code=401,
                detail="Invalid username or password."
            )

        # Create JWT payload
        payload = {
            "user_id": user.id,
            "username": user.username,
        "exp": datetime.utcnow() + timedelta(
        minutes=JWT_EXPIRATION_MINUTES
    )
}

        # Generate JWT token
        access_token = jwt.encode(
            payload,
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    finally:

        db.close()

# ==========================================
# CREATE SHORT URL
# ==========================================

@app.post("/urls")
def create_short_url(
    request: URLRequest,
    current_user: dict = Depends(get_current_user)):

    db = SessionLocal()

    try:

        # Choose custom alias or generate random code
        short_code = (
            request.custom_alias
            or generate_short_code()
        )

        # Check duplicate short code
        existing_url = db.query(URL).filter(
            URL.short_code == short_code
        ).first()

        if existing_url:

            raise HTTPException(
                status_code=409,
                detail="This short code is already in use."
            )

        # Calculate expiration
        expires_at = None

        if request.expires_in_hours:

            expires_at = (
                datetime.utcnow()
                + timedelta(
                    hours=request.expires_in_hours
                )
            )

        # Create database record
        new_url = URL(
    user_id=current_user["user_id"],
    original_url=str(request.original_url),
    short_code=short_code,
    expires_at=expires_at
)

        db.add(new_url)

        db.commit()

        db.refresh(new_url)

        # Prepare Redis cache data
        cache_data = {
            "original_url": new_url.original_url,
            "expires_at": (
                new_url.expires_at.isoformat()
                if new_url.expires_at
                else None
            )
        }

        redis_key = f"url:{short_code}"

        # Store in Redis
        if expires_at:

            ttl = int(
                (
                    expires_at
                    - datetime.utcnow()
                ).total_seconds()
            )

            if ttl > 0:

                redis_client.setex(
                    redis_key,
                    ttl,
                    json.dumps(cache_data)
                )

        else:

            redis_client.set(
                redis_key,
                json.dumps(cache_data)
            )

        return {
            "id": new_url.id,
            "original_url": new_url.original_url,
            "short_code": new_url.short_code,
            "short_url": (
                f"http://127.0.0.1:8000/"
                f"{new_url.short_code}"
            ),
            "expires_at": new_url.expires_at
        }

    finally:

        db.close()

# ==========================================
# GET CURRENT USER'S URLS
# ==========================================


@app.get("/users/me/urls")
def get_my_urls(
    current_user: dict = Depends(get_current_user)
):

    db = SessionLocal()

    try:

        urls = db.query(URL).filter(
            URL.user_id == current_user["user_id"]
        ).all()

        return [
            {
                "id": url.id,
                "original_url": url.original_url,
                "short_code": url.short_code,
                "click_count": url.click_count,
                "created_at": url.created_at,
                "expires_at": url.expires_at
            }
            for url in urls
        ]

    finally:

        db.close()


# ==========================================
# REDIRECT SHORT URL
# ==========================================

@app.get("/{short_code}")
def redirect_to_original(short_code: str):

    redis_key = f"url:{short_code}"

    # ======================================
    # REDIS CACHE HIT
    # ======================================

    cached_data = redis_client.get(redis_key)

    if cached_data:

        data = json.loads(cached_data)

        original_url = data["original_url"]

        # Check expiration
        if data["expires_at"]:

            expires_at = datetime.fromisoformat(
                data["expires_at"]
            )

            if datetime.utcnow() > expires_at:

                redis_client.delete(
                    redis_key
                )

                raise HTTPException(
                    status_code=410,
                    detail="This short URL has expired."
                )

        # Update click count
        db = SessionLocal()

        try:

            url = db.query(URL).filter(
                URL.short_code == short_code
            ).first()

            if not url:

                redis_client.delete(
                    redis_key
                )

                raise HTTPException(
                    status_code=404,
                    detail="Short URL not found"
                )

            url.click_count += 1

            db.commit()

        finally:

            db.close()

        return RedirectResponse(
            url=original_url
        )

    # ======================================
    # REDIS CACHE MISS
    # ======================================

    db = SessionLocal()

    try:

        url = db.query(URL).filter(
            URL.short_code == short_code
        ).first()

        if not url:

            raise HTTPException(
                status_code=404,
                detail="Short URL not found"
            )

        # Check expiration
        if (
            url.expires_at
            and datetime.utcnow() > url.expires_at
        ):

            raise HTTPException(
                status_code=410,
                detail="This short URL has expired."
            )

        # Prepare Redis cache data
        cache_data = {
            "original_url": url.original_url,
            "expires_at": (
                url.expires_at.isoformat()
                if url.expires_at
                else None
            )
        }

        # Cache URL
        if url.expires_at:

            ttl = int(
                (
                    url.expires_at
                    - datetime.utcnow()
                ).total_seconds()
            )

            if ttl > 0:

                redis_client.setex(
                    redis_key,
                    ttl,
                    json.dumps(cache_data)
                )

        else:

            redis_client.set(
                redis_key,
                json.dumps(cache_data)
            )

        # Increase click count
        url.click_count += 1

        db.commit()

        return RedirectResponse(
            url=url.original_url
        )

    finally:

        db.close()


# ==========================================
# URL ANALYTICS
# ==========================================

@app.get("/urls/{short_code}/analytics")
def get_url_analytics(
    short_code: str,
    current_user: dict = Depends(get_current_user)
):

    db = SessionLocal()

    try:

        url = db.query(URL).filter(
            URL.short_code == short_code
        ).first()

        if not url:

            raise HTTPException(
                status_code=404,
                detail="Short URL not found"
            )

        if url.user_id != current_user["user_id"]:

            raise HTTPException(
                status_code=403,
                detail="You do not have permission to view this URL's analytics."
            )

        return {
            "id": url.id,
            "original_url": url.original_url,
            "short_code": url.short_code,
            "click_count": url.click_count,
            "created_at": url.created_at,
            "expires_at": url.expires_at
        }

    finally:

        db.close()

# ==========================================
# DELETE URL
# ==========================================

@app.delete("/urls/{short_code}")
def delete_url(
    short_code: str,
    current_user: dict = Depends(get_current_user)
):

    db = SessionLocal()

    try:

        # Find URL
        url = db.query(URL).filter(
            URL.short_code == short_code
        ).first()

        if not url:

            raise HTTPException(
                status_code=404,
                detail="Short URL not found."
            )

        # Check ownership
        if url.user_id != current_user["user_id"]:

            raise HTTPException(
                status_code=403,
                detail="You do not have permission to delete this URL."
            )

        # Delete Redis cache
        redis_key = f"url:{short_code}"
        redis_client.delete(redis_key)

        # Delete database record
        db.delete(url)
        db.commit()

        return {
            "message": "Short URL deleted successfully.",
            "short_code": short_code
        }

    finally:

        db.close()