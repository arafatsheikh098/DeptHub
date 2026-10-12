import argparse
import getpass
import sys

from sqlmodel import Session, select

from app.auth import get_password_hash
from app.database import engine, init_db
from app.models.user import User


def create_admin(
    email: str | None = None,
    password: str | None = None,
    session: Session | None = None,
) -> None:
    """Create a new admin user."""
    if not email:
        email = input("Admin Email: ").strip()

    if not email:
        print("Error: Email cannot be empty.", file=sys.stderr)
        sys.exit(1)

    clean_email = email.lower().strip()

    def _execute(s: Session):
        existing = s.exec(select(User).where(User.email == clean_email)).first()
        if existing:
            msg = f"Error: User with email '{clean_email}' already exists."
            print(msg, file=sys.stderr)
            sys.exit(1)

        nonlocal password
        if not password:
            password = getpass.getpass("Admin Password: ").strip()

        if not password:
            print("Error: Password cannot be empty.", file=sys.stderr)
            sys.exit(1)

        user = User(
            email=clean_email,
            password_hash=get_password_hash(password),
        )
        s.add(user)
        s.commit()
        print(f"Admin user '{clean_email}' created successfully.")

    if session:
        _execute(session)
    else:
        init_db()
        with Session(engine) as s:
            _execute(s)


def main() -> None:
    parser = argparse.ArgumentParser(description="DeptHub Command Line Interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_admin_parser = subparsers.add_parser(
        "create-admin", help="Create an administrative user"
    )
    create_admin_parser.add_argument("--email", help="Admin email address")
    create_admin_parser.add_argument("--password", help="Admin password")

    args = parser.parse_args()

    if args.command == "create-admin":
        create_admin(args.email, args.password)


if __name__ == "__main__":
    main()
