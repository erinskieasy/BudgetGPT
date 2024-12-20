import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from database import Database

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
SECRET_KEY = secrets.token_hex(32)  # Generate a random secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

class Auth:
    def __init__(self):
        self.db = Database()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Generate password hash."""
        return pwd_context.hash(password)

    def create_access_token(self, data: dict) -> str:
        """Create a new JWT token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def decode_token(self, token: str) -> Optional[dict]:
        """Decode and verify a JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None

    def register_user(self, username: str, password: str) -> dict:
        """Register a new user."""
        try:
            self.db.ensure_connection()
            with self.db.conn.cursor() as cur:
                # Check if username already exists
                cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cur.fetchone():
                    raise ValueError("Username already exists")

                # Create new user
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash)
                    VALUES (%s, %s)
                    RETURNING id, username, created_at;
                    """,
                    (username, self.get_password_hash(password))
                )
                user = cur.fetchone()
                self.db.conn.commit()

                return {
                    "id": user[0],
                    "username": user[1],
                    "created_at": user[2],
                }
        except Exception as e:
            self.db.conn.rollback()
            raise e

    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Authenticate a user and return user data if successful."""
        try:
            self.db.ensure_connection()
            with self.db.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, username, password_hash, created_at
                    FROM users
                    WHERE username = %s
                    """,
                    (username,)
                )
                user = cur.fetchone()
                
                if not user or not self.verify_password(password, user[2]):
                    return None

                return {
                    "id": user[0],
                    "username": user[1],
                    "created_at": user[3]
                }
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            return None

    def get_current_user(self, token: str) -> Optional[dict]:
        """Get current user data from JWT token."""
        payload = self.decode_token(token)
        if not payload:
            return None
            
        try:
            self.db.ensure_connection()
            with self.db.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, username, created_at
                    FROM users
                    WHERE id = %s
                    """,
                    (payload.get("user_id"),)
                )
                user = cur.fetchone()
                if not user:
                    return None
                    
                return {
                    "id": user[0],
                    "username": user[1],
                    "created_at": user[2]
                }
        except Exception:
            return None

    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Change user's password."""
        try:
            self.db.ensure_connection()
            with self.db.conn.cursor() as cur:
                # Verify current password
                cur.execute(
                    """
                    SELECT password_hash
                    FROM users
                    WHERE id = %s
                    """,
                    (user_id,)
                )
                result = cur.fetchone()
                if not result or not self.verify_password(current_password, result[0]):
                    return False

                # Update to new password
                cur.execute(
                    """
                    UPDATE users
                    SET password_hash = %s
                    WHERE id = %s
                    """,
                    (self.get_password_hash(new_password), user_id)
                )
                self.db.conn.commit()
                return True
        except Exception as e:
            print(f"Password change error: {str(e)}")
            return False