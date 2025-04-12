import aiosqlite
import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple


class Database:
    """Central database manager for the bot using aiosqlite for async operations"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one database instance exists"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: str = "database/data2.db", **kwargs):
        """Initialize the database connection"""
        if self._initialized:
            return
            
        self.db_path = db_path
        self.timeout = kwargs.get('timeout', 30.0)
        self._pool = None
        self._connection = None
        self._lock = asyncio.Lock()
        Database._initialized = True
    
    async def init_database(self, bot = None):
        """Initialize all database tables
        
        This method should be called when the bot starts to ensure all tables exist.
        """
        # User levels system
        await self.create_table("user_levels", """
            user_id INTEGER,
            guild_id INTEGER,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0,
            last_message TIMESTAMP,
            PRIMARY KEY (user_id, guild_id)
        """)
        
        await self.create_table("level_settings", """
            guild_id INTEGER PRIMARY KEY,
            announcement_channel INTEGER,
            level_up_message TEXT,
            is_enabled BOOLEAN DEFAULT 1,
            xp_blacklist TEXT DEFAULT "[]"
        """)
        
        # Threading system
        await self.create_table("threading", """
            guild_id INTEGER PRIMARY KEY,
            thread_channel TEXT
        """)
        
        # Stick messages system
        await self.create_table("stick_messages", """
            guild_id INTEGER PRIMARY KEY,
            stick_messages TEXT
        """)
        
        # User notification settings
        await self.create_table("user_settings", """
            user_id INTEGER PRIMARY KEY,
            dm_notif TEXT
        """)

        if bot:
            from utilities import PersistentView
            from cogs.engage_chat import ButtonsUI
            bot.add_view(ButtonsUI("", bot))
            
            # Load any components from templates
            try:
                import os
                for file in os.listdir("./templates"):
                    if file.endswith(".json"):
                        with open(f"./templates/{file}", "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if "components" in data and data["components"]:
                                bot.add_view(PersistentView(data["components"]))
            except Exception as e:
                print(f"Error loading persistent views: {e}")
    
    async def _get_connection(self) -> aiosqlite.Connection:
        """Get a database connection"""
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path, timeout=self.timeout)
            self._connection.row_factory = aiosqlite.Row
        return self._connection
    
    async def close(self) -> None:
        """Close the database connection"""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
    
    async def execute(self, query: str, params: tuple = (), *, commit: bool = True) -> Optional[int]:
        """Execute a database query
        
        Args:
            query: SQL query to execute
            params: Parameters for the query
            commit: Whether to commit after execution
            
        Returns:
            The rowid of the last inserted row or None
        """
        async with self._lock:
            conn = await self._get_connection()
            cursor = await conn.execute(query, params)
            if commit:
                await conn.commit()
            return cursor.lastrowid
    
    async def executemany(self, query: str, params_list: List[tuple], *, commit: bool = True) -> None:
        """Execute a database query with multiple parameter sets
        
        Args:
            query: SQL query to execute
            params_list: List of parameter tuples for the query
            commit: Whether to commit after execution
        """
        async with self._lock:
            conn = await self._get_connection()
            await conn.executemany(query, params_list)
            if commit:
                await conn.commit()
    
    async def execute_script(self, script: str, *, commit: bool = True) -> None:
        """Execute a multi-statement SQL script
        
        Args:
            script: SQL script to execute
            commit: Whether to commit after execution
        """
        async with self._lock:
            conn = await self._get_connection()
            await conn.executescript(script)
            if commit:
                await conn.commit()
    
    async def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch a single row from the database
        
        Args:
            query: SQL query to execute
            params: Parameters for the query
            
        Returns:
            The first row as a dictionary or None if no rows were returned
        """
        async with self._lock:
            conn = await self._get_connection()
            async with conn.execute(query, params) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
    
    async def fetchall(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows from the database
        
        Args:
            query: SQL query to execute
            params: Parameters for the query
            
        Returns:
            All rows as a list of dictionaries
        """
        async with self._lock:
            conn = await self._get_connection()
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def fetchvalue(self, query: str, params: tuple = ()) -> Any:
        """Fetch a single value from the database
        
        Args:
            query: SQL query to execute
            params: Parameters for the query
            
        Returns:
            The first column of the first row or None if no rows were returned
        """
        async with self._lock:
            conn = await self._get_connection()
            async with conn.execute(query, params) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0]
                return None
    
    async def transaction(self):
        """Create a transaction context manager
        
        Returns:
            A transaction context manager
        
        Example:
            ```python
            async with db.transaction() as conn:
                await conn.execute("INSERT INTO users VALUES (?, ?)", (1, "John"))
                await conn.execute("INSERT INTO posts VALUES (?, ?, ?)", (1, 1, "Hello"))
            ```
        """
        class Transaction:
            def __init__(self, db):
                self.db = db
                self.conn = None
            
            async def __aenter__(self):
                self.conn = await self.db._get_connection()
                await self.conn.execute("BEGIN TRANSACTION")
                return self.conn
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if exc_type is None:
                    await self.conn.commit()
                else:
                    await self.conn.rollback()
        
        return Transaction(self)
    
    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if the table exists, False otherwise
        """
        query = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name=?
        """
        result = await self.fetchvalue(query, (table_name,))
        return result is not None
    
    async def create_table(self, table_name: str, schema: str) -> None:
        """Create a table if it doesn't exist
        
        Args:
            table_name: Name of the table to create
            schema: Schema for the table (column definitions)
        """
        query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {schema}
            )
        """
        await self.execute(query)
    
    async def insert(self, table: str, data: Dict[str, Any], *, replace: bool = False) -> int:
        """Insert a row into a table
        
        Args:
            table: Table to insert into
            data: Dictionary of column names and values
            replace: Whether to replace existing data (REPLACE INTO)
            
        Returns:
            The rowid of the inserted row
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        values = tuple(data.values())
        
        cmd = "REPLACE INTO" if replace else "INSERT INTO"
        query = f"{cmd} {table} ({columns}) VALUES ({placeholders})"
        
        return await self.execute(query, values)
    
    async def update(self, table: str, data: Dict[str, Any], condition: str, condition_params: tuple) -> None:
        """Update rows in a table
        
        Args:
            table: Table to update
            data: Dictionary of column names and values to update
            condition: WHERE condition
            condition_params: Parameters for the condition
        """
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        values = tuple(data.values()) + condition_params
        
        query = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        await self.execute(query, values)
    
    async def delete(self, table: str, condition: str, params: tuple) -> None:
        """Delete rows from a table
        
        Args:
            table: Table to delete from
            condition: WHERE condition
            params: Parameters for the condition
        """
        query = f"DELETE FROM {table} WHERE {condition}"
        await self.execute(query, params)
    
    async def upsert(self, table: str, data: Dict[str, Any], key_columns: List[str]) -> None:
        """Insert or update a row in a table
        
        Args:
            table: Table to insert/update
            data: Dictionary of column names and values
            key_columns: List of column names that form the primary key
        """
        key_data = {k: data[k] for k in key_columns}
        
        where_clause = ' AND '.join([f"{key} = ?" for key in key_data.keys()])
        existing = await self.fetchone(
            f"SELECT 1 FROM {table} WHERE {where_clause}",
            tuple(key_data.values())
        )
        
        if existing:
            non_key_data = {k: v for k, v in data.items() if k not in key_columns}
            if non_key_data:
                await self.update(
                    table,
                    non_key_data,
                    where_clause,
                    tuple(key_data.values())
                )
        else:
            await self.insert(table, data)
    
    async def json_get(self, table: str, key_column: str, key_value: Any, data_column: str) -> Any:
        """Get a JSON value from the database
        
        Args:
            table: Table to query
            key_column: Column to filter on
            key_value: Value to filter for
            data_column: Column containing the JSON data
            
        Returns:
            The parsed JSON data or None
        """
        query = f"SELECT {data_column} FROM {table} WHERE {key_column} = ?"
        result = await self.fetchvalue(query, (key_value,))
        
        if result:
            return json.loads(result)
        return None
    
    async def json_set(self, table: str, key_column: str, key_value: Any, data_column: str, data: Any) -> None:
        """Set a JSON value in the database
        
        Args:
            table: Table to update
            key_column: Column to filter on
            key_value: Value to filter for
            data_column: Column to store the JSON data
            data: Data to store (will be converted to JSON)
        """
        json_data = json.dumps(data)
        
        exists = await self.fetchvalue(
            f"SELECT 1 FROM {table} WHERE {key_column} = ?",
            (key_value,)
        )
        
        if exists:
            await self.update(
                table,
                {data_column: json_data},
                f"{key_column} = ?",
                (key_value,)
            )
        else:
            await self.insert(
                table,
                {key_column: key_value, data_column: json_data}
            )
    
    async def get_user_level(self, user_id: int, guild_id: int) -> Tuple[int, int, Optional[int]]:
        """Get a user's XP level information
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            
        Returns:
            Tuple of (level, xp, rank) or (0, 0, None) if no data found
        """
        user_data = await self.fetchone(
            "SELECT xp, level FROM user_levels WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        )
        
        if not user_data:
            return (0, 0, None)
        
        rank_data = await self.fetchall(
            "SELECT user_id FROM user_levels WHERE guild_id = ? ORDER BY xp DESC",
            (guild_id,)
        )
        
        rank = None
        for i, row in enumerate(rank_data):
            if row['user_id'] == user_id:
                rank = i + 1
                break
        
        return (user_data['level'], user_data['xp'], rank)
    
    async def get_auto_thread_channels(self, guild_id: int) -> Dict[str, Dict[str, Any]]:
        """Get the auto thread channels for a guild
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Dictionary of channel IDs to thread settings
        """
        result = await self.fetchvalue(
            "SELECT thread_channel FROM threading WHERE guild_id = ?",
            (guild_id,)
        )
        
        if result:
            return json.loads(result)
        return {}
    
    async def save_auto_thread_channels(self, guild_id: int, channels: Dict[str, Dict[str, Any]]) -> None:
        """Save the auto thread channels for a guild
        
        Args:
            guild_id: Discord guild ID
            channels: Dictionary of channel IDs to thread settings
        """
        await self.json_set('threading', 'guild_id', guild_id, 'thread_channel', channels) 