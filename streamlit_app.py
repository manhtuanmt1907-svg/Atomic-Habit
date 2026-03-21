import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from datetime import datetime

# --- Supabase Configuration ---
SUPABASE_URL = "https://molaytmoymgthduukuit.supabase.co"
SUPABASE_KEY = "sb_publishable_88HQlQ3M-0G5p_Yh6894qQ_VFAARnLp"

class SupabaseManager:
    """Manager class for handling all Supabase interactions."""
    
    @staticmethod
    @st.cache_resource
    def get_client() -> Client:
        try:
            return create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            st.error(f"Lỗi kết nối Supabase: {e}")
            return None

    @staticmethod
    def get_total_balance(client: Client) -> float:
        try:
            res = client.table("transactions").select("amount").execute()
            return sum(item['amount'] for item in res.data) if res.data else 0
        except Exception:
            return 0

    @staticmethod
    def get_habits(client: Client) -> list:
        try:
            res = client.table("habits").select("*").execute()
            return res.data if res.data else []
        except Exception:
            return []

    @staticmethod
    def add_habit(client: Client, name: str, incentive: float) -> bool:
        try:
            client.table("habits").insert({"name": name, "incentive_amount": incentive}).execute()
            return True
        except Exception:
            return False

    @staticmethod
    def log_habit(client: Client, habit_id: int, incentive: float) -> bool:
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            # 1. Log completion
            client.table("habit_logs").insert({"habit_id": habit_id, "log_date": today}).execute()
            # 2. Add transaction as reward
            client.table("transactions").insert({
                "amount": incentive, 
                "transaction_type": "income", 
                "category": "Habit Rewarded",
                "description": f"Dopamine Hit từ Habit ID: {habit_id}"
            }).execute()
            return True
        except Exception:
            return False

    @staticmethod
    def get_cumulative_revenue(client: Client) -> pd.DataFrame:
        try:
            # Join habit_logs with habits to get incentive_amount
            res = client.table("habit_logs").select("log_date, habits(incentive_amount)").execute()
            if not res or not res.data:
                return pd.DataFrame()
            
            data = []
            for item in res.data:
                # PostgREST join returns nested dict for 'habits'
                incentive = item.get('habits', {}).get('incentive_amount', 0)
                data.append({
                    "Date": item['log_date'],
                    "Revenue": incentive
                })
            
            df = pd.DataFrame(data)
            df['Date'] = pd.to_datetime(df['Date'])
            # Aggregate by date
            daily_rev = df.groupby('Date')['Revenue'].sum().reset_index()
            daily_rev = daily_rev.sort_values('Date')
            # Calculate cumulative sum
            daily_rev['Cumulative'] = daily_rev['Revenue'].cumsum()
            return daily_rev
        except Exception:
            return pd.DataFrame()

class HabitApp:
    """The main Application class using OOP approach."""
    
    def __init__(self):
        self.manager = SupabaseManager
        self.client = self.manager.get_client()

    def render_sidebar(self):
        with st.sidebar:
            st.title("💰 Finance Dashboard")
            balance = self.manager.get_total_balance(self.client)
            st.metric("Số dư hiện tại", f"{balance:,.0f} VNĐ", delta_color="normal")
            
            st.divider()
            st.subheader("🎯 Identity Goal")
            habits = self.manager.get_habits(self.client)
            if habits:
                # Display the most recent or first habit as the identity goal
                goal = habits[-1]['name']
                st.info(f"Hôm nay tôi là: **{goal}**")
            else:
                st.caption("Hãy thiết lập thói quen để định hình bản thân.")

    def render_habit_tracker(self):
        st.header("🔥 Habit Tracker")
        habits = self.manager.get_habits(self.client)
        
        if not habits:
            st.info("Chưa có thói quen nào. Hãy thêm ở form phía dưới!")
            return

        cols = st.columns(min(len(habits), 3))
        for i, h in enumerate(habits):
            with cols[i % 3]:
                with st.container(border=True):
                    st.subheader(h['name'])
                    st.write(f"Tiền thưởng: `{h['incentive_amount']:,.0f}` VNĐ")
                    if st.button("Đã hoàn thành ✅", key=f"btn_{h['id']}", use_container_width=True):
                        if self.manager.log_habit(self.client, h['id'], h['incentive_amount']):
                            st.balloons()
                            st.success("Tuyệt vời! +Dopamine")
                            st.rerun()

    def render_finance_stats(self):
        st.header("📈 Thống kê Tài chính")
        df = self.manager.get_cumulative_revenue(self.client)
        
        if not df.empty:
            fig = px.bar(
                df, x='Date', y='Cumulative', 
                title="Doanh thu tích lũy từ Thói quen",
                labels={'Cumulative': 'Tổng tiền (VNĐ)', 'Date': 'Ngày'},
                template="plotly_white",
                color_discrete_sequence=['#2ecc71']
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Chưa có dữ liệu giao dịch để hiển thị biểu đồ.")

    def render_add_habit_form(self):
        st.divider()
        with st.expander("➕ Thêm thói quen mới", expanded=False):
            with st.form("new_habit", clear_on_submit=True):
                name = st.text_input("Tên thói quen (VD: Đọc sách 30p)")
                amount = st.number_input("Tiền thưởng (VNĐ)", min_value=0, step=1000, value=10000)
                if st.form_submit_button("Lưu thói quen"):
                    if name:
                        if self.manager.add_habit(self.client, name, amount):
                            st.success("Đã thêm thành công!")
                            st.rerun()
                    else:
                        st.error("Tên thói quen không được để trống.")

    def run(self):
        st.set_page_config(page_title="Finance & Habits", page_icon="🎯", layout="wide")
        
        if self.client is None:
            st.critical("Không thể khởi tạo ứng dụng do lỗi kết nối.")
            return

        self.render_sidebar()
        
        tab_tracker, tab_finance = st.tabs(["🚀 Habit Tracker", "📊 Finance Stats"])
        
        with tab_tracker:
            self.render_habit_tracker()
            self.render_add_habit_form()
            
        with tab_finance:
            self.render_finance_stats()

if __name__ == "__main__":
    app = HabitApp()
    app.run()
