import sqlite3
from datetime import datetime, timedelta

DB_NAME = "app_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Habits table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            incentive_amount REAL DEFAULT 0,
            frequency_type TEXT DEFAULT 'daily',
            current_streak INTEGER DEFAULT 0,
            weight INTEGER DEFAULT 1,
            frequency TEXT DEFAULT '0,1,2,3,4,5,6'
        )
    ''')
    
    # Column check and update
    cursor.execute("PRAGMA table_info(habits)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'weight' not in columns:
        cursor.execute("ALTER TABLE habits ADD COLUMN weight INTEGER DEFAULT 1")
    if 'frequency' not in columns:
        try:
            cursor.execute("ALTER TABLE habits ADD COLUMN frequency TEXT DEFAULT '0,1,2,3,4,5,6'")
        except sqlite3.OperationalError: pass

    # Habit logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER,
            log_date TEXT,
            status TEXT,
            FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE
        )
    ''')
    
    # Accounts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            balance REAL DEFAULT 0
        )
    ''')
    
    # Transactions table
    cursor.execute('''
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
    ''')
    
    # Quotes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            author TEXT
        )
    ''')
    
    # User settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monthly_budget REAL DEFAULT 3000000,
            theme TEXT DEFAULT 'dark',
            currency TEXT DEFAULT 'VNĐ'
        )
    ''')
    
    cursor.execute("PRAGMA table_info(user_settings)")
    cols = [col[1] for col in cursor.fetchall()]
    if 'theme' not in cols: cursor.execute("ALTER TABLE user_settings ADD COLUMN theme TEXT DEFAULT 'dark'")
    if 'currency' not in cols: cursor.execute("ALTER TABLE user_settings ADD COLUMN currency TEXT DEFAULT 'VNĐ'")
    
    cursor.execute("SELECT COUNT(*) FROM user_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO user_settings (monthly_budget, theme, currency) VALUES (3000000, 'dark', 'VNĐ')")
        
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

def add_habit(name, incentive=0, weight=1, frequency="0,1,2,3,4,5,6"):
    conn = get_db_connection()
    conn.execute("INSERT INTO habits (name, incentive_amount, weight, frequency) VALUES (?, ?, ?, ?)", (name, incentive, weight, frequency))
    conn.commit()
    conn.close()

def delete_habit(habit_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    conn.commit()
    conn.close()

def get_habit_logs_for_date(date_str):
    conn = get_db_connection()
    logs = conn.execute("SELECT habit_id FROM habit_logs WHERE log_date = ? AND status = 'done'", (date_str,)).fetchall()
    conn.close()
    return [log['habit_id'] for log in logs]

def get_habit_logs_last_30_days(habit_id):
    conn = get_db_connection()
    thirty_days_ago = (datetime.now().date() - timedelta(days=29)).strftime("%Y-%m-%d")
    logs = conn.execute('''
        SELECT log_date FROM habit_logs 
        WHERE habit_id = ? AND status = 'done' AND log_date >= ?
    ''', (habit_id, thirty_days_ago)).fetchall()
    conn.close()
    return [log['log_date'] for log in logs]

def get_habit_streak(habit_id, frequency_str):
    conn = get_db_connection()
    logs = conn.execute('SELECT log_date FROM habit_logs WHERE habit_id = ? AND status = "done" ORDER BY log_date DESC', (habit_id,)).fetchall()
    log_dates = [row['log_date'] for row in logs]
    conn.close()

    streak = 0
    current_date = datetime.now().date()
    
    for i in range(100): # Backward Check
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
    logs = conn.execute('''
        SELECT l.log_date, SUM(h.weight) as total_weight
        FROM habit_logs l
        JOIN habits h ON l.habit_id = h.id
        WHERE l.status = 'done' AND l.log_date >= ?
        GROUP BY l.log_date
    ''', (seven_days_ago,)).fetchall()
    conn.close()
    return {log['log_date']: log['total_weight'] for log in logs}

def get_total_active_habit_weight():
    conn = get_db_connection()
    row = conn.execute("SELECT SUM(weight) as total FROM habits").fetchone()
    conn.close()
    return row['total'] if row['total'] else 0

def toggle_habit_log(habit_id, date_str, is_done):
    conn = get_db_connection()
    if is_done:
        conn.execute("INSERT OR IGNORE INTO habit_logs (habit_id, log_date, status) VALUES (?, ?, 'done')", (habit_id, date_str))
    else:
        conn.execute("DELETE FROM habit_logs WHERE habit_id = ? AND log_date = ?", (habit_id, date_str))
    
    # Simple streak logic (will be overruled by get_habit_streak in display)
    update_streak_legacy(conn, habit_id)
    
    conn.commit()
    conn.close()

def update_streak_legacy(conn, habit_id):
    # This legacy streak is just for db column maintenance
    logs = conn.execute("SELECT log_date FROM habit_logs WHERE habit_id = ? AND status = 'done' ORDER BY log_date DESC", (habit_id,)).fetchall()
    dates = [datetime.strptime(l['log_date'], "%Y-%m-%d").date() for l in logs]
    streak = 0
    if dates:
        today = datetime.now().date()
        if dates[0] == today or dates[0] == today - timedelta(days=1):
            streak = 1
            for i in range(len(dates) - 1):
                if (dates[i] - dates[i+1]).days == 1: streak += 1
                else: break
    conn.execute("UPDATE habits SET current_streak = ? WHERE id = ?", (streak, habit_id))

def get_habit_stats():
    conn = get_db_connection()
    freq = conn.execute('''
        SELECT h.name, COUNT(l.id) as count FROM habits h LEFT JOIN habit_logs l ON h.id = l.habit_id GROUP BY h.id
    ''').fetchall()
    trend = conn.execute('''
        SELECT log_date, COUNT(id) as count FROM habit_logs GROUP BY log_date ORDER BY log_date ASC
    ''').fetchall()
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
    existing = conn.execute("SELECT id FROM accounts WHERE name = ?", (name,)).fetchone()
    if existing:
        conn.execute("UPDATE accounts SET balance = ? WHERE id = ?", (balance, existing['id']))
    else:
        conn.execute("INSERT INTO accounts (name, balance) VALUES (?, ?)", (name, balance))
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
    return budget['monthly_budget'] if budget else 3000000

def get_settings():
    conn = get_db_connection()
    settings = conn.execute("SELECT * FROM user_settings LIMIT 1").fetchone()
    conn.close()
    return dict(settings) if settings else {"id": 1, "monthly_budget": 3000000, "theme": "dark", "currency": "VNĐ"}

def update_settings(budget, theme, currency):
    conn = get_db_connection()
    conn.execute("UPDATE user_settings SET monthly_budget = ?, theme = ?, currency = ?", (budget, theme, currency))
    conn.commit()
    conn.close()

def get_monthly_expenses(month_start):
    conn = get_db_connection()
    expenses = conn.execute('''
        SELECT SUM(amount) as total FROM transactions WHERE transaction_type = 'expense' AND category != 'Chuyển đi' AND created_at >= ?
    ''', (month_start,)).fetchone()
    conn.close()
    return expenses['total'] if expenses['total'] else 0

def get_daily_spending_last_7_days():
    conn = get_db_connection()
    seven_days_ago = (datetime.now().date() - timedelta(days=6)).strftime("%Y-%m-%d")
    logs = conn.execute('''
        SELECT substr(created_at, 1, 10) as day, SUM(amount) as total FROM transactions WHERE transaction_type = 'expense' AND category != 'Chuyển đi' AND created_at >= ? GROUP BY day
    ''', (seven_days_ago,)).fetchall()
    conn.close()
    return {log['day']: log['total'] for log in logs}

def add_transaction(account_id, amount, t_type, category, description):
    conn = get_db_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    acc = conn.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if acc:
        new_balance = acc['balance'] + (-amount if t_type == 'expense' else amount)
        conn.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account_id))
        conn.execute('''
            INSERT INTO transactions (account_id, amount, transaction_type, category, description, created_at) VALUES (?, ?, ?, ?, ?, ?)
        ''', (account_id, amount, t_type, category, description, now))
    conn.commit()
    conn.close()

def transfer_funds(from_id, to_id, amount, from_name, to_name):
    conn = get_db_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    acc_from = conn.execute("SELECT balance FROM accounts WHERE id = ?", (from_id,)).fetchone()
    acc_to = conn.execute("SELECT balance FROM accounts WHERE id = ?", (to_id,)).fetchone()
    if acc_from and acc_to:
        conn.execute("UPDATE accounts SET balance = ? WHERE id = ?", (acc_from['balance'] - amount, from_id))
        conn.execute("UPDATE accounts SET balance = ? WHERE id = ?", (acc_to['balance'] + amount, to_id))
        conn.execute('''
            INSERT INTO transactions (account_id, amount, transaction_type, category, description, created_at) VALUES (?, ?, 'expense', 'Chuyển đi', ?, ?)
        ''', (from_id, amount, f"Chuyển sang {to_name}", now))
        conn.execute('''
            INSERT INTO transactions (account_id, amount, transaction_type, category, description, created_at) VALUES (?, ?, 'income', 'Nhận tiền', ?, ?)
        ''', (to_id, amount, f"Nhận từ {from_name}", now))
    conn.commit()
    conn.close()

def get_recent_transactions(limit=15, t_type="All"):
    conn = get_db_connection()
    c = conn.cursor()
    query = "SELECT amount, transaction_type, category, description, created_at FROM transactions"
    params = []
    if t_type == "Expense": query = "SELECT amount, transaction_type, category, description, created_at FROM transactions WHERE transaction_type = 'expense'"
    elif t_type == "Income": query = "SELECT amount, transaction_type, category, description, created_at FROM transactions WHERE transaction_type = 'income'"
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]