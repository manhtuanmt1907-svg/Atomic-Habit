import sqlite3
import os
from datetime import datetime, timedelta
from contextlib import closing

safe_dir = os.environ.get("HOME") or os.environ.get("USERPROFILE") or os.getcwd()
DB_NAME = os.path.join(safe_dir, "app_data.db")


def init_db():
    conn = sqlite3.connect(DB_NAME, timeout=10.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Habits table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            incentive_amount REAL DEFAULT 0,
            frequency_type TEXT DEFAULT 'daily',
            current_streak INTEGER DEFAULT 0,
            weight INTEGER DEFAULT 1,
            frequency TEXT DEFAULT '0,1,2,3,4,5,6'
        )
    """)

    # Column check and update
    cursor.execute("PRAGMA table_info(habits)")
    columns = [row["name"] for row in cursor.fetchall()]
    if "weight" not in columns:
        cursor.execute("ALTER TABLE habits ADD COLUMN weight INTEGER DEFAULT 1")
    if "streak" not in columns:
        cursor.execute("ALTER TABLE habits ADD COLUMN streak INTEGER DEFAULT 0")
    if "frequency" not in columns:
        try:
            cursor.execute(
                "ALTER TABLE habits ADD COLUMN frequency TEXT DEFAULT '0,1,2,3,4,5,6'"
            )
        except sqlite3.OperationalError:
            pass
    if "description" not in columns:
        try:
            cursor.execute("ALTER TABLE habits ADD COLUMN description TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

    # Habit logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER,
            log_date TEXT,
            status TEXT,
            FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE
        )
    """)

    # Accounts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            balance REAL DEFAULT 0
        )
    """)

    # Transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            amount REAL,
            transaction_type TEXT,
            category TEXT,
            description TEXT,
            created_at TEXT,
            FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE
        )
    """)

    # Quotes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            author TEXT
        )
    """)

    # User settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monthly_budget REAL DEFAULT 3000000,
            theme TEXT DEFAULT 'dark',
            currency TEXT DEFAULT 'VNĐ'
        )
    """)

    cursor.execute("PRAGMA table_info(user_settings)")
    cols = [row["name"] for row in cursor.fetchall()]
    if "theme" not in cols:
        cursor.execute("ALTER TABLE user_settings ADD COLUMN theme TEXT DEFAULT 'dark'")
    if "currency" not in cols:
        cursor.execute(
            "ALTER TABLE user_settings ADD COLUMN currency TEXT DEFAULT 'VNĐ'"
        )
    if "pomodoro_show_time" not in cols:
        cursor.execute(
            "ALTER TABLE user_settings ADD COLUMN pomodoro_show_time INTEGER DEFAULT 1"
        )
    if "current_xp" not in cols:
        cursor.execute(
            "ALTER TABLE user_settings ADD COLUMN current_xp INTEGER DEFAULT 0"
        )
    if "current_level" not in cols:
        cursor.execute(
            "ALTER TABLE user_settings ADD COLUMN current_level INTEGER DEFAULT 1"
        )

    cursor.execute("SELECT COUNT(*) FROM user_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO user_settings (monthly_budget, theme, currency, pomodoro_show_time) VALUES (3000000, 'dark', 'VNĐ', 1)"
        )

    cursor.execute("PRAGMA table_info(transactions)")
    cols = [row["name"] for row in cursor.fetchall()]
    if "category" not in cols:
        cursor.execute(
            "ALTER TABLE transactions ADD COLUMN category TEXT DEFAULT 'Khác'"
        )

    # App Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM app_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO app_settings (key, value) VALUES ('pomodoro_mode', 'timer')"
        )
        cursor.execute(
            "INSERT INTO app_settings (key, value) VALUES ('pomodoro_duration', '30')"
        )

    # Focus logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS focus_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT,
            focus_seconds INTEGER
        )
    """)

    # Sound settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sound_settings (
            id INTEGER PRIMARY KEY,
            is_muted INTEGER DEFAULT 0,
            focus_start_path TEXT DEFAULT 'assets/sounds/focus_start.mp3',
            break_start_path TEXT DEFAULT 'assets/sounds/break_start.mp3'
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM sound_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO sound_settings (id, is_muted, focus_start_path, break_start_path) VALUES (1, 0, 'sounds/focus_start.mp3', 'sounds/break_start.mp3')"
        )

    # Skill Trees table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skill_trees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT ''
        )
    """)

    # Skill Nodes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skill_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tree_id INTEGER,
            parent_id INTEGER,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            sp_cost INTEGER DEFAULT 10,
            is_repeatable INTEGER DEFAULT 0,
            exclusive_group_id TEXT,
            FOREIGN KEY (tree_id) REFERENCES skill_trees (id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES skill_nodes (id)
        )
    """)

    # User Skills table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id INTEGER UNIQUE,
            status TEXT DEFAULT 'locked',
            current_sp_invested INTEGER DEFAULT 0,
            FOREIGN KEY (node_id) REFERENCES skill_nodes (id) ON DELETE CASCADE
        )
    """)

    # Node Tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS node_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id INTEGER,
            task_type TEXT DEFAULT 'checklist',
            content TEXT DEFAULT '',
            is_completed INTEGER DEFAULT 0,
            FOREIGN KEY (node_id) REFERENCES skill_nodes (id) ON DELETE CASCADE
        )
    """)

    # global_sp column in user_settings
    cursor.execute("PRAGMA table_info(user_settings)")
    cols = [row["name"] for row in cursor.fetchall()]
    if "global_sp" not in cols:
        cursor.execute(
            "ALTER TABLE user_settings ADD COLUMN global_sp INTEGER DEFAULT 0"
        )

    conn.commit()
    conn.close()


def get_db_connection():
    # Thêm timeout và check_same_thread
    conn = sqlite3.connect(DB_NAME, timeout=10.0, check_same_thread=False)
    # Bật chế độ WAL giúp ghi dữ liệu song song không bị kẹt
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


# --- Habits ---
def get_all_habits():
    with closing(get_db_connection()) as conn:
        habits = conn.execute("SELECT * FROM habits").fetchall()
    return habits


def add_habit(name, description="", incentive=0, weight=1, frequency="0,1,2,3,4,5,6"):
    with closing(get_db_connection()) as conn:
        conn.execute(
            "INSERT INTO habits (name, description, incentive_amount, weight, frequency) VALUES (?, ?, ?, ?, ?)",
            (name, description, incentive, weight, frequency),
        )
        conn.commit()


def delete_habit(habit_id):
    with closing(get_db_connection()) as conn:
        conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
        conn.commit()


def get_habit_logs_for_date(date_str):
    with closing(get_db_connection()) as conn:
        logs = conn.execute(
            "SELECT habit_id FROM habit_logs WHERE log_date = ? AND status = 'done'",
            (date_str,),
        ).fetchall()
    return [log["habit_id"] for log in logs]


def get_habit_logs_last_30_days(habit_id):
    with closing(get_db_connection()) as conn:
        thirty_days_ago = (datetime.now().date() - timedelta(days=29)).strftime(
            "%Y-%m-%d"
        )
        logs = conn.execute(
            """
            SELECT log_date FROM habit_logs 
            WHERE habit_id = ? AND status = 'done' AND log_date >= ?
        """,
            (habit_id, thirty_days_ago),
        ).fetchall()
    return [log["log_date"] for log in logs]


def get_habit_streak(habit_id, frequency_str):
    with closing(get_db_connection()) as conn:
        logs = conn.execute(
            'SELECT log_date FROM habit_logs WHERE habit_id = ? AND status = "done" ORDER BY log_date DESC',
            (habit_id,),
        ).fetchall()
        log_dates = [row["log_date"] for row in logs]

    streak = 0
    current_date = datetime.now().date()

    for i in range(100):  # Backward Check
        check_date = current_date - timedelta(days=i)
        check_weekday = str(check_date.weekday())
        check_date_str = check_date.strftime("%Y-%m-%d")

        if check_weekday in frequency_str:
            if check_date_str in log_dates:
                streak += 1
            elif i == 0:
                # If today is scheduled but not yet checked, streak is NOT broken
                continue
            else:
                # If a scheduled day in private past was missed -> Streak broken
                break
    return streak


def get_daily_habit_progress_last_7_days():
    with closing(get_db_connection()) as conn:
        seven_days_ago = (datetime.now().date() - timedelta(days=6)).strftime(
            "%Y-%m-%d"
        )
        logs = conn.execute(
            """
            SELECT l.log_date, SUM(h.weight) as total_weight
            FROM habit_logs l
            JOIN habits h ON l.habit_id = h.id
            WHERE l.status = 'done' AND l.log_date >= ?
            GROUP BY l.log_date
        """,
            (seven_days_ago,),
        ).fetchall()
    return {log["log_date"]: log["total_weight"] for log in logs}


def get_total_active_habit_weight():
    with closing(get_db_connection()) as conn:
        row = conn.execute("SELECT SUM(weight) as total FROM habits").fetchone()
    return row["total"] if row["total"] else 0


def toggle_habit_log(habit_id, date_str, is_done):
    with closing(get_db_connection()) as conn:
        if is_done:
            conn.execute(
                "INSERT OR IGNORE INTO habit_logs (habit_id, log_date, status) VALUES (?, ?, 'done')",
                (habit_id, date_str),
            )
        else:
            conn.execute(
                "DELETE FROM habit_logs WHERE habit_id = ? AND log_date = ?",
                (habit_id, date_str),
            )

        # Simple streak logic (will be overruled by get_habit_streak in display)
        update_streak_legacy(conn, habit_id)

        conn.commit()


def update_streak_legacy(conn, habit_id):
    # This legacy streak is just for db column maintenance
    logs = conn.execute(
        "SELECT log_date FROM habit_logs WHERE habit_id = ? AND status = 'done' ORDER BY log_date DESC",
        (habit_id,),
    ).fetchall()
    dates = [datetime.strptime(l["log_date"], "%Y-%m-%d").date() for l in logs]
    streak = 0
    if dates:
        today = datetime.now().date()
        if dates[0] == today or dates[0] == today - timedelta(days=1):
            streak = 1
            for i in range(len(dates) - 1):
                if (dates[i] - dates[i + 1]).days == 1:
                    streak += 1
                else:
                    break
    conn.execute(
        "UPDATE habits SET current_streak = ? WHERE id = ?", (streak, habit_id)
    )


def get_habit_stats():
    with closing(get_db_connection()) as conn:
        freq = conn.execute("""
            SELECT h.name, COUNT(l.id) as count FROM habits h LEFT JOIN habit_logs l ON h.id = l.habit_id GROUP BY h.id
        """).fetchall()
        trend = conn.execute("""
            SELECT log_date, COUNT(id) as count FROM habit_logs GROUP BY log_date ORDER BY log_date ASC
        """).fetchall()
    return freq, trend


# --- Quotes ---
def get_all_quotes():
    with closing(get_db_connection()) as conn:
        quotes = conn.execute("SELECT * FROM quotes").fetchall()
    return quotes


def add_quote(text, author):
    with closing(get_db_connection()) as conn:
        conn.execute("INSERT INTO quotes (text, author) VALUES (?, ?)", (text, author))
        conn.commit()


def delete_quote(quote_id):
    with closing(get_db_connection()) as conn:
        conn.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
        conn.commit()


# --- Finance ---
def get_all_accounts():
    with closing(get_db_connection()) as conn:
        accounts = conn.execute("SELECT * FROM accounts").fetchall()
    return accounts


def add_account(name, balance=0):
    with closing(get_db_connection()) as conn:
        existing = conn.execute(
            "SELECT id FROM accounts WHERE name = ?", (name,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE accounts SET balance = ? WHERE id = ?",
                (balance, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO accounts (name, balance) VALUES (?, ?)", (name, balance)
            )
        conn.commit()


def delete_account(account_id):
    with closing(get_db_connection()) as conn:
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        conn.commit()


def get_budget():
    with closing(get_db_connection()) as conn:
        budget = conn.execute(
            "SELECT monthly_budget FROM user_settings LIMIT 1"
        ).fetchone()
    return budget["monthly_budget"] if budget else 3000000


def get_settings():
    with closing(get_db_connection()) as conn:
        settings = conn.execute("SELECT * FROM user_settings LIMIT 1").fetchone()
    return (
        dict(settings)
        if settings
        else {
            "id": 1,
            "monthly_budget": 3000000,
            "theme": "dark",
            "currency": "VNĐ",
            "pomodoro_show_time": 1,
        }
    )


def update_settings(budget, theme, currency, pomodoro_show_time=1):
    with closing(get_db_connection()) as conn:
        conn.execute(
            "UPDATE user_settings SET monthly_budget = ?, theme = ?, currency = ?, pomodoro_show_time = ?",
            (budget, theme, currency, pomodoro_show_time),
        )
        conn.commit()


def get_monthly_expenses(month_start):
    with closing(get_db_connection()) as conn:
        expenses = conn.execute(
            """
            SELECT SUM(amount) as total FROM transactions WHERE transaction_type = 'expense' AND category != 'Chuyển đi' AND created_at >= ?
        """,
            (month_start,),
        ).fetchone()
    return expenses["total"] if expenses["total"] else 0


def get_expenses_by_category(month_start):
    with closing(get_db_connection()) as conn:
        rows = conn.execute(
            """
            SELECT category, SUM(amount) as total FROM transactions WHERE transaction_type = 'expense' AND category != 'Chuyển đi' AND created_at >= ? GROUP BY category
        """,
            (month_start,),
        ).fetchall()
    return {row["category"]: row["total"] for row in rows}


def get_daily_spending_last_7_days():
    with closing(get_db_connection()) as conn:
        seven_days_ago = (datetime.now().date() - timedelta(days=6)).strftime(
            "%Y-%m-%d"
        )
        logs = conn.execute(
            """
            SELECT substr(created_at, 1, 10) as day, SUM(amount) as total FROM transactions WHERE transaction_type = 'expense' AND category != 'Chuyển đi' AND created_at >= ? GROUP BY day
        """,
            (seven_days_ago,),
        ).fetchall()
    return {log["day"]: log["total"] for log in logs}


def add_transaction(account_id, amount, t_type, category, description):
    with closing(get_db_connection()) as conn:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        acc = conn.execute(
            "SELECT balance FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if acc:
            new_balance = acc["balance"] + (-amount if t_type == "expense" else amount)
            conn.execute(
                "UPDATE accounts SET balance = ? WHERE id = ?",
                (new_balance, account_id),
            )
            conn.execute(
                """
                INSERT INTO transactions (account_id, amount, transaction_type, category, description, created_at) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (account_id, amount, t_type, category, description, now),
            )
        conn.commit()


