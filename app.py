import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import random
from supabase import create_client

# ==========================================
# 1. KẾT NỐI DATABASE
# ==========================================
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()
USER_ID = "c1b89663-eb6a-462c-b55f-9a12dc10596b"

st.set_page_config(page_title="Atomic Finance Pro", layout="wide")
st.title("🎯 Kỷ luật & Tài chính")

# Lấy dữ liệu quotes và hiển thị ngẫu nhiên 1 câu
quotes_data = supabase.table("quotes").select("*").eq("user_id", USER_ID).execute().data
if quotes_data:
    q = random.choice(quotes_data)
    author_text = f" — *{q['author']}*" if q['author'] else ""
    st.info(f"💡 **\"{q['text']}\"**{author_text}")
else:
    st.info("💡 Trạm Quotes đang trống. Hãy thêm câu nói tâm đắc của ông vào Tab bên dưới nhé!")

tab_habit, tab_finance, tab_quote = st.tabs(["✅ Quản lý Thói quen", "💰 Quản lý Tài chính", "💬 Trạm Quotes"])

# ==========================================
# TAB 1: HABIT MANAGER
# ==========================================
with tab_habit:
    col_list, col_chart = st.columns([1, 1.2])
    
    with col_list:
        st.subheader("Lộ trình hôm nay")
        with st.expander("➕ Thêm thói quen mới"):
            with st.form("new_habit", clear_on_submit=True):
                name = st.text_input("Tên thói quen (VD: Đọc sách 30p)")
                if st.form_submit_button("Lưu thói quen") and name:
                    supabase.table("habits").insert({"user_id": USER_ID, "name": name, "incentive_amount": 0}).execute()
                    st.rerun()

        habits = supabase.table("habits").select("*").eq("user_id", USER_ID).execute().data
        today_str = datetime.now().strftime("%Y-%m-%d")
        logs_today = supabase.table("habit_logs").select("habit_id").eq("log_date", today_str).execute().data
        done_ids = [log['habit_id'] for log in logs_today] if logs_today else []

        if not habits:
            st.write("Chưa có thói quen nào.")
        else:
            for h in habits:
                c1, c2 = st.columns([5, 1])
                is_done = h['id'] in done_ids
                with c1:
                    checked = st.checkbox(h['name'], value=is_done, key=f"chk_{h['id']}")
                    if checked and not is_done:
                        supabase.table("habit_logs").insert({"habit_id": h['id'], "status": "done"}).execute()
                        st.rerun()
                    elif not checked and is_done:
                        supabase.table("habit_logs").delete().eq("habit_id", h['id']).eq("log_date", today_str).execute()
                        st.rerun()
                with c2:
                    if st.button("🗑️", key=f"del_{h['id']}"):
                        supabase.table("habits").delete().eq("id", h['id']).execute()
                        st.rerun()

    with col_chart:
        st.subheader("📊 Thống kê Kỷ luật")
        all_logs = supabase.table("habit_logs").select("log_date, habits(name)").execute().data
        if all_logs:
            df_logs = pd.DataFrame([{"Ngày": log['log_date'], "Thói quen": log['habits']['name']} for log in all_logs])
            
            freq_df = df_logs['Thói quen'].value_counts().reset_index()
            freq_df.columns = ['Thói quen', 'Số lần']
            fig_bar = px.bar(freq_df, x='Số lần', y='Thói quen', orientation='h', color='Thói quen')
            st.plotly_chart(fig_bar, use_container_width=True)

            trend_df = df_logs.groupby('Ngày').size().reset_index(name='Số thói quen')
            trend_df = trend_df.sort_values('Ngày')
            fig_line = px.line(trend_df, x='Ngày', y='Số thói quen', markers=True)
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.write("Chưa có dữ liệu.")

# ==========================================
# TAB 2: FINANCE MANAGER
# ==========================================
with tab_finance:
    accounts = supabase.table("accounts").select("*").eq("user_id", USER_ID).execute().data
    
    # --- THANH NGÂN SÁCH (BUDGET BAR) ---
