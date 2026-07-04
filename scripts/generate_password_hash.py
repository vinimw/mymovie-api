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
    parser = argparse.ArgumentParser(description="Generate bcrypt hashes for one or more admin passwords.")
    parser.add_argument(
        "passwords",
        nargs="*",
        help="Plain text password(s) to hash. Use commas to generate hashes for multiple users at once.",
    )
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        help="Skip password confirmation in interactive mode.",
    )
    parser.add_argument(
        "--csv-output",
        action="store_true",
        help="Print hashes as a single comma-separated line, ready for ADMIN_PASSWORD_HASHES.",
    )
    return parser.parse_args()


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise SystemExit("Password must be at most 72 bytes long for bcrypt.")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def main() -> None:
    args = parse_args()

    normalized_passwords = [item.strip() for value in args.passwords for item in value.split(",") if item.strip()]

    if not normalized_passwords:
        password = getpass("Enter password to hash: ")
        if not password:
            raise SystemExit("Password cannot be empty.")

        if not args.no_confirm:
            password_confirmation = getpass("Confirm password: ")
            if password != password_confirmation:
                raise SystemExit("Passwords do not match.")

        normalized_passwords = [password]

    hashes = [hash_password(password) for password in normalized_passwords]
    if args.csv_output or len(hashes) > 1:
        print(",".join(hashes))
        return

    print(hashes[0])


if __name__ == "__main__":
    main()
