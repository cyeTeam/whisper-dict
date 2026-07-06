import ctypes
import logging
import threading
from typing import Optional

logger = logging.getLogger('dictation.overlay')

WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

LWA_ALPHA = 0x2

COLOR_IDLE = 0x00A0A0A0
COLOR_LISTENING = 0x000033FF
COLOR_PROCESSING = 0x0000CCFF

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

UINT = ctypes.c_uint
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
LRESULT = ctypes.c_ssize_t
LONG = ctypes.c_long

WndProcType = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_void_p, UINT, WPARAM, LPARAM)


class RECT(ctypes.Structure):
    _fields_ = [
        ('left', LONG),
        ('top', LONG),
        ('right', LONG),
        ('bottom', LONG),
    ]


class POINT(ctypes.Structure):
    _fields_ = [
        ('x', LONG),
        ('y', LONG),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ('hwnd', ctypes.c_void_p),
        ('message', UINT),
        ('wParam', WPARAM),
        ('lParam', LPARAM),
        ('time', ctypes.c_ulong),
        ('pt', POINT),
    ]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ('hdc', ctypes.c_void_p),
        ('fErase', ctypes.c_int),
        ('rcPaint', RECT),
        ('fRestore', ctypes.c_int),
        ('fIncUpdate', ctypes.c_int),
        ('rgbReserved', ctypes.c_byte * 32),
    ]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ('cbSize', UINT),
        ('style', UINT),
        ('lpfnWndProc', WndProcType),
        ('cbClsExtra', ctypes.c_int),
        ('cbWndExtra', ctypes.c_int),
        ('hInstance', ctypes.c_void_p),
        ('hIcon', ctypes.c_void_p),
        ('hCursor', ctypes.c_void_p),
        ('hbrBackground', ctypes.c_void_p),
        ('lpszMenuName', ctypes.c_wchar_p),
        ('lpszClassName', ctypes.c_wchar_p),
        ('hIconSm', ctypes.c_void_p),
    ]


class OverlayIndicator:
    def __init__(self, size: int = 28, padding: int = 20):
        self.size = size
        self.padding = padding
        self._hwnd: Optional[int] = None
        self._running = False
        self._color = COLOR_IDLE
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._lock = threading.Lock()
        self._wnd_proc_cb: Optional[WndProcType] = None

    def _wnd_proc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if msg == 0x000F:
            self._on_paint(hwnd)
            return 0
        elif msg == 0x0014:
            return 1
        elif msg == 0x0002:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _on_paint(self, hwnd: int) -> None:
        ps = PAINTSTRUCT()
        ctypes.memset(ctypes.byref(ps), 0, ctypes.sizeof(ps))
        hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))

        rect = RECT()
        user32.GetClientRect(hwnd, ctypes.byref(rect))

        brush = gdi32.CreateSolidBrush(self._color)
        old_brush = gdi32.SelectObject(hdc, brush)
        old_pen = gdi32.SelectObject(hdc, gdi32.GetStockObject(8))

        gdi32.Ellipse(hdc, 0, 0, rect.right, rect.bottom)

        gdi32.SelectObject(hdc, old_pen)
        gdi32.SelectObject(hdc, old_brush)
        gdi32.DeleteObject(brush)

        user32.EndPaint(hwnd, ctypes.byref(ps))

    def _thread_run(self) -> None:
        hinstance = kernel32.GetModuleHandleW(None)

        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(wc)
        wc.style = 0
        self._wnd_proc_cb = WndProcType(self._wnd_proc)
        wc.lpfnWndProc = self._wnd_proc_cb
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = hinstance
        wc.hIcon = None
        wc.hCursor = user32.LoadCursorW(None, 32512)
        wc.hbrBackground = None
        wc.lpszMenuName = None
        wc.lpszClassName = 'WhisperDictOverlay'
        wc.hIconSm = None

        atom = user32.RegisterClassExW(ctypes.byref(wc))
        if atom == 0:
            logger.error('RegisterClassExW failed: %d', ctypes.get_last_error())
            return

        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        x = self.padding
        y = sh - self.size - self.padding

        self._hwnd = user32.CreateWindowExW(
            WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
            'WhisperDictOverlay',
            None,
            WS_POPUP,
            x, y, self.size, self.size,
            None, None, hinstance, None,
        )

        if not self._hwnd:
            logger.error('CreateWindowExW failed: %d', ctypes.get_last_error())
            return

        user32.SetLayeredWindowAttributes(self._hwnd, 0, 204, LWA_ALPHA)

        user32.ShowWindow(self._hwnd, 1)
        user32.SetWindowPos(self._hwnd, -1, 0, 0, 0, 0, 0x0002 | 0x0001)

        self._ready.set()

        msg = MSG()
        while self._running:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        with self._lock:
            self._hwnd = None
            self._running = False
            self._ready.clear()

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._ready.clear()
        self._thread = threading.Thread(target=self._thread_run, daemon=True)
        self._thread.start()
        self._ready.wait()

    def set_idle(self) -> None:
        self._set_color(COLOR_IDLE)

    def set_listening(self) -> None:
        self._set_color(COLOR_LISTENING)

    def set_processing(self) -> None:
        self._set_color(COLOR_PROCESSING)

    def _set_color(self, color: int) -> None:
        self._color = color
        with self._lock:
            hwnd = self._hwnd
            running = self._running
        if hwnd and user32.IsWindow(hwnd):
            user32.InvalidateRect(hwnd, None, True)
            user32.UpdateWindow(hwnd)
        elif not running:
            self.start()
            with self._lock:
                if self._hwnd:
                    user32.InvalidateRect(self._hwnd, None, True)
                    user32.UpdateWindow(self._hwnd)

    def stop(self) -> None:
        with self._lock:
            self._running = False
            hwnd = self._hwnd
            self._hwnd = None
        if hwnd and user32.IsWindow(hwnd):
            user32.PostMessageW(hwnd, 0x0010, 0, 0)