def transfer_funds(from_id, to_id, amount, from_name, to_name):
    with closing(get_db_connection()) as conn:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        acc_from = conn.execute(
            "SELECT balance FROM accounts WHERE id = ?", (from_id,)
        ).fetchone()
        acc_to = conn.execute(
            "SELECT balance FROM accounts WHERE id = ?", (to_id,)
        ).fetchone()
        if acc_from and acc_to:
            conn.execute(
                "UPDATE accounts SET balance = ? WHERE id = ?",
                (acc_from["balance"] - amount, from_id),
            )
            conn.execute(
                "UPDATE accounts SET balance = ? WHERE id = ?",
                (acc_to["balance"] + amount, to_id),
            )
            conn.execute(
                """
                INSERT INTO transactions (account_id, amount, transaction_type, category, description, created_at) VALUES (?, ?, 'expense', 'Chuyển đi', ?, ?)
            """,
                (from_id, amount, f"Chuyển sang {to_name}", now),
            )
            conn.execute(
                """
                INSERT INTO transactions (account_id, amount, transaction_type, category, description, created_at) VALUES (?, ?, 'income', 'Nhận tiền', ?, ?)
            """,
                (to_id, amount, f"Nhận từ {from_name}", now),
            )
        conn.commit()


def get_recent_transactions(limit=15, t_type="All"):
    with closing(get_db_connection()) as conn:
        c = conn.cursor()
        query = "SELECT amount, transaction_type, category, description, created_at FROM transactions"
        params = []
        if t_type == "Expense":
            query = "SELECT amount, transaction_type, category, description, created_at FROM transactions WHERE transaction_type = 'expense'"
        elif t_type == "Income":
            query = "SELECT amount, transaction_type, category, description, created_at FROM transactions WHERE transaction_type = 'income'"
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        c.execute(query, params)
        rows = c.fetchall()
    return [dict(row) for row in rows]


