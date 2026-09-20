"""Create the first admin explicitly: python bootstrap_admin.py (local terminal only)."""
import asyncio
from getpass import getpass
from sqlalchemy import select, func
from app.db.session import init_db, async_session
from app.models.models import User, UserRole
from app.core.security import hash_password

async def main():
    await init_db()
    async with async_session() as db:
        if await db.scalar(select(func.count(User.id)).where(User.role == UserRole.ADMIN)):
            raise SystemExit("An admin already exists. Use authenticated registration.")
        username = input("Admin username: ").strip()
        email = input("Email: ").strip()
        password = getpass("Password (12+ characters): ")
        if len(username) < 3 or len(password) < 12:
            raise SystemExit("Username or password too short")
        db.add(User(username=username, email=email, hashed_password=hash_password(password), role=UserRole.ADMIN, is_active=True))
        await db.commit()
        print("Admin created")
if __name__ == "__main__":
    asyncio.run(main())
