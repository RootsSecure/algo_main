"""Add Raspberry Pi gateway columns to devices."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_device_gateway_columns"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("devices")}

    additions = {
        "gateway_enabled": sa.Column("gateway_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        "gateway_hardware_id": sa.Column("gateway_hardware_id", sa.String(length=255), nullable=True),
        "gateway_token_jti": sa.Column("gateway_token_jti", sa.String(length=255), nullable=True),
        "gateway_session_jti": sa.Column("gateway_session_jti", sa.String(length=255), nullable=True),
        "gateway_last_seen_at": sa.Column("gateway_last_seen_at", sa.DateTime(timezone=True), nullable=True),
        "gateway_last_ip": sa.Column("gateway_last_ip", sa.String(length=120), nullable=True),
    }

    for name, column in additions.items():
        if name not in columns:
            op.add_column("devices", column)


def downgrade() -> None:
    pass
