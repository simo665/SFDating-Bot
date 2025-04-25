import sqlite3
import config

def check_table_schema():
    """Check the schema of the pending_matches table"""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get the schema
        cursor.execute("PRAGMA table_info(pending_matches)")
        columns = cursor.fetchall()
        
        print("Columns in pending_matches table:")
        for col in columns:
            print(col)
        
        # Get a sample row
        cursor.execute("SELECT * FROM pending_matches LIMIT 1")
        sample = cursor.fetchone()
        
        if sample:
            print("\nSample row:")
            print(sample)
            print(f"Number of columns in sample: {len(sample)}")
        else:
            print("\nNo data in pending_matches table")
            
        conn.close()
    except Exception as e:
        print(f"Error checking table schema: {e}")

if __name__ == "__main__":
    check_table_schema()