"""024 - inventory management tables."""

MIGRATION_ID = 24
DESCRIPTION = "inventory items, dynamic fields, values, category state"


def up(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_category_states (
            id TEXT PRIMARY KEY,
            category_id TEXT NOT NULL UNIQUE,
            last_author TEXT NOT NULL DEFAULT '',
            last_written_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_items (
            id TEXT PRIMARY KEY,
            category_id TEXT NOT NULL,
            name TEXT NOT NULL,
            unit TEXT NOT NULL DEFAULT '',
            active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_fields (
            id TEXT PRIMARY KEY,
            category_id TEXT NOT NULL,
            name TEXT NOT NULL,
            field_type TEXT NOT NULL DEFAULT 'text',
            sort_order INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_values (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL,
            field_id TEXT NOT NULL,
            value TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(item_id, field_id)
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_inventory_category_states_category_id "
        "ON inventory_category_states(category_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_inventory_items_category_id "
        "ON inventory_items(category_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_inventory_fields_category_id "
        "ON inventory_fields(category_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_inventory_values_item_id "
        "ON inventory_values(item_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_inventory_values_field_id "
        "ON inventory_values(field_id)"
    )
    conn.commit()
