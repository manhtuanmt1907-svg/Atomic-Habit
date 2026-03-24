import sqlite3
from datetime import datetime, timedelta

DB_NAME = "app_data.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
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
            "INSERT INTO sound_settings (id, is_muted, focus_start_path, break_start_path) VALUES (1, 0, 'assets/sounds/focus_start.mp3', 'assets/sounds/break_start.mp3')"
        )

    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# --- Habits ---
def get_all_habits():
    conn = get_db_connection()
    habits = conn.execute("SELECT * FROM habits").fetchall()
    conn.close()
    return habits


def add_habit(name, description="", incentive=0, weight=1, frequency="0,1,2,3,4,5,6"):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO habits (name, description, incentive_amount, weight, frequency) VALUES (?, ?, ?, ?, ?)",
        (name, description, incentive, weight, frequency),
    )
    conn.commit()
    conn.close()


def delete_habit(habit_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    conn.commit()
    conn.close()


def get_habit_logs_for_date(date_str):
    conn = get_db_connection()
    logs = conn.execute(
        "SELECT habit_id FROM habit_logs WHERE log_date = ? AND status = 'done'",
        (date_str,),
    ).fetchall()
    conn.close()
    return [log["habit_id"] for log in logs]


def get_habit_logs_last_30_days(habit_id):
    conn = get_db_connection()
    thirty_days_ago = (datetime.now().date() - timedelta(days=29)).strftime("%Y-%m-%d")
    logs = conn.execute(
        """
        SELECT log_date FROM habit_logs 
        WHERE habit_id = ? AND status = 'done' AND log_date >= ?
    """,
        (habit_id, thirty_days_ago),
    ).fetchall()
    conn.close()
    return [log["log_date"] for log in logs]


def get_habit_streak(habit_id, frequency_str):
    conn = get_db_connection()
    logs = conn.execute(
        'SELECT log_date FROM habit_logs WHERE habit_id = ? AND status = "done" ORDER BY log_date DESC',
        (habit_id,),
    ).fetchall()
    log_dates = [row["log_date"] for row in logs]
    conn.close()

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
    conn = get_db_connection()
    seven_days_ago = (datetime.now().date() - timedelta(days=6)).strftime("%Y-%m-%d")
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
    conn.close()
    return {log["log_date"]: log["total_weight"] for log in logs}


def get_total_active_habit_weight():
    conn = get_db_connection()
    row = conn.execute("SELECT SUM(weight) as total FROM habits").fetchone()
    conn.close()
    return row["total"] if row["total"] else 0


def toggle_habit_log(habit_id, date_str, is_done):
    conn = get_db_connection()
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
    conn.close()


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
    conn = get_db_connection()
    freq = conn.execute("""
        SELECT h.name, COUNT(l.id) as count FROM habits h LEFT JOIN habit_logs l ON h.id = l.habit_id GROUP BY h.id
    """).fetchall()
    trend = conn.execute("""
        SELECT log_date, COUNT(id) as count FROM habit_logs GROUP BY log_date ORDER BY log_date ASC
    """).fetchall()
    conn.close()
    return freq, trend


# --- Quotes ---
def get_all_quotes():
    conn = get_db_connection()
    quotes = conn.execute("SELECT * FROM quotes").fetchall()
    conn.close()
    return quotes


def add_quote(text, author):
    conn = get_db_connection()
    conn.execute("INSERT INTO quotes (text, author) VALUES (?, ?)", (text, author))
    conn.commit()
    conn.close()


def delete_quote(quote_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
    conn.commit()
    conn.close()


# --- Finance ---
def get_all_accounts():
    conn = get_db_connection()
    accounts = conn.execute("SELECT * FROM accounts").fetchall()
    conn.close()
    return accounts


def add_account(name, balance=0):
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT id FROM accounts WHERE name = ?", (name,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE accounts SET balance = ? WHERE id = ?", (balance, existing["id"])
        )
    else:
        conn.execute(
            "INSERT INTO accounts (name, balance) VALUES (?, ?)", (name, balance)
        )
    conn.commit()
    conn.close()


def delete_account(account_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()


def get_budget():
    conn = get_db_connection()
    budget = conn.execute("SELECT monthly_budget FROM user_settings LIMIT 1").fetchone()
    conn.close()
    return budget["monthly_budget"] if budget else 3000000


def get_settings():
    conn = get_db_connection()
    settings = conn.execute("SELECT * FROM user_settings LIMIT 1").fetchone()
    conn.close()
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
    conn = get_db_connection()
    conn.execute(
        "UPDATE user_settings SET monthly_budget = ?, theme = ?, currency = ?, pomodoro_show_time = ?",
        (budget, theme, currency, pomodoro_show_time),
    )
    conn.commit()
    conn.close()


def get_monthly_expenses(month_start):
    conn = get_db_connection()
    expenses = conn.execute(
        """
        SELECT SUM(amount) as total FROM transactions WHERE transaction_type = 'expense' AND category != 'Chuyển đi' AND created_at >= ?
    """,
        (month_start,),
    ).fetchone()
    conn.close()
    return expenses["total"] if expenses["total"] else 0


def get_expenses_by_category(month_start):
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT category, SUM(amount) as total FROM transactions WHERE transaction_type = 'expense' AND category != 'Chuyển đi' AND created_at >= ? GROUP BY category
    """,
        (month_start,),
    ).fetchall()
    conn.close()
    return {row["category"]: row["total"] for row in rows}


def get_daily_spending_last_7_days():
    conn = get_db_connection()
    seven_days_ago = (datetime.now().date() - timedelta(days=6)).strftime("%Y-%m-%d")
    logs = conn.execute(
        """
        SELECT substr(created_at, 1, 10) as day, SUM(amount) as total FROM transactions WHERE transaction_type = 'expense' AND category != 'Chuyển đi' AND created_at >= ? GROUP BY day
    """,
        (seven_days_ago,),
    ).fetchall()
    conn.close()
    return {log["day"]: log["total"] for log in logs}


def add_transaction(account_id, amount, t_type, category, description):
    conn = get_db_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    acc = conn.execute(
        "SELECT balance FROM accounts WHERE id = ?", (account_id,)
    ).fetchone()
    if acc:
        new_balance = acc["balance"] + (-amount if t_type == "expense" else amount)
        conn.execute(
            "UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account_id)
        )
        conn.execute(
            """
            INSERT INTO transactions (account_id, amount, transaction_type, category, description, created_at) VALUES (?, ?, ?, ?, ?, ?)
        """,
            (account_id, amount, t_type, category, description, now),
        )
    conn.commit()
    conn.close()


def transfer_funds(from_id, to_id, amount, from_name, to_name):
    conn = get_db_connection()
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
    conn.close()


def get_recent_transactions(limit=15, t_type="All"):
    conn = get_db_connection()
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
    conn.close()
    return [dict(row) for row in rows]


# --- App Settings ---
def get_setting(key, default_value=None):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key = ?", (key,)
    ).fetchone()
    conn.close()
    return row["value"] if row is not None else default_value


def update_setting(key, value):
    conn = get_db_connection()
    conn.execute(
        "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
        (key, str(value)),
    )
    conn.commit()
    conn.close()


def hard_reset():
    conn = get_db_connection()
    conn.execute("DELETE FROM transactions")
    conn.execute("DELETE FROM habit_logs")
    conn.execute("DELETE FROM habits")
    conn.execute("DELETE FROM app_settings")
    conn.execute("DELETE FROM accounts")
    conn.execute("DELETE FROM quotes")
    conn.execute("DELETE FROM user_settings")
    conn.execute("DELETE FROM sound_settings")
    conn.commit()
    conn.close()

    # Reload default settings safely by re-running init logic
    init_db()


# --- Phase 3.5 Heatmap Helpers ---
def get_daily_habit_completion_ratio(date_str):
    conn = get_db_connection()
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
        conn.close()
        return 0.0

    completed_count = conn.execute(
        "SELECT COUNT(DISTINCT habit_id) FROM habit_logs WHERE log_date = ? AND status = 'done'",
        (date_str,),
    ).fetchone()[0]
    conn.close()
    return min(1.0, completed_count / scheduled_count)


def get_daily_finance_activity(date_str):
    conn = get_db_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE created_at LIKE ?", (date_str + "%",)
    ).fetchone()[0]
    conn.close()
    return count


def log_focus_time(date_str, seconds):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO focus_logs (log_date, focus_seconds) VALUES (?, ?)",
        (date_str, seconds),
    )
    conn.commit()
    conn.close()


def get_daily_focus_seconds(date_str):
    conn = get_db_connection()
    total = conn.execute(
        "SELECT SUM(focus_seconds) FROM focus_logs WHERE log_date = ?", (date_str,)
    ).fetchone()[0]
    conn.close()
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
    conn = get_db_connection()
    row = conn.execute(
        "SELECT current_xp, current_level FROM user_settings LIMIT 1"
    ).fetchone()
    conn.close()
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
    conn = get_db_connection()
    conn.execute(
        "UPDATE user_settings SET current_xp = ?, current_level = ?", (xp, level)
    )
    conn.commit()
    conn.close()
    return xp, level


def deduct_xp(amount):
    """Deduct XP (min 0), persist to DB, return (new_xp, level)."""
    xp, level = get_xp_level()
    xp = max(0, xp - amount)
    conn = get_db_connection()
    conn.execute(
        "UPDATE user_settings SET current_xp = ?, current_level = ?", (xp, level)
    )
    conn.commit()
    conn.close()
    return xp, level


def get_species_emoji(level):
    if level >= 10:
        return SPECIES_UNLOCK[10]
    return SPECIES_UNLOCK.get(level, "\U0001f331")


# --- Sound Settings ---
def get_sound_settings():
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM sound_settings LIMIT 1").fetchone()
    conn.close()
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
    conn = get_db_connection()
    conn.execute(f"UPDATE sound_settings SET {key} = ? WHERE id = 1", (value,))
    conn.commit()
    conn.close()


# ============================================================
# --- Skill Tree Backend ---
# ============================================================

def get_global_sp():
    """Return the user's current global Skill Points."""
    conn = get_db_connection()
    row = conn.execute("SELECT global_sp FROM user_settings LIMIT 1").fetchone()
    conn.close()
    return (dict(row).get("global_sp", 0) or 0) if row else 0


def add_global_sp(amount):
    """Add SP to the global pool (can be negative to deduct)."""
    current = get_global_sp()
    new_sp = max(0, current + amount)
    conn = get_db_connection()
    conn.execute("UPDATE user_settings SET global_sp = ?", (new_sp,))
    conn.commit()
    conn.close()
    return new_sp


# --- Tree CRUD ---
def create_skill_tree(name, description=""):
    """Create a new skill tree and return its id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO skill_trees (name, description) VALUES (?, ?)",
        (name, description),
    )
    tree_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return tree_id


def get_all_skill_trees():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM skill_trees").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_skill_tree_by_name(name):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM skill_trees WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Node CRUD ---
def create_skill_node(
    tree_id,
    parent_id,
    name,
    description="",
    sp_cost=10,
    is_repeatable=False,
    exclusive_group_id=None,
):
    """Create a skill node and initialise its user_skills row as 'locked'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO skill_nodes
           (tree_id, parent_id, name, description, sp_cost,
            is_repeatable, exclusive_group_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            tree_id,
            parent_id,
            name,
            description,
            sp_cost,
            1 if is_repeatable else 0,
            exclusive_group_id,
        ),
    )
    node_id = cursor.lastrowid
    # Auto-create the user_skills entry
    cursor.execute(
        "INSERT INTO user_skills (node_id, status, current_sp_invested) VALUES (?, 'locked', 0)",
        (node_id,),
    )
    conn.commit()
    conn.close()
    return node_id


def get_tree_nodes(tree_id):
    """Return all nodes for a tree, enriched with their user_skills status."""
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT n.*, COALESCE(u.status, 'locked') AS status,
                  COALESCE(u.current_sp_invested, 0) AS current_sp_invested
           FROM skill_nodes n
           LEFT JOIN user_skills u ON n.id = u.node_id
           WHERE n.tree_id = ?
           ORDER BY n.id""",
        (tree_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_node(node_id):
    """Return a single node dict with its status."""
    conn = get_db_connection()
    row = conn.execute(
        """SELECT n.*, COALESCE(u.status, 'locked') AS status,
                  COALESCE(u.current_sp_invested, 0) AS current_sp_invested
           FROM skill_nodes n
           LEFT JOIN user_skills u ON n.id = u.node_id
           WHERE n.id = ?""",
        (node_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_skill_node(node_id, name, description, sp_cost, is_repeatable):
    conn = get_db_connection()
    conn.execute(
        """UPDATE skill_nodes 
           SET name = ?, description = ?, sp_cost = ?, is_repeatable = ?
           WHERE id = ?""",
        (name, description, sp_cost, 1 if is_repeatable else 0, node_id),
    )
    conn.commit()
    conn.close()


def delete_skill_node(node_id):
    """Delete a node and all its children recursively."""
    conn = get_db_connection()

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
    conn.close()


# --- Node Tasks ---
def add_node_task(node_id, task_type, content):
    """Add a verification task to a node. task_type: 'checklist', 'text_review', 'code_snippet'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO node_tasks (node_id, task_type, content, is_completed) VALUES (?, ?, ?, 0)",
        (node_id, task_type, content),
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id


def get_node_tasks(node_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM node_tasks WHERE node_id = ? ORDER BY id",
        (node_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def complete_node_task(task_id):
    conn = get_db_connection()
    conn.execute("UPDATE node_tasks SET is_completed = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


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

    # Parent check
    if node["parent_id"] is not None:
        parent = get_node(node["parent_id"])
        if parent and parent["status"] == "locked":
            return False, f"Cần mở khóa '{parent['name']}' trước."

    # Exclusive group check
    if node["exclusive_group_id"]:
        conn = get_db_connection()
        conflict = conn.execute(
            """SELECT n.name FROM skill_nodes n
               JOIN user_skills u ON n.id = u.node_id
               WHERE n.exclusive_group_id = ?
                 AND n.id != ?
                 AND u.status IN ('unlocked', 'mastered')""",
            (node["exclusive_group_id"], node_id),
        ).fetchone()
        conn.close()
        if conflict:
            return (
                False,
                f"Nhánh '{conflict['name']}' đã được chọn (loại trừ lẫn nhau).",
            )

    # Tasks check
    if not are_all_tasks_completed(node_id):
        return False, "Chưa hoàn thành hết các nhiệm vụ xác minh."

    # SP check
    sp = get_global_sp()
    if sp < node["sp_cost"]:
        return False, f"Không đủ SP (cần {node['sp_cost']}, hiện có {sp})."

    return True, "Có thể mở khóa."


def invest_sp(node_id, amount=None):
    """Invest SP into a node. If amount is None, invest the full sp_cost.
    Returns (success: bool, message: str, new_status: str|None)."""
    node = get_node(node_id)
    if not node:
        return False, "Node không tồn tại.", None

    can_unlock, reason = check_node_unlockability(node_id)
    if not can_unlock:
        return False, reason, None

    cost = node["sp_cost"]
    invest_amount = amount if amount is not None else cost
    invest_amount = min(invest_amount, cost - node["current_sp_invested"])

    if invest_amount <= 0:
        return False, "Không cần đầu tư thêm.", None

    sp = get_global_sp()
    if sp < invest_amount:
        return False, f"Không đủ SP (cần {invest_amount}, hiện có {sp}).", None

    # Deduct and invest
    add_global_sp(-invest_amount)
    new_invested = node["current_sp_invested"] + invest_amount
    new_status = "unlocked" if new_invested >= cost else "locked"

    conn = get_db_connection()
    conn.execute(
        "UPDATE user_skills SET current_sp_invested = ?, status = ? WHERE node_id = ?",
        (new_invested, new_status, node_id),
    )
    conn.commit()
    conn.close()

    return True, f"Đã đầu tư {invest_amount} SP. Trạng thái: {new_status}.", new_status


def master_node(node_id):
    """Mark a node as mastered (post-unlock progression)."""
    conn = get_db_connection()
    conn.execute(
        "UPDATE user_skills SET status = 'mastered' WHERE node_id = ?",
        (node_id,),
    )
    conn.commit()
    conn.close()
