import bcrypt
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.config import settings

def get_password_hash(password: str) -> str:
    """Hashes a plaintext password using modern bcrypt."""
    # bcrypt requires bytes, so we encode the string.
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    # We decode it back to a string so SQLAlchemy can store it easily.
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against the stored hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Generates a JWT containing the user's ID and their tenant's ID."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.identity_user_jwt_expire_minutes)
        
    to_encode.update({"exp": expire})
    
    # We encode using the Identity Service's own secret key
    encoded_jwt = jwt.encode(to_encode, settings.identity_secret_key, algorithm=settings.identity_algorithm)
    return encoded_jwt