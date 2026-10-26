"""Measure the mouse DPI step from raw input counts. Read only.

    python tools/vw_dpi.py measure [--cm 10] [--seconds 20]

Put a ruler on the pad, hold the mouse at 0, run the command, then slide the
mouse straight right along the ruler by --cm centimetres (default 10) and stop.
The tool sums the raw horizontal counts Windows receives from every mouse
(WM_INPUT, so "Enhance pointer precision" and the pointer speed slider do not
change the number) for --seconds, then prints counts, the measured DPI and the
nearest step of the R110 (800 / 1200 / 1600). It registers a hidden message
window for raw input only: it never moves the cursor, never sends input and
never touches the game. docs/controls.md.
"""

import argparse
import json
import sys
import time

STEPS = (800, 1200, 1600)
EDPI = 1920  # sens 2.4 at 800 DPI, docs/controls.md


def dpi_from_counts(counts, cm):
    return abs(counts) / (cm / 2.54)


def nearest_step(dpi, steps=STEPS):
    return min(steps, key=lambda s: abs(s - dpi))


def sensitivity_for(dpi, edpi=EDPI):
    return round(edpi / float(dpi), 3)


def _raw_counts(seconds):  # pragma: no cover - needs a real mouse
    import ctypes
    from ctypes import wintypes as W

    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    WM_INPUT, RID_INPUT, RIM_TYPEMOUSE, RIDEV_INPUTSINK = 0x00FF, 0x10000003, 0, 0x100
    HWND_MESSAGE = W.HWND(-3)
    LRESULT = ctypes.c_ssize_t
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, W.HWND, W.UINT, W.WPARAM, W.LPARAM)

    class RAWINPUTDEVICE(ctypes.Structure):
        _fields_ = [("usUsagePage", W.USHORT), ("usUsage", W.USHORT),
                    ("dwFlags", W.DWORD), ("hwndTarget", W.HWND)]

    class RAWINPUTHEADER(ctypes.Structure):
        _fields_ = [("dwType", W.DWORD), ("dwSize", W.DWORD),
                    ("hDevice", W.HANDLE), ("wParam", W.WPARAM)]

    class RAWMOUSE(ctypes.Structure):
        _fields_ = [("usFlags", W.USHORT), ("_pad", W.USHORT), ("ulButtons", W.ULONG),
                    ("ulRawButtons", W.ULONG), ("lLastX", W.LONG), ("lLastY", W.LONG),
                    ("ulExtraInformation", W.ULONG)]

    class RAWINPUT(ctypes.Structure):
        _fields_ = [("header", RAWINPUTHEADER), ("mouse", RAWMOUSE)]

    class WNDCLASSW(ctypes.Structure):
        _fields_ = [("style", W.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                    ("cbWndExtra", ctypes.c_int), ("hInstance", W.HINSTANCE),
                    ("hIcon", W.HICON), ("hCursor", W.HANDLE), ("hbrBackground", W.HBRUSH),
                    ("lpszMenuName", W.LPCWSTR), ("lpszClassName", W.LPCWSTR)]

    u32.DefWindowProcW.restype = LRESULT
    u32.DefWindowProcW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    u32.GetRawInputData.argtypes = [W.HANDLE, W.UINT, ctypes.c_void_p,
                                    ctypes.POINTER(W.UINT), W.UINT]
    u32.CreateWindowExW.restype = W.HWND
    u32.CreateWindowExW.argtypes = [W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, ctypes.c_int, W.HWND,
                                    W.HMENU, W.HINSTANCE, W.LPVOID]
    total = {"x": 0, "y": 0, "events": 0}

    def proc(hwnd, msg, wp, lp):
        if msg == WM_INPUT:
            ri = RAWINPUT()
            size = W.UINT(ctypes.sizeof(ri))
            if u32.GetRawInputData(W.HANDLE(lp), RID_INPUT, ctypes.byref(ri),
                                   ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER)) > 0:
                if ri.header.dwType == RIM_TYPEMOUSE and not (ri.mouse.usFlags & 1):
                    total["x"] += ri.mouse.lLastX
                    total["y"] += ri.mouse.lLastY
                    total["events"] += 1
        return u32.DefWindowProcW(hwnd, msg, wp, lp)

    cb = WNDPROC(proc)
    hinst = k32.GetModuleHandleW(None)
    wc = WNDCLASSW(lpfnWndProc=cb, hInstance=hinst, lpszClassName="vw_dpi_raw")
    u32.RegisterClassW(ctypes.byref(wc))
    hwnd = u32.CreateWindowExW(0, "vw_dpi_raw", "vw_dpi", 0, 0, 0, 0, 0,
                               HWND_MESSAGE, None, hinst, None)
    dev = RAWINPUTDEVICE(0x01, 0x02, RIDEV_INPUTSINK, hwnd)
    if not u32.RegisterRawInputDevices(ctypes.byref(dev), 1, ctypes.sizeof(dev)):
        raise OSError("RegisterRawInputDevices failed")
    msg = W.MSG()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        while u32.PeekMessageW(ctypes.byref(msg), hwnd, 0, 0, 1):
            u32.TranslateMessage(ctypes.byref(msg))
            u32.DispatchMessageW(ctypes.byref(msg))
        time.sleep(0.005)
    u32.DestroyWindow(hwnd)
    return total


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("--cm", type=float, default=10.0)
    m.add_argument("--seconds", type=float, default=20.0)
    a = ap.parse_args(argv)
    print("Slide the mouse %.1f cm straight right along a ruler within %.0f s..."
          % (a.cm, a.seconds), file=sys.stderr)
    t = _raw_counts(a.seconds)
    out = {"counts_x": t["x"], "counts_y": t["y"], "events": t["events"], "cm": a.cm}
    if t["x"]:
        dpi = dpi_from_counts(t["x"], a.cm)
        step = nearest_step(dpi)
        out.update(dpi_measured=round(dpi), nearest_step=step,
                   sensitivity_for_edpi_1920=sensitivity_for(step))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
