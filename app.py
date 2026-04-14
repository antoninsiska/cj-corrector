#!/usr/bin/env python3
"""
CJ Correcter – status bar app + native AppKit correction popup.

The popup is created inside THIS process (the .app bundle with LSUIElement=YES),
so macOS grants it full authority to appear above every full-screen Space.
grammar_correct.py is still used only by the Automator right-click service.
"""
import os, sys, time, json, difflib, threading, subprocess
import objc
from AppKit import (
    NSApplication, NSStatusBar, NSMenu, NSMenuItem, NSObject,
    NSVariableStatusItemLength, NSApplicationActivationPolicyAccessory,
    NSEvent, NSKeyDownMask,
    NSPasteboard, NSPasteboardTypeString,
    NSPanel, NSScreen, NSBackingStoreBuffered,
    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSTextField, NSTextView, NSScrollView, NSButton,
    NSColor, NSFont, NSMutableAttributedString, NSAttributedString,
    NSForegroundColorAttributeName, NSFontAttributeName,
    NSStrikethroughStyleAttributeName, NSStrikethroughColorAttributeName,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
)
try:
    from AppKit import NSWindowCollectionBehaviorFullScreenAuxiliary
except ImportError:
    NSWindowCollectionBehaviorFullScreenAuxiliary = 256

try:
    from AppKit import NSEventModifierFlagCommand, NSEventModifierFlagShift
except ImportError:
    NSEventModifierFlagCommand = 1 << 20
    NSEventModifierFlagShift   = 1 << 17

from ApplicationServices import AXIsProcessTrustedWithOptions

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
INSTALL_DIR  = os.path.expanduser("~/.cj_correcter")
MISTAKES_FILE = os.path.join(INSTALL_DIR, "mistakes.json")

try:
    sys.path.insert(0, SCRIPT_DIR)
    from ollama_client import MODEL_NAME
except Exception:
    MODEL_NAME = "ufal/byt5-small-geccc-mate"

HOTKEY_KEYCODE = 5          # g
HOTKEY_MASK    = NSEventModifierFlagCommand | NSEventModifierFlagShift

# ── global controller reference (set in main) ─────────────────────────────────
_controller = None

# ── clipboard helpers ─────────────────────────────────────────────────────────

def _clip_get():
    return NSPasteboard.generalPasteboard().stringForType_(NSPasteboardTypeString) or ""

def _clip_set(text):
    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, NSPasteboardTypeString)

def _keystroke(key, mod=""):
    mods = ", ".join(f"{m} down" for m in mod.split()) if mod else ""
    if mods:
        script = f'tell application "System Events" to keystroke "{key}" using {{{mods}}}'
    else:
        script = f'tell application "System Events" to keystroke "{key}"'
    subprocess.run(["osascript", "-e", script], capture_output=True, timeout=4)

def _save_mistake(original, correction):
    os.makedirs(INSTALL_DIR, exist_ok=True)
    data = {}
    if os.path.exists(MISTAKES_FILE):
        with open(MISTAKES_FILE) as f:
            data = json.load(f)
    e = data.setdefault(original, {"count": 0, "correction": correction})
    e["count"] += 1; e["correction"] = correction
    with open(MISTAKES_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── diff attributed string ────────────────────────────────────────────────────

def _diff_string(original, corrected):
    RED   = NSColor.colorWithRed_green_blue_alpha_(1.0,  0.23, 0.19, 1.0)
    GREEN = NSColor.colorWithRed_green_blue_alpha_(0.20, 0.78, 0.35, 1.0)
    NORM  = NSColor.labelColor()
    FONT  = NSFont.systemFontOfSize_(13)
    BOLD  = NSFont.boldSystemFontOfSize_(13)

    attr_normal = {NSFontAttributeName: FONT, NSForegroundColorAttributeName: NORM}
    attr_del    = {NSFontAttributeName: FONT, NSForegroundColorAttributeName: RED,
                   NSStrikethroughStyleAttributeName: 1,
                   NSStrikethroughColorAttributeName: RED}
    attr_ins    = {NSFontAttributeName: BOLD, NSForegroundColorAttributeName: GREEN}

    result = NSMutableAttributedString.alloc().init()
    ow = original.split()
    cw = corrected.split()
    ops = list(difflib.SequenceMatcher(None, ow, cw, autojunk=False).get_opcodes())

    def app(text, attrs):
        result.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(text, attrs))

    space = lambda: app(" ", attr_normal)
    first = [True]
    def gap():
        if not first[0]: space()
        first[0] = False

    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            chunk = " ".join(ow[i1:i2])
            if chunk: gap(); app(chunk, attr_normal)
        elif tag == "replace":
            gap()
            app(" ".join(ow[i1:i2]), attr_del); space()
            app(" ".join(cw[j1:j2]), attr_ins)
        elif tag == "delete":
            gap(); app(" ".join(ow[i1:i2]), attr_del)
        elif tag == "insert":
            gap(); app(" ".join(cw[j1:j2]), attr_ins)

    return result


