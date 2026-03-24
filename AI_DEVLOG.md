# STUDYGRAM - AI KNOWLEDGE BASE & RULES
- **Flet Syntax:** ALWAYS use capitalized modules: ft.Colors, ft.Icons, ft.Margin, ft.Padding.
- **Red Screen of Death (Audio Bug):** On Desktop, `flet_audio` causes a fatal crash. ALWAYS check `is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]`. Only import and use `fta.Audio` if `is_mobile` is True. On Desktop, set audio variables to `None`.
- **Navigation Bar:** Use `ft.NavigationBarDestination`, NOT `NavigationDestination`.
- **ExpansionTile:** Do NOT use `initially_expanded`. It does not exist and causes crashes.
- **UI Paradigm:** Mobile-first, strict purple-themed (`ft.colors.PURPLE`), scrollable columns (`scroll="auto"`), no nested scrolling.
### ADVANCED SKILL TREE ARCHITECTURE
- **Dynamic Data Only:** The Skill Tree UI in Tab 1 must NOT be hardcoded. It must be generated dynamically from SQLite database records.
- **Node Properties:** Each node needs: `id`, `tree_id` (e.g., Python ICPC), `name`, `description`, `parent_id` (for branching), `sp_required` (cost to unlock), `is_repeatable` (boolean for farming SP), `mutually_exclusive_group` (if node A and B have the same group ID, unlocking one locks the other forever).
- **Verification Tasks:** Nodes contain tasks (e.g., Checklists, Text Reflection, Code Snippet). Unlocking/Farming a node requires completing its linked tasks.
- **Alignment:** NEVER use ft.alignment.center or similar string attributes. ALWAYS use coordinate-based alignment like ft.alignment.Alignment(0, 0) for center, or ft.alignment.Alignment(-1, -1) for top-left.
- **Classes over Modules:** NEVER use lowercase submodules for instances (e.g., no ft.animation.Animation, no ft.alignment.center). Access classes directly from ft with PascalCase (e.g., ft.Animation, ft.Alignment, ft.AnimationCurve.DECELERATE).