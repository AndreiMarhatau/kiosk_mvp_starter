from app.db import SessionLocal
from app.crud import create_user, get_user_by_username


def main(username: str, password: str, role: str = "admin"):
    db = SessionLocal()
    try:
        if get_user_by_username(db, username):
            print("EXISTS")
            return 0
        u = create_user(db, username, password, role)
        print("CREATED" if u else "EXISTS")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    username = sys.argv[1] if len(sys.argv) > 1 else "user"
    password = sys.argv[2] if len(sys.argv) > 2 else "user"
    role = sys.argv[3] if len(sys.argv) > 3 else "admin"
    raise SystemExit(main(username, password, role))