# --- THANH NGÂN SÁCH (BUDGET BAR) ---
    st.write("### 🎯 Ngân sách tháng này")
    
    # Lấy ngân sách từ settings
    settings = supabase.table("user_settings").select("monthly_budget").eq("user_id", USER_ID).execute().data
    budget = float(settings[0]['monthly_budget']) if settings else 3000000.0
    
    # Tính tổng chi tiêu tháng hiện tại
    current_month = datetime.now().strftime("%Y-%m-01")
    expenses_this_month = supabase.table("transactions").select("amount")\
        .eq("user_id", USER_ID).eq("transaction_type", "expense").gte("created_at", current_month).execute().data
    
    total_spent = sum([e['amount'] for e in expenses_this_month]) if expenses_this_month else 0
    # Tính tổng chi tiêu tháng hiện tại (ĐÃ LOẠI TRỪ CHUYỂN VÍ)
    current_month = datetime.now().strftime("%Y-%m-01")
    expenses_this_month = supabase.table("transactions").select("amount")\
        .eq("user_id", USER_ID)\
        .eq("transaction_type", "expense")\
        .neq("category", "Chuyển đi")\
        .gte("created_at", current_month)\
        .execute().data
    # Vẽ thanh tiến trình (Tránh lỗi chia cho 0 nếu ông set ngân sách = 0)
    progress_pct = min(total_spent / budget, 1.0) if budget > 0 else 1.0
    
    c_bud1, c_bud2 = st.columns([3, 1])
    c_bud1.progress(progress_pct, text=f"Đã tiêu: {total_spent:,.0f} / {budget:,.0f} VNĐ")
    
    if progress_pct < 0.5:
        c_bud2.success("An toàn! 🟢")
    elif progress_pct < 0.8:
        c_bud2.warning("Sắp hết rồi! 🟡")
    else:
        c_bud2.error("Báo động đỏ! 🔴")

    # TÍNH NĂNG MỚI: Chỉnh sửa mục tiêu
    with st.expander("⚙️ Điều chỉnh ngân sách mục tiêu"):
        with st.form("budget_form", clear_on_submit=False):
            col_b1, col_b2 = st.columns([3, 1])
            new_budget = col_b1.number_input("Ngân sách mong muốn (VNĐ)", min_value=0, step=100000, value=int(budget))
            if col_b2.form_submit_button("Cập nhật"):
                # Cập nhật thẳng vào Database
                supabase.table("user_settings").update({"monthly_budget": new_budget}).eq("user_id", USER_ID).execute()
                st.rerun()

    st.divider()
    
    col_input, col_report = st.columns([1, 1])
    
    with col_input:
        st.write("### 📝 Ghi sổ nhanh")
        if not accounts:
            st.warning("Vui lòng tạo ví bên cạnh trước!")
        else:
            with st.form("trans_form", clear_on_submit=True):
                # Thêm option Chuyển ví
                t_type = st.radio("Loại giao dịch", ["Chi tiêu (-)", "Thu nhập (+)", "Chuyển ví (↔)"], horizontal=True)
                
                # Giao diện thay đổi động dựa trên loại giao dịch
                if t_type == "Chuyển ví (↔)":
                    c_from, c_to = st.columns(2)
                    acc_from = c_from.selectbox("Từ ví", options=[a['name'] for a in accounts], key="from")
                    acc_to = c_to.selectbox("Sang ví", options=[a['name'] for a in accounts], key="to")
                    category = "Chuyển tiền nội bộ"
                else:
                    acc_choice = st.selectbox("Chọn ví", options=[a['name'] for a in accounts])
                    cats = ["Ăn uống", "Học tập", "Đi lại", "Giải trí", "Khác"] if t_type == "Chi tiêu (-)" else ["Tiêu vặt", "Làm thêm", "Khác"]
                    category = st.selectbox("Phân loại", options=cats)
                
                amount = st.number_input("Số tiền", min_value=0, step=1000)
                note = st.text_input("Ghi chú")
                
                if st.form_submit_button("Lưu giao dịch") and amount > 0:
                    if t_type == "Chuyển ví (↔)":
                        if acc_from == acc_to:
                            st.error("Trùng ví rồi ông ơi!")
                        else:
                            id_from = next(a['id'] for a in accounts if a['name'] == acc_from)
                            id_to = next(a['id'] for a in accounts if a['name'] == acc_to)
                            bal_from = float(next(a['balance'] for a in accounts if a['name'] == acc_from))
                            bal_to = float(next(a['balance'] for a in accounts if a['name'] == acc_to))
                            
                            # Cập nhật 2 ví
                            supabase.table("accounts").update({"balance": bal_from - amount}).eq("id", id_from).execute()
                            supabase.table("accounts").update({"balance": bal_to + amount}).eq("id", id_to).execute()
                            # Ghi log
                            supabase.table("transactions").insert([
                                {"user_id": USER_ID, "account_id": id_from, "amount": amount, "transaction_type": "expense", "category": "Chuyển đi", "description": f"Chuyển sang {acc_to}"},
                                {"user_id": USER_ID, "account_id": id_to, "amount": amount, "transaction_type": "income", "category": "Nhận tiền", "description": f"Nhận từ {acc_from}"}
                            ]).execute()
                            st.rerun()
                    else:
                        selected_acc = next(a for a in accounts if a['name'] == acc_choice)
                        final_amt = -amount if t_type == "Chi tiêu (-)" else amount
                        supabase.table("accounts").update({"balance": float(selected_acc['balance']) + final_amt}).eq("id", selected_acc['id']).execute()
                        supabase.table("transactions").insert({
                            "user_id": USER_ID, "account_id": selected_acc['id'], 
                            "amount": amount, "transaction_type": "expense" if t_type == "Chi tiêu (-)" else "income",
                            "category": category, "description": note
                        }).execute()
                        st.rerun()

    with col_report:
        st.write("### 🏦 Quản lý Ví tiền")
        with st.expander("🆕 Tạo/Chỉnh sửa ví", expanded=not bool(accounts)):
            with st.form("new_wallet", clear_on_submit=True):
                new_acc_name = st.text_input("Tên ví (VD: Tiền mặt, BIDV)")
                init_bal = st.number_input("Số dư", min_value=0, step=1000)
                if st.form_submit_button("Tạo/Cập nhật ví") and new_acc_name:
                    # Logic update nếu trùng tên, tạo mới nếu chưa có
                    existing = next((a for a in accounts if a['name'] == new_acc_name), None)
                    if existing:
                        supabase.table("accounts").update({"balance": init_bal}).eq("id", existing['id']).execute()
                    else:
                        supabase.table("accounts").insert({"user_id": USER_ID, "name": new_acc_name, "balance": init_bal}).execute()
                    st.rerun()
                    
        if accounts:
            for acc in accounts:
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{acc['name']}**: {acc['balance']:,} VNĐ")
                if c2.button("Xóa", key=f"del_acc_{acc['id']}"):
                    supabase.table("accounts").delete().eq("id", acc['id']).execute()
                    st.rerun()

# ==========================================
# TAB 3: QUOTES MANAGER
# ==========================================
with tab_quote:
    col_q1, col_q2 = st.columns([1, 1])
    
    with col_q1:
        st.subheader("✒️ Thêm Quote mới")
        with st.form("new_quote", clear_on_submit=True):
            text = st.text_area("Câu nói tâm đắc")
            author = st.text_input("Tác giả (không bắt buộc)")
            if st.form_submit_button("Lưu lại"):
                if text:
                    supabase.table("quotes").insert({"user_id": USER_ID, "text": text, "author": author}).execute()
                    st.rerun()
                else:
                    st.warning("Ghi nội dung vào đã chứ!")

    with col_q2:
        st.subheader("📚 Bộ sưu tập của ông")
        if quotes_data:
            for q in quotes_data:
                with st.container(border=True):
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(f"> {q['text']}")
                        if q['author']:
                            st.caption(f"— {q['author']}")
                    with c2:
                        if st.button("🗑️", key=f"del_q_{q['id']}"):
                            supabase.table("quotes").delete().eq("id", q['id']).execute()
                            st.rerun()
        else:
            st.write("Chưa lưu câu nào.")