def _count_changes(original, corrected):
    ow = original.split(); cw = corrected.split()
    return sum(1 for t, *_ in
               difflib.SequenceMatcher(None, ow, cw, autojunk=False).get_opcodes()
               if t != "equal")

# ── native correction panel ───────────────────────────────────────────────────

class CorrectionPanel(NSObject):
    """
    NSPanel created inside the app bundle process → can appear above
    every full-screen Space without any tricks.
    """

    def initWithOriginal_corrected_mistakes_oldClip_(
            self, original, corrected, mistakes, old_clip):
        self = objc.super(CorrectionPanel, self).init()
        if self is None: return None
        self._original  = original
        self._corrected = corrected
        self._mistakes  = mistakes
        self._old_clip  = old_clip
        self._panel     = None
        return self

    def show(self):
        W, H   = 460, 220
        sf     = NSScreen.mainScreen().frame()
        x      = sf.size.width  - W - 16
        y      = sf.size.height - H - 36    # just below menu bar

        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            ((x, y), (W, H)),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered, False,
        )
        panel.setTitle_("Czech Grammar Correction")
        panel.setLevel_(1000)   # NSScreenSaverWindowLevel
        panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces |
            NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        panel.setDelegate_(self)
        self._panel = panel

        cv   = panel.contentView()
        cw   = cv.frame().size.width
        ch   = cv.frame().size.height

        # ── status label ──
        n = _count_changes(self._original, self._corrected)
        status_text = ("✅  No grammar mistakes found"
                       if n == 0 else
                       f"🔴  {n} mistake{'s' if n != 1 else ''} found")

        status = NSTextField.alloc().initWithFrame_(((12, ch-30), (cw-24, 22)))
        status.setStringValue_(status_text)
        status.setEditable_(False); status.setBezeled_(False)
        status.setDrawsBackground_(False)
        status.setFont_(NSFont.boldSystemFontOfSize_(12))
        cv.addSubview_(status)

        # ── separator ──
        sep1 = NSTextField.alloc().initWithFrame_(((0, ch-34), (cw, 1)))
        sep1.setDrawsBackground_(True)
        sep1.setBackgroundColor_(NSColor.separatorColor())
        sep1.setBezeled_(False); sep1.setEditable_(False)
        cv.addSubview_(sep1)

        # ── diff text view ──
        scroll = NSScrollView.alloc().initWithFrame_(((0, 44), (cw, ch-38)))
        scroll.setHasVerticalScroller_(True)
        scroll.setAutohidesScrollers_(True)

        tv = NSTextView.alloc().initWithFrame_(scroll.bounds())
        tv.setEditable_(False)
        tv.textStorage().setAttributedString_(
            _diff_string(self._original, self._corrected))
        tv.setBackgroundColor_(NSColor.textBackgroundColor())
        tv.setTextContainerInset_((14, 8))
        scroll.setDocumentView_(tv)
        cv.addSubview_(scroll)

        # ── bottom separator ──
        sep2 = NSTextField.alloc().initWithFrame_(((0, 43), (cw, 1)))
        sep2.setDrawsBackground_(True)
        sep2.setBackgroundColor_(NSColor.separatorColor())
        sep2.setBezeled_(False); sep2.setEditable_(False)
        cv.addSubview_(sep2)

        # ── buttons ──
        cancel = NSButton.alloc().initWithFrame_(((cw-168, 9), (76, 26)))
        cancel.setTitle_("Cancel"); cancel.setBezelStyle_(1)  # NSBezelStyleRounded
        cancel.setTarget_(self); cancel.setAction_("cancel:")
        cv.addSubview_(cancel)

        accept = NSButton.alloc().initWithFrame_(((cw-84, 9), (76, 26)))
        accept.setTitle_("Accept" if n > 0 else "OK")
        accept.setBezelStyle_(1)
        accept.setKeyEquivalent_("\r")   # Return key = accept
        accept.setTarget_(self); accept.setAction_("accept:")
        cv.addSubview_(accept)

        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        panel.makeKeyAndOrderFront_(None)

    # ── window delegate: close = cancel ──────────────────────────────────────
    def windowWillClose_(self, notification):
        _clip_set(self._old_clip)

    # ── actions ───────────────────────────────────────────────────────────────
    def accept_(self, sender):
        for m in self._mistakes:
            o = m.get("original","").strip()
            c = m.get("correction","").strip()
            if o and c != "∅": _save_mistake(o, c)
        _clip_set(self._corrected)
        time.sleep(0.06)
        _keystroke("v", "command")
        self._panel.setDelegate_(None)
        self._panel.close()

    def cancel_(self, sender):
        _clip_set(self._old_clip)
        self._panel.setDelegate_(None)
        self._panel.close()


