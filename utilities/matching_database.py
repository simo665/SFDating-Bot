import sqlite3
import logging
import time
import config

logger = logging.getLogger("./errors/errors.log")


def setup_database():
    """Set up the SQLite database with required tables"""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        # Create match_history table to store match history
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS match_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            matched_user_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            status TEXT NOT NULL,
            timestamp INTEGER NOT NULL
        )
        ''')

        # Create user_preferences table to store user preferences
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id INTEGER PRIMARY KEY,
            opt_out BOOLEAN DEFAULT 0,
            blocked_users TEXT DEFAULT '',
            last_match_time INTEGER DEFAULT 0,
            preferences TEXT DEFAULT '{}'
        )
        ''')

        # Create pending_matches table to store pending match confirmations
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requester_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            message_id INTEGER,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            status TEXT DEFAULT 'pending'
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database setup completed successfully")
    except Exception as e:
        logger.error(f"Error setting up database: {e}")


def get_user_preferences(user_id):
    """Get user preferences from the database"""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM user_preferences WHERE user_id = ?',
                       (user_id, ))
        result = cursor.fetchone()

        if not result:
            # Create default preferences if not exist
            cursor.execute(
                'INSERT INTO user_preferences (user_id, opt_out, blocked_users, last_match_time) VALUES (?, 0, "", ?)',
                (user_id, int(time.time())))
            conn.commit()

            cursor.execute('SELECT * FROM user_preferences WHERE user_id = ?',
                           (user_id, ))
            result = cursor.fetchone()

        conn.close()

        if result:
            return {
                "user_id": result[0],
                "opt_out": bool(result[1]),
                "blocked_users": result[2].split(",") if result[2] else [],
                "last_match_time": result[3],
                "preferences": result[4]
            }
        return None
    except Exception as e:
        logger.error(f"Error getting user preferences: {e}")
        return None


def update_user_preferences(user_id, preferences):
    """Update user preferences in the database"""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute(
            'SELECT user_id FROM user_preferences WHERE user_id = ?',
            (user_id, ))
        result = cursor.fetchone()

        if result:
            # Update existing preferences
            set_clauses = []
            values = []

            for key, value in preferences.items():
                if key == "blocked_users" and isinstance(value, list):
                    value = ",".join(map(str, value))

                set_clauses.append(f"{key} = ?")
                values.append(value)

            query = f"UPDATE user_preferences SET {', '.join(set_clauses)} WHERE user_id = ?"
            values.append(user_id)

            cursor.execute(query, values)
        else:
            # Create new preferences
            blocked_users = ""
            if "blocked_users" in preferences and isinstance(
                    preferences["blocked_users"], list):
                blocked_users = ",".join(map(str,
                                             preferences["blocked_users"]))

            opt_out = preferences.get("opt_out", 0)
            last_match_time = preferences.get("last_match_time",
                                              int(time.time()))
            prefs_json = preferences.get("preferences", "{}")

            cursor.execute(
                'INSERT INTO user_preferences (user_id, opt_out, blocked_users, last_match_time, preferences) VALUES (?, ?, ?, ?, ?)',
                (user_id, opt_out, blocked_users, last_match_time, prefs_json))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        return False


def add_match_history(user_id, matched_user_id, score, status="pending"):
    """Add a match to the history"""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        timestamp = int(time.time())

        cursor.execute(
            'INSERT INTO match_history (user_id, matched_user_id, score, status, timestamp) VALUES (?, ?, ?, ?, ?)',
            (user_id, matched_user_id, score, status, timestamp))

        match_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return match_id
    except Exception as e:
        logger.error(f"Error adding match history: {e}")
        return None


def update_match_status(match_id, status):
    """Update the status of a match"""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('UPDATE match_history SET status = ? WHERE id = ?',
                       (status, match_id))

        conn.commit()
        conn.close()

        return True
    except Exception as e:
        logger.error(f"Error updating match status: {e}")
        return False


