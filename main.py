import flet as ft
import database as db
from datetime import datetime
import random
import time
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

BOT_PHRASES = {
    "INCOME": ["Lúa về rồi ông ơi! 🤖", "Ông giáo lại cá kiếm à? Tuyệt! 😎"],
    "EXPENSE": [
        "Lại chi nữa à? Nhịn ăn sáng đi nhé! 😠",
        "Tôi ghi xé sổ rồi. Cẩn thận ví mỏng! 🤖",
    ],
    "HABIT_PRAISE": [
        "Quá đỉnh ông giáo! Cứ thế mà gõ code! 😎",
        "Thói quen chuẩn đét! Cứ thế tiến lên! 😎",
    ],
    "MISSED_LOGS": [
        "Hôm qua ông quên cái gì đấy? Dám lười à? 😠",
        "Ông giáo có phải đang thả lỏng quá không? 😠",
    ],
}


class FocusManager:
    def __init__(
        self, page: ft.Page, get_settings_fn, bot_text_ref, audio_focus, audio_break
    ):
        self.page = page
        self.get_settings = get_settings_fn
        self.bot_text = bot_text_ref

        # Nhận động cơ âm thanh của Mobile
        self.audio_focus = audio_focus
        self.audio_break = audio_break
        self.is_muted = False

        # --- XP/Level from DB ---

        self.running = False
        self.mode = "work"
        self.time_left = 30 * 60
        self.total_time = 30 * 60

        # --- XP/Level from DB ---
        try:
            self.current_xp, self.current_level = db.get_xp_level()
        except:
            self.current_xp, self.current_level = 0, 1

        self.bot_text.visible = False
        self.bot_text.value = ""
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
            "30:00", size=70, weight=ft.FontWeight.W_600, color=ft.colors.WHITE
        )
        self.overlay_status = ft.Text(
            "Đang tập trung...", size=20, color=ft.colors.WHITE
        )
        self.health_text = ft.Text(
            random.choice(self.health_quotes),
            italic=True,
            size=14,
            text_align=ft.TextAlign.CENTER,
            color=ft.colors.with_opacity(0.85, ft.colors.WHITE),
        )
        self.close_btn = ft.IconButton(
            icon=ft.icons.CLOSE,
            on_click=self.close_overlay,
            icon_size=30,
            icon_color=ft.colors.WHITE,
        )

        self.pomodoro_overlay = ft.Container(
            expand=True,
            visible=False,
            bgcolor=ft.colors.with_opacity(0.98, ft.colors.BLACK),
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
                                color=ft.colors.with_opacity(0.15, ft.colors.WHITE),
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
            "30:00", size=40, weight=ft.FontWeight.W_600, color=ft.colors.WHITE
        )
        self.pomo_progress = ft.ProgressBar(
            value=0,
            color=ft.colors.PURPLE_400,
            bgcolor=ft.colors.PURPLE_50,
            height=8,
        )

        self.play_btn = ft.IconButton(
            icon=ft.icons.PLAY_ARROW,
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
            color=ft.colors.WHITE,
            text_align=ft.TextAlign.CENTER,
        )

        # Timer display setup
        self.pomo_display.size = 65
        self.pomo_display.color = ft.colors.WHITE
        self.pomo_display.weight = "bold"

        # ProgressRing (circular timer)
        self.pomo_progress = ft.ProgressRing(
            width=280,
            height=280,
            stroke_width=8,
            color=C_PRI,
            bgcolor=ft.colors.with_opacity(0.1, ft.colors.WHITE),
            value=1.0,
        )

        timer_circle = ft.Container(
            alignment=ft.alignment.Alignment(0, 0),
            padding=ft.padding.symmetric(vertical=20),
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
                                    color=ft.colors.with_opacity(0.6, ft.colors.WHITE),
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
            icon=ft.icons.RESTART_ALT,
            icon_size=28,
            icon_color=ft.colors.with_opacity(0.5, ft.colors.WHITE),
            on_click=self.close_overlay,
        )

        controls_row = ft.Row(
            [self.reset_btn, play_btn_container],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=30,
        )

        # Tree Link XP bar (compact inline)
        self.tree_xp_bar = ft.ProgressBar(
            value=current_xp / 500,
            color=C_TER,
            bgcolor=ft.colors.with_opacity(0.1, ft.colors.WHITE),
            height=5,
        )
        tree_link_row = ft.Container(
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            border_radius=15,
            bgcolor=ft.colors.with_opacity(0.08, ft.colors.WHITE),
            content=ft.Row(
                [
                    ft.Text(species_emoji, size=22),
                    ft.Column(
                        [
                            ft.Text(
                                f"Level {current_level}",
                                size=13,
                                weight="bold",
                                color=ft.colors.WHITE,
                            ),
                            self.tree_xp_bar,
                            ft.Text(
                                f"{current_xp}/500 XP",
                                size=10,
                                color=ft.colors.with_opacity(0.6, ft.colors.WHITE),
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=10,
            ),
        )

        self.local_bot_text = ft.Text(
            color=ft.colors.with_opacity(0.85, ft.colors.WHITE), size=13
        )
        self.bot_container = ft.Container(
            visible=False,
            padding=15,
            border_radius=15,
            bgcolor=ft.colors.with_opacity(0.1, ft.colors.WHITE),
            content=ft.Row(
                [
                    ft.Icon(ft.icons.SMART_TOY, color=C_PRI, size=20),
                    self.local_bot_text,
                ],
                spacing=10,
            ),
        )
        self.bot_text.size = 13

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
                    self.bot_container,
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
            ft.colors.WHITE
            if self.mode == "work"
            else ft.colors.with_opacity(0.7, ft.colors.WHITE)
        )
        self.pomo_progress.color = (
            ft.colors.PURPLE_400 if self.mode == "work" else ft.colors.PURPLE_200
        )

        try:
            self.pomo_display.update()
            self.pomo_progress.update()
            self.pomo_slider.update()
        except:
            pass

    async def _timer_task(self):
        import asyncio

        # Refresh mute status from DB before playing
        try:
            snd = db.get_sound_settings()
            self.is_muted = bool(snd.get("is_muted", 0))
        except:
            pass
        if self.audio_focus and not self.is_muted:
            self.audio_focus.play()

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

                # Ép Flet cập nhật toàn bộ trang để không bị lỡ nhịp
                self.page.update()

                # --- XỬ LÝ KHI ĐỒNG HỒ VỀ 00:00 ---
                if self.time_left <= 0:
                    if self.mode == "work":
                        # 🌳 CỘNG XP TREE LINK (DB-driven)
                        earned_xp = max(10, int(self.total_time / 60) * 10)

                        old_level = self.current_level
                        self.current_xp, self.current_level = db.add_xp(earned_xp)

                        # Check Level Up
                        if self.current_level > old_level:
                            # Play level up sound
                            try:
                                if not self.is_muted:
                                    # Reuse break sound as level-up fanfare
                                    if self.audio_break:
                                        self.audio_break.play()
                            except:
                                pass
                            try:
                                self.page.snack_bar = ft.SnackBar(
                                    ft.Text(
                                        f"🎉 LÊN CẤP {self.current_level}! Mở khóa: {db.get_species_emoji(self.current_level)}!",
                                        color=ft.colors.WHITE,
                                        weight="bold",
                                    ),
                                    bgcolor=ft.colors.PINK_600,
                                )
                                self.page.snack_bar.open = True
                            except:
                                pass

                        # Tiến hóa sinh vật from DB species map
                        new_emoji = db.get_species_emoji(self.current_level)
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
                        except:
                            pass

                        # Chuyển sang giờ nghỉ
                        self.mode = "rest"
                        self.time_left = max(1, int(self.total_time / 5))
                        self.total_time = self.time_left

                        # Play break sound
                        try:
                            if self.audio_break and not self.is_muted:
                                self.audio_break.play()
                        except:
                            pass

                        try:
                            self.page.launch_url("vibrate:500")
                        except:
                            pass

                        try:
                            self.page.snack_bar = ft.SnackBar(
                                ft.Text(
                                    f"Đã cộng +{earned_xp} XP! Nghỉ ngơi thôi. 🌳",
                                    color=ft.colors.WHITE,
                                ),
                                bgcolor=ft.colors.GREEN_700,
                            )
                            self.page.snack_bar.open = True
                        except:
                            pass
                        self.page.update()
                    else:
                        # Hết giờ nghỉ -> Quay lại giờ làm
                        self.running = False
                        self.mode = "work"
                        self.time_left = int(self.pomo_slider.value) * 60
                        self.total_time = self.time_left
                        self.play_btn.icon = ft.icons.PLAY_ARROW

                        try:
                            self.page.snack_bar = ft.SnackBar(
                                ft.Text(
                                    "Hết giờ nghỉ! Quay lại làm việc nào. 🚀",
                                    color=ft.colors.WHITE,
                                ),
                                bgcolor=ft.colors.BLUE_700,
                            )
                            self.page.snack_bar.open = True
                        except:
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

    def apply_penalty(self):
        """KỶ LUẬT SẮT: Penalty when window loses focus during work."""
        self.running = False
        self.play_btn.icon = ft.icons.PLAY_ARROW

        # Deduct 50 XP (min 0)
        self.current_xp, self.current_level = db.deduct_xp(50)

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
                    color=ft.colors.WHITE,
                    weight="bold",
                ),
                bgcolor=ft.colors.RED_700,
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
            self.play_btn.icon = ft.icons.STOP

            # Play focus start sound
            if self.audio_focus and not self.is_muted:
                self.audio_focus.play()

            # Show bot with starting message
            self.local_bot_text.value = "Sẵn sàng vào việc chưa ông giáo? 🤖🌲"
            self.bot_container.visible = True

            self.health_text.value = random.choice(self.health_quotes)
            self.pomodoro_overlay.visible = True
            self.page.update()

            self.page.run_task(self._timer_task)
            self.page.run_task(self.update_quotes_task)
        else:
            self.running = False
            self.play_btn.icon = ft.icons.PLAY_ARROW
            self.time_left = int(self.pomo_slider.value) * 60
            self.total_time = self.time_left
            # Hide bot when stopped
            self.bot_container.visible = False

        self.play_btn.update()
        self.update_ui()

    def close_overlay(self, e):
        self.running = False
        self.time_left = int(self.pomo_slider.value) * 60
        self.total_time = self.time_left
        self.play_btn.icon = ft.icons.PLAY_ARROW
        self.pomodoro_overlay.visible = False
        self.bot_container.visible = False
        self.update_ui()
        self.page.update()

    def reload_sounds(self):
        """Reload sound settings from DB and update ft.Audio sources."""
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


def main(page: ft.Page):
    page.title = "Studygram"
    db.init_db()
    settings = db.get_settings()
    audio_focus = ft.Audio(src="sounds/focus_start.mp3", autoplay=False)
    audio_break = ft.Audio(src="sounds/break_start.mp3", autoplay=False)
    page.overlay.extend([audio_focus, audio_break])

    # --- FilePicker for Sound (MOBILE SAFE) ---
    target_sound_key_ref = [""]

    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0 and target_sound_key_ref[0]:
            _apply_custom_sound(target_sound_key_ref[0], e.files[0].path)
            refresh_settings()
            try:
                render_settings()
            except:
                pass

    sound_file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(sound_file_picker)
    page.theme_mode = (
        ft.ThemeMode.LIGHT if settings["theme"] == "light" else ft.ThemeMode.DARK
    )
    page.theme = ft.Theme(color_scheme_seed=ft.colors.PURPLE, use_material3=True)
    page.bgcolor = "#F8F9FA" if settings["theme"] == "light" else "#121212"
    page.padding = 15
    page.window_full_screen = False

    # --- STRICT MODE: Window blur penalty ---
    def on_window_event(e):
        if e.data == "blur" and focus_manager.running and focus_manager.mode == "work":
            focus_manager.apply_penalty()

    page.window_width = 390
    # --- ĐÂY MỚI LÀ CHỖ ĐỂ KHỞI TẠO (CHẠY 1 LẦN) ---

    # --- Bot Card (Bản Titanium - Chống mọi loại lỗi) ---
    bot_text = ft.Text(
        value="Studygram Bot: Chào ông giáo! Sẵn sàng học chưa?",
        size=14,
        italic=True,
        color="onSurface",  # Dùng string an toàn hơn gọi ft.colors
    )

    bot_card = ft.Card(
        elevation=0,
        color=ft.colors.TRANSPARENT,  # BẮT BUỘC LÀ bgcolor, tuyệt đối không dùng color ở đây
        margin=ft.margin.only(bottom=15),
        content=ft.Container(
            bgcolor=ft.colors.with_opacity(0.15, ft.colors.WHITE),
            padding=15,
            border=ft.border.all(1, ft.colors.PURPLE_400),
            border_radius=10,
            content=ft.Row(controls=[bot_text], wrap=True),  # Ép chữ phải xuống dòng
        ),
    )
    global_habit_count = 0

    def update_bot(situation):
        import random

        if situation == "OVER_LIMIT":
            bot_card.content.bgcolor = (
                ft.colors.RED_900 if settings["theme"] == "dark" else ft.colors.RED_100
            )
            bot_text.bgcolor = (
                ft.colors.WHITE if settings["theme"] == "dark" else ft.colors.RED_900
            )
            page.snack_bar = ft.SnackBar(
                ft.Text(
                    "CẢNH BÁO! Vượt ngân sách rồi ông giáo ơi!", color=ft.colors.WHITE
                ),
                bgcolor=ft.colors.RED_700,
            )
            page.snack_bar.open = True
            page.update()
        else:
            is_d = settings["theme"] == "dark"
            bot_card.content.bgcolor = (
                ft.colors.with_opacity(0.1, ft.colors.PURPLE)
                if is_d
                else ft.colors.PURPLE_50
            )
            bot_text.color = "onSurface"

            if random.random() < 0.3:
                bot_text.value = f"Studygram Bot: {random.choice(HUST_QUOTES)}"
            else:
                opts = BOT_PHRASES.get(situation, ["Xin chào ông giáo! 🤖"])
                bot_text.value = f"Studygram Bot: {random.choice(opts)}"

        try:
            bot_text.update()
            bot_card.update()
        except:
            pass

    page.window_height = 844

    def _apply_custom_sound(target_key, file_path_str):
        """Copy a sound file to assets/sounds and update DB + ft.Audio."""
        try:
            file_path_str = file_path_str.strip()
            if not file_path_str or not os.path.isfile(file_path_str):
                page.snack_bar = ft.SnackBar(
                    ft.Text(
                        "Không tìm thấy file! Kiểm tra lại đường dẫn.",
                        color=ft.colors.WHITE,
                    ),
                    bgcolor=ft.colors.RED_700,
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
                ft.Text(f"Đã nạp: {filename} 🔊", color=ft.colors.WHITE),
                bgcolor=ft.colors.GREEN_700,
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
        page.theme = ft.Theme(color_scheme_seed=ft.colors.PURPLE, use_material3=True)
        page.bgcolor = "#F8F9FA" if settings["theme"] == "light" else "#121212"
        focus_manager.update_ui()
        page.update()

    # --- Pomodoro System ---
    def _get_settings():
        return settings

    focus_manager = FocusManager(
        page, _get_settings, bot_text, audio_focus, audio_break
    )
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
            render_habits()
        elif idx == 1:
            render_finance()
        elif idx == 2:
            render_focus()
        elif idx == 3:
            render_settings()
        page.update()

    nav_bar = ft.NavigationBar(
        selected_index=0,
        destinations=[
            ft.NavigationDestination(
                label="Habits", icon=ft.icons.CHECK_CIRCLE_OUTLINE
            ),
            ft.NavigationDestination(label="Finance", icon=ft.icons.ATTACH_MONEY),
            ft.NavigationDestination(label="Focus", icon=ft.icons.CENTER_FOCUS_STRONG),
            ft.NavigationDestination(label="Settings", icon=ft.icons.SETTINGS),
        ],
        on_change=handle_tab_change,
    )

    content_container = ft.Column(expand=True, scroll="auto", spacing=20)

    # --- Render Functions ---
    def render_habits():
        try:
            content_container.controls.clear()
            content_container.controls.append(bot_card)

            habits = db.get_all_habits()
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_weekday = str(datetime.now().weekday())
            done_ids = db.get_habit_logs_for_date(today_str)

            import datetime as dt

            # Logic MISSED_YESTERDAY
            yesterday_str = (datetime.now() - dt.timedelta(days=1)).strftime("%Y-%m-%d")
            y_done = db.get_habit_logs_for_date(yesterday_str)
            y_habits = [
                h
                for h in habits
                if str((datetime.now() - dt.timedelta(days=1)).weekday())
                in (dict(h).get("frequency") or "0,1,2,3,4,5,6")
            ]
            if len(y_habits) > 0 and len(y_done) == 0:
                update_bot("MISSED_LOGS")

            content_container.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Studygram",
                        size=24,
                        weight=ft.FontWeight.W_600,
                        color=ft.colors.PURPLE_400,
                    ),
                    margin=ft.margin.only(top=20),
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
                    color=ft.colors.GREEN,
                    bgcolor=ft.colors.GREEN_100,
                    height=8,
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
                border_color=ft.colors.TRANSPARENT,
                focused_border_color=ft.colors.PURPLE_400,
                expand=True,
            )
            desc_input = ft.TextField(
                label="Mô tả chi tiết",
                border_radius=10,
                filled=True,
                border_color=ft.colors.TRANSPARENT,
                focused_border_color=ft.colors.PURPLE_400,
                multiline=True,
                expand=True,
            )
            weight_dd = ft.Dropdown(
                border_radius=10,
                filled=True,
                border_color=ft.colors.TRANSPARENT,
                focused_border_color=ft.colors.PURPLE_400,
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
                    render_habits()
                    page.update()

            add_btn = ft.ElevatedButton(
                "Thêm Thói Quen",
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=10),
                    bgcolor=ft.colors.PURPLE_600,
                    color=ft.colors.WHITE,
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
                ft.Divider(height=1, color=ft.colors.GREY_800)
            )

            habit_list = ft.Column(spacing=10)
            if not filtered_habits:
                habit_list.controls.append(
                   py ft.Text(
                        "Nghỉ ngơi thôi! Nay không có lịch thói quen nào.",
                        color=ft.colors.GREY_500,
                    )
                )
            else:
                for h in filtered_habits:
                    is_done = h["id"] in done_ids
                    freq = dict(h).get("frequency") or "0,1,2,3,4,5,6"
                    streak = db.get_habit_streak(h["id"], freq)

                    def toggle_cb(e, hid=h["id"]):
                        db.toggle_habit_log(hid, today_str, e.control.value)
                        if e.control.value:
                            nonlocal global_habit_count
                            global_habit_count += 1
                            if global_habit_count % 5 == 0:
                                update_bot("HABIT_PRAISE")
                        render_habits()
                        page.update()

                    def del_h(e, hid=h["id"]):
                        db.delete_habit(hid)
                        render_habits()
                        page.update()

                    habit_list.controls.append(
                        ft.Container(
                            padding=10,
                            border_radius=10,
                            bgcolor=ft.colors.with_opacity(0.02, ft.colors.ON_SURFACE),
                            content=ft.Row(
                                [
                                    ft.Checkbox(
                                        label=f"{h['name']} (W:{h['weight']} | Chuỗi: 🔥 {streak})",
                                        value=is_done,
                                        on_change=toggle_cb,
                                        expand=True,
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.DELETE_OUTLINE,
                                        icon_color=ft.colors.RED_400,
                                        on_click=del_h,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                        )
                    )
            content_container.controls.append(habit_list)

            page.update()
        except Exception as e:
            import traceback

            content_container.controls.clear()
            content_container.controls.append(
                ft.Text(
                    f"LỖI RỒI ÔNG GIÁO ƠI:\n{str(e)}\n\n{traceback.format_exc()}",
                    bgcolor=ft.colors.RED_500,
                    selectable=True,
                )
            )
            page.update()

    def render_finance(filter_type="All"):
        try:
            content_container.controls.clear()
            content_container.controls.append(bot_card)
            accounts = db.get_all_accounts()
            budget = settings["monthly_budget"]
            month_start = datetime.now().strftime("%Y-%m-01")
            spent = db.get_monthly_expenses(month_start)

            content_container.controls.append(
                ft.Text("🎯 Ngân sách tháng này", size=20, weight=ft.FontWeight.W_600)
            )
            progress = min(spent / budget, 1.0) if budget > 0 else 1.0
            if progress >= 1.0:
                update_bot("OVER_LIMIT")
            color = (
                ft.colors.GREEN
                if progress < 0.5
                else ft.colors.ORANGE
                if progress < 0.8
                else ft.colors.RED
            )
            content_container.controls.append(
                ft.ProgressBar(value=progress, color=color, bgcolor=ft.colors.GREY_200)
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
                        ft.colors.PURPLE_400,
                        ft.colors.INDIGO_400,
                        ft.colors.BLUE_400,
                        ft.colors.TEAL_400,
                        ft.colors.GREEN_400,
                        ft.colors.ORANGE_400,
                        ft.colors.RED_400,
                    ]
                    for i, (cat, amt) in enumerate(cat_expenses.items()):
                        pie_sections.append(
                            ft.PieChartSection(
                                amt,
                                title=f"{cat}\n{int(amt / spent * 100)}%",
                                title_style=ft.TextStyle(
                                    size=12,
                                    bgcolor=ft.colors.with_opacity(
                                        0.15, ft.colors.WHITE
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
                            content=pie_chart, alignment=ft.alignment.center, padding=10
                        )
                    )
                except AttributeError:
                    content_container.controls.append(
                        ft.Text(
                            "PieChart không khả dụng trên phiên bản Flet này.",
                            size=12,
                            color=ft.colors.GREY_500,
                            italic=True,
                        )
                    )

            content_container.controls.append(ft.Container(height=20))
            content_container.controls.append(
                ft.Divider(height=1, color=ft.colors.GREY_800)
            )

            content_container.controls.append(
                ft.Text("🏦 Quản lý Ví tiền", size=18, weight=ft.FontWeight.W_600)
            )
            acc_name = ft.TextField(
                border_radius=10,
                filled=True,
                border_color=ft.colors.TRANSPARENT,
                focused_border_color=ft.colors.PURPLE_400,
                label="Tên ví",
                expand=True,
            )
            acc_bal = ft.TextField(
                border_radius=10,
                filled=True,
                border_color=ft.colors.TRANSPARENT,
                focused_border_color=ft.colors.PURPLE_400,
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
                ft.Row([acc_name, acc_bal, ft.IconButton(ft.icons.ADD, on_click=add_a)])
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
                                ft.icons.DELETE,
                                icon_color=ft.colors.RED_300,
                                on_click=del_a,
                            ),
                        ]
                    )
                )
            content_container.controls.append(ft.Container(height=20))
            content_container.controls.append(
                ft.Divider(height=1, color=ft.colors.GREY_800)
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
                border_color=ft.colors.TRANSPARENT,
                focused_border_color=ft.colors.PURPLE_400,
                options=[ft.dropdown.Option(a["name"]) for a in accounts],
                label="Chọn ví",
                expand=True,
            )
            acc_select2 = ft.Dropdown(
                border_radius=10,
                filled=True,
                border_color=ft.colors.TRANSPARENT,
                focused_border_color=ft.colors.PURPLE_400,
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
                border_color=ft.colors.TRANSPARENT,
                focused_border_color=ft.colors.PURPLE_400,
                label="Số tiền",
                value="0",
            )
            note_in = ft.TextField(
                border_radius=10,
                filled=True,
                border_color=ft.colors.TRANSPARENT,
                focused_border_color=ft.colors.PURPLE_400,
                label="Ghi chú",
            )

            def save_t(e):
                amt = float(amount_in.value or 0)
                if amt <= 0:
                    return
                if t_type.value == "transfer":
                    if acc_select.value != acc_select2.value:
                        id_from = next(
                            a["id"] for a in accounts if a["name"] == acc_select.value
                        )
                        id_to = next(
                            a["id"] for a in accounts if a["name"] == acc_select2.value
                        )
                        db.transfer_funds(
                            id_from, id_to, amt, acc_select.value, acc_select2.value
                        )
                else:
                    aid = next(
                        a["id"] for a in accounts if a["name"] == acc_select.value
                    )
                    db.add_transaction(
                        aid, amt, t_type.value, selected_cat, note_in.value
                    )
                    if t_type.value == "income":
                        update_bot("INCOME")
                    elif t_type.value == "expense":
                        update_bot("EXPENSE")
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
                    ft.ElevatedButton(
                        "Lưu giao dịch",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            bgcolor=ft.colors.PURPLE_600,
                            color=ft.colors.WHITE,
                        ),
                        on_click=save_t,
                    ),
                ]
            )

            content_container.controls.append(ft.Container(height=20))
            content_container.controls.append(
                ft.Divider(height=1, color=ft.colors.GREY_800)
            )

            filter_dd = ft.Dropdown(
                border_radius=10,
                filled=True,
                border_color=ft.colors.TRANSPARENT,
                focused_border_color=ft.colors.PURPLE_400,
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

            history_list = ft.Column(spacing=10)
            txs = db.get_recent_transactions(15, filter_type)
            if not txs:
                history_list.controls.append(
                    ft.Text("Chưa có giao dịch nào.", color=ft.colors.GREY_500)
                )
            else:
                for tx in txs:
                    icon = (
                        ft.icons.ARROW_DOWNWARD
                        if tx["transaction_type"] == "expense"
                        else ft.icons.ARROW_UPWARD
                    )
                    bgcolor = (
                        ft.colors.RED_500
                        if tx["transaction_type"] == "expense"
                        else ft.colors.GREEN_500
                    )
                    history_list.controls.append(
                        ft.Container(
                            padding=10,
                            border_radius=10,
                            bgcolor=ft.colors.with_opacity(0.02, ft.colors.ON_SURFACE),
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
                    bgcolor=ft.colors.RED_500,
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
                        color=ft.colors.PURPLE_400,
                    ),
                    margin=ft.margin.only(top=20),
                )
            )

            content_container.controls.append(focus_manager.pomodoro_card)
            content_container.controls.append(
                ft.Divider(height=1, color=ft.colors.GREY_800)
            )

            # --- Random Quote ---
            quotes_data = db.get_all_quotes()
            quote_card = ft.Container(
                bgcolor=ft.colors.with_opacity(0.05, ft.colors.ON_SURFACE),
                padding=15,
                border_radius=15,
                margin=ft.margin.only(bottom=20),
            )
            if quotes_data:
                q = random.choice(quotes_data)
                quote_card.content = ft.Column(
                    [
                        ft.Text(
                            f'💡 "{q["text"]}"',
                            weight=ft.FontWeight.W_600,
                            color=ft.colors.INDIGO_700,
                        ),
                        ft.Text(
                            f" — {q['author']}",
                            italic=True,
                            size=12,
                            color=ft.colors.GREY_700,
                        ),
                    ]
                )
            else:
                quote_card.content = ft.Text(
                    "💡 Trạm Quotes đang trống...", color=ft.colors.INDIGO_700
                )
            content_container.controls.append(quote_card)

            # --- 30-Day Heatmap ---
            import datetime as dt

            today_dt = dt.date.today()

            empty_c = ft.colors.with_opacity(0.1, ft.colors.WHITE)

            def get_intensity_green(ratio):
                if ratio <= 0:
                    return empty_c
                if ratio < 0.3:
                    return ft.colors.GREEN_200
                if ratio < 0.6:
                    return ft.colors.GREEN_400
                return ft.colors.GREEN_700

            def get_intensity_blue(count):
                if count <= 0:
                    return empty_c
                if count < 2:
                    return ft.colors.BLUE_200
                if count < 4:
                    return ft.colors.BLUE_400
                return ft.colors.BLUE_700

            def get_intensity_purple(seconds):
                if seconds <= 0:
                    return empty_c
                if seconds < 1500:
                    return ft.colors.PURPLE_200
                if seconds < 3600:
                    return ft.colors.PURPLE_400
                return ft.colors.PURPLE_700

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
                color=ft.colors.with_opacity(0.15, ft.colors.WHITE),
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
                ft.Divider(height=1, color=ft.colors.GREY_800)
            )

            # --- Quote Collection ---
            content_container.controls.append(
                ft.Text("✒️ Thêm Quote mới", size=20, weight=ft.FontWeight.W_600)
            )
            q_text = ft.TextField(
                border_radius=10,
                filled=True,
                border_color=ft.colors.TRANSPARENT,
                focused_border_color=ft.colors.PURPLE_400,
                label="Câu nói tâm đắc",
                multiline=True,
            )
            q_author = ft.TextField(
                border_radius=10,
                filled=True,
                border_color=ft.colors.TRANSPARENT,
                focused_border_color=ft.colors.PURPLE_400,
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
                    ft.ElevatedButton(
                        "Lưu Quote",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            bgcolor=ft.colors.PURPLE_600,
                            color=ft.colors.WHITE,
                        ),
                        on_click=save_q,
                    ),
                ]
            )
            content_container.controls.append(
                ft.Divider(height=1, color=ft.colors.GREY_800)
            )
            content_container.controls.append(
                ft.Text("📚 Bộ sưu tập Quote", size=18, weight=ft.FontWeight.W_600)
            )

            quote_list = ft.Column(spacing=10)
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
                                            color=ft.colors.GREY_600,
                                        ),
                                    ],
                                    expand=True,
                                ),
                                ft.IconButton(
                                    ft.icons.DELETE_OUTLINE,
                                    icon_color=ft.colors.RED_300,
                                    on_click=del_q,
                                ),
                            ]
                        ),
                        padding=10,
                        border=ft.border.all(1, ft.colors.GREY_200),
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
                    bgcolor=ft.colors.RED_500,
                    selectable=True,
                )
            )
            page.update()

    def render_settings():
        try:
            content_container.controls.clear()
            content_container.controls.append(
                ft.Text("⚙️ Cài đặt hệ thống", size=20, weight=ft.FontWeight.W_600)
            )
            theme_dd = ft.Dropdown(
                border_radius=10,
                filled=True,
                border_color=ft.colors.TRANSPARENT,
                focused_border_color=ft.colors.PURPLE_400,
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
                border_color=ft.colors.TRANSPARENT,
                focused_border_color=ft.colors.PURPLE_400,
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
                border_color=ft.colors.TRANSPARENT,
                focused_border_color=ft.colors.PURPLE_400,
                label="Ngân sách mục tiêu (VNĐ)",
                value=str(int(settings["monthly_budget"])),
                text_align=ft.TextAlign.RIGHT,
            )

            pomo_switch = ft.Switch(
                label="Hiển thị thời gian Pomodoro (Chế độ Trồng cây)",
                value=bool(settings.get("pomodoro_show_time", 1)),
            )

            def save_settings(e):
                db.update_settings(
                    float(budget_input.value),
                    theme_dd.value,
                    curr_dd.value,
                    1 if pomo_switch.value else 0,
                )
                refresh_settings()
                render_settings()
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
                        ft.Text("Đã dọn dẹp sạch sẽ!"), bgcolor=ft.colors.GREEN_700
                    )
                    page.snack_bar.open = True

                    bot_text.value = "Studygram Bot: Đã dọn sạch lỗi rồi ông giáo! Vào Tab Focus 'trồng cây' thử xem có bị văng nữa không nhé! 😎"
                    try:
                        bot_text.update()
                    except:
                        pass

                    page.update()
                    refresh_settings()
                    render_settings()

                def cancel_reset(ex):
                    reset_dialog.open = False
                    page.update()

                reset_dialog = ft.AlertDialog(
                    title=ft.Text("⚠ Cảnh Báo Nguy Hiểm"),
                    content=ft.Text("Xóa là mất trắng nhé ông giáo! Nghĩ kỹ chưa?"),
                    actions=[
                        ft.TextButton("Khỏi, sợ rồi", on_click=cancel_reset),
                        ft.ElevatedButton(
                            "Xóa sập nguồn!",
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=10),
                                bgcolor=ft.colors.PURPLE_600,
                                color=ft.colors.WHITE,
                            ),
                            on_click=do_reset,
                        ),
                    ],
                )
                page.overlay.append(reset_dialog)
                reset_dialog.open = True
                page.update()

            reset_btn = ft.ElevatedButton(
                "Hard Reset Data",
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=10),
                    bgcolor=ft.colors.PURPLE_600,
                    color=ft.colors.WHITE,
                ),
                icon=ft.icons.WARNING,
                on_click=confirm_hard_reset,
            )

            content_container.controls.extend(
                [
                    theme_dd,
                    curr_dd,
                    budget_input,
                    pomo_switch,
                    ft.ElevatedButton(
                        "Lưu tất cả",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            bgcolor=ft.colors.PURPLE_600,
                            color=ft.colors.WHITE,
                        ),
                        icon=ft.icons.SAVE,
                        on_click=save_settings,
                    ),
                ]
            )

            # --- Sound & Notifications ---
            content_container.controls.append(ft.Container(height=20))
            content_container.controls.append(
                ft.Divider(height=1, color=ft.colors.GREY_800)
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
                        color=ft.colors.WHITE,
                    ),
                    bgcolor=ft.colors.PURPLE_700,
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

            def pick_focus_sound(e):
                target_sound_key_ref[0] = "focus_start_path"
                sound_file_picker.pick_files(
                    allow_multiple=False, allowed_extensions=["mp3", "wav"]
                )

            def pick_break_sound(e):
                target_sound_key_ref[0] = "break_start_path"
                sound_file_picker.pick_files(
                    allow_multiple=False, allowed_extensions=["mp3", "wav"]
                )

            content_container.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.icons.PLAY_CIRCLE, color=ft.colors.PURPLE_400),
                    title=ft.Text("Âm thanh bắt đầu"),
                    subtitle=ft.Text(
                        focus_path_display, size=12, color=ft.colors.GREY_500
                    ),
                    trailing=ft.ElevatedButton(
                        "Đổi",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            bgcolor=ft.colors.PURPLE_600,
                            color=ft.colors.WHITE,
                        ),
                        on_click=pick_focus_sound,
                    ),
                )
            )
            content_container.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.icons.FREE_BREAKFAST, color=ft.colors.GREEN_400),
                    title=ft.Text("Âm thanh nghỉ ngơi"),
                    subtitle=ft.Text(
                        break_path_display, size=12, color=ft.colors.GREY_500
                    ),
                    trailing=ft.ElevatedButton(
                        "Đổi",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            bgcolor=ft.colors.PURPLE_600,
                            color=ft.colors.WHITE,
                        ),
                        on_click=pick_break_sound,
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
                    bgcolor=ft.colors.RED_500,
                    selectable=True,
                )
            )
            page.update()

    # Initial UI Build
    page.navigation_bar = nav_bar
    main_wrapper = ft.Container(
        content=content_container,
        border_radius=15,
        bgcolor=ft.colors.TRANSPARENT,
        padding=10,
        expand=True,
    )
    render_habits()
    page.add(main_wrapper)
    page.update()


ft.app(target=main)
