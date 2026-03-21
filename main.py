import flet as ft
import database as db
from datetime import datetime
import random

def main(page: ft.Page):
    page.title = "Atomic Finance Pro"
    db.init_db()
    settings = db.get_settings()
    
    page.theme_mode = ft.ThemeMode.LIGHT if settings['theme'] == 'light' else ft.ThemeMode.DARK
    page.padding = 20
    page.window.width = 400
    page.window.height = 800

    # --- State Management / Helpers ---
    def format_money(amount):
        curr = settings.get('currency', 'VNĐ')
        if curr == 'kVNĐ':
            return f"{amount/1000:,.1f} kVNĐ"
        elif curr == 'USD':
            return f"${amount/25000:,.2f}"
        else:
            return f"{amount:,.0f} VNĐ"

    def refresh_settings():
        nonlocal settings
        settings = db.get_settings()
        page.theme_mode = ft.ThemeMode.LIGHT if settings['theme'] == 'light' else ft.ThemeMode.DARK
        page.update()

    def get_color_intensity(ratio, color_set):
        if ratio <= 0: return color_set[0]
        if ratio <= 0.33: return color_set[1]
        if ratio <= 0.66: return color_set[2]
        return color_set[3]

    # --- Navigation ---
    def handle_tab_change(e):
        idx = e.control.selected_index
        content_container.controls.clear()
        if idx == 0:
            render_habits()
        elif idx == 1:
            render_finance()
        elif idx == 2:
            render_review()
        elif idx == 3:
            render_settings()
        page.update()

    nav_bar = ft.NavigationBar(
        selected_index=0,
        destinations=[
            ft.NavigationBarDestination(label="Habits", icon=ft.Icons.CHECK_CIRCLE_OUTLINE),
            ft.NavigationBarDestination(label="Finance", icon=ft.Icons.ATTACH_MONEY),
            ft.NavigationBarDestination(label="Review", icon=ft.Icons.ANALYTICS),
            ft.NavigationBarDestination(label="Settings", icon=ft.Icons.SETTINGS),
        ],
        on_change=handle_tab_change
    )

    content_container = ft.Column(expand=True, scroll=ft.ScrollMode.ADAPTIVE)

    # --- Render Functions ---
    def render_habits():
        content_container.controls.clear()
        habits = db.get_all_habits()
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_weekday = str(datetime.now().weekday())
        done_ids = db.get_habit_logs_for_date(today_str)

        content_container.controls.append(ft.Text("Lộ trình hôm nay", size=20, weight=ft.FontWeight.BOLD))
        
        # Filter habits for today
        filtered_habits = []
        for h in habits:
            freq = dict(h).get('frequency') or "0,1,2,3,4,5,6"
            if today_weekday in freq:
                filtered_habits.append(h)
        
        total = len(filtered_habits)
        done_count = sum(1 for h in filtered_habits if h['id'] in done_ids)
        progress = done_count / total if total > 0 else 0
        content_container.controls.append(ft.ProgressBar(value=progress, color=ft.Colors.GREEN, bgcolor=ft.Colors.GREEN_100))
        content_container.controls.append(ft.Text(f"Tiến độ: {done_count}/{total}", size=12))

        # Add Habit Form
        name_input = ft.TextField(label="Tên thói quen mới", text_size=14, expand=True)
        weight_dd = ft.Dropdown(
            label="Tỷ trọng", width=100,
            options=[ft.dropdown.Option("1"), ft.dropdown.Option("2"), ft.dropdown.Option("3"), ft.dropdown.Option("5"), ft.dropdown.Option("8")],
            value="1"
        )
        
        # Multiple Day Selection (Chips)
        days_data = [("T2", "0"), ("T3", "1"), ("T4", "2"), ("T5", "3"), ("T6", "4"), ("T7", "5"), ("CN", "6")]
        chips = []
        def chip_toggle(e):
            page.update()

        for label, key in days_data:
            chips.append(ft.Chip(label=ft.Text(label), selected=True, data=key, on_select=chip_toggle))

        def add_h(e):
            if name_input.value:
                selected_keys = [c.data for c in chips if c.selected]
                freq_str = ",".join(selected_keys) if selected_keys else "0,1,2,3,4,5,6"
                db.add_habit(name_input.value, weight=int(weight_dd.value), frequency=freq_str)
                name_input.value = ""
                for c in chips: c.selected = True
                render_habits()
                page.update()

        content_container.controls.append(ft.Row([name_input, weight_dd, ft.IconButton(icon=ft.Icons.ADD_CIRCLE, on_click=add_h, icon_color=ft.Colors.INDIGO_600)]))
        content_container.controls.append(ft.Row(chips, wrap=True, alignment=ft.MainAxisAlignment.START))
        content_container.controls.append(ft.Divider())

        if not filtered_habits:
            content_container.controls.append(ft.Text("Nghỉ ngơi thôi! Nay không có lịch thói quen nào.", color=ft.Colors.GREY_500))
        else:
            for h in filtered_habits:
                is_done = h['id'] in done_ids
                freq = dict(h).get('frequency') or "0,1,2,3,4,5,6"
                streak = db.get_habit_streak(h['id'], freq)
                
                def toggle_cb(e, hid=h['id']):
                    db.toggle_habit_log(hid, today_str, e.control.value)
                    render_habits()
                    page.update()
                def del_h(e, hid=h['id']):
                    db.delete_habit(hid)
                    render_habits()
                    page.update()

                content_container.controls.append(
                    ft.Row([
                        ft.Checkbox(label=f"{h['name']} (W:{h['weight']} | Chuỗi: 🔥 {streak})", value=is_done, on_change=toggle_cb, expand=True),
                        ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_400, on_click=del_h)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )

    def render_finance(filter_type="All"):
        content_container.controls.clear()
        accounts = db.get_all_accounts()
        budget = settings['monthly_budget']
        month_start = datetime.now().strftime("%Y-%m-01")
        spent = db.get_monthly_expenses(month_start)

        content_container.controls.append(ft.Text("🎯 Ngân sách tháng này", size=20, weight=ft.FontWeight.BOLD))
        progress = min(spent / budget, 1.0) if budget > 0 else 1.0
        color = ft.Colors.GREEN if progress < 0.5 else ft.Colors.ORANGE if progress < 0.8 else ft.Colors.RED
        content_container.controls.append(ft.ProgressBar(value=progress, color=color, bgcolor=ft.Colors.GREY_200))
        content_container.controls.append(ft.Text(f"Đã tiêu: {format_money(spent)} / {format_money(budget)}", size=14))
        content_container.controls.append(ft.Divider())

        content_container.controls.append(ft.Text("🏦 Quản lý Ví tiền", size=18, weight=ft.FontWeight.BOLD))
        acc_name = ft.TextField(label="Tên ví", expand=True)
        acc_bal = ft.TextField(label="Số dư", value="0", expand=True)
        def add_a(e):
            if acc_name.value:
                db.add_account(acc_name.value, float(acc_bal.value or 0))
                render_finance(filter_type)
                page.update()
        content_container.controls.append(ft.Row([acc_name, acc_bal, ft.IconButton(ft.Icons.ADD, on_click=add_a)]))

        for a in accounts:
            def del_a(e, aid=a['id']):
                db.delete_account(aid)
                render_finance(filter_type)
                page.update()
            content_container.controls.append(ft.Row([
                ft.Text(f"**{a['name']}**: {format_money(a['balance'])}", expand=True),
                ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED_300, on_click=del_a)
            ]))
        content_container.controls.append(ft.Divider())

        content_container.controls.append(ft.Text("📝 Ghi sổ nhanh", size=18, weight=ft.FontWeight.BOLD))
        t_type = ft.RadioGroup(content=ft.Row([
            ft.Radio(value="expense", label="Chi tiêu (-)"),
            ft.Radio(value="income", label="Thu nhập (+)"),
            ft.Radio(value="transfer", label="Chuyển ví (↔)")
        ], wrap=True))
        t_type.value = "expense"
        acc_select = ft.Dropdown(options=[ft.dropdown.Option(a['name']) for a in accounts], label="Chọn ví", expand=True)
        acc_select2 = ft.Dropdown(options=[ft.dropdown.Option(a['name']) for a in accounts], label="Ví đích", visible=False, expand=True)
        def type_change(e):
            acc_select2.visible = (t_type.value == "transfer")
            page.update()
        t_type.on_change = type_change
        amount_in = ft.TextField(label="Số tiền", value="0")
        note_in = ft.TextField(label="Ghi chú")
        def save_t(e):
            amt = float(amount_in.value or 0)
            if amt <= 0: return
            if t_type.value == "transfer":
                if acc_select.value != acc_select2.value:
                    id_from = next(a['id'] for a in accounts if a['name'] == acc_select.value)
                    id_to = next(a['id'] for a in accounts if a['name'] == acc_select2.value)
                    db.transfer_funds(id_from, id_to, amt, acc_select.value, acc_select2.value)
            else:
                aid = next(a['id'] for a in accounts if a['name'] == acc_select.value)
                db.add_transaction(aid, amt, t_type.value, "Giao dịch", note_in.value)
            render_finance(filter_type)
            page.update()
        content_container.controls.extend([t_type, acc_select, acc_select2, amount_in, note_in, ft.ElevatedButton("Lưu giao dịch", on_click=save_t)])

        content_container.controls.append(ft.Divider())
        filter_dd = ft.Dropdown(label="Lọc", options=[ft.dropdown.Option("All"), ft.dropdown.Option("Expense"), ft.dropdown.Option("Income")], value=filter_type, width=120)
        filter_dd.on_change = lambda e: render_finance(e.control.value) or page.update()
        row_hist = ft.Row([ft.Text("🕒 Lịch sử", size=18, weight=ft.FontWeight.BOLD), filter_dd], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        content_container.controls.append(row_hist)
        
        history_list = ft.Column()
        txs = db.get_recent_transactions(15, filter_type)
        if not txs:
            history_list.controls.append(ft.Text("Chưa có giao dịch nào.", color=ft.Colors.GREY_500))
        else:
            for tx in txs:
                icon = ft.Icons.ARROW_DOWNWARD if tx['transaction_type'] == 'expense' else ft.Icons.ARROW_UPWARD
                color = ft.Colors.RED_500 if tx['transaction_type'] == 'expense' else ft.Colors.GREEN_500
                history_list.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(icon, color=color),
                        title=ft.Text(f"{tx['category']}", weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(f"{tx['description']} • {tx['created_at'][:10]}", size=12),
                        trailing=ft.Text(format_money(tx['amount']), color=color, weight=ft.FontWeight.BOLD)
                    )
                )
        content_container.controls.append(ft.Container(content=history_list, padding=ft.padding.only(bottom=80)))

    def render_review():
        content_container.controls.clear()
        
        # --- Random Quote ---
        quotes_data = db.get_all_quotes()
        quote_card = ft.Container(bgcolor=ft.Colors.INDIGO_50, padding=15, border_radius=10, margin=ft.Margin.only(bottom=20))
        if quotes_data:
            q = random.choice(quotes_data)
            quote_card.content = ft.Column([ft.Text(f"💡 \"{q['text']}\"", weight=ft.FontWeight.BOLD, color=ft.Colors.INDIGO_700), ft.Text(f" — {q['author']}", italic=True, size=12, color=ft.Colors.GREY_700)])
        else:
            quote_card.content = ft.Text("💡 Trạm Quotes đang trống...", color=ft.Colors.INDIGO_700)
        content_container.controls.append(quote_card)

        # --- Weekly Intensity ---
        content_container.controls.append(ft.Text("📊 Weekly Analysis", size=18, weight=ft.FontWeight.BOLD))
        import datetime as dt
        today_dt = dt.date.today()
        daily_spend = db.get_daily_spending_last_7_days()
        daily_habit_w = db.get_daily_habit_progress_last_7_days()
        total_habit_w = db.get_total_active_habit_weight()
        budget = db.get_budget()
        weekly_quota = budget / 7

        empty_color = ft.Colors.GREY_300 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.GREY_800
        
        # Finance Intensity Row
        finance_row = ft.Row(spacing=8)
        finance_colors = [empty_color, ft.Colors.INDIGO_100, ft.Colors.INDIGO_300, ft.Colors.INDIGO_700]
        for i in range(6, -1, -1):
            day = (today_dt - dt.timedelta(days=i)).strftime("%Y-%m-%d")
            spend = daily_spend.get(day, 0)
            ratio = spend / weekly_quota if weekly_quota > 0 else 0
            finance_row.controls.append(ft.Container(width=40, height=40, border_radius=4, bgcolor=get_color_intensity(ratio, finance_colors), tooltip=f"{day}: {format_money(spend)}"))
        
        # Habit Intensity Row
        habit_row = ft.Row(spacing=8)
        habit_colors = [empty_color, ft.Colors.GREEN_100, ft.Colors.GREEN_300, ft.Colors.GREEN_700]
        for i in range(6, -1, -1):
            day = (today_dt - dt.timedelta(days=i)).strftime("%Y-%m-%d")
            w_done = daily_habit_w.get(day, 0)
            ratio = w_done / total_habit_w if total_habit_w > 0 else 0
            habit_row.controls.append(ft.Container(width=40, height=40, border_radius=4, bgcolor=get_color_intensity(ratio, habit_colors), tooltip=f"{day}: Score {w_done}/{total_habit_w}"))

        content_container.controls.append(ft.Text("Finance Intensity (Spend vs Weekly Quota):", size=12))
        content_container.controls.append(finance_row)
        content_container.controls.append(ft.Text("Habits Consistency (Weighted Completion):", size=12))
        content_container.controls.append(habit_row)
        content_container.controls.append(ft.Divider())

        # --- Quote Collection ---
        content_container.controls.append(ft.Text("✒️ Thêm Quote mới", size=20, weight=ft.FontWeight.BOLD))
        q_text = ft.TextField(label="Câu nói tâm đắc", multiline=True)
        q_author = ft.TextField(label="Tác giả")
        def save_q(e):
            if q_text.value:
                db.add_quote(q_text.value, q_author.value)
                render_review()
                page.update()
        content_container.controls.extend([q_text, q_author, ft.ElevatedButton("Lưu Quote", on_click=save_q)])
        content_container.controls.append(ft.Divider())
        content_container.controls.append(ft.Text("📚 Bộ sưu tập Quote", size=18, weight=ft.FontWeight.BOLD))
        for q in quotes_data:
            def del_q(e, qid=q['id']):
                db.delete_quote(qid)
                render_review()
                page.update()
            content_container.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Column([ft.Text(f"\"{q['text']}\"", italic=True), ft.Text(f"— {q['author']}", size=12, color=ft.Colors.GREY_600)], expand=True),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_300, on_click=del_q)
                    ]),
                    padding=10, border=ft.Border.all(1, ft.Colors.GREY_200), border_radius=5
                )
            )

    def render_settings():
        content_container.controls.clear()
        content_container.controls.append(ft.Text("⚙️ Cài đặt hệ thống", size=20, weight=ft.FontWeight.BOLD))
        theme_dd = ft.Dropdown(label="Giao diện", options=[ft.dropdown.Option("light", "Sáng ☀️"), ft.dropdown.Option("dark", "Tối 🌙")], value=settings['theme'])
        curr_dd = ft.Dropdown(label="Đơn vị tiền tệ", options=[ft.dropdown.Option("VNĐ"), ft.dropdown.Option("kVNĐ"), ft.dropdown.Option("USD")], value=settings['currency'])
        budget_input = ft.TextField(label="Ngân sách mục tiêu (VNĐ)", value=str(int(settings['monthly_budget'])), text_align=ft.TextAlign.RIGHT)
        def save_settings(e):
            db.update_settings(float(budget_input.value), theme_dd.value, curr_dd.value)
            refresh_settings()
            render_settings()
            page.update()
            page.snack_bar = ft.SnackBar(ft.Text("Đã lưu cài đặt!"))
            page.snack_bar.open = True
            page.update()
        content_container.controls.extend([theme_dd, curr_dd, budget_input, ft.ElevatedButton("Lưu tất cả", icon=ft.Icons.SAVE, on_click=save_settings)])

    # Initial UI Build
    page.navigation_bar = nav_bar
    page.add(content_container)
    render_habits()

ft.run(main)