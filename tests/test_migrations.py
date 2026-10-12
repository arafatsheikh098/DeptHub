import os
import tempfile

import pytest
from alembic.config import Config

from alembic import command


def test_alembic_upgrade_and_downgrade_sqlite():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        db_path = tmp.name
        sqlite_url = f"sqlite:///{db_path}"

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", sqlite_url)

        # Upgrade to head
        command.upgrade(alembic_cfg, "head")

        # Downgrade to base
        command.downgrade(alembic_cfg, "base")

        # Upgrade again to head
        command.upgrade(alembic_cfg, "head")


@pytest.mark.skipif(
    not os.environ.get("POSTGRES_TEST_URL"),
    reason="POSTGRES_TEST_URL not set, skipping postgres migration test",
)
def test_alembic_upgrade_and_downgrade_postgres():
    postgres_url = os.environ["POSTGRES_TEST_URL"]
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", postgres_url)

    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")