def get_recent_matches(user_id, limit=5):
    """Get recent matches for a user"""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute(
            'SELECT matched_user_id FROM match_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?',
            (user_id, limit))

        results = cursor.fetchall()
        conn.close()

        return [result[0] for result in results]
    except Exception as e:
        logger.error(f"Error getting recent matches: {e}")
        return []


def add_pending_match(requester_id, target_id, score, message_id=None):
    """Add a pending match"""
    try:
        # Ensure the table exists
        check_pending_matches_table()
        
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        now = int(time.time())
        expires_at = now + config.MATCH_ACCEPTANCE_TIMEOUT

        cursor.execute(
            'INSERT INTO pending_matches (requester_id, target_id, score, message_id, created_at, expires_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (requester_id, target_id, score, message_id, now, expires_at,
             'pending'))

        match_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return match_id
    except Exception as e:
        logger.error(f"Error adding pending match: {e}")
        return None


def update_pending_match(match_id, status, message_id=None):
    """Update a pending match status"""
    try:
        # Ensure the table exists
        check_pending_matches_table()
        
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        if message_id is not None:
            cursor.execute(
                'UPDATE pending_matches SET status = ?, message_id = ? WHERE id = ?',
                (status, message_id, match_id))
        else:
            cursor.execute(
                'UPDATE pending_matches SET status = ? WHERE id = ?',
                (status, match_id))

        conn.commit()
        conn.close()

        return True
    except Exception as e:
        logger.error(f"Error updating pending match: {e}")
        return False


def get_pending_match(match_id):
    """Get a pending match by ID"""
    try:
        # Ensure the table exists
        check_pending_matches_table()
        
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM pending_matches WHERE id = ?',
                       (match_id, ))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "id": result[0],
                "requester_id": result[1],
                "target_id": result[2],
                "score": result[3],
                "message_id": result[4],
                "created_at": result[5],
                "expires_at": result[6],
                "status": result[7]
            }
        return None
    except Exception as e:
        logger.error(f"Error getting pending match: {e}")
        return None


def get_pending_match_by_message_id(message_id):
    """Get a pending match by message ID"""
    try:
        # Ensure the table exists
        check_pending_matches_table()
        
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM pending_matches WHERE message_id = ?',
                       (message_id, ))

        result = cursor.fetchone()
        conn.close()

        return result  # Return raw tuple for direct unpacking
    except Exception as e:
        logger.error(f"Error getting pending match by message ID: {e}")
        return None


def get_active_pending_matches(user_id):
    """Get active pending matches for a user"""
    try:
        # Ensure the table exists
        check_pending_matches_table()
        
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        now = int(time.time())

        cursor.execute(
            'SELECT * FROM pending_matches WHERE (requester_id = ? OR target_id = ?) AND status = "pending" AND expires_at > ?',
            (user_id, user_id, now))

        results = cursor.fetchall()
        conn.close()

        pending_matches = []
        for result in results:
            pending_matches.append({
                "id": result[0],
                "requester_id": result[1],
                "target_id": result[2],
                "score": result[3],
                "message_id": result[4],
                "created_at": result[5],
                "expires_at": result[6],
                "status": result[7]
            })

        return pending_matches
    except Exception as e:
        logger.error(f"Error getting active pending matches: {e}")
        return []


