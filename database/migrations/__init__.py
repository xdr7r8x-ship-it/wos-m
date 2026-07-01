"""
Database Migrations for WOS-M
© MANSOUR — WOS-M. All rights reserved.
"""

MIGRATIONS = [
    {
        "version": 1,
        "name": "add_alliance_auto_gift",
        "description": "Add auto_gift_enabled and gift_channel_id to alliances",
        "sql": """
            ALTER TABLE alliances ADD COLUMN auto_gift_enabled INTEGER DEFAULT 0;
            ALTER TABLE alliances ADD COLUMN gift_channel_id TEXT;
        """
    },
    {
        "version": 2,
        "name": "add_unique_redemption",
        "description": "Add unique constraint to prevent duplicate redemptions",
        "sql": """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_redemptions_unique 
            ON gift_redemptions(code_id, player_id);
        """
    }
]


async def run_migrations(db):
    """Run all pending migrations."""
    from config.settings import settings
    
    # Create migrations tracking table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Get current version
    row = await db.fetchone("SELECT MAX(version) as version FROM migrations")
    current_version = row["version"] if row and row["version"] else 0
    
    for migration in MIGRATIONS:
        if migration["version"] > current_version:
            print(f"Running migration {migration['version']}: {migration['name']}")
            try:
                # Run the SQL
                for statement in migration["sql"].strip().split(";"):
                    if statement.strip():
                        await db.execute(statement)
                await db.connection.commit()
                
                # Record migration
                await db.execute(
                    "INSERT INTO migrations (version, name) VALUES (?, ?)",
                    (migration["version"], migration["name"])
                )
                await db.connection.commit()
                print(f"Migration {migration['version']} completed")
            except Exception as e:
                print(f"Migration {migration['version']} failed: {e}")
                # Continue with other migrations