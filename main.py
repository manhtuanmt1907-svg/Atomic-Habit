import flet as ft
import database as db
from datetime import datetime
import random
import flet_audio as fta
import shutil
import os

import asyncio

QUOTES_LIST = [
    "Đừng đếm những gì bạn đã mất, hãy quý trọng những gì bạn đang có.",
    "Mọi thành tựu vĩ đại đều cần thời gian. Cứ từ từ mà tiến!",
    "Kỷ luật là cầu nối giữa mục tiêu và thành tựu.",
    "Chỉ có hành động mới xua tan được sự lo lắng.",
    "Tiến thêm một bước nhỏ mỗi ngày còn hơn đứng im mãi mãi.",
]

HUST_QUOTES = [
    "Học tài thi phận, học kỹ thuật thì thi... lại! 😆",
    "Chào mừng bạn đến với Bách Khoa, nơi mà điểm D là một niềm tự hào! 🤖",
    "Sóng gió phủ đời trai, tương lai nhờ code chạy được. 👨‍💻",
    "Nếu lỗi cứ sinh ra, hãy coi đó là một tính năng đi ông ơi! 🚀",
    "Bình tĩnh sống! Bug chưa fix thì đêm nay không ngủ. 🦉",
]

I_CHING_HEXAGRAMS = [
    {
        "name": "Truân (䷂)",
        "symbol": "䷂",
        "advice": "Quẻ Truân: Vạn sự khởi đầu nan. Code hôm nay có thể nhiều bug, hãy kiên nhẫn nháp ra giấy trước khi gõ.",
    },
    {
        "name": "Thái (䷀)",
        "symbol": "䷀",
        "advice": "Quẻ Thái: Hanh thông đại lợi. Đây là ngày tốt để học kiến thức mới, mọi thứ sẽ suôn sẻ!",
    },
    {
        "name": "Ký Tế (䷾)",
        "symbol": "䷾",
        "advice": "Quẻ Ký Tế: Hoàn thành tốt đẹp. Hãy tập trung hoàn thiện bài tập và review lại code cũ.",
    },
    {
        "name": "Bĩ (䷁)",
        "symbol": "䷁",
        "advice": "Quẻ Bĩ: Bế tắc cần cẩn trọng. Đừng ép bản thân quá, hãy nghỉ ngơi rồi quay lại với đầu óc tỉnh táo.",
    },
    {
        "name": "Phục (䷇)",
        "symbol": "䷇",
        "advice": "Quẻ Phục: Bắt đầu lại tuyệt vời. Ngày phù hợp để reset thói quen và lên kế hoạch mới.",
    },
]


