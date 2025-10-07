# reset_password.py
import sys
from dotenv import load_dotenv
load_dotenv()

from app.db.session import SessionLocal
from app.db import models
from app.services.security import hash_password

def reset_password(email: str, new_password: str):
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            print("User not found:", email)
            return 1
        user.hashed_password = hash_password(new_password)
        db.add(user)
        db.commit()
        print(f"Password reset for {email}")
        return 0
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python reset_password.py <email> <new_password>")
        sys.exit(2)
    email = sys.argv[1]
    new_password = sys.argv[2]
    sys.exit(reset_password(email, new_password))