# --- App Settings ---
def get_setting(key, default_value=None):
    with closing(get_db_connection()) as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row is not None else default_value


def update_setting(key, value):
    with closing(get_db_connection()) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        conn.commit()


def hard_reset():
    with closing(get_db_connection()) as conn:
        conn.execute("DELETE FROM transactions")
        conn.execute("DELETE FROM habit_logs")
        conn.execute("DELETE FROM habits")
        conn.execute("DELETE FROM app_settings")
        conn.execute("DELETE FROM accounts")
        conn.execute("DELETE FROM quotes")
        conn.execute("DELETE FROM user_settings")
        conn.execute("DELETE FROM sound_settings")
        conn.commit()

    # Reload default settings safely by re-running init logic
    init_db()


# --- Phase 3.5 Heatmap Helpers ---
def get_daily_habit_completion_ratio(date_str):
    with closing(get_db_connection()) as conn:
        from datetime import datetime

        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        weekday_str = str(dt.weekday())

        habits = conn.execute("SELECT id, frequency FROM habits").fetchall()
        scheduled_count = 0
        for h in habits:
            freq = dict(h).get("frequency") or "0,1,2,3,4,5,6"
            if weekday_str in freq:
                scheduled_count += 1

        if scheduled_count == 0:
            return 0.0

        completed_count = conn.execute(
            "SELECT COUNT(DISTINCT habit_id) FROM habit_logs WHERE log_date = ? AND status = 'done'",
            (date_str,),
        ).fetchone()[0]
    return min(1.0, completed_count / scheduled_count)


