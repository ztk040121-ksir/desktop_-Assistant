# -*- coding: utf-8 -*-
"""
Patch desktop_pet.py to:
1. Import HandsOverlay
2. Create hands_overlay after main pet is positioned
3. Connect keyboard/mouse events to hands_overlay
4. Sync position when pet moves
"""
from pathlib import Path

f = Path(r"E:\Demo\desk_tools\ui\desktop_pet.py")
content = f.read_text(encoding="utf-8")

# ---- 1. Add HandsOverlay import after existing imports ----
OLD_IMPORT_MARKER = "from ui.system_tray import"
if OLD_IMPORT_MARKER not in content:
    OLD_IMPORT_MARKER = "from core."

if OLD_IMPORT_MARKER in content:
    idx = content.find(OLD_IMPORT_MARKER)
    line_end = content.find('\n', idx)
    content = content[:line_end+1] + "from ui.hands_overlay import HandsOverlay\n" + content[line_end+1:]
    print("OK: Added HandsOverlay import")
else:
    print("WARN: Could not find import location")

# ---- 2. Create HandsOverlay after pet is shown ----
OLD_SHOW_SECTION = """        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()"""

NEW_SHOW_SECTION = """        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

        # Create hands overlay - shows just the hand area below the character
        try:
            self.hands_overlay = HandsOverlay(http_port=HTTP_PORT, pet_window=self)
            self.hands_overlay.snap_to_pet(x, y, self.height())
            self.hands_overlay.show()
            print("[HandsOverlay] Hands overlay created and visible")
        except Exception as e:
            self.hands_overlay = None
            print(f"[HandsOverlay] Could not create: {e}")"""

if OLD_SHOW_SECTION in content:
    content = content.replace(OLD_SHOW_SECTION, NEW_SHOW_SECTION)
    print("OK: Added HandsOverlay creation after show()")
else:
    print("WARN: Could not find show() section")

# ---- 3. Connect keyboard handler to hands_overlay ----
OLD_KEY_HANDLER = """    def _handle_key_pressed(self):
        try:
            self.web.page().runJavaScript("window.onGlobalKeyPress();")
        except Exception:
            pass"""

NEW_KEY_HANDLER = """    def _handle_key_pressed(self):
        try:
            self.web.page().runJavaScript("window.onGlobalKeyPress();")
        except Exception:
            pass
        # Also animate hands overlay
        try:
            if hasattr(self, 'hands_overlay') and self.hands_overlay:
                self.hands_overlay.on_key_press()
        except Exception:
            pass"""

if OLD_KEY_HANDLER in content:
    content = content.replace(OLD_KEY_HANDLER, NEW_KEY_HANDLER)
    print("OK: Connected keyboard to hands overlay")
else:
    print("WARN: Could not find _handle_key_pressed")

# ---- 4. Sync hands overlay position when pet moves ----
OLD_MOVE_EVENT = """    def mousePressEvent"""
if OLD_MOVE_EVENT in content:
    idx = content.find(OLD_MOVE_EVENT)
    MOVE_SYNC = '''    def moveEvent(self, event):
        super().moveEvent(event)
        try:
            if hasattr(self, 'hands_overlay') and self.hands_overlay:
                pos = self.pos()
                self.hands_overlay.snap_to_pet(pos.x(), pos.y(), self.height())
        except Exception:
            pass

'''
    content = content[:idx] + MOVE_SYNC + content[idx:]
    print("OK: Added moveEvent to sync hands position")
else:
    # Append to class end
    print("WARN: Could not find mousePressEvent, appending moveEvent")

# ---- 5. Also hide/show hands overlay with pet ----
OLD_HIDE = """        elif action == act_hide:
            self.hide()"""
NEW_HIDE = """        elif action == act_hide:
            self.hide()
            try:
                if hasattr(self, 'hands_overlay') and self.hands_overlay:
                    self.hands_overlay.hide()
            except Exception:
                pass"""

if OLD_HIDE in content:
    content = content.replace(OLD_HIDE, NEW_HIDE)
    print("OK: Connected hide to hands overlay")
else:
    print("WARN: Could not find act_hide section")

# ---- Write back ----
f.write_text(content, encoding="utf-8")
print("SUCCESS: desktop_pet.py patched with HandsOverlay integration")