def check_pending_matches_table():
    """Check if pending_matches table exists and create it if not"""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pending_matches'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            logger.warning("pending_matches table does not exist, creating it now")
            # Create pending_matches table to store pending match confirmations
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requester_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                message_id INTEGER,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                status TEXT DEFAULT 'pending'
            )
            ''')
            conn.commit()
            logger.info("Created pending_matches table")
        
        conn.close()
        return table_exists
    except Exception as e:
        logger.error(f"Error checking pending_matches table: {e}")
        return False

def cleanup_expired_matches():
    """Clean up expired pending matches"""
    try:
        # First ensure the table exists
        check_pending_matches_table()
        
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        now = int(time.time())

        cursor.execute(
            'UPDATE pending_matches SET status = "expired" WHERE status = "pending" AND expires_at < ?',
            (now, ))

        updated = cursor.rowcount

        conn.commit()
        conn.close()

        if updated > 0:
            logger.info(f"Cleaned up {updated} expired pending matches")

        return updated
    except Exception as e:
        logger.error(f"Error cleaning up expired matches: {e}")
        return 0


def update_last_match_time(user_id):
    """Update the last match time for a user"""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        now = int(time.time())

        cursor.execute(
            'UPDATE user_preferences SET last_match_time = ? WHERE user_id = ?',
            (now, user_id))

        if cursor.rowcount == 0:
            cursor.execute(
                'INSERT INTO user_preferences (user_id, last_match_time) VALUES (?, ?)',
                (user_id, now))

        conn.commit()
        conn.close()

        return True
    except Exception as e:
        logger.error(f"Error updating last match time: {e}")
        return False


def block_user(user_id, blocked_user_id):
    """Add a user to the blocked list"""
    try:
        preferences = get_user_preferences(user_id)

        if not preferences:
            preferences = {
                "user_id": user_id,
                "opt_out": False,
                "blocked_users": [str(blocked_user_id)],
                "last_match_time": int(time.time())
            }
        else:
            blocked_users = preferences["blocked_users"]
            if str(blocked_user_id) not in blocked_users:
                blocked_users.append(str(blocked_user_id))

            preferences["blocked_users"] = blocked_users

        update_user_preferences(user_id, preferences)
        return True
    except Exception as e:
        logger.error(f"Error blocking user: {e}")
        return False


def opt_out_user(user_id, opt_out=True):
    """Opt a user out of matching"""
    try:
        preferences = get_user_preferences(user_id)

        if not preferences:
            preferences = {
                "user_id": user_id,
                "opt_out": opt_out,
                "blocked_users": [],
                "last_match_time": int(time.time())
            }
        else:
            preferences["opt_out"] = opt_out

        update_user_preferences(user_id, preferences)
        return True
    except Exception as e:
        logger.error(f"Error updating opt out status: {e}")
        return False


def has_active_match(user_id):
    """Check if the user has an active match"""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        # Check if user has an active match as either the requester or the target
        cursor.execute(
            """
            SELECT m.id, m.user_id, m.matched_user_id
            FROM match_history m
            WHERE (m.user_id = ? OR m.matched_user_id = ?)
            AND m.status = 'accepted'
            ORDER BY m.timestamp DESC
            LIMIT 1
            """, (user_id, user_id))

        result = cursor.fetchone()
        
        # If there's a result, we need to also check if there's been any unmatch events AFTER this match
        if result:
            match_id, first_user_id, second_user_id = result
            match_timestamp = cursor.execute(
                "SELECT timestamp FROM match_history WHERE id = ?", 
                (match_id,)
            ).fetchone()[0]
            
            # Check for any unmatch events between these users after the match was made
            other_user_id = second_user_id if user_id == first_user_id else first_user_id
            
            # Look for any 'unmatched', 'unmatched_by_user', or 'unmatched_by_other' records after the match
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM match_history 
                WHERE ((user_id = ? AND matched_user_id = ?) OR (user_id = ? AND matched_user_id = ?))
                AND status IN ('unmatched', 'unmatched_by_user', 'unmatched_by_other')
                AND timestamp > ?
                """, (user_id, other_user_id, other_user_id, user_id, match_timestamp))
            
            unmatch_count = cursor.fetchone()[0]
            conn.close()
            
            # If there are no unmatch events after the match, the match is still active
            if unmatch_count == 0:
                return True, match_id, other_user_id
            else:
                # There are unmatch events, so the match is no longer active
                return False, None, None
        else:
            conn.close()
            return False, None, None
    except Exception as e:
        logger.error(f"Error checking active match: {e}")
        return False, None, None


def get_excluded_matches(user_id, days=7):
    """
    Get a list of users that should be excluded from new match suggestions:
    1. Users who recently declined this user's match requests
    2. Users who this user recently declined
    3. Users who recently unmatched from this user
    4. Users who this user recently unmatched from

    Parameters:
    - user_id: The ID of the user requesting a match
    - days: Number of days to consider recent (default is 7 days)

    Returns:
    - List of user IDs that should be excluded from match suggestions
    """
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        # Calculate the cutoff time (default: 7 days ago)
        cutoff_time = int(time.time()) - (days * 86400)

        # Get all statuses that should be excluded (declined, unmatched by user, unmatched by other)
        excluded_statuses = ('declined', 'unmatched', 'unmatched_by_user', 'unmatched_by_other')
        
        excluded_users = []
        
        # Find all users who match exclusion criteria for this user
        for status in excluded_statuses:
            # Find users who have this status with the user (user was requester)
            cursor.execute(
                """
                SELECT matched_user_id 
                FROM match_history 
                WHERE user_id = ? 
                AND status = ? 
                AND timestamp > ?
                """, (user_id, status, cutoff_time))
            results1 = cursor.fetchall()
            
            # Find users who have this status with the user (user was target)
            cursor.execute(
                """
                SELECT user_id 
                FROM match_history 
                WHERE matched_user_id = ? 
                AND status = ? 
                AND timestamp > ?
                """, (user_id, status, cutoff_time))
            results2 = cursor.fetchall()
            
            # Add these users to the exclusion list
            excluded_users.extend([row[0] for row in results1])
            excluded_users.extend([row[0] for row in results2])

        conn.close()

        # Remove duplicates and return
        return list(set(excluded_users))
    except Exception as e:
        logger.error(f"Error getting excluded matches: {e}")
        return []
        
        
def get_recently_declined_matches(user_id, days=7):
    """
    Get a list of users that have recently declined the user's match request.
    These users will be excluded from new match suggestions for a specified period.
    
    Note: This function is maintained for backwards compatibility.
    Use get_excluded_matches() for complete exclusion list.

    Parameters:
    - user_id: The ID of the user requesting a match
    - days: Number of days to consider recent (default is 7 days)

    Returns:
    - List of user IDs that have recently declined a match with this user
    """
    # Call the more comprehensive function that includes all excluded matches
    return get_excluded_matches(user_id, days)


def unmatch_users(match_id):
    """Break a match between two users"""
    try:
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()

        # First, get the two users involved in the match
        cursor.execute(
            "SELECT user_id, matched_user_id FROM match_history WHERE id = ?",
            (match_id, ))

        result = cursor.fetchone()

        if not result:
            conn.close()
            return False, None, None

        user_id, matched_user_id = result

        # Update match status to 'unmatched'
        cursor.execute(
            "UPDATE match_history SET status = 'unmatched' WHERE id = ?",
            (match_id, ))
        
        # Record unmatch timestamp
        current_time = int(time.time())
        
        # Add a new entry to match history with 'unmatched' status
        # This ensures both users are properly tracked as having unmatched each other
        cursor.execute(
            "INSERT INTO match_history (user_id, matched_user_id, score, status, timestamp) VALUES (?, ?, 0, ?, ?)",
            (user_id, matched_user_id, 'unmatched_by_user', current_time))
            
        # Also record the reverse direction to ensure both users are properly tracked
        cursor.execute(
            "INSERT INTO match_history (user_id, matched_user_id, score, status, timestamp) VALUES (?, ?, 0, ?, ?)",
            (matched_user_id, user_id, 'unmatched_by_other', current_time))

        conn.commit()
        conn.close()

        return True, user_id, matched_user_id
    except Exception as e:
        logger.error(f"Error unmatching users: {e}")
        return False, None, None