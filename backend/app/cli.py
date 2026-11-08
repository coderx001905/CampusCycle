import getpass
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.auth import provision_platform_admin, reset_platform_admin_password


def provision_admin() -> int:
    name = input("Platform Admin name: ").strip()
    email = input("Platform Admin email: ").strip()
    password = getpass.getpass("Platform Admin password (min 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if not name or len(name) > 150:
        print("Name must contain 1 to 150 characters.", file=sys.stderr)
        return 2
    try:
        validated_email = TypeAdapter(EmailStr).validate_python(email)
    except ValidationError:
        print("Enter a valid email address.", file=sys.stderr)
        return 2
    if len(password) < 12 or len(password) > 128:
        print("Password must contain 12 to 128 characters.", file=sys.stderr)
        return 2
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 2
    # Clear references to the unencoded password before performing persistence.
    password_to_hash = password
    del password, confirmation
    db: Session = SessionLocal()
    try:
        provision_platform_admin(db, name=name, email=str(validated_email), password=password_to_hash)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print("Platform Admin provisioning failed.", file=sys.stderr)
        return 1
    finally:
        db.close()
        del password_to_hash
    print("Platform Admin created successfully.")
    return 0


def reset_admin_password() -> int:
    password = getpass.getpass("New Platform Admin password (min 12 characters): ")
    confirmation = getpass.getpass("Confirm new password: ")
    if len(password) < 12 or len(password) > 128:
        print("Password must contain 12 to 128 characters.", file=sys.stderr)
        return 2
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 2
    password_to_hash = password
    del password, confirmation
    db: Session = SessionLocal()
    try:
        reset_platform_admin_password(db, new_password=password_to_hash)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print("Platform Admin password reset failed.", file=sys.stderr)
        return 1
    finally:
        db.close()
        del password_to_hash
    print("Platform Admin password reset successfully; all active sessions revoked.")
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m app.cli [provision-admin | reset-admin-password]", file=sys.stderr)
        raise SystemExit(2)
    command = sys.argv[1]
    if command == "provision-admin":
        if sys.argv[1:] != ["provision-admin"]:
            print("Usage: python -m app.cli provision-admin", file=sys.stderr)
            raise SystemExit(2)
        raise SystemExit(provision_admin())
    elif command == "reset-admin-password":
        if sys.argv[1:] != ["reset-admin-password"]:
            print("Usage: python -m app.cli reset-admin-password", file=sys.stderr)
            raise SystemExit(2)
        raise SystemExit(reset_admin_password())
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Usage: python -m app.cli [provision-admin | reset-admin-password]", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
