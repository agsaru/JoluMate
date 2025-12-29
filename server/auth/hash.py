from passlib.context import CryptContext

context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

def hash_password(password: str) -> str:
    if not password or not password.strip():
        raise ValueError("Password cannot be empty")
    try:
        return context.hash(password)
    except Exception as e:
        raise SystemError("Failed to hash password") from e

def verify_password(password: str, hashed_password: str) -> bool:
    if not password or not hashed_password:
        return False
    try:
        return context.verify(password, hashed_password)
    except Exception:
        return False

