"""Unit tests for the read-only analysis tools, using synthetic inputs only (no game data)."""
import importlib.util
import os
import struct
import tempfile
import unittest
import zlib

TOOLS = os.path.join(os.path.dirname(__file__), "..", "tools")


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


erf_list = load("erf_list")
ppc_addr_refs = load("ppc_addr_refs")
gfx_calls = load("gfx_calls")


def write_tmp(data):
    f = tempfile.NamedTemporaryFile(delete=False)
    f.write(data)
    f.close()
    return f.name


class ErfListTest(unittest.TestCase):
    def test_v20_entries(self):
        name = "optionsmenu.gfx".encode("utf-16-le").ljust(64, b"\0")
        data = "ERF V2.0".encode("utf-16-le") + struct.pack("<IIII", 1, 2009, 1, 0xFFFFFFFF)
        data += name + struct.pack("<II", 0x68, 4) + b"abcd"
        path = write_tmp(data)
        self.assertEqual(list(erf_list.read_entries(path)), [(0x68, 4, 4, "optionsmenu.gfx")])

    def test_v21_entries_report_stored_and_unpacked_size(self):
        payload = zlib.compress(b"x" * 100)
        data = b"ERF V2.1".ljust(16, b"\0") + struct.pack("<IIII", 1, 0, 0x0118006D, 0xFFFF)
        data += b"radialquickbar.gfx".ljust(32, b"\0") + struct.pack("<III", 0x4C, len(payload), 100)
        path = write_tmp(data + payload)
        self.assertEqual(list(erf_list.read_entries(path)), [(0x4C, len(payload), 100, "radialquickbar.gfx")])

    def test_rejects_unknown_magic(self):
        path = write_tmp(b"ERF V3.0".ljust(0x20, b"\0"))
        with self.assertRaises(ValueError):
            list(erf_list.read_entries(path))


def elf64_be(code_words, vaddr=0x10000):
    """Minimal big-endian ELF64 with one executable PT_LOAD segment holding code_words."""
    code = struct.pack(f">{len(code_words)}I", *code_words)
    phoff, phentsize = 0x40, 0x38
    off = phoff + phentsize
    hdr = bytearray(0x40)
    hdr[:4] = b"\x7fELF"
    struct.pack_into(">Q", hdr, 0x20, phoff)
    struct.pack_into(">HH", hdr, 0x36, phentsize, 1)
    ph = struct.pack(">IIQQQQQQ", 1, 5, off, vaddr, vaddr, len(code), len(code), 0x10000)
    return bytes(hdr) + ph + code


def lis(rd, hi):
    return (15 << 26) | (rd << 21) | (0 << 16) | (hi & 0xFFFF)


def addic(rd, ra, simm):
    return (12 << 26) | (rd << 21) | (ra << 16) | (simm & 0xFFFF)


def lwz(rt, ra, simm):
    return (32 << 26) | (rt << 21) | (ra << 16) | (simm & 0xFFFF)


NOP = 0x60000000


class PpcAddrRefsTest(unittest.TestCase):
    def run_tool(self, words, targets, capsys_lines):
        path = write_tmp(elf64_be(words))
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ppc_addr_refs.main(["x", path] + targets)
        capsys_lines.extend(buf.getvalue().split())

    def test_lis_addic_negative_low_half(self):
        # 0x158a818 = (0x159 << 16) - 0x57e8
        out = []
        self.run_tool([lis(5, 0x159), NOP, addic(5, 5, -0x57E8)], ["158a818"], out)
        self.assertEqual(out, ["0158a818", "00010000", "00010008"])

    def test_lis_lwz_global_load(self):
        out = []
        self.run_tool([lis(3, 0x15B), lwz(3, 3, -0x1740)], ["15ae8c0"], out)
        self.assertEqual(out, ["015ae8c0", "00010000", "00010004"])

    def test_other_register_is_not_paired(self):
        out = []
        self.run_tool([lis(4, 0x135), addic(3, 9, 0xC40)], ["1350c40"], out)
        self.assertEqual(out, [])


def swf_with_actions(actions):
    """CFX (zlib) movie with one DoAction tag containing the given AVM1 bytes."""
    rect = bytes([0x08, 0x00])  # nbits=1 -> 2 bytes
    header = rect + struct.pack("<HH", 0x1800, 1)
    body = actions + b"\0"
    tag = struct.pack("<HI", (12 << 6) | 0x3F, len(body)) + body
    swf = header + tag + struct.pack("<H", 0)
    comp = zlib.compress(swf)
    return b"CFX\x08" + struct.pack("<I", 8 + len(swf)) + comp


def push(*items):
    out = b""
    for kind, v in items:
        if kind == "s":
            out += b"\0" + v.encode() + b"\0"
        elif kind == "i":
            out += b"\x07" + struct.pack("<i", v)
    return b"\x96" + struct.pack("<H", len(out)) + out


class GfxCallsTest(unittest.TestCase):
    def test_flash_external_interface_call_name(self):
        acts = push(("s", "x"), ("s", "EnableGamepadEvents"), ("i", 1), ("s", "flash")) + b"\x1c"
        acts += push(("s", "external")) + b"\x4e" + push(("s", "ExternalInterface")) + b"\x4e"
        acts += push(("s", "call")) + b"\x52"
        path = write_tmp(swf_with_actions(acts))
        self.assertIn(("ExternalInterface", "EnableGamepadEvents"), gfx_calls.movie_calls(path))

    def test_dispatcher_first_argument(self):
        acts = push(("s", "CycleFullScreenGUILeftMessage"), ("s", "SendMessage"), ("i", 2),
                    ("s", "ExternalInterface")) + b"\x1c" + push(("s", "call")) + b"\x52"
        path = write_tmp(swf_with_actions(acts))
        self.assertIn(("ExternalInterface", "SendMessage:CycleFullScreenGUILeftMessage"),
                      gfx_calls.movie_calls(path))

    def test_fscommand(self):
        acts = b"\x83" + struct.pack("<H", 22) + b"FSCommand:MoveToFront\0" + b"\0"
        path = write_tmp(swf_with_actions(acts))
        self.assertIn(("fscommand", "MoveToFront"), gfx_calls.movie_calls(path))


if __name__ == "__main__":
    unittest.main()
