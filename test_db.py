import database as db
import os

def test_db():
    # Remove existing DB for clean test
    if os.path.exists(db.DB_NAME):
        os.remove(db.DB_NAME)
    
    print("Testing DB initialization...")
    db.init_db()
    
    print("Testing Quotes...")
    db.add_quote("Test Quote", "Test Author")
    quotes = db.get_all_quotes()
    assert len(quotes) == 1
    assert quotes[0]['text'] == "Test Quote"
    db.delete_quote(quotes[0]['id'])
    assert len(db.get_all_quotes()) == 0
    
    print("Testing Habits...")
    db.add_habit("Read", 100)
    habits = db.get_all_habits()
    assert len(habits) == 1
    hid = habits[0]['id']
    db.toggle_habit_log(hid, "2026-03-21", True)
    logs = db.get_habit_logs_for_date("2026-03-21")
    assert hid in logs
    
    print("Testing Finance...")
    db.add_account("Cash", 1000)
    db.add_account("Bank", 5000)
    accs = db.get_all_accounts()
    assert len(accs) == 2
    
    cash_id = next(a['id'] for a in accs if a['name'] == "Cash")
    bank_id = next(a['id'] for a in accs if a['name'] == "Bank")
    
    db.add_transaction(cash_id, 200, "expense", "Food", "Lunch")
    accs = db.get_all_accounts()
    cash_bal = next(a['balance'] for a in accs if a['name'] == "Cash")
    assert cash_bal == 800
    
    db.transfer_funds(bank_id, cash_id, 500, "Bank", "Cash")
    accs = db.get_all_accounts()
    cash_bal = next(a['balance'] for a in accs if a['name'] == "Cash")
    bank_bal = next(a['balance'] for a in accs if a['name'] == "Bank")
    assert cash_bal == 1300
    assert bank_bal == 4500
    
    print("All basic DB tests passed!")

if __name__ == "__main__":
    test_db()