class FocusManager:
    def __init__(self, page: ft.Page, get_settings_fn, audio_focus, audio_break):
        self.page = page
        self.is_mobile = self.page.platform in [
            ft.PagePlatform.ANDROID,
            ft.PagePlatform.IOS,
        ]
        self.get_settings = get_settings_fn
        self.audio_focus = audio_focus
        self.audio_break = audio_break
        self.is_muted = False
        # --- XP/Level from DB ---

        self.running = False
        self._task_running = False
        self.mode = "work"
        self.time_left = 30 * 60
        self.total_time = 30 * 60

        # --- XP/Level from DB ---
        try:
            self.current_xp, self.current_level = db.get_xp_level()
        except:
            self.current_xp, self.current_level = 0, 1

        self.health_quotes = [
            "Quy tắc 20-20-20: Nhìn xa 20 feet (6m) trong 20 giây.",
            "Xoay nhẹ cổ tay và khớp vai để tránh bị bó cơ.",
            "Uống một ngụm nước, não bộ cần H2O để xử lý Giải tích!",
            "Nháy mắt liên tục vài lần để làm ẩm giác mạc nhé.",
            "Hít sâu 3 nhịp, đẩy hết CO2 ra ngoài cho tỉnh táo.",
        ]

        import random

        self.overlay_emoji = ft.Text(db.get_species_emoji(self.current_level), size=100)
        self.main_emoji = ft.Text(db.get_species_emoji(self.current_level), size=100)
        self.overlay_timer_text = ft.Text(
            "30:00", size=70, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE
        )
        self.overlay_status = ft.Text(
            "Đang tập trung...", size=20, color=ft.Colors.WHITE
        )
        self.health_text = ft.Text(
            random.choice(self.health_quotes),
            italic=True,
            size=14,
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE),
        )
        self.close_btn = ft.IconButton(
            icon=ft.Icons.CLOSE,
            on_click=self.close_overlay,
            icon_size=30,
            icon_color=ft.Colors.WHITE,
        )

        self.pomodoro_overlay = ft.Container(
            expand=True,
            visible=False,
            bgcolor=ft.Colors.with_opacity(0.98, ft.Colors.BLACK),
            padding=30,
            content=ft.Column(
                [
                    ft.Row([self.close_btn], alignment=ft.MainAxisAlignment.END),
                    ft.Column(
                        [
                            self.overlay_emoji,
                            self.overlay_timer_text,
                            self.overlay_status,
                            ft.Container(height=30),
                            ft.Card(
                                bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
                                content=ft.Container(
                                    padding=20, content=self.health_text
                                ),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        expand=True,
                    ),
                ]
            ),
        )
        self.page.overlay.append(self.pomodoro_overlay)

        self.pomo_slider = ft.Slider(
            min=30,
            max=150,
            divisions=2,
            value=30,
            label="{value} phút",
            on_change=self.on_slider_change,
        )
        self.pomo_display = ft.Text(
            "30:00", size=40, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE
        )
        self.pomo_progress = ft.ProgressBar(
            value=0,
            color=ft.Colors.PURPLE_400,
            bgcolor=ft.Colors.PURPLE_50,
            height=8,
            border_radius=4,
        )

        self.play_btn = ft.IconButton(
            icon=ft.Icons.PLAY_ARROW,
            icon_size=40,
            icon_color="purple700",
            on_click=self.toggle_timer,
        )

        # ==========================================
        # 🎨 STUDYGRAM LABS - BK ENGINEERING STYLE
        # ==========================================
        C_BG = "#1E1B4B"
        C_PRI = "#C4B5FD"
        C_SEC = "#8BA9FA"
        C_TER = "#F472B6"

        # Fetch XP/Level
        try:
            current_xp, current_level = db.get_xp_level()
            species_emoji = db.get_species_emoji(current_level)
        except:
            current_xp, current_level, species_emoji = 0, 1, "🌱"

        # Header
        header = ft.Text(
            "STUDYGRAM LABS",
            size=22,
            weight="bold",
            color=ft.Colors.WHITE,
            text_align=ft.TextAlign.CENTER,
        )

        # Timer display setup
        self.pomo_display.size = 65
        self.pomo_display.color = ft.Colors.WHITE
        self.pomo_display.weight = "bold"

        # ProgressRing (circular timer)
        self.pomo_progress = ft.ProgressRing(
            width=280,
            height=280,
            stroke_width=8,
            color=C_PRI,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            value=1.0,
        )

        timer_circle = ft.Container(
            alignment=ft.alignment.Alignment(0, 0),
            padding=ft.Padding(0, 20, 0, 20),
            content=ft.Stack(
                [
                    ft.Container(
                        alignment=ft.alignment.Alignment(0, 0),
                        content=self.pomo_progress,
                    ),
                    ft.Container(
                        width=280,
                        height=280,
                        alignment=ft.alignment.Alignment(0, 0),
                        content=ft.Column(
                            [
                                self.main_emoji,
                                self.pomo_display,
                                ft.Text(
                                    "F O C U S",
                                    size=12,
                                    color=ft.Colors.with_opacity(0.6, ft.Colors.WHITE),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ),
                ]
            ),
        )

        # Play/Reset controls
        self.play_btn.icon_size = 35
        self.play_btn.icon_color = C_BG
        play_btn_container = ft.Container(
            content=self.play_btn,
            bgcolor=C_SEC,
            shape=ft.BoxShape.CIRCLE,
            padding=10,
            shadow=ft.BoxShadow(
                spread_radius=1, blur_radius=20, color=C_SEC, offset=ft.Offset(0, 0)
            ),
        )
        self.reset_btn = ft.IconButton(
            icon=ft.Icons.RESTART_ALT,
            icon_size=28,
            icon_color=ft.Colors.with_opacity(0.5, ft.Colors.WHITE),
            on_click=self.close_overlay,
        )

        controls_row = ft.Row(
            [self.reset_btn, play_btn_container],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=30,
        )

        # Tree Link XP displays
        self.tree_emoji_text = ft.Text(species_emoji, size=22)
        self.level_text = ft.Text(
            f"Level {current_level}",
            size=13,
            weight="bold",
            color=ft.Colors.WHITE,
        )
        self.xp_text = ft.Text(
            f"{current_xp}/500 XP",
            size=10,
            color=ft.Colors.with_opacity(0.6, ft.Colors.WHITE),
        )

        self.tree_xp_bar = ft.ProgressBar(
            value=current_xp / 500,
            color=C_TER,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            height=5,
            border_radius=3,
        )
        tree_link_row = ft.Container(
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            border_radius=15,
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
            content=ft.Row(
                [
                    self.tree_emoji_text,
                    ft.Column(
                        [
                            self.level_text,
                            self.tree_xp_bar,
                            self.xp_text,
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=10,
            ),
        )

        # Final assembly
        self.pomodoro_card = ft.Container(
            expand=True,
            bgcolor=C_BG,
            padding=20,
            content=ft.Column(
                [
                    header,
                    timer_circle,
                    controls_row,
                    self.pomo_slider,
                    tree_link_row,
                ],
                spacing=10,
                scroll=ft.ScrollMode.HIDDEN,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def on_slider_change(self, e):
        if not self.running:
            self.update_ui()

    def update_ui(self):
        settings = self.get_settings()
        if not self.running:
            self.pomo_slider.visible = True
            self.pomo_progress.value = 0
            if settings.get("pomodoro_show_time", 1) == 1:
                self.pomo_display.value = f"{int(self.pomo_slider.value)}:00"
            else:
                try:
                    _xp, _lvl = db.get_xp_level()
                    self.pomo_display.value = db.get_species_emoji(_lvl)
                except:
                    self.pomo_display.value = "🌱"
            self.overlay_timer_text.value = f"{int(self.pomo_slider.value)}:00"
        else:
            self.pomo_slider.visible = False
            ratio = (
                1.0 - (self.time_left / self.total_time) if self.total_time > 0 else 1
            )
            safe_time = max(0, self.time_left)
            if settings.get("pomodoro_show_time", 1) == 1:
                mins = safe_time // 60
                secs = safe_time % 60
                self.pomo_display.value = f"{mins:02d}:{secs:02d}"
            else:
                try:
                    _xp, _lvl = db.get_xp_level()
                    self.pomo_display.value = db.get_species_emoji(_lvl)
                except:
                    self.pomo_display.value = "🌱"
            self.pomo_progress.value = ratio

        self.pomo_display.color = (
            ft.Colors.WHITE
            if self.mode == "work"
            else ft.Colors.with_opacity(0.7, ft.Colors.WHITE)
        )
        self.pomo_progress.color = (
            ft.Colors.PURPLE_400 if self.mode == "work" else ft.Colors.PURPLE_200
        )

        try:
            self.pomo_display.update()
            self.pomo_progress.update()
            self.pomo_slider.update()
        except:
            pass

    async def _timer_task(self):
        import asyncio

        # Refresh mute status from DB before playing (off-thread)
        try:
            snd = await asyncio.to_thread(db.get_sound_settings)
            self.is_muted = bool(snd.get("is_muted", 0))
        except Exception:
            pass

        # [CHỐNG DÍNH LUỒNG 4s]
        if getattr(self, "_task_running", False):
            return
        self._task_running = True

        try:
            while self.running and self.time_left > 0:
                await asyncio.sleep(1)
                if not self.running:
                    break

                self.time_left -= 1

                # --- ÉP UPDATE GIAO DIỆN (Tất cả đồng hồ) ---
                mins, secs = divmod(max(0, self.time_left), 60)
                time_str = f"{mins:02d}:{secs:02d}"

                self.pomo_display.value = time_str
                self.overlay_timer_text.value = time_str
                if self.total_time > 0:
                    self.pomo_progress.value = 1.0 - (self.time_left / self.total_time)

                # UPDATE TỪNG CÁI MỘT THAY VÌ UPDATE CẢ PAGE
                self.pomo_display.update()
                self.overlay_timer_text.update()
                if self.total_time > 0:
                    self.pomo_progress.update()

                # --- XỬ LÝ KHI ĐỒNG HỒ VỀ 00:00 ---
                if self.time_left <= 0:
                    if self.mode == "work":
                        # 🌳 CỘNG XP TREE LINK (DB-driven, off-thread)
                        earned_xp = max(10, int(self.total_time / 60) * 10)

                        old_level = self.current_level
                        self.current_xp, self.current_level = await asyncio.to_thread(
                            db.add_xp, earned_xp
                        )

                        # Check Level Up
                        if self.current_level > old_level:
                            try:
                                new_emoji = await asyncio.to_thread(
                                    db.get_species_emoji, self.current_level
                                )
                                self.page.snack_bar = ft.SnackBar(
                                    ft.Text(
                                        f"🎉 LÊN CẤP {self.current_level}! Mở khóa: {new_emoji}!",
                                        color=ft.Colors.WHITE,
                                        weight="bold",
                                    ),
                                    bgcolor=ft.Colors.PINK_600,
                                )
                                self.page.snack_bar.open = True
                            except Exception:
                                pass

                        # Tiến hóa sinh vật from DB species map (off-thread)
                        new_emoji = await asyncio.to_thread(
                            db.get_species_emoji, self.current_level
                        )
                        self.overlay_emoji.value = new_emoji
                        self.main_emoji.value = new_emoji

                        # Update XP bar
                        xp_needed = self.current_level * 500
                        try:
                            self.tree_xp_bar.value = (
                                min(1.0, self.current_xp / xp_needed)
                                if xp_needed > 0
                                else 0
                            )
                        except Exception:
                            pass

                        # Chuyển sang giờ nghỉ
                        self.mode = "rest"
                        self.time_left = max(1, int(self.total_time / 5))
                        self.total_time = self.time_left

                        # Play break sound
                        try:
                            if self.audio_break and not self.is_muted:
                                self.audio_break.play()
                        except Exception:
                            pass

                        try:
                            self.page.launch_url("vibrate:500")
                        except Exception:
                            pass

                        try:
                            self.page.snack_bar = ft.SnackBar(
                                ft.Text(
                                    f"Đã cộng +{earned_xp} XP! Nghỉ ngơi thôi. 🌳",
                                    color=ft.Colors.WHITE,
                                ),
                                bgcolor=ft.Colors.GREEN_700,
                            )
                            self.page.snack_bar.open = True
                        except Exception:
                            pass
                        self.page.update()
                    else:
                        # Hết giờ nghỉ -> Quay lại giờ làm
                        self.running = False
                        self.mode = "work"
                        self.time_left = int(self.pomo_slider.value) * 60
                        self.total_time = self.time_left
                        self.play_btn.icon = ft.Icons.PLAY_ARROW

                        try:
                            self.page.snack_bar = ft.SnackBar(
                                ft.Text(
                                    "Hết giờ nghỉ! Quay lại làm việc nào. 🚀",
                                    color=ft.Colors.WHITE,
                                ),
                                bgcolor=ft.Colors.BLUE_700,
                            )
                            self.page.snack_bar.open = True
                        except Exception:
                            pass
                        self.page.update()
                        break
        finally:
            self._task_running = False

    async def update_quotes_task(self):
        import asyncio, random

        while self.running:
            await asyncio.sleep(300)
            if not self.running:
                break
            # --- FIXED QUOTES BUG ---
            self.health_text.value = random.choice(self.health_quotes)
            try:
                self.health_text.update()
            except:
                pass

    async def apply_penalty(self):
        """KỶ LUẬT SẮT: Penalty when window loses focus during work."""
        self.running = False
        self.play_btn.icon = ft.Icons.PLAY_ARROW
        import asyncio

        self.current_xp, self.current_level = await asyncio.to_thread(db.deduct_xp, 50)
        # Change emoji to dead plant
        self.overlay_emoji.value = "🥀"
        self.main_emoji.value = "🥀"

        # Update XP bar
        xp_needed = self.current_level * 500
        try:
            self.tree_xp_bar.value = (
                min(1.0, self.current_xp / xp_needed) if xp_needed > 0 else 0
            )
        except:
            pass

        # Show penalty SnackBar
        try:
            self.page.snack_bar = ft.SnackBar(
                ft.Text(
                    "KỶ LUẬT SẮT: Bạn đã xao nhãng! Cây héo và bị trừ 50 XP! 🥀",
                    color=ft.Colors.WHITE,
                    weight="bold",
                ),
                bgcolor=ft.Colors.RED_700,
            )
            self.page.snack_bar.open = True
        except:
            pass

        self.update_ui()
        self.page.update()

    def toggle_timer(self, e):
        # Refresh mute status before playing
        try:
            snd = db.get_sound_settings()
            self.is_muted = bool(snd.get("is_muted", 0))
        except:
            pass
        import random

        if not self.running:
            self.running = True
            self.mode = "work"
            self.total_time = int(self.pomo_slider.value) * 60
            self.time_left = self.total_time
            self.play_btn.icon = ft.Icons.STOP

            # Play focus start sound
            if self.audio_focus and not self.is_muted:
                self.audio_focus.play()

            self.health_text.value = random.choice(self.health_quotes)
            self.pomodoro_overlay.visible = True
            self.page.update()

            self.page.run_task(self._timer_task)
            self.page.run_task(self.update_quotes_task)
        else:
            self.running = False
            self.play_btn.icon = ft.Icons.PLAY_ARROW
            self.time_left = int(self.pomo_slider.value) * 60
            self.total_time = self.time_left

        self.play_btn.update()
        self.update_ui()

    def close_overlay(self, e):
        self.running = False
        self.time_left = int(self.pomo_slider.value) * 60
        self.total_time = self.time_left
        self.play_btn.icon = ft.Icons.PLAY_ARROW
        self.pomodoro_overlay.visible = False
        self.update_ui()
        self.page.update()

    def reload_sounds(self):
        """Reload sound settings from DB and update fta.Audio sources."""
        try:
            snd_settings = db.get_sound_settings()
            self.is_muted = bool(snd_settings.get("is_muted", 0))
            focus_path = snd_settings.get("focus_start_path", "sounds/focus_start.mp3")
            break_path = snd_settings.get("break_start_path", "sounds/break_start.mp3")
            if self.audio_focus:
                self.audio_focus.src = focus_path
            if self.audio_break:
                self.audio_break.src = break_path
            self.page.update()
        except Exception as e:
            print(f"Reload sounds error: {e}")

    def sync_xp(self):
        """Fetch latest XP and Level from DB and update the Focus UI."""
        try:
            current_xp, current_level = db.get_xp_level()
            xp_needed = current_level * 500
            emoji = db.get_species_emoji(current_level)

            self.tree_xp_bar.value = (
                min(1.0, current_xp / xp_needed) if xp_needed > 0 else 0
            )
            self.level_text.value = f"Level {current_level}"
            self.xp_text.value = f"{current_xp}/{xp_needed} XP"
            self.tree_emoji_text.value = emoji
            self.main_emoji.value = emoji
            self.overlay_emoji.value = emoji

            self.tree_xp_bar.update()
            self.level_text.update()
            self.xp_text.update()
            self.tree_emoji_text.update()
            self.main_emoji.update()
            self.overlay_emoji.update()
        except:
            pass


def _seed_dummy_icpc_tree():
    """Seed the Python ICPC skill tree if it doesn't already exist."""
    existing = db.get_skill_tree_by_name("Python ICPC")
    if existing:
        return  # already seeded

    tree_id = db.create_skill_tree(
        "Python ICPC",
        "Lộ trình luyện thi lập trình thi đấu ICPC bằng Python",
    )

    # Give starter SP so the user can begin unlocking
    db.add_global_sp(150)

    # Root node — Cú pháp & Mảng (no parent)
    root_id = db.create_skill_node(
        tree_id,
        None,
        "Cú pháp & Mảng",
        description="Nền tảng Python: biến, vòng lặp, mảng, chuỗi.",
        sp_cost=20,
        is_repeatable=False,
    )
    db.add_node_task(
        root_id, "checklist", "Giải 5 bài cơ bản trên Codeforces (A-level)"
    )
    db.add_node_task(
        root_id, "checklist", "Viết chương trình sắp xếp mảng bằng 3 thuật toán"
    )

    # Branch A — Cấu trúc dữ liệu
    ds_id = db.create_skill_node(
        tree_id,
        root_id,
        "Cấu trúc dữ liệu",
        description="Stack, Queue, Linked List, Heap, HashMap.",
        sp_cost=30,
        is_repeatable=False,
        exclusive_group_id="icpc_branch_1",
    )
    db.add_node_task(ds_id, "checklist", "Implement Stack & Queue từ đầu")
    db.add_node_task(ds_id, "text_review", "Viết báo cáo so sánh HashMap vs TreeMap")

    # Branch B — Thuật toán (mutually exclusive with Branch A)
    algo_id = db.create_skill_node(
        tree_id,
        root_id,
        "Thuật toán",
        description="Two Pointers, Binary Search, Greedy, Backtracking.",
        sp_cost=30,
        is_repeatable=False,
        exclusive_group_id="icpc_branch_1",
    )
    db.add_node_task(algo_id, "checklist", "Giải 10 bài Two Pointers trên LeetCode")
    db.add_node_task(algo_id, "code_snippet", "Viết Binary Search template chuẩn")

    # Leaf nodes under Branch A
    db.create_skill_node(
        tree_id,
        ds_id,
        "Segment Tree & BIT",
        description="Cây phân đoạn, Binary Indexed Tree.",
        sp_cost=50,
        is_repeatable=True,
    )
    db.create_skill_node(
        tree_id,
        ds_id,
        "Disjoint Set Union",
        description="Union-Find cho bài toán đồ thị.",
        sp_cost=40,
        is_repeatable=False,
    )

    # Leaf nodes under Branch B
    db.create_skill_node(
        tree_id,
        algo_id,
        "Quy hoạch động (DP)",
        description="Knapsack, LIS, LCS, DP trên cây.",
        sp_cost=60,
        is_repeatable=True,
    )
    db.create_skill_node(
        tree_id,
        algo_id,
        "Đồ thị nâng cao",
        description="BFS/DFS, Dijkstra, Floyd, Kruskal.",
        sp_cost=50,
        is_repeatable=False,
    )


def main(page: ft.Page):
    page.title = "Studygram"
    if page.platform not in [
        ft.PagePlatform.ANDROID,
        ft.PagePlatform.IOS,
        "android",
        "ios",
    ]:
        page.window.width = 390
        page.window.height = 844

    import csv
    import os

    # --- HÀM LÕI XỬ LÝ DỮ LIỆU CSV (DÙNG CHUNG) ---
    def process_csv_file(file_path):
        try:
            count = 0
            with open(file_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("name", "").strip()
                    if not name:
                        continue

                    desc = row.get("description", "").strip()

                    # Chống crash khi cột weight trong Excel bị bỏ trống
                    weight_str = row.get("weight", "1").strip()
                    try:
                        weight = int(weight_str) if weight_str else 1
                    except ValueError:
                        weight = 1

                    freq = row.get("frequency", "0,1,2,3,4,5,6").strip()

                    db.add_habit(name, desc, weight, freq)
                    count += 1

            page.snack_bar = ft.SnackBar(
                ft.Text(
                    f"Thành công! Đã nạp {count} thói quen vào hệ thống. 🎉",
                    color=ft.Colors.WHITE,
                    weight="bold",
                ),
                bgcolor=ft.Colors.GREEN_700,
            )
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Lỗi đọc file CSV: {str(ex)}", color=ft.Colors.WHITE),
                bgcolor=ft.Colors.RED_700,
            )
            page.snack_bar.open = True
            page.update()

    # === 1. KIỂM TRA NỀN TẢNG ===
    is_mobile = page.platform in [
        ft.PagePlatform.ANDROID,
        ft.PagePlatform.IOS,
        "android",
        "ios",
    ]

    # Khởi tạo biến trống trên Windows để tránh Crash
    csv_picker = None
    audio_picker = None
    audio_focus = None
    audio_break = None
    bg_music = None

    # === 2. CHỈ NẠP FILEPICKER & AUDIO TRÊN ĐIỆN THOẠI ===
    if is_mobile:

        def on_csv_picked(e: ft.FilePickerResultEvent):
            if e.files:
                process_csv_file(e.files[0].path)

        csv_picker = ft.FilePicker()
        csv_picker.on_result = on_csv_picked

        audio_picker = ft.FilePicker()
        audio_focus = fta.Audio(src="sounds/focus_start.mp3", autoplay=False)
        audio_break = fta.Audio(src="sounds/break_start.mp3", autoplay=False)
        bg_music = fta.Audio(autoplay=False, volume=0.5)

        page.overlay.extend(
            [csv_picker, audio_picker, audio_focus, audio_break, bg_music]
        )

        def on_audio_picked(e: ft.FilePickerResultEvent):
            if e.files and len(e.files) > 0:
                if bg_music is None:
                    return
                bg_music.src = e.files[0].path
                bg_music.update()
                page.snack_bar = ft.SnackBar(
                    ft.Text("Đã tải bài hát thành công!", color=ft.Colors.WHITE),
                    bgcolor=ft.Colors.GREEN_700,
                )
                page.snack_bar.open = True
                page.update()

        audio_picker.on_result = on_audio_picked

    page.update()  # Chốt sổ các control ngầm

    # 4. KHỞI TẠO DỮ LIỆU & GIAO DIỆN
    db.init_db()
    _seed_dummy_icpc_tree()
    settings = db.get_settings()

    page.theme_mode = (
        ft.ThemeMode.LIGHT if settings["theme"] == "light" else ft.ThemeMode.DARK
    )
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.PURPLE, use_material3=True)
    page.bgcolor = "#F8F9FA" if settings["theme"] == "light" else "#121212"
    page.padding = 15
    if page.platform not in [
        ft.PagePlatform.ANDROID,
        ft.PagePlatform.IOS,
        "android",
        "ios",
    ]:
        page.window_full_screen = False

    def on_window_event(e):
        if e.data == "blur" and focus_manager.running and focus_manager.mode == "work":
            page.run_task(focus_manager.apply_penalty)

    page.on_window_event = on_window_event

    # ---- BÊN DƯỚI LÀ HÀM def _apply_custom_sound... ÔNG GIÁO GIỮ NGUYÊN NHÉ ----

    def _apply_custom_sound(target_key, file_path_str):
        """Copy a sound file to assets/sounds and update DB + fta.Audio."""
        try:
            file_path_str = file_path_str.strip()
            if not file_path_str or not os.path.isfile(file_path_str):
                page.snack_bar = ft.SnackBar(
                    ft.Text(
                        "Không tìm thấy file! Kiểm tra lại đường dẫn.",
                        color=ft.Colors.WHITE,
                    ),
                    bgcolor=ft.Colors.RED_700,
                )
                page.snack_bar.open = True
                page.update()
                return
            os.makedirs("assets/sounds", exist_ok=True)
            filename = os.path.basename(file_path_str)
            dest_path = os.path.join("assets", "sounds", filename)
            shutil.copy2(file_path_str, dest_path)
            rel_path = f"sounds/{filename}"
            db.update_sound_setting(target_key, rel_path)
            if audio_focus and target_key == "focus_start_path":
                audio_focus.src = rel_path
            elif audio_break and target_key == "break_start_path":
                audio_break.src = rel_path
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Đã nạp: {filename} 🔊", color=ft.Colors.WHITE),
                bgcolor=ft.Colors.GREEN_700,
            )
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            print(f"Lỗi nạp âm thanh: {ex}")

    def format_money(amount):
        curr = settings.get("currency", "VNĐ")
        if curr == "kVNĐ":
            return f"{amount / 1000:,.1f} kVNĐ"
        elif curr == "USD":
            return f"${amount / 25000:,.2f}"
        else:
            return f"{amount:,.0f} VNĐ"

    def refresh_settings():
        nonlocal settings
        settings = db.get_settings()
        page.theme_mode = (
            ft.ThemeMode.LIGHT if settings["theme"] == "light" else ft.ThemeMode.DARK
        )
        page.theme = ft.Theme(color_scheme_seed=ft.Colors.PURPLE, use_material3=True)
        page.bgcolor = "#F8F9FA" if settings["theme"] == "light" else "#121212"
        focus_manager.update_ui()
        page.update()

    # --- Pomodoro System ---
    def _get_settings():
        return settings

    focus_manager = FocusManager(page, _get_settings, audio_focus, audio_break)
    page.on_window_event = on_window_event

    def get_color_intensity(ratio, color_set):
        if ratio <= 0:
            return color_set[0]
        if ratio <= 0.33:
            return color_set[1]
        if ratio <= 0.66:
            return color_set[2]
        return color_set[3]

    # --- Navigation ---
    def handle_tab_change(e):
        idx = e.control.selected_index
        content_container.controls.clear()
        if idx == 0:
            render_focus()
        elif idx == 1:
            render_quests()
        elif idx == 2:
            render_finance()
        elif idx == 3:
            render_explore()
        page.update()

    nav_bar = ft.NavigationBar(
        selected_index=0,
        destinations=[
            ft.NavigationBarDestination(
                label="Focus", icon=ft.Icons.CENTER_FOCUS_STRONG
            ),
            ft.NavigationBarDestination(label="Quests", icon=ft.Icons.CHECKLIST),
            ft.NavigationBarDestination(label="Finance", icon=ft.Icons.ATTACH_MONEY),
            ft.NavigationBarDestination(label="Explore", icon=ft.Icons.EXPLORE),
        ],
        on_change=handle_tab_change,
    )

    content_container = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.ALWAYS,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    # --- Render Functions ---
    def render_quests():
        try:
            content_container.controls.clear()
            content_container.scroll = "auto"

            trees = db.get_all_skill_trees()
            tree = trees[0] if trees else None
            if not tree:
                _seed_dummy_icpc_tree()
                trees = db.get_all_skill_trees()
                tree = trees[0] if trees else None

            nodes = db.get_tree_nodes(tree["id"]) if tree else []

            _nodes_fixed = []
            for n in nodes:
                n_dict = dict(n)
                # Nếu nhánh đang bị khóa, kiểm tra xem nó đã đủ điều kiện mở chưa
                if n_dict["status"] == "locked":
                    can_unlock, _ = db.check_node_unlockability(n_dict["id"])
                    if can_unlock:
                        n_dict["status"] = "unlocked"  # Đổi sang màu tím để nhận exp
                _nodes_fixed.append(n_dict)
            nodes = _nodes_fixed

            is_builder = page.session.store.get("builder_mode") or False

            # --- CODE GIAO DIỆN BÚT CHÌ ĐỔI TÊN CÂY ---
            current_tree_name = tree["name"] if tree else "Chưa có tên"

            def save_tree_name(e):
                new_name = edit_name_field.value
                if new_name.strip() and tree:
                    db.update_skill_tree(tree["id"], new_name.strip())
                    rename_dialog.open = False
                    render_quests()  # Vẽ lại trang để cập nhật tên mới
                    page.update()

            edit_name_field = ft.TextField(
                label="Đổi tên lộ trình cày cuốc:", value=current_tree_name
            )
            rename_dialog = ft.AlertDialog(
                title=ft.Text("Đổi tên Phó Bản"),
                content=edit_name_field,
                actions=[
                    ft.TextButton(
                        "Hủy",
                        on_click=lambda e: (
                            setattr(rename_dialog, "open", False),
                            page.update(),
                        ),
                    ),
                    ft.ElevatedButton(
                        "Lưu thay đổi",
                        on_click=save_tree_name,
                        bgcolor=ft.Colors.PURPLE_700,
                        color=ft.Colors.WHITE,
                    ),
                ],
                on_dismiss=lambda e: (
                    (page.overlay.remove(rename_dialog), page.update())
                    if rename_dialog in page.overlay
                    else None
                ),
            )

            tree_title = ft.Text(
                current_tree_name,
                size=24,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE,
            )

            edit_btn = ft.IconButton(
                icon=ft.Icons.EDIT_ROUNDED,
                icon_color=ft.Colors.GREY_400,
                tooltip="Đổi tên phó bản",
                on_click=lambda e: (
                    page.overlay.append(rename_dialog),
                    setattr(rename_dialog, "open", True),
                    page.update(),
                ),
            )

            # Cụm tiêu đề gồm Tên Cây + Nút Bút Chì
            title_group = ft.Row(
                [tree_title, edit_btn], alignment=ft.MainAxisAlignment.START
            )

            # Khung chứa Tiêu đề
            header_row = ft.Row(
                [
                    ft.Text(
                        "Skill Tree", size=26, weight="bold", color=ft.Colors.WHITE
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
            # --- KẾT THÚC ĐOẠN DÁN ---

            if is_builder:

                def on_create_root(e):
                    root_name_field = ft.TextField(label="Tên Kỹ Năng Gốc")

                    def on_root_save(e2):
                        db.create_skill_node(
                            tree_id=tree["id"] if tree else 1,
                            parent_id=None,
                            name=root_name_field.value or "Nhánh Gốc Mới",
                            description="",
                            sp_cost=20,
                            is_repeatable=False,
                        )
                        root_dialog.open = False
                        render_quests()
                        page.update()

                    def on_root_dismiss(ex):
                        if root_dialog in page.overlay:
                            page.overlay.remove(root_dialog)
                        page.update()

                    root_dialog = ft.AlertDialog(
                        title=ft.Text("Thêm Nhánh Gốc"),
                        content=root_name_field,
                        actions=[
                            ft.TextButton(
                                "Hủy",
                                on_click=lambda _: (
                                    setattr(root_dialog, "open", False) or page.update()
                                ),
                            ),
                            ft.ElevatedButton("Tạo Gốc", on_click=on_root_save),
                        ],
                        on_dismiss=on_root_dismiss,
                    )
                    page.overlay.append(root_dialog)
                    root_dialog.open = True
                    page.update()

                header_row.controls.append(
                    ft.ElevatedButton(
                        "+ Tạo Nhánh Gốc Mới",
                        icon=ft.Icons.ADD_BOX,
                        on_click=on_create_root,
                    )
                )

            content_container.controls.append(
                ft.Container(padding=10, content=header_row)
            )

            def handle_node_click(e):
                node_data = e.control.data
                if is_builder:
                    name_field = ft.TextField(
                        label="Tên Kỹ Năng", value=node_data["name"]
                    )
                    desc_field = ft.TextField(
                        label="Mô tả", value=node_data["description"]
                    )
                    sp_field = ft.TextField(
                        label="Thưởng EXP (mỗi mốc)",
                        value=str(node_data["sp_cost"]),
                        keyboard_type=ft.KeyboardType.NUMBER,
                    )
                    repeat_switch = ft.Switch(
                        label="Cho phép cày lặp lại (Farm SP)",
                        value=bool(node_data["is_repeatable"]),
                    )
                    max_level_field = ft.TextField(
                        label="Số Cấp Độ (Max Level)",
                        value=str(node_data.get("max_level", 1)),
                        keyboard_type=ft.KeyboardType.NUMBER,
                    )

                    def on_save(e_save):
                        db.update_skill_node(
                            node_data["id"],
                            name_field.value,
                            desc_field.value,
                            int(sp_field.value or 0),
                            repeat_switch.value,
                            int(max_level_field.value or 1),
                        )
                        dialog.open = False
                        render_quests()
                        page.update()

                    def on_delete(e_del):
                        db.delete_skill_node(node_data["id"])
                        dialog.open = False
                        render_quests()
                        page.update()

                    def on_add_child(e_add):
                        dialog.open = False
                        child_name_field = ft.TextField(label="Tên Kỹ Năng Con")

                        def on_child_save(e_csave):
                            db.create_skill_node(
                                tree_id=tree["id"],
                                parent_id=node_data["id"],
                                name=child_name_field.value or "Kỹ Năng Mới",
                                description="",
                                sp_cost=10,
                                is_repeatable=False,
                            )
                            child_dialog.open = False
                            render_quests()
                            page.update()

                        def on_child_dismiss(ex):
                            if child_dialog in page.overlay:
                                page.overlay.remove(child_dialog)
                            page.update()

                        child_dialog = ft.AlertDialog(
                            title=ft.Text("Thêm Nhánh Con"),
                            content=child_name_field,
                            actions=[
                                ft.TextButton(
                                    "Hủy",
                                    on_click=lambda _: (
                                        setattr(child_dialog, "open", False)
                                        or page.update()
                                    ),
                                ),
                                ft.ElevatedButton("Thêm", on_click=on_child_save),
                            ],
                            on_dismiss=on_child_dismiss,
                        )
                        page.overlay.append(child_dialog)
                        child_dialog.open = True
                        page.update()

                    def on_builder_dismiss(ex):
                        if dialog in page.overlay:
                            page.overlay.remove(dialog)
                        page.update()

                    dialog = ft.AlertDialog(
                        title=ft.Text("Chỉnh Sửa (Builder)"),
                        content=ft.Column(
                            [
                                name_field,
                                desc_field,
                                sp_field,
                                repeat_switch,
                                max_level_field,
                            ],
                            tight=True,
                        ),
                        actions=[
                            ft.TextButton(
                                "+ Thêm Nhánh", on_click=on_add_child, icon=ft.Icons.ADD
                            ),
                            ft.ElevatedButton(
                                "Lưu",
                                on_click=on_save,
                                bgcolor=ft.Colors.PURPLE_700,
                                color=ft.Colors.WHITE,
                            ),
                            ft.TextButton(
                                "Xóa",
                                on_click=on_delete,
                                icon=ft.Icons.DELETE,
                                icon_color=ft.Colors.RED,
                            ),
                        ],
                        on_dismiss=on_builder_dismiss,
                    )
                    page.overlay.append(dialog)
                    dialog.open = True
                    page.update()
                    return

                if node_data["status"] == "locked":
                    # Lấy lý do bị khóa từ Database (do chưa cày xong nhánh trên)
                    can_unlock, reason = db.check_node_unlockability(node_data["id"])
                    page.snack_bar = ft.SnackBar(
                        ft.Text(
                            f"🔒 CHƯA THỂ MỞ KHÓA: {reason}",
                            color=ft.Colors.WHITE,
                            weight="bold",
                        ),
                        bgcolor=ft.Colors.RED_800,
                    )
                    page.snack_bar.open = True
                    page.update()
                    return

                # NẾU NHÁNH ĐÃ MAX CẤP VÀ KHÔNG CHO CÀY LẠI -> Bật thông báo màu CAM
                if node_data["status"] == "mastered" and not node_data["is_repeatable"]:
                    page.snack_bar = ft.SnackBar(
                        ft.Text(
                            "✅ Kỹ năng này đã đạt cấp tối đa, không thể cày thêm!",
                            color=ft.Colors.WHITE,
                        ),
                        bgcolor=ft.Colors.ORANGE_800,
                    )
                    page.snack_bar.open = True
                    page.update()
                    return

                def on_verify_click(e2):
                    success, msg, new_status = db.complete_node_milestone(
                        node_data["id"]
                    )

                    bs.open = False
                    page.snack_bar = ft.SnackBar(
                        ft.Text(msg),
                        bgcolor=ft.Colors.GREEN_700 if success else ft.Colors.RED_700,
                    )
                    page.snack_bar.open = True
                    page.update()
                    render_quests()
                    focus_manager.sync_xp()
                    page.update()

                bs = ft.BottomSheet(
                    content=ft.Container(
                        padding=20,
                        content=ft.Column(
                            [
                                ft.Text(
                                    node_data["name"],
                                    size=20,
                                    weight="bold",
                                    color=ft.Colors.WHITE,
                                ),
                                ft.Text(
                                    node_data["description"] or "Không có mô tả.",
                                    color=ft.Colors.GREY_300,
                                ),
                                ft.Text(
                                    f"Thưởng: {node_data['sp_cost']} EXP 🌟",
                                    color=ft.Colors.GREEN_400,
                                ),
                                ft.ElevatedButton(
                                    "Hoàn Thành Mốc & Nhận EXP",
                                    on_click=on_verify_click,
                                    bgcolor=ft.Colors.GREEN_700,
                                    color=ft.Colors.WHITE,
                                ),
                            ],
                            tight=True,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ),
                    on_dismiss=lambda e: (
                        (page.overlay.remove(e.control), page.update())
                        if e.control in page.overlay
                        else None
                    ),
                )
                page.overlay.append(bs)
                bs.open = True
                page.update()

            node_dict = {n["id"]: n for n in nodes}
            children_dict = {}
            root_id = None
            for n in nodes:
                pid = n["parent_id"]
                if pid is None:
                    root_id = n["id"]
                if pid not in children_dict:
                    children_dict[pid] = []
                children_dict[pid].append(n)

            def build_node_ui(node_id):
                node = node_dict[node_id]
                state = node["status"]

                if state == "locked":
                    bg = ft.Colors.GREY_900
                    icon = ft.Icons.LOCK
                    icon_color = ft.Colors.GREY_500
                    glow = ft.Colors.TRANSPARENT
                elif state == "unlocked":
                    bg = ft.Colors.PURPLE_800
                    icon = ft.Icons.PLAY_ARROW
                    icon_color = ft.Colors.WHITE
                    glow = ft.Colors.with_opacity(0.3, ft.Colors.PURPLE_800)
                else:
                    bg = ft.Colors.PURPLE_ACCENT_700
                    icon = ft.Icons.CHECK_CIRCLE
                    icon_color = ft.Colors.WHITE
                    glow = ft.Colors.with_opacity(0.6, ft.Colors.PURPLE_ACCENT_700)

                max_lvl = node.get("max_level", 1)
                cur_lvl = node.get("current_level", 0)

                # Build segmented progress bars (binary: 1.0 = done, 0.0 = not done)
                if state != "locked" and max_lvl > 1:
                    bar_spacing = 2
                    total_width = 120
                    bar_width = (total_width - (max_lvl - 1) * bar_spacing) / max_lvl
                    seg_bars = []
                    for i in range(max_lvl):
                        val = 1.0 if i < cur_lvl else 0.0
                        seg_bars.append(
                            ft.ProgressBar(
                                value=val,
                                color=ft.Colors.GREEN_400,
                                bgcolor=ft.Colors.GREY_900,
                                width=bar_width,
                                height=6,
                                border_radius=3,
                            )
                        )
                    progress_widget = ft.Row(seg_bars, spacing=bar_spacing)
                elif state != "locked":
                    single_val = (
                        1.0 if state == "mastered" else (1.0 if cur_lvl > 0 else 0.0)
                    )
                    progress_widget = ft.ProgressBar(
                        value=single_val,
                        color=ft.Colors.GREEN_400,
                        bgcolor=ft.Colors.GREY_900,
                        width=120,
                        height=6,
                        border_radius=3,
                    )
                else:
                    progress_widget = ft.Container(height=6)

                level_suffix = f"\n(Lv.{cur_lvl}/{max_lvl})" if max_lvl > 1 else ""

                node_container = ft.Container(
                    data=node,
                    on_click=handle_node_click
                    if (is_builder or state != "mastered" or node["is_repeatable"])
                    else None,
                    content=ft.Column(
                        [
                            ft.Container(
                                content=ft.Icon(icon, color=icon_color, size=35),
                                width=80,
                                height=80,
                                border_radius=40,
                                bgcolor=bg,
                                alignment=ft.alignment.Alignment(0, 0),
                                shadow=ft.BoxShadow(
                                    blur_radius=20, color=glow, spread_radius=5
                                )
                                if glow != ft.Colors.TRANSPARENT
                                else None,
                            ),
                            ft.Text(
                                node["name"] + level_suffix,
                                size=14,
                                weight="bold",
                                text_align=ft.TextAlign.CENTER,
                                color=bg if state != "locked" else ft.Colors.GREY_500,
                            ),
                            progress_widget,
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=10,
                    width=170,
                )

                children = children_dict.get(node_id, [])
                if not children:
                    return ft.Column(
                        [node_container],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0,
                    )

                v_line = ft.Container(width=2, height=20, bgcolor=ft.Colors.PURPLE_500)

                children_cols = []
                for child in children:
                    children_cols.append(
                        ft.Column(
                            [
                                ft.Container(
                                    width=2, height=20, bgcolor=ft.Colors.PURPLE_500
                                ),
                                build_node_ui(child["id"]),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                        )
                    )

                children_row = ft.Row(
                    children_cols,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    spacing=0,
                )

                if len(children) > 1:
                    h_line_width = 170 * (len(children) - 1)
                    h_line = ft.Container(
                        width=h_line_width, height=2, bgcolor=ft.Colors.PURPLE_500
                    )
                    return ft.Column(
                        [node_container, v_line, h_line, children_row],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0,
                    )
                else:
                    return ft.Column(
                        [node_container, v_line, children_row],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0,
                    )

            if root_id:
                skill_tree = ft.Row(
                    [build_node_ui(root_id)],
                    scroll=ft.ScrollMode.ALWAYS,
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            else:
                skill_tree = ft.Container()

            # --- ĐOẠN CODE BỊ XÓA NHẦM (DÁN NGAY TRÊN SKILL_TREE_CARD) ---
            inner_title_row = ft.Row(
                [
                    ft.Text(
                        f"\U0001f332 {tree['name'] if tree else 'Chưa có tên'} Skill Tree",
                        size=22,
                        weight="bold",
                        color=ft.Colors.PURPLE_200,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.EDIT_ROUNDED,
                        icon_color=ft.Colors.PURPLE_200,
                        on_click=lambda e: (
                            page.overlay.append(rename_dialog),
                            setattr(rename_dialog, "open", True),
                            page.update(),
                        ),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            )
            # -------------------------------------------------------------

            # --- CARD SKILL TREE CỦA ÔNG GIÁO (ĐÃ ĐƯỢC LẮP BÚT CHÌ) ---
            skill_tree_card = ft.Container(
                bgcolor="#1E1B4B",
                border_radius=20,
                padding=20,
                margin=ft.Margin(0, 0, 0, 20),
                content=ft.Column(
                    [
                        inner_title_row,  # <-- NÓ NẰM Ở ĐÂY NÀY!
                        ft.Divider(height=1, color=ft.Colors.PURPLE_900),
                        ft.Container(height=10),
                        skill_tree,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
            content_container.controls.append(skill_tree_card)
            content_container.controls.append(ft.Container(height=10))
            content_container.controls.append(
                ft.Divider(height=1, color=ft.Colors.GREY_800)
            )

            # --- HABITS (existing logic) ---
            habits = db.get_all_habits()
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_weekday = str(datetime.now().weekday())
            done_ids = db.get_habit_logs_for_date(today_str)

            habit_view_mode = page.session.store.get("habit_view_mode") or "list"
            if habit_view_mode == "canvas":
                habit_view_mode = "grid"

            def toggle_habit_view(e):
                page.session.store.set(
                    "habit_view_mode", "grid" if habit_view_mode == "list" else "list"
                )
                render_quests()
                page.update()

            view_toggle_btn = ft.IconButton(
                icon=ft.Icons.GRID_VIEW
                if habit_view_mode == "list"
                else ft.Icons.VIEW_LIST,
                on_click=toggle_habit_view,
                tooltip="Lưới thói quen"
                if habit_view_mode == "list"
                else "Danh sách thói quen",
            )

            content_container.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text(
                                "✅ Thói Quen Hôm Nay",
                                size=22,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.PURPLE_400,
                            ),
                            view_toggle_btn,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    margin=ft.Margin(0, 10, 0, 0),
                )
            )

            # Filter habits for today
            filtered_habits = []
            for h in habits:
                freq = dict(h).get("frequency") or "0,1,2,3,4,5,6"
                if today_weekday in freq:
                    filtered_habits.append(h)

            total = len(filtered_habits)
            done_count = sum(1 for h in filtered_habits if h["id"] in done_ids)
            progress = done_count / total if total > 0 else 0
            content_container.controls.append(
                ft.ProgressBar(
                    value=progress,
                    color=ft.Colors.GREEN,
                    bgcolor=ft.Colors.GREEN_100,
                    height=8,
                    border_radius=4,
                )
            )
            content_container.controls.append(
                ft.Text(f"Tiến độ: {done_count}/{total}", size=12)
            )

            # Add Habit Form
            name_input = ft.TextField(
                label="Tên thói quen",
                border_radius=10,
                filled=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.PURPLE_400,
                expand=True,
            )
            desc_input = ft.TextField(
                label="Mô tả chi tiết",
                border_radius=10,
                filled=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.PURPLE_400,
                multiline=True,
                expand=True,
            )
            weight_dd = ft.Dropdown(
                border_radius=10,
                filled=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.PURPLE_400,
                label="Tỷ trọng",
                options=[
                    ft.dropdown.Option("1"),
                    ft.dropdown.Option("2"),
                    ft.dropdown.Option("3"),
                    ft.dropdown.Option("5"),
                    ft.dropdown.Option("8"),
                ],
                value="1",
            )

            # Multiple Day Selection (Chips)
            days_data = [
                ("T2", "0"),
                ("T3", "1"),
                ("T4", "2"),
                ("T5", "3"),
                ("T6", "4"),
                ("T7", "5"),
                ("CN", "6"),
            ]
            chips = []

            def chip_toggle(e):
                page.update()

            for label, key in days_data:
                chips.append(
                    ft.Chip(
                        label=ft.Text(label),
                        selected=True,
                        data=key,
                        on_select=chip_toggle,
                    )
                )

            freq_selector = ft.ExpansionTile(
                title=ft.Text("Tần suất lặp lại"), controls=[ft.Row(chips, wrap=True)]
            )

            def add_h(e):
                if name_input.value:
                    selected_keys = [c.data for c in chips if c.selected]
                    freq_str = (
                        ",".join(selected_keys) if selected_keys else "0,1,2,3,4,5,6"
                    )
                    db.add_habit(
                        name_input.value,
                        description=desc_input.value,
                        weight=int(weight_dd.value),
                        frequency=freq_str,
                    )
                    name_input.value = ""
                    desc_input.value = ""
                    for c in chips:
                        c.selected = True
                    render_quests()
                    page.update()

            add_btn = ft.Button(
                "Thêm Thói Quen",
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=10),
                    bgcolor=ft.Colors.PURPLE_600,
                    color=ft.Colors.WHITE,
                ),
                on_click=add_h,
            )

            content_container.controls.append(ft.Container(height=20))
            content_container.controls.append(
                ft.Column(
                    [
                        name_input,
                        desc_input,
                        weight_dd,
                        freq_selector,
                        ft.Row([ft.Container(content=add_btn, expand=True)]),
                    ],
                    spacing=15,
                )
            )
            content_container.controls.append(
                ft.Divider(height=1, color=ft.Colors.GREY_800)
            )

            if not filtered_habits:
                habit_list = ft.ListView(
                    expand=True, spacing=10, scroll=ft.ScrollMode.ALWAYS
                )
                habit_list.controls.append(
                    ft.Text(
                        "Nghỉ ngơi thôi! Nay không có lịch thói quen nào.",
                        color=ft.Colors.GREY_500,
                    )
                )
                content_container.controls.append(habit_list)
            else:
                if habit_view_mode == "list":
                    habit_list = ft.ListView(
                        expand=True, spacing=10, scroll=ft.ScrollMode.ALWAYS
                    )
                    for h in filtered_habits:
                        is_done = h["id"] in done_ids
                        freq = dict(h).get("frequency") or "0,1,2,3,4,5,6"
                        streak = db.get_habit_streak(h["id"], freq)
                        weight = dict(h).get("weight", 1)

                        def toggle_cb(e, hid=h["id"]):
                            db.toggle_habit_log(hid, today_str, e.control.value)
                            render_quests()
                            page.update()

                        def del_h(e, hid=h["id"]):
                            db.delete_habit(hid)
                            render_quests()
                            page.update()

                        habit_list.controls.append(
                            ft.Container(
                                padding=15,
                                border_radius=15,
                                bgcolor=ft.Colors.with_opacity(
                                    0.1, ft.Colors.PURPLE_300
                                ),
                                content=ft.Row(
                                    [
                                        ft.Checkbox(
                                            value=is_done,
                                            on_change=toggle_cb,
                                        ),
                                        ft.Column(
                                            [
                                                ft.Text(
                                                    h["name"], size=18, weight="bold"
                                                ),
                                                ft.Text(
                                                    dict(h).get("description", "")
                                                    or "",
                                                    size=12,
                                                    color=ft.Colors.WHITE_54,
                                                ),
                                            ],
                                            expand=True,
                                            spacing=2,
                                        ),
                                        ft.Column(
                                            [
                                                ft.Row(
                                                    [
                                                        ft.Icon(
                                                            ft.Icons.LOCAL_FIRE_DEPARTMENT,
                                                            color=ft.Colors.ORANGE,
                                                            size=16,
                                                        ),
                                                        ft.Text(str(streak)),
                                                    ]
                                                ),
                                                ft.Text(
                                                    f"Tỉ trọng: {weight}",
                                                    size=12,
                                                    color=ft.Colors.GREY_400,
                                                ),
                                            ],
                                            tight=True,
                                            spacing=5,
                                            alignment=ft.MainAxisAlignment.CENTER,
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE_OUTLINE,
                                            icon_color=ft.Colors.RED_400,
                                            on_click=del_h,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                            )
                        )
                    content_container.controls.append(habit_list)
                else:
                    grid_row = ft.Row(
                        wrap=True,
                        spacing=15,
                        run_spacing=15,
                        alignment=ft.MainAxisAlignment.CENTER,
                    )
                    grid_container = ft.Column(
                        controls=[grid_row],
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    )

                    for h in habits:
                        if h["id"] in done_ids:
                            continue

                        freq = dict(h).get("frequency") or "0,1,2,3,4,5,6"
                        streak = db.get_habit_streak(h["id"], freq)

                        def create_grid_item(habit_data, streak_val):
                            weight = int(dict(habit_data).get("weight", 1))
                            dynamic_size = 90 + (weight - 1) * 25

                            def open_sheet(e):
                                async def _confirm_done(e2):
                                    sheet.open = False
                                    page.update()

                                    db.toggle_habit_log(
                                        habit_data["id"], today_str, True
                                    )
                                    page.snack_bar = ft.SnackBar(
                                        ft.Text(
                                            "Đã hoàn thành thói quen!",
                                            color=ft.Colors.WHITE,
                                        ),
                                        bgcolor=ft.Colors.GREEN_700,
                                    )
                                    page.snack_bar.open = True

                                    # Step 1: Pulse out
                                    widget.scale = 1.2
                                    widget.update()

                                    # DÙNG ASYNC SLEEP THAY VÌ TIME.SLEEP
                                    import asyncio

                                    await asyncio.sleep(0.15)

                                    # Step 2: Shatter
                                    widget.scale = 0.1
                                    widget.opacity = 0
                                    widget.update()
                                    await asyncio.sleep(0.2)
                                    # Step 3: Remove and reorganize
                                    if widget in grid_row.controls:
                                        grid_row.controls.remove(widget)
                                    grid_row.update()

                                    render_quests()
                                    page.update()

                                sheet = ft.BottomSheet(
                                    content=ft.Container(
                                        padding=20,
                                        content=ft.Column(
                                            [
                                                ft.Text(
                                                    f"Thói quen: {habit_data['name']}",
                                                    size=20,
                                                    weight="bold",
                                                    color=ft.Colors.PURPLE_400,
                                                ),
                                                ft.ElevatedButton(
                                                    "Đánh dấu hoàn thành hôm nay",
                                                    icon=ft.Icons.CHECK_CIRCLE,
                                                    bgcolor=ft.Colors.GREEN_600,
                                                    color=ft.Colors.WHITE,
                                                    on_click=_confirm_done,
                                                ),
                                            ],
                                            tight=True,
                                        ),
                                    ),
                                    on_dismiss=lambda e: (
                                        (page.overlay.remove(e.control), page.update())
                                        if e.control in page.overlay
                                        else None
                                    ),
                                )
                                page.overlay.append(sheet)
                                sheet.open = True
                                page.update()

                            widget = ft.Container(
                                key=f"habit_{habit_data['id']}",
                                width=dynamic_size,
                                height=dynamic_size,
                                border_radius=15,
                                bgcolor=ft.Colors.PURPLE_800,
                                shadow=ft.BoxShadow(
                                    blur_radius=10,
                                    spread_radius=2,
                                    color=ft.Colors.with_opacity(0.3, ft.Colors.PURPLE),
                                ),
                                animate_scale=ft.Animation(
                                    150, ft.AnimationCurve.DECELERATE
                                ),
                                animate_opacity=ft.Animation(
                                    200, ft.AnimationCurve.EASE_OUT
                                ),
                                on_click=open_sheet,
                                content=ft.Stack(
                                    [
                                        ft.Column(
                                            [
                                                ft.Container(
                                                    content=ft.Row(
                                                        [
                                                            ft.Icon(
                                                                ft.Icons.LOCAL_FIRE_DEPARTMENT,
                                                                color=ft.Colors.ORANGE,
                                                                size=14,
                                                            ),
                                                            ft.Text(
                                                                str(streak_val), size=12
                                                            ),
                                                        ],
                                                        alignment=ft.MainAxisAlignment.END,
                                                        spacing=2,
                                                    ),
                                                    padding=ft.Padding(0, 5, 5, 0),
                                                ),
                                                ft.Container(
                                                    content=ft.Text(
                                                        habit_data["name"],
                                                        weight="bold",
                                                        size=16,
                                                        text_align="center",
                                                    ),
                                                    alignment=ft.alignment.Alignment(
                                                        0, 0
                                                    ),
                                                    expand=True,
                                                ),
                                            ]
                                        )
                                    ]
                                ),
                            )
                            return widget

                        grid_row.controls.append(create_grid_item(h, streak))

                    content_container.controls.append(grid_container)

            page.update()
        except Exception as e:
            import traceback

            content_container.controls.clear()
            content_container.controls.append(
                ft.Text(
                    f"LỖI RỒI ÔNG GIÁO ƠI:\n{str(e)}\n\n{traceback.format_exc()}",
                    bgcolor=ft.Colors.RED_500,
                    selectable=True,
                )
            )
            page.update()

    def render_finance(filter_type="All"):
        try:
            content_container.controls.clear()
            accounts = db.get_all_accounts()
            budget = settings["monthly_budget"]
            month_start = datetime.now().strftime("%Y-%m-01")
            spent = db.get_monthly_expenses(month_start)

            content_container.controls.append(
                ft.Text("🎯 Ngân sách tháng này", size=20, weight=ft.FontWeight.W_600)
            )
            budget = float(settings.get("monthly_budget", 0))
            progress = min(spent / budget, 1.0) if budget > 0 else 0.0
            color = (
                ft.Colors.GREEN
                if progress < 0.5
                else ft.Colors.ORANGE
                if progress < 0.8
                else ft.Colors.RED
            )
            content_container.controls.append(
                ft.ProgressBar(value=progress, color=color, bgcolor=ft.Colors.GREY_200)
            )
            content_container.controls.append(
                ft.Text(
                    f"Đã tiêu: {format_money(spent)} / {format_money(budget)}", size=14
                )
            )

            # Pie Chart implementation
            cat_expenses = db.get_expenses_by_category(month_start)
            if spent > 0 and cat_expenses:
                try:
                    pie_sections = []
                    pie_colors = [
                        ft.Colors.PURPLE_400,
                        ft.Colors.INDIGO_400,
                        ft.Colors.BLUE_400,
                        ft.Colors.TEAL_400,
                        ft.Colors.GREEN_400,
                        ft.Colors.ORANGE_400,
                        ft.Colors.RED_400,
                    ]
                    for i, (cat, amt) in enumerate(cat_expenses.items()):
                        pie_sections.append(
                            ft.PieChartSection(
                                amt,
                                title=f"{cat}\n{int(amt / spent * 100)}%",
                                title_style=ft.TextStyle(
                                    size=12,
                                    bgcolor=ft.Colors.with_opacity(
                                        0.15, ft.Colors.WHITE
                                    ),
                                    weight=ft.FontWeight.W_600,
                                ),
                                color=pie_colors[i % len(pie_colors)],
                                radius=40,
                            )
                        )
                    pie_chart = ft.PieChart(
                        sections=pie_sections,
                        sections_space=2,
                        center_space_radius=30,
                        height=150,
                    )
                    content_container.controls.append(
                        ft.Container(
                            content=pie_chart,
                            alignment=ft.alignment.Alignment(0, 0),
                            padding=10,
                        )
                    )
                except AttributeError:
                    content_container.controls.append(
                        ft.Text(
                            "PieChart không khả dụng trên phiên bản Flet này.",
                            size=12,
                            color=ft.Colors.GREY_500,
                            italic=True,
                        )
                    )

            content_container.controls.append(ft.Container(height=20))
            content_container.controls.append(
                ft.Divider(height=1, color=ft.Colors.GREY_800)
            )

            content_container.controls.append(
                ft.Text("🏦 Quản lý Ví tiền", size=18, weight=ft.FontWeight.W_600)
            )
            acc_name = ft.TextField(
                border_radius=10,
                filled=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.PURPLE_400,
                label="Tên ví",
                expand=True,
            )
            acc_bal = ft.TextField(
                border_radius=10,
                filled=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.PURPLE_400,
                label="Số dư",
                value="0",
                expand=True,
            )

            def add_a(e):
                if acc_name.value:
                    db.add_account(acc_name.value, float(acc_bal.value or 0))
                    render_finance(filter_type)
                    page.update()

            content_container.controls.append(
                ft.Row([acc_name, acc_bal, ft.IconButton(ft.Icons.ADD, on_click=add_a)])
            )

            for a in accounts:

                def del_a(e, aid=a["id"]):
                    db.delete_account(aid)
                    render_finance(filter_type)
                    page.update()

                content_container.controls.append(
                    ft.Row(
                        [
                            ft.Text(
                                f"**{a['name']}**: {format_money(a['balance'])}",
                                expand=True,
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE,
                                icon_color=ft.Colors.RED_300,
                                on_click=del_a,
                            ),
                        ]
                    )
                )
            content_container.controls.append(ft.Container(height=20))
            content_container.controls.append(
                ft.Divider(height=1, color=ft.Colors.GREY_800)
            )

            content_container.controls.append(
                ft.Text("📝 Ghi sổ nhanh", size=18, weight=ft.FontWeight.W_600)
            )
            t_type = ft.RadioGroup(
                content=ft.Row(
                    [
                        ft.Radio(value="expense", label="Chi tiêu (-)"),
                        ft.Radio(value="income", label="Thu nhập (+)"),
                        ft.Radio(value="transfer", label="Chuyển ví (↔)"),
                    ],
                    wrap=True,
                )
            )
            t_type.value = "expense"

            cat_names = ["Ăn uống", "Học tập", "Sức khỏe", "Du lịch", "Khác"]
            selected_cat = "Khác"

            def on_cat_select(e):
                nonlocal selected_cat
                selected_cat = getattr(e.control.label, "value", "Khác")
                for c in cat_row.controls:
                    c.selected = getattr(c.label, "value", "") == selected_cat
                page.update()

            try:
                chip_func = ft.ChoiceChip
            except AttributeError:
                chip_func = ft.Chip

            cat_row = ft.Row(
                [
                    chip_func(
                        label=ft.Text(n),
                        selected=(n == "Khác"),
                        on_select=on_cat_select,
                    )
                    for n in cat_names
                ],
                wrap=True,
            )

            acc_select = ft.Dropdown(
                border_radius=10,
                filled=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.PURPLE_400,
                options=[ft.dropdown.Option(a["name"]) for a in accounts],
                label="Chọn ví",
                expand=True,
            )
            acc_select2 = ft.Dropdown(
                border_radius=10,
                filled=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.PURPLE_400,
                options=[ft.dropdown.Option(a["name"]) for a in accounts],
                label="Ví đích",
                visible=False,
                expand=True,
            )

            def type_change(e):
                acc_select2.visible = t_type.value == "transfer"
                cat_row.visible = t_type.value != "transfer"
                page.update()

            t_type.on_change = type_change

            amount_in = ft.TextField(
                border_radius=10,
                filled=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.PURPLE_400,
                label="Số tiền",
                value="0",
            )
            note_in = ft.TextField(
                border_radius=10,
                filled=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.PURPLE_400,
                label="Ghi chú",
            )

            def save_t(e):
                # 1. Chống lỗi crash khi nhập chữ cái hoặc để trống
                try:
                    amt = float(amount_in.value or 0)
                except ValueError:
                    page.snack_bar = ft.SnackBar(
                        ft.Text("Vui lòng nhập định dạng số hợp lệ!"),
                        bgcolor=ft.Colors.RED_700,
                    )
                    page.snack_bar.open = True
                    page.update()
                    return

                # Validate Inputs implicitly
                if amt <= 0 or not acc_select.value:
                    return

                if t_type.value == "transfer":
                    if not acc_select2.value or acc_select.value == acc_select2.value:
                        return

                    # 2. Chống lỗi StopIteration crash khi không tìm thấy Ví
                    id_from = next(
                        (a["id"] for a in accounts if a["name"] == acc_select.value),
                        None,
                    )
                    id_to = next(
                        (a["id"] for a in accounts if a["name"] == acc_select2.value),
                        None,
                    )

                    if id_from and id_to:
                        db.transfer_funds(
                            id_from, id_to, amt, acc_select.value, acc_select2.value
                        )
                else:
                    aid = next(
                        (a["id"] for a in accounts if a["name"] == acc_select.value),
                        None,
                    )
                    if aid:
                        db.add_transaction(
                            aid, amt, t_type.value, selected_cat, note_in.value
                        )

                render_finance(filter_type)
                page.update()

            content_container.controls.extend(
                [
                    t_type,
                    cat_row,
                    acc_select,
                    acc_select2,
                    amount_in,
                    note_in,
                    ft.Button(
                        "Lưu giao dịch",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            bgcolor=ft.Colors.PURPLE_600,
                            color=ft.Colors.WHITE,
                        ),
                        on_click=save_t,
                    ),
                ]
            )

            content_container.controls.append(ft.Container(height=20))
            content_container.controls.append(
                ft.Divider(height=1, color=ft.Colors.GREY_800)
            )

            filter_dd = ft.Dropdown(
                border_radius=10,
                filled=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.PURPLE_400,
                label="Lọc",
                options=[
                    ft.dropdown.Option("All"),
                    ft.dropdown.Option("Expense"),
                    ft.dropdown.Option("Income"),
                ],
                value=filter_type,
                width=120,
            )
            filter_dd.on_change = lambda e: (
                render_finance(e.control.value) or page.update()
            )
            row_hist = ft.Row(
                [ft.Text("🕒 Lịch sử", size=18, weight=ft.FontWeight.W_600), filter_dd],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
            content_container.controls.append(row_hist)

            history_list = ft.ListView(
                expand=True, spacing=10, scroll=ft.ScrollMode.ALWAYS
            )
            txs = db.get_recent_transactions(15, filter_type)
            if not txs:
                history_list.controls.append(
                    ft.Text("Chưa có giao dịch nào.", color=ft.Colors.GREY_500)
                )
            else:
                for tx in txs:
                    icon = (
                        ft.Icons.ARROW_DOWNWARD
                        if tx["transaction_type"] == "expense"
                        else ft.Icons.ARROW_UPWARD
                    )
                    bgcolor = (
                        ft.Colors.RED_500
                        if tx["transaction_type"] == "expense"
                        else ft.Colors.GREEN_500
                    )
                    history_list.controls.append(
                        ft.Container(
                            padding=10,
                            border_radius=10,
                            bgcolor=ft.Colors.with_opacity(0.02, ft.Colors.ON_SURFACE),
                            content=ft.ListTile(
                                leading=ft.Icon(icon, color=color),
                                title=ft.Text(
                                    f"{tx['category']}", weight=ft.FontWeight.W_600
                                ),
                                subtitle=ft.Text(
                                    f"{tx['description']} • {tx['created_at'][:10]}",
                                    size=12,
                                ),
                                trailing=ft.Text(
                                    format_money(tx["amount"]),
                                    color=color,
                                    weight=ft.FontWeight.W_600,
                                ),
                            ),
                        )
                    )
            content_container.controls.append(history_list)

            page.update()
        except Exception as e:
            import traceback

            content_container.controls.clear()
            content_container.controls.append(
                ft.Text(
                    f"LỖI RỒI ÔNG GIÁO ƠI:\n{str(e)}\n\n{traceback.format_exc()}",
                    bgcolor=ft.Colors.RED_500,
                    selectable=True,
                )
            )
            page.update()

    def render_focus():
        try:
            content_container.controls.clear()
            content_container.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Focus Space",
                        size=24,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.PURPLE_400,
                    ),
                    margin=ft.Margin(0, 20, 0, 0),
                )
            )

            content_container.controls.append(focus_manager.pomodoro_card)
            content_container.controls.append(
                ft.Divider(height=1, color=ft.Colors.GREY_800)
            )

            # --- 🎵 STRICT MODE MUSIC PLAYER ---
            def toggle_music(e):
                if bg_music is None:
                    return
                if e.control.icon == ft.Icons.PLAY_CIRCLE_FILLED:
                    bg_music.play()
                    e.control.icon = ft.Icons.PAUSE_CIRCLE_FILLED
                else:
                    bg_music.pause()
                    e.control.icon = ft.Icons.PLAY_CIRCLE_FILLED
                e.control.update()

            music_controls = ft.Column(
                [
                    ft.Text(
                        "🎧 Focus Music Station",
                        size=18,
                        weight="bold",
                        color=ft.Colors.PURPLE_400,
                    ),
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.LIBRARY_MUSIC,
                                on_click=lambda _: audio_picker.pick_files(
                                    allow_multiple=False,
                                    allowed_extensions=["mp3", "wav"],
                                ),
                                tooltip="Chọn bài nhạc",
                                icon_color=ft.Colors.PURPLE_300,
                                disabled=not is_mobile,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.PLAY_CIRCLE_FILLED,
                                on_click=toggle_music,
                                icon_size=35,
                                icon_color=ft.Colors.PURPLE_ACCENT,
                                disabled=not is_mobile,
                            ),
                            ft.Slider(
                                min=0,
                                max=1,
                                value=0.5,
                                on_change=lambda e: (
                                    (
                                        setattr(
                                            bg_music, "volume", float(e.control.value)
                                        )
                                        or bg_music.update()
                                    )
                                    if bg_music
                                    else None
                                ),
                                expand=True,
                                disabled=not is_mobile,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            )

            if not is_mobile:
                music_controls.controls.append(
                    ft.Text(
                        "🎵 Tính năng nhạc nền chỉ có sẵn trên Điện thoại",
                        color=ft.Colors.RED_400,
                        size=12,
                        italic=True,
                    )
                )

            music_player = ft.Container(
                bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.PURPLE),
                border_radius=15,
                padding=15,
                content=music_controls,
            )
            content_container.controls.append(music_player)
            content_container.controls.append(
                ft.Divider(height=1, color=ft.Colors.GREY_800)
            )

            # --- Random Quote (merged: static + DB) ---
            quotes_data = db.get_all_quotes()
            all_quotes = list(QUOTES_LIST) + list(HUST_QUOTES)
            for q in quotes_data:
                all_quotes.append(f'"{q["text"]}" — {q["author"]}')

            quote_card = ft.Container(
                bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
                padding=15,
                border_radius=15,
                margin=ft.Margin(0, 0, 0, 20),
            )
            if all_quotes:
                chosen = random.choice(all_quotes)
                quote_card.content = ft.Text(
                    f"💡 {chosen}",
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.INDIGO_700,
                )
            else:
                quote_card.content = ft.Text(
                    "💡 Trạm Quotes đang trống...", color=ft.Colors.INDIGO_700
                )
            content_container.controls.append(quote_card)

            # --- 30-Day Heatmap ---
            import datetime as dt

            today_dt = dt.date.today()

            empty_c = ft.Colors.with_opacity(0.1, ft.Colors.WHITE)

            def get_intensity_green(ratio):
                if ratio <= 0:
                    return empty_c
                if ratio < 0.3:
                    return ft.Colors.GREEN_200
                if ratio < 0.6:
                    return ft.Colors.GREEN_400
                return ft.Colors.GREEN_700

            def get_intensity_blue(count):
                if count <= 0:
                    return empty_c
                if count < 2:
                    return ft.Colors.BLUE_200
                if count < 4:
                    return ft.Colors.BLUE_400
                return ft.Colors.BLUE_700

            def get_intensity_purple(seconds):
                if seconds <= 0:
                    return empty_c
                if seconds < 1500:
                    return ft.Colors.PURPLE_200
                if seconds < 3600:
                    return ft.Colors.PURPLE_400
                return ft.Colors.PURPLE_700

            heatmap_row = ft.Row(
                wrap=True,
                spacing=8,
                run_spacing=8,
                alignment=ft.MainAxisAlignment.CENTER,
            )

            for i in range(30):
                target_date = today_dt - dt.timedelta(days=29 - i)
                date_str = target_date.strftime("%Y-%m-%d")
                date_label = target_date.strftime("%d/%m")

                habit_ratio = db.get_daily_habit_completion_ratio(date_str)
                finance_count = db.get_daily_finance_activity(date_str)
                focus_secs = db.get_daily_focus_seconds(date_str)

                color_habit = get_intensity_green(habit_ratio)
                color_finance = get_intensity_blue(finance_count)
                color_focus = get_intensity_purple(focus_secs)

                chart = ft.Container(
                    width=30,
                    height=30,
                    border_radius=15,
                    tooltip=date_label,
                    gradient=ft.SweepGradient(
                        start_angle=0,
                        end_angle=6.283,
                        colors=[
                            color_habit,
                            color_habit,
                            color_finance,
                            color_finance,
                            color_focus,
                            color_focus,
                        ],
                        stops=[0.0, 0.33, 0.33, 0.66, 0.66, 1.0],
                    ),
                )
                heatmap_row.controls.append(chart)

            heatmap_card = ft.Card(
                bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
                elevation=0,
                content=ft.Container(
                    padding=20,
                    border_radius=15,
                    content=ft.Column(
                        [
                            ft.Text(
                                "Tổng quan 30 ngày (Habits, Finance, Focus)",
                                weight=ft.FontWeight.W_600,
                                size=16,
                            ),
                            heatmap_row,
                        ],
                        spacing=15,
                    ),
                ),
            )
            content_container.controls.append(heatmap_card)
            content_container.controls.append(
                ft.Divider(height=1, color=ft.Colors.GREY_800)
            )

            # --- Quote Collection ---
            content_container.controls.append(
                ft.Text("✒️ Thêm Quote mới", size=20, weight=ft.FontWeight.W_600)
            )
            q_text = ft.TextField(
                border_radius=10,
                filled=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.PURPLE_400,
                label="Câu nói tâm đắc",
                multiline=True,
            )
            q_author = ft.TextField(
                border_radius=10,
                filled=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.PURPLE_400,
                label="Tác giả",
            )

            def save_q(e):
                if q_text.value:
                    db.add_quote(q_text.value, q_author.value)
                    render_focus()
                    page.update()

            content_container.controls.extend(
                [
                    q_text,
                    q_author,
                    ft.Button(
                        "Lưu Quote",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            bgcolor=ft.Colors.PURPLE_600,
                            color=ft.Colors.WHITE,
                        ),
                        on_click=save_q,
                    ),
                ]
            )
            content_container.controls.append(
                ft.Divider(height=1, color=ft.Colors.GREY_800)
            )
            content_container.controls.append(
                ft.Text("📚 Bộ sưu tập Quote", size=18, weight=ft.FontWeight.W_600)
            )

            quote_list = ft.ListView(
                expand=True, spacing=10, scroll=ft.ScrollMode.ALWAYS
            )
            for q in quotes_data:

                def del_q(e, qid=q["id"]):
                    db.delete_quote(qid)
                    render_focus()
                    page.update()

                quote_list.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(f'"{q["text"]}"', italic=True),
                                        ft.Text(
                                            f"— {q['author']}",
                                            size=12,
                                            color=ft.Colors.GREY_600,
                                        ),
                                    ],
                                    expand=True,
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE_OUTLINE,
                                    icon_color=ft.Colors.RED_300,
                                    on_click=del_q,
                                ),
                            ]
                        ),
                        padding=10,
                        border=ft.Border.all(1, ft.Colors.GREY_200),
                        border_radius=5,
                    )
                )
            content_container.controls.append(quote_list)

            page.update()
        except Exception as e:
            import traceback

            content_container.controls.clear()
            content_container.controls.append(
                ft.Text(
                    f"LỖI RỒI ÔNG GIÁO ƠI:\n{str(e)}\n\n{traceback.format_exc()}",
                    bgcolor=ft.Colors.RED_500,
                    selectable=True,
                )
            )
            page.update()

    def render_explore():
        try:
            content_container.controls.clear()

            # --- BUILDER MODE TOGGLE ---
            def on_builder_toggle(e):
                page.session.store.set("builder_mode", e.control.value)
                page.update()

            content_container.controls.append(
                ft.Container(
                    padding=10,
                    content=ft.Switch(
                        label="Chế độ Kiến Tạo (Builder Mode)",
                        value=page.session.store.get("builder_mode") or False,
                        on_change=on_builder_toggle,
                        active_color=ft.Colors.PURPLE_ACCENT,
                    ),
                )
            )

            # --- ☯️ I CHING DAILY FOCUS ---
            hexagram_result = ft.Column(
                visible=False,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            )

            def gieo_que(e):
                q = random.choice(I_CHING_HEXAGRAMS)
                hexagram_result.controls.clear()
                hexagram_result.controls.extend(
                    [
                        ft.Text(q["symbol"], size=60),
                        ft.Text(
                            q["name"],
                            size=22,
                            weight="bold",
                            color=ft.Colors.PURPLE_200,
                        ),
                        ft.Container(
                            padding=15,
                            border_radius=10,
                            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
                            content=ft.Text(
                                q["advice"],
                                size=15,
                                text_align=ft.TextAlign.CENTER,
                                color=ft.Colors.WHITE,
                            ),
                        ),
                    ]
                )
                hexagram_result.visible = True
                page.update()

            iching_card = ft.Card(
                elevation=0,
                bgcolor=ft.Colors.TRANSPARENT,
                content=ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.PURPLE_700),
                    border_radius=15,
                    padding=20,
                    content=ft.Column(
                        [
                            ft.Text(
                                "☯️ Gieo Quẻ Khởi Ngày",
                                size=22,
                                weight="bold",
                                color=ft.Colors.PURPLE_300,
                            ),
                            ft.Text(
                                "Gieo quẻ Kinh Dịch để nhận lời nhắn cho ngày học tập",
                                size=12,
                                color=ft.Colors.with_opacity(0.5, ft.Colors.WHITE),
                            ),
                            ft.Container(height=10),
                            hexagram_result,
                            ft.Container(height=10),
                            ft.Button(
                                "Gieo Quẻ (Lập Quẻ)",
                                icon=ft.Icons.AUTO_AWESOME,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=10),
                                    bgcolor=ft.Colors.PURPLE_700,
                                    color=ft.Colors.WHITE,
                                ),
                                on_click=gieo_que,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                ),
            )
            content_container.controls.append(iching_card)
            content_container.controls.append(ft.Container(height=20))
            content_container.controls.append(
                ft.Divider(height=1, color=ft.Colors.GREY_800)
            )

            # --- ⚙️ SETTINGS (inline) ---
            content_container.controls.append(
                ft.Text("⚙️ Cài đặt hệ thống", size=20, weight=ft.FontWeight.W_600)
            )
            theme_dd = ft.Dropdown(
                border_radius=10,
                filled=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.PURPLE_400,
                label="Giao diện",
                options=[
                    ft.dropdown.Option("light", "Sáng ☀️"),
                    ft.dropdown.Option("dark", "Tối 🌙"),
                ],
                value=settings["theme"],
            )
            curr_dd = ft.Dropdown(
                border_radius=10,
                filled=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.PURPLE_400,
                label="Đơn vị tiền tệ",
                options=[
                    ft.dropdown.Option("VNĐ"),
                    ft.dropdown.Option("kVNĐ"),
                    ft.dropdown.Option("USD"),
                ],
                value=settings["currency"],
            )
            budget_input = ft.TextField(
                border_radius=10,
                filled=True,
                border_color=ft.Colors.TRANSPARENT,
                focused_border_color=ft.Colors.PURPLE_400,
                label="Ngân sách mục tiêu (VNĐ)",
                value=str(int(settings["monthly_budget"])),
                text_align=ft.TextAlign.RIGHT,
            )

            pomo_switch = ft.Switch(
                label="Hiển thị thời gian Pomodoro (Chế độ Trồng cây)",
                value=bool(settings.get("pomodoro_show_time", 1)),
            )

            def save_settings(e):
                try:
                    # Ép kiểu xem có phải là số không
                    safe_budget = float(budget_input.value or 0)
                except ValueError:
                    page.snack_bar = ft.SnackBar(
                        ft.Text("Ngân sách phải là con số!", color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.RED_700,
                    )
                    page.snack_bar.open = True
                    page.update()
                    return

                db.update_settings(
                    float(budget_input.value),
                    theme_dd.value,
                    curr_dd.value,
                    1 if pomo_switch.value else 0,
                )
                refresh_settings()
                render_explore()
                page.update()
                page.snack_bar = ft.SnackBar(ft.Text("Đã lưu cài đặt!"))
                page.snack_bar.open = True
                page.update()

            def confirm_hard_reset(e):
                def do_reset(ex):
                    import database as dbi

                    dbi.hard_reset()

                    reset_dialog.open = False
                    page.snack_bar = ft.SnackBar(
                        ft.Text("Đã dọn dẹp sạch sẽ!"), bgcolor=ft.Colors.GREEN_700
                    )
                    page.snack_bar.open = True

                    page.update()
                    refresh_settings()
                    render_explore()

                def cancel_reset(ex):
                    reset_dialog.open = False
                    page.update()

                def on_reset_dismiss(ex):
                    if reset_dialog in page.overlay:
                        page.overlay.remove(reset_dialog)
                    page.update()

                reset_dialog = ft.AlertDialog(
                    title=ft.Text("⚠ Cảnh Báo Nguy Hiểm"),
                    content=ft.Text("Xóa là mất trắng nhé ông giáo! Nghĩ kỹ chưa?"),
                    actions=[
                        ft.TextButton("Khỏi, sợ rồi", on_click=cancel_reset),
                        ft.Button(
                            "Xóa sập nguồn!",
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=10),
                                bgcolor=ft.Colors.PURPLE_600,
                                color=ft.Colors.WHITE,
                            ),
                            on_click=do_reset,
                        ),
                    ],
                    on_dismiss=on_reset_dismiss,
                )
                page.overlay.append(reset_dialog)
                reset_dialog.open = True
                page.update()

            reset_btn = ft.Button(
                "Hard Reset Data",
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=10),
                    bgcolor=ft.Colors.PURPLE_600,
                    color=ft.Colors.WHITE,
                ),
                icon=ft.Icons.WARNING,
                on_click=confirm_hard_reset,
            )

            content_container.controls.extend(
                [
                    theme_dd,
                    curr_dd,
                    budget_input,
                    pomo_switch,
                    ft.Button(
                        "Lưu tất cả",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            bgcolor=ft.Colors.PURPLE_600,
                            color=ft.Colors.WHITE,
                        ),
                        icon=ft.Icons.SAVE,
                        on_click=save_settings,
                    ),
                ]
            )

            # --- Sound & Notifications ---
            content_container.controls.append(ft.Container(height=20))
            content_container.controls.append(
                ft.Divider(height=1, color=ft.Colors.GREY_800)
            )
            content_container.controls.append(
                ft.Text("🔊 Âm thanh & Thông báo", size=18, weight=ft.FontWeight.W_600)
            )

            snd_settings = db.get_sound_settings()
            mute_switch = ft.Switch(
                label="Tắt tiếng (Mute)", value=bool(snd_settings.get("is_muted", 0))
            )

            def on_mute_change(e):
                val = 1 if mute_switch.value else 0
                db.update_sound_setting("is_muted", val)
                focus_manager.is_muted = bool(val)
                page.snack_bar = ft.SnackBar(
                    ft.Text(
                        "Đã tắt tiếng! 🔇" if val else "Đã bật tiếng! 🔊",
                        color=ft.Colors.WHITE,
                    ),
                    bgcolor=ft.Colors.PURPLE_700,
                )
                page.snack_bar.open = True
                page.update()

            mute_switch.on_change = on_mute_change
            content_container.controls.append(mute_switch)

            focus_path_display = os.path.basename(
                snd_settings.get("focus_start_path", "focus_start.mp3")
            )
            break_path_display = os.path.basename(
                snd_settings.get("break_start_path", "break_start.mp3")
            )

            def _open_sound_dialog(target_key, current_display):
                path_input = ft.TextField(
                    label="Đường dẫn file âm thanh (.mp3, .wav)",
                    hint_text="VD: C:/Music/my_sound.mp3",
                    border_radius=10,
                    filled=True,
                    expand=True,
                )

                def on_save(ex):
                    _apply_custom_sound(target_key, path_input.value or "")
                    sound_dialog.open = False
                    page.update()
                    render_explore()

                def on_cancel(ex):
                    sound_dialog.open = False
                    page.update()

                sound_dialog = ft.AlertDialog(
                    title=ft.Text("🔊 Đổi âm thanh"),
                    content=ft.Column(
                        [
                            ft.Text(
                                f"Hiện tại: {current_display}",
                                size=12,
                                color=ft.Colors.GREY_500,
                            ),
                            path_input,
                            ft.Text(
                                "Dán đường dẫn tuyệt đối đến file .mp3 hoặc .wav",
                                size=11,
                                italic=True,
                                color=ft.Colors.GREY_500,
                            ),
                        ],
                        tight=True,
                        spacing=10,
                    ),
                    actions=[
                        ft.TextButton("Hủy", on_click=on_cancel),
                        ft.Button(
                            "Nạp âm thanh",
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=10),
                                bgcolor=ft.Colors.PURPLE_600,
                                color=ft.Colors.WHITE,
                            ),
                            on_click=on_save,
                        ),
                    ],
                    on_dismiss=lambda ex: (
                        (page.overlay.remove(sound_dialog), page.update())
                        if sound_dialog in page.overlay
                        else None
                    ),
                )
                page.overlay.append(sound_dialog)
                sound_dialog.open = True
                page.update()

            def pick_focus_sound(e):
                _open_sound_dialog("focus_start_path", focus_path_display)

            def pick_break_sound(e):
                _open_sound_dialog("break_start_path", break_path_display)

            content_container.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.PLAY_CIRCLE, color=ft.Colors.PURPLE_400),
                    title=ft.Text("Âm thanh bắt đầu"),
                    subtitle=ft.Text(
                        focus_path_display, size=12, color=ft.Colors.GREY_500
                    ),
                    trailing=ft.Button(
                        "Đổi",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            bgcolor=ft.Colors.PURPLE_600,
                            color=ft.Colors.WHITE,
                        ),
                        on_click=pick_focus_sound,
                    ),
                )
            )
            content_container.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.FREE_BREAKFAST, color=ft.Colors.GREEN_400),
                    title=ft.Text("Âm thanh nghỉ ngơi"),
                    subtitle=ft.Text(
                        break_path_display, size=12, color=ft.Colors.GREY_500
                    ),
                    trailing=ft.Button(
                        "Đổi",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            bgcolor=ft.Colors.PURPLE_600,
                            color=ft.Colors.WHITE,
                        ),
                        on_click=pick_break_sound,
                    ),
                )
            )

            # --- 🛠 QUẢN LÝ DỮ LIỆU ---
            def handle_csv_import(e):
                if is_mobile and csv_picker is not None:
                    # Chạy mượt trên điện thoại
                    csv_picker.pick_files(
                        allow_multiple=False, allowed_extensions=["csv"]
                    )
                else:
                    # Bị lỗi trên Windows -> Hiện bảng nhập đường dẫn như âm thanh
                    path_input = ft.TextField(
                        label="Đường dẫn file CSV tuyệt đối",
                        hint_text="VD: C:/Downloads/template.csv",
                        border_radius=10,
                        filled=True,
                        expand=True,
                    )

                    def on_dialog_save(ex):
                        import os

                        path = path_input.value.strip()
                        if path and os.path.isfile(path):
                            process_csv_file(path)  # Đã viết ở trên cùng
                            csv_dialog.open = False
                            page.update()
                        else:
                            page.snack_bar = ft.SnackBar(
                                ft.Text("Không tìm thấy file!", color=ft.Colors.WHITE),
                                bgcolor=ft.Colors.RED_700,
                            )
                            page.snack_bar.open = True
                            page.update()

                    def on_dialog_cancel(ex):
                        csv_dialog.open = False
                        page.update()

                    def on_dialog_dismiss(ex):
                        if csv_dialog in page.overlay:
                            page.overlay.remove(csv_dialog)
                        page.update()

                    csv_dialog = ft.AlertDialog(
                        title=ft.Text("📥 Nhập CSV (Chế độ Windows)"),
                        content=ft.Column(
                            [
                                path_input,
                                ft.Text(
                                    "Dán đường dẫn trực tiếp do Flet FilePicker bị lỗi trên Windows.",
                                    size=12,
                                    italic=True,
                                ),
                            ],
                            tight=True,
                        ),
                        actions=[
                            ft.TextButton("Hủy", on_click=on_dialog_cancel),
                            ft.Button(
                                "Nạp dữ liệu",
                                bgcolor=ft.Colors.PURPLE_600,
                                color=ft.Colors.WHITE,
                                on_click=on_dialog_save,
                            ),
                        ],
                        on_dismiss=on_dialog_dismiss,  # <<< Gắn thêm cỗ máy dọn rác vào đây
                    )

                    page.overlay.append(csv_dialog)
                    csv_dialog.open = True
                    page.update()

            content_container.controls.append(ft.Container(height=20))
            content_container.controls.append(
                ft.Card(
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.PURPLE_700),
                    content=ft.Container(
                        padding=15,
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Icon(
                                            ft.Icons.STORAGE, color=ft.Colors.PURPLE_300
                                        ),
                                        ft.Text(
                                            "🛠 Quản lý Dữ liệu",
                                            size=18,
                                            weight="bold",
                                            color=ft.Colors.PURPLE_200,
                                        ),
                                    ],
                                    spacing=10,
                                ),
                                ft.Text(
                                    "Sao lưu và nhập liệu hệ thống",
                                    size=12,
                                    color=ft.Colors.with_opacity(0.5, ft.Colors.WHITE),
                                ),
                                ft.Container(height=10),
                                ft.Button(
                                    "Nhập dữ liệu từ CSV template",
                                    icon=ft.Icons.UPLOAD_FILE,
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                        bgcolor=ft.Colors.PURPLE_800,
                                        color=ft.Colors.WHITE,
                                    ),
                                    on_click=handle_csv_import,
                                ),
                            ]
                        ),
                    ),
                )
            )

            content_container.controls.append(ft.Container(height=30))
            content_container.controls.append(reset_btn)

            page.update()
        except Exception as e:
            import traceback

            content_container.controls.clear()
            content_container.controls.append(
                ft.Text(
                    f"LỖI RỒI ÔNG GIÁO ƠI:\n{str(e)}\n\n{traceback.format_exc()}",
                    bgcolor=ft.Colors.RED_500,
                    selectable=True,
                )
            )
            page.update()

    # Initial UI Build
    page.navigation_bar = nav_bar
    main_wrapper = ft.Container(
        content=content_container,
        border_radius=15,
        bgcolor=ft.Colors.TRANSPARENT,
        padding=10,
        expand=True,
    )
    render_focus()
    page.add(ft.SafeArea(main_wrapper, expand=True))
    page.update()


ft.run(main)
