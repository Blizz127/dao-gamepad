#!/usr/bin/env python3
"""List entries in a Dragon Age: Origins ERF archive (read-only).

ERF V2.0 (PC), little-endian:
  0x00  char16[8]  "ERF V2.0"
  0x10  u32        file_count
  0x14  u32        year
  0x18  u32        day
  0x1C  u32        unknown (0xFFFFFFFF)
  0x20  entries[file_count]: char16[32] name, u32 offset, u32 size

ERF V2.1 (PS3 dump), little-endian, entries may be compressed:
  0x00  char[16]   "ERF V2.1", zero padded
  0x10  u32        file_count
  0x14  u32        unknown
  0x18  u32        unknown (flags?)
  0x1C  u32        unknown
  0x20  entries[file_count]: char[32] name, u32 offset, u32 stored_size, u32 size

Prints: offset<TAB>stored_size<TAB>size<TAB>name
"""
import struct
import sys

MAGIC_V20 = "ERF V2.0".encode("utf-16-le")
MAGIC_V21 = b"ERF V2.1"


def read_entries(path):
    """Yield (offset, stored_size, size, name) for each entry."""
    with open(path, "rb") as f:
        head = f.read(0x20)
        count = struct.unpack_from("<I", head, 0x10)[0]
        if head[:16] == MAGIC_V20:
            table = f.read(count * 72)
            for i in range(count):
                o = i * 72
                name = table[o:o + 64].decode("utf-16-le").split("\0", 1)[0]
                offset, size = struct.unpack_from("<II", table, o + 64)
                yield offset, size, size, name
        elif head[:8] == MAGIC_V21:
            table = f.read(count * 44)
            for i in range(count):
                o = i * 44
                name = table[o:o + 32].split(b"\0", 1)[0].decode("ascii")
                offset, stored, size = struct.unpack_from("<III", table, o + 32)
                yield offset, stored, size, name
        else:
            raise ValueError(f"{path}: unsupported ERF header {head[:16]!r}")


def main(argv):
    if len(argv) < 2:
        print(f"usage: {argv[0]} ARCHIVE.erf [...]", file=sys.stderr)
        return 2
    for path in argv[1:]:
        for offset, stored, size, name in read_entries(path):
            print(f"{offset}\t{stored}\t{size}\t{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