def get_daily_finance_activity(date_str):
    with closing(get_db_connection()) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE created_at LIKE ?",
            (date_str + "%",),
        ).fetchone()[0]
    return count


def log_focus_time(date_str, seconds):
    with closing(get_db_connection()) as conn:
        conn.execute(
            "INSERT INTO focus_logs (log_date, focus_seconds) VALUES (?, ?)",
            (date_str, seconds),
        )
        conn.commit()


def get_daily_focus_seconds(date_str):
    with closing(get_db_connection()) as conn:
        total = conn.execute(
            "SELECT SUM(focus_seconds) FROM focus_logs WHERE log_date = ?", (date_str,)
        ).fetchone()[0]
    return total if total else 0


# --- Phase 5.1 XP/Level Helpers ---
XP_PER_LEVEL = 500

SPECIES_UNLOCK = {
    1: "\U0001f331",  # 🌱
    2: "\U0001f33f",  # 🌿
    3: "\U0001f332",  # 🌲
    4: "\U0001f333",  # 🌳
    5: "\U0001f338",  # 🌸
    6: "\U0001f98a",  # 🦊
    7: "\U0001f333\U0001f98a",  # 🌳🦊
    8: "\U0001f98c",  # 🦌
    9: "\U0001f333\U0001f98c",  # 🌳🦌
    10: "\U0001f34e",  # 🍎
}


