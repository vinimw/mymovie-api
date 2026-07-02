from __future__ import annotations

import argparse
from getpass import getpass

try:
    import bcrypt
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Dependency missing: install the project requirements and activate the virtualenv before "
        "running this script. Example: `source .venv/bin/activate && pip install -r requirements.txt`."
    ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a bcrypt hash for ADMIN_PASSWORD_HASH.")
    parser.add_argument(
        "password",
        nargs="?",
        help="Plain text password to hash. If omitted, interactive mode is used.",
    )
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        help="Skip password confirmation in interactive mode.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    password = args.password or getpass("Enter password to hash: ")
    if not password:
        raise SystemExit("Password cannot be empty.")

    if args.password is None and not args.no_confirm:
        password_confirmation = getpass("Confirm password: ")
        if password != password_confirmation:
            raise SystemExit("Passwords do not match.")

    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise SystemExit("Password must be at most 72 bytes long for bcrypt.")

    print(bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8"))


if __name__ == "__main__":
    main()
