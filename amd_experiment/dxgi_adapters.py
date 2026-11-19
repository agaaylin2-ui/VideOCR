"""List DXGI adapters using the same EnumAdapters ordering as ORT DirectML."""
import ctypes
import json
import sys
from ctypes import wintypes


class GUID(ctypes.Structure):
    _fields_ = [("data1", wintypes.DWORD), ("data2", wintypes.WORD), ("data3", wintypes.WORD), ("data4", ctypes.c_ubyte * 8)]


class LUID(ctypes.Structure):
    _fields_ = [("low", wintypes.DWORD), ("high", wintypes.LONG)]


class AdapterDesc(ctypes.Structure):
    _fields_ = [("description", wintypes.WCHAR * 128), ("vendor", wintypes.UINT), ("device", wintypes.UINT), ("subsystem", wintypes.UINT), ("revision", wintypes.UINT), ("dedicated_video", ctypes.c_size_t), ("dedicated_system", ctypes.c_size_t), ("shared_system", ctypes.c_size_t), ("luid", LUID)]


def method(obj, index, result, *args):
    table = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    return ctypes.WINFUNCTYPE(result, ctypes.c_void_p, *args)(table[index])


def main():
    if sys.platform != "win32":
        raise RuntimeError("DXGI is available only on Windows")
    iid = GUID(0x7B7166EC, 0x21C7, 0x44AE, (ctypes.c_ubyte * 8)(0xB2, 0x1A, 0xC9, 0xAE, 0x32, 0x1A, 0xE3, 0x69))
    factory = ctypes.c_void_p()
    dxgi = ctypes.WinDLL("dxgi.dll")
    dxgi.CreateDXGIFactory.argtypes = [ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
    dxgi.CreateDXGIFactory.restype = ctypes.c_long
    hr = dxgi.CreateDXGIFactory(ctypes.byref(iid), ctypes.byref(factory))
    if hr < 0:
        raise OSError(f"CreateDXGIFactory failed: 0x{hr & 0xffffffff:08x}")
    adapters = []
    try:
        enum = method(factory, 7, ctypes.c_long, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p))
        for index in range(128):
            adapter = ctypes.c_void_p()
            hr = enum(factory, index, ctypes.byref(adapter))
            if (hr & 0xffffffff) == 0x887A0002:
                break
            if hr < 0:
                raise OSError(f"EnumAdapters({index}) failed: 0x{hr & 0xffffffff:08x}")
            try:
                desc = AdapterDesc()
                hr = method(adapter, 8, ctypes.c_long, ctypes.POINTER(AdapterDesc))(adapter, ctypes.byref(desc))
                if hr < 0:
                    raise OSError(f"GetDesc failed: 0x{hr & 0xffffffff:08x}")
                adapters.append({"index": index, "name": desc.description, "vendor_id": f"{desc.vendor:04x}", "device_id": f"{desc.device:04x}", "dedicated_bytes": desc.dedicated_video})
            finally:
                method(adapter, 2, wintypes.ULONG)(adapter)
    finally:
        method(factory, 2, wintypes.ULONG)(factory)
    print(json.dumps(adapters))


if __name__ == "__main__":
    main()