def get_xp_level():
    with closing(get_db_connection()) as conn:
        row = conn.execute(
            "SELECT current_xp, current_level FROM user_settings LIMIT 1"
        ).fetchone()
    if row:
        return dict(row).get("current_xp", 0) or 0, dict(row).get(
            "current_level", 1
        ) or 1
    return 0, 1


def add_xp(amount):
    xp, level = get_xp_level()
    xp += amount
    while xp >= XP_PER_LEVEL:
        xp -= XP_PER_LEVEL
        level += 1
    with closing(get_db_connection()) as conn:
        conn.execute(
            "UPDATE user_settings SET current_xp = ?, current_level = ?", (xp, level)
        )
        conn.commit()
    return xp, level


def deduct_xp(amount):
    """Deduct XP (min 0), persist to DB, return (new_xp, level)."""
    xp, level = get_xp_level()
    xp = max(0, xp - amount)
    with closing(get_db_connection()) as conn:
        conn.execute(
            "UPDATE user_settings SET current_xp = ?, current_level = ?", (xp, level)
        )
        conn.commit()
    return xp, level


def get_species_emoji(level):
    if level >= 10:
        return SPECIES_UNLOCK[10]
    return SPECIES_UNLOCK.get(level, "\U0001f331")


# --- Sound Settings ---
def get_sound_settings():
    with closing(get_db_connection()) as conn:
        row = conn.execute("SELECT * FROM sound_settings LIMIT 1").fetchone()
    if row:
        return dict(row)
    return {
        "id": 1,
        "is_muted": 0,
        "focus_start_path": "assets/sounds/focus_start.mp3",
        "break_start_path": "assets/sounds/break_start.mp3",
    }