# ── status bar ────────────────────────────────────────────────────────────────

class StatusBarController(NSObject):

    def init(self):
        self = objc.super(StatusBarController, self).init()
        if self is None: return None
        self._popup = None     # keep strong ref

        sb = NSStatusBar.systemStatusBar()
        self._item = sb.statusItemWithLength_(NSVariableStatusItemLength)
        self._item.button().setTitle_("Č✓")
        self._item.setVisible_(True)
        self._build_menu()
        self._setup_hotkey()
        return self

    # ── menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self):
        menu = NSMenu.new()
        for title in [f"Model: {MODEL_NAME}", "Hotkey: ⌘⇧G  (works everywhere)"]:
            it = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, None, "")
            it.setEnabled_(False); menu.addItem_(it)
        menu.addItem_(NSMenuItem.separatorItem())
        for title, sel in [("Correct Clipboard Text", "correctClipboard:"),
                            ("Statistics",             "showStats:")]:
            it = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, sel, "")
            it.setTarget_(self); menu.addItem_(it)
        menu.addItem_(NSMenuItem.separatorItem())
        q = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit","terminate:","q")
        q.setTarget_(NSApplication.sharedApplication()); menu.addItem_(q)
        self._item.setMenu_(menu)

    # ── hotkey ────────────────────────────────────────────────────────────────

    def _setup_hotkey(self):
        AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": True})
        def handler(event):
            flags = event.modifierFlags() & 0xFFFF0000
            if event.keyCode() == HOTKEY_KEYCODE and (flags & HOTKEY_MASK) == HOTKEY_MASK:
                threading.Thread(target=self._hotkey_thread, daemon=True).start()
        self._monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSKeyDownMask, handler)

    def _hotkey_thread(self):
        old = _clip_get()
        _clip_set("")
        time.sleep(0.05)
        _keystroke("c", "command")
        time.sleep(0.25)
        text = _clip_get()
        if not text:
            _clip_set(old); return
        self._run_correction(text, old)

    # ── correction ────────────────────────────────────────────────────────────

    def _run_correction(self, text, old_clip):
        """Run model in background, then show popup on main thread."""
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "setLoadingTitle:", None, False)
        try:
            sys.path.insert(0, SCRIPT_DIR)
            from ollama_client import correct_czech
            result = correct_czech(text)
        except Exception as e:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "resetTitle:", None, False)
            return
        payload = {
            "original":  text,
            "corrected": result.get("corrected", text),
            "mistakes":  result.get("mistakes", []),
            "old_clip":  old_clip,
        }
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "showCorrectionResult:", payload, False)

    def setLoadingTitle_(self, _):
        self._item.button().setTitle_("Č…")

    def resetTitle_(self, _):
        self._item.button().setTitle_("Č✓")

    def showCorrectionResult_(self, payload):
        self._item.button().setTitle_("Č✓")
        self._popup = CorrectionPanel.alloc()\
            .initWithOriginal_corrected_mistakes_oldClip_(
                payload["original"],
                payload["corrected"],
                payload["mistakes"],
                payload["old_clip"],
            )
        self._popup.show()

    # ── menu actions ──────────────────────────────────────────────────────────

    def correctClipboard_(self, _):
        text = _clip_get()
        if text:
            threading.Thread(
                target=self._run_correction, args=(text, text), daemon=True
            ).start()

    def showStats_(self, _):
        subprocess.Popen(
            ["python3", os.path.join(SCRIPT_DIR, "stats_window.py")],
            start_new_session=True)


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    global _controller
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    _controller = StatusBarController.new()
    app.run()

if __name__ == "__main__":
    main()
