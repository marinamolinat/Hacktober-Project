"""Usage:
  python manage.py init-db                       # create the 11 tables (snowflake/002_schema.sql)
  python manage.py ingest <username>             # scrape + extract one account now
"""
import sys

from dotenv import load_dotenv

load_dotenv()

import db  # noqa: E402
import ingest  # noqa: E402
import store  # noqa: E402

if __name__ == "__main__":
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if cmd == "init-db":
        db.init_schema()
        print("schema ready")
    elif cmd == "ingest" and len(args) == 1:
        account = store.get_or_create_account(store.normalize_handle(args[0]))
        ingest.ingest_account(account["account_id"], account["username"])
        print("done")
    else:
        print(__doc__)