def update_sound_setting(key, value):
    if key not in ("is_muted", "focus_start_path", "break_start_path"):
        return
    with closing(get_db_connection()) as conn:
        conn.execute(f"UPDATE sound_settings SET {key} = ? WHERE id = 1", (value,))
        conn.commit()


# ============================================================
# --- Skill Tree Backend ---
# ============================================================


def get_global_sp():
    """Return the user's current global Skill Points."""
    with closing(get_db_connection()) as conn:
        row = conn.execute("SELECT global_sp FROM user_settings LIMIT 1").fetchone()
    return (dict(row).get("global_sp", 0) or 0) if row else 0


def add_global_sp(amount):
    """Add SP to the global pool (can be negative to deduct)."""
    current = get_global_sp()
    new_sp = max(0, current + amount)
    with closing(get_db_connection()) as conn:
        conn.execute("UPDATE user_settings SET global_sp = ?", (new_sp,))
        conn.commit()
    return new_sp


# --- Tree CRUD ---
def create_skill_tree(name, description=""):
    """Create a new skill tree and return its id."""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO skill_trees (name, description) VALUES (?, ?)",
            (name, description),
        )
        tree_id = cursor.lastrowid
        conn.commit()
    return tree_id


def get_all_skill_trees():
    with closing(get_db_connection()) as conn:
        rows = conn.execute("SELECT * FROM skill_trees").fetchall()
    return [dict(r) for r in rows]


def get_skill_tree_by_name(name):
    with closing(get_db_connection()) as conn:
        row = conn.execute(
            "SELECT * FROM skill_trees WHERE name = ?", (name,)
        ).fetchone()
    return dict(row) if row else None


def update_skill_tree(tree_id, new_name, new_description=""):
    """Đổi tên và mô tả cho Cây kỹ năng hiện tại"""
    from contextlib import closing

    with closing(get_db_connection()) as conn:
        conn.execute(
            "UPDATE skill_trees SET name = ?, description = ? WHERE id = ?",
            (new_name, new_description, tree_id),
        )
        conn.commit()


