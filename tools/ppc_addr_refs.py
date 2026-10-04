#!/usr/bin/env python3
"""Find PowerPC code that materialises given addresses via lis + addi/ori (read-only).

PS3 executables often build string addresses as
    lis   rX, hi        (addis rX, 0, hi)
    addi/addic rY, rX, lo  (signed lo)   or   ori rY, rX, lo
with up to a few unrelated instructions in between. This scans the executable
LOAD segment of a big-endian ELF64 and reports every pair that yields a target.

Usage: ppc_addr_refs.py ELF ADDR [ADDR ...]   (hex addresses)
Prints: target<TAB>lis_va<TAB>use_va
"""
import struct
import sys

WINDOW = 12  # instructions to look ahead for the low-half instruction
# D-form loads/stores: lwz lwzu lbz lbzu stw stwu stb stbu lhz lha sth lfs lfd stfs stfd, ld (58), std (62)
LOAD_STORE_D = {32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 44, 48, 50, 52, 54, 58, 62}


def load_segments(d):
    phoff = struct.unpack_from(">Q", d, 0x20)[0]
    phentsize, phnum = struct.unpack_from(">HH", d, 0x36)
    segs = []
    for i in range(phnum):
        ptype, flags, off, vaddr, _paddr, filesz, _memsz, _align = struct.unpack_from(
            ">IIQQQQQQ", d, phoff + i * phentsize)
        if ptype == 1 and filesz:
            segs.append((off, vaddr, filesz, flags))
    return segs


def main(argv):
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[1], "rb") as f:
        d = f.read()
    targets = {int(a, 16) for a in argv[2:]}
    for off, vaddr, size, flags in load_segments(d):
        if not flags & 1:  # PF_X
            continue
        words = struct.unpack_from(f">{size // 4}I", d, off)
        for i, w in enumerate(words):
            if w >> 26 != 15 or (w >> 16) & 31 != 0:  # lis rD, imm == addis rD, 0, imm
                continue
            rd = (w >> 21) & 31
            hi = w & 0xFFFF
            for j in range(i + 1, min(i + 1 + WINDOW, len(words))):
                u = words[j]
                op = u >> 26
                ra = (u >> 16) & 31
                # addi (14) and addic/addic. (12/13): the PS3 compiler favours addic.
                if op in (12, 13, 14) and ra == rd:  # rY = rD + simm
                    lo = u & 0xFFFF
                    value = ((hi << 16) + (lo - 0x10000 if lo & 0x8000 else lo)) & 0xFFFFFFFF
                elif op == 24 and ((u >> 21) & 31) == rd:  # ori rA, rS, uimm (rS field is bits 21-25)
                    value = ((hi << 16) | (u & 0xFFFF)) & 0xFFFFFFFF
                elif op in LOAD_STORE_D and ra == rd:  # lwz/lbz/stw/... rT, simm(rD): global access
                    lo = u & 0xFFFF
                    if op in (58, 62):  # DS-form (ld/std): low 2 bits are sub-opcode
                        lo &= 0xFFFC
                    value = ((hi << 16) + (lo - 0x10000 if lo & 0x8000 else lo)) & 0xFFFFFFFF
                else:
                    continue
                if value in targets:
                    print(f"{value:08x}\t{vaddr + 4 * i:08x}\t{vaddr + 4 * j:08x}")
                break
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