# --- Node CRUD ---
def create_skill_node(
    tree_id,
    parent_id,
    name,
    description="",
    sp_cost=10,
    is_repeatable=False,
    exclusive_group_id=None,
    max_level=1,
):
    """Create a skill node and initialise its user_skills row as 'locked'."""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO skill_nodes
               (tree_id, parent_id, name, description, sp_cost,
                is_repeatable, exclusive_group_id, max_level)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tree_id,
                parent_id,
                name,
                description,
                sp_cost,
                1 if is_repeatable else 0,
                exclusive_group_id,
                max_level,
            ),
        )
        node_id = cursor.lastrowid
        # Auto-create the user_skills entry
        cursor.execute(
            "INSERT INTO user_skills (node_id, status, current_sp_invested, current_level) VALUES (?, 'locked', 0, 0)",
            (node_id,),
        )
        conn.commit()
    return node_id


def _ensure_multilevel_columns(conn):
    """Safely add max_level and current_level columns if missing."""
    try:
        conn.execute("ALTER TABLE skill_nodes ADD COLUMN max_level INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE user_skills ADD COLUMN current_level INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass


def get_tree_nodes(tree_id):
    """Return all nodes for a tree, enriched with their user_skills status."""
    with closing(get_db_connection()) as conn:
        _ensure_multilevel_columns(conn)
        rows = conn.execute(
            """SELECT n.*, COALESCE(n.max_level, 1) AS max_level,
                      COALESCE(u.status, 'locked') AS status,
                      COALESCE(u.current_sp_invested, 0) AS current_sp_invested,
                      COALESCE(u.current_level, 0) AS current_level
               FROM skill_nodes n
               LEFT JOIN user_skills u ON n.id = u.node_id
               WHERE n.tree_id = ?
               ORDER BY n.id""",
            (tree_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_node(node_id):
    """Return a single node dict with its status."""
    with closing(get_db_connection()) as conn:
        _ensure_multilevel_columns(conn)
        row = conn.execute(
            """SELECT n.*, COALESCE(n.max_level, 1) AS max_level,
                      COALESCE(u.status, 'locked') AS status,
                      COALESCE(u.current_sp_invested, 0) AS current_sp_invested,
                      COALESCE(u.current_level, 0) AS current_level
               FROM skill_nodes n
               LEFT JOIN user_skills u ON n.id = u.node_id
               WHERE n.id = ?""",
            (node_id,),
        ).fetchone()
    return dict(row) if row else None


def update_skill_node(node_id, name, description, sp_cost, is_repeatable, max_level=1):
    with closing(get_db_connection()) as conn:
        conn.execute(
            """UPDATE skill_nodes 
               SET name = ?, description = ?, sp_cost = ?, is_repeatable = ?, max_level = ?
               WHERE id = ?""",
            (name, description, sp_cost, 1 if is_repeatable else 0, max_level, node_id),
        )
        conn.commit()


def delete_skill_node(node_id):
    """Delete a node and all its children recursively."""
    with closing(get_db_connection()) as conn:

        def get_all_descendants(n_id):
            descendants = []
            rows = conn.execute(
                "SELECT id FROM skill_nodes WHERE parent_id = ?", (n_id,)
            ).fetchall()
            for r in rows:
                child_id = r["id"]
                descendants.append(child_id)
                descendants.extend(get_all_descendants(child_id))
            return descendants

        to_delete = [node_id] + get_all_descendants(node_id)

        for d_id in to_delete:
            conn.execute("DELETE FROM user_skills WHERE node_id = ?", (d_id,))
            conn.execute("DELETE FROM node_tasks WHERE node_id = ?", (d_id,))
            conn.execute("DELETE FROM skill_nodes WHERE id = ?", (d_id,))

        conn.commit()


# --- Node Tasks ---
def add_node_task(node_id, task_type, content):
    """Add a verification task to a node. task_type: 'checklist', 'text_review', 'code_snippet'."""
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO node_tasks (node_id, task_type, content, is_completed) VALUES (?, ?, ?, 0)",
            (node_id, task_type, content),
        )
        task_id = cursor.lastrowid
        conn.commit()
    return task_id


def get_node_tasks(node_id):
    with closing(get_db_connection()) as conn:
        rows = conn.execute(
            "SELECT * FROM node_tasks WHERE node_id = ? ORDER BY id",
            (node_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def complete_node_task(task_id):
    with closing(get_db_connection()) as conn:
        conn.execute("UPDATE node_tasks SET is_completed = 1 WHERE id = ?", (task_id,))
        conn.commit()


def are_all_tasks_completed(node_id):
    """Check if every task for a node is completed."""
    tasks = get_node_tasks(node_id)
    if not tasks:
        return True  # no tasks means no barrier
    return all(t["is_completed"] for t in tasks)


# --- Unlockability & SP Investment Logic ---
def check_node_unlockability(node_id):
    """Return (can_unlock: bool, reason: str).

    Rules:
    1. Node must currently be 'locked'.
    2. If parent_id exists, parent must be 'unlocked' or 'mastered'.
    3. If exclusive_group_id is set, no *other* node in the same
       group may already be 'unlocked' or 'mastered'.
    4. All verification tasks must be completed.
    5. User must have enough global SP >= sp_cost.
    """
    node = get_node(node_id)
    if not node:
        return False, "Node không tồn tại."

    if node["status"] == "mastered" and not node["is_repeatable"]:
        return False, "Node đã hoàn thành và không lặp lại được."

    if node["status"] == "unlocked":
        return False, "Node đã được mở khóa."

    # Parent check — child MUST wait until parent is fully mastered
    if node["parent_id"] is not None:
        parent = get_node(node["parent_id"])
        if parent and parent["status"] != "mastered":
            return False, f"Cần hoàn thành tối đa '{parent['name']}' trước."

    # Exclusive group check
    if node["exclusive_group_id"]:
        with closing(get_db_connection()) as conn:
            conflict = conn.execute(
                """SELECT n.name FROM skill_nodes n
                   JOIN user_skills u ON n.id = u.node_id
                   WHERE n.exclusive_group_id = ?
                     AND n.id != ?
                     AND u.status IN ('unlocked', 'mastered')""",
                (node["exclusive_group_id"], node_id),
            ).fetchone()
        if conflict:
            return (
                False,
                f"Nhánh '{conflict['name']}' đã được chọn (loại trừ lẫn nhau).",
            )

    # Tasks check
    if not are_all_tasks_completed(node_id):
        return False, "Chưa hoàn thành hết các nhiệm vụ xác minh."

    return True, "Có thể mở khóa."


def complete_node_milestone(node_id):
    """Complete one milestone of a node, granting EXP to the user.
    Returns (success: bool, message: str, new_status: str|None)."""
    node = get_node(node_id)
    if not node:
        return False, "Node không tồn tại.", None

    current_level = node.get("current_level", 0)
    max_level = node.get("max_level", 1)
    exp_reward = node.get("sp_cost", 10)  # sp_cost is now treated as exp_reward

    if current_level >= max_level:
        return False, "Đã max cấp!", "mastered"

    # Check unlockability (parent mastery, exclusive groups, tasks)
    can_unlock, reason = check_node_unlockability(node_id)
    if not can_unlock and node["status"] == "locked":
        return False, reason, None

    new_level = current_level + 1
    new_status = "mastered" if new_level >= max_level else "unlocked"

    with closing(get_db_connection()) as conn:
        conn.execute(
            "UPDATE user_skills SET current_level = ?, status = ?, current_sp_invested = 0 WHERE node_id = ?",
            (new_level, new_status, node_id),
        )
        conn.commit()

    # Grant EXP to the user's global XP pool
    add_xp(exp_reward)

    level_info = f" (Lv.{new_level}/{max_level})" if max_level > 1 else ""
    return (
        True,
        f"Hoàn thành mốc! Nhận {exp_reward} EXP 🌟{level_info}",
        new_status,
    )


def master_node(node_id):
    """Mark a node as mastered (post-unlock progression)."""
    with closing(get_db_connection()) as conn:
        conn.execute(
            "UPDATE user_skills SET status = 'mastered' WHERE node_id = ?",
            (node_id,),
        )
        conn.commit()
