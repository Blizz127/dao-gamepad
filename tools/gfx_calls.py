#!/usr/bin/env python3
"""Extract engine-facing calls from Scaleform GFX/CFX movies (read-only).

DAO GUI movies talk to the engine through ActionScript 2:
  ExternalInterface.call("Name", args...)   and   fscommand("Name", arg)
This walks the SWF tag stream (including sprites), decodes AVM1 actions in
DoAction/DoInitAction tags, and reports the string literal used as the call name.

Usage: gfx_calls.py MOVIE.gfx [...]   -> prints  movie<TAB>kind<TAB>name
"""
import struct
import sys
import zlib

TAG_DO_ACTION = 12
TAG_DEFINE_SPRITE = 39
TAG_DO_INIT_ACTION = 59

ACT_CONSTANT_POOL = 0x88
ACT_PUSH = 0x96
ACT_GET_VARIABLE = 0x1C
ACT_CALL_METHOD = 0x52
ACT_CALL_FUNCTION = 0x3D
ACT_GET_URL = 0x83
ACT_DEFINE_FUNCTION = 0x9B
ACT_DEFINE_FUNCTION2 = 0x8E

DISPATCHERS = {"SendMessage", "GetValue", "GetNumber", "GetString"}


def swf_body(data):
    """Return the uncompressed SWF body (after the 8-byte header)."""
    sig = data[:3]
    if sig in (b"CFX", b"CWS"):
        return zlib.decompress(data[8:])
    if sig in (b"GFX", b"FWS"):
        return data[8:]
    raise ValueError(f"not a GFX/SWF movie (signature {sig!r})")


def skip_header(body):
    """Skip RECT frame size + frame rate + frame count; return tag stream offset."""
    nbits = body[0] >> 3
    rect_bytes = (5 + nbits * 4 + 7) // 8
    return rect_bytes + 4


def iter_tags(buf, pos, end):
    while pos + 2 <= end:
        code_len = struct.unpack_from("<H", buf, pos)[0]
        pos += 2
        code, length = code_len >> 6, code_len & 0x3F
        if length == 0x3F:
            length = struct.unpack_from("<I", buf, pos)[0]
            pos += 4
        if code == 0:
            return
        yield code, pos, length
        pos += length


def iter_action_blocks(buf, pos, end):
    for code, start, length in iter_tags(buf, pos, end):
        if code == TAG_DO_ACTION:
            yield start, start + length
        elif code == TAG_DO_INIT_ACTION:
            yield start + 2, start + length  # u16 sprite id
        elif code == TAG_DEFINE_SPRITE:
            yield from iter_action_blocks(buf, start + 4, start + length)  # u16 id, u16 frames


def read_cstr(buf, pos):
    end = buf.index(b"\0", pos)
    return buf[pos:end].decode("latin-1"), end + 1


def decode_push(buf, pos, end, pool):
    out = []
    while pos < end:
        t = buf[pos]
        pos += 1
        if t == 0:
            s, pos = read_cstr(buf, pos)
            out.append(("str", s))
        elif t == 1:
            out.append(("num", struct.unpack_from("<f", buf, pos)[0]))
            pos += 4
        elif t in (2, 3):
            out.append(("lit", None))
        elif t == 4:
            out.append(("reg", buf[pos]))
            pos += 1
        elif t == 5:
            out.append(("lit", buf[pos]))
            pos += 1
        elif t == 6:
            out.append(("num", struct.unpack_from("<d", buf[pos + 4:pos + 8] + buf[pos:pos + 4])[0]))
            pos += 8
        elif t == 7:
            out.append(("num", struct.unpack_from("<i", buf, pos)[0]))
            pos += 4
        elif t == 8:
            i = buf[pos]
            pos += 1
            out.append(("str", pool[i] if i < len(pool) else None))
        elif t == 9:
            i = struct.unpack_from("<H", buf, pos)[0]
            pos += 2
            out.append(("str", pool[i] if i < len(pool) else None))
        else:
            break
    return out


def external_call_name(recent):
    """Name argument of an ExternalInterface.call about to run, or None.

    Two compiled shapes occur (tail of the push/op stream before CallMethod):
      ..., name, nargs, "ExternalInterface", getvar, "call"
      ..., name, nargs, "flash", getvar, "external", GetMember,
           "ExternalInterface", GetMember, "call"
    A non-literal name (register/expression) is reported as "<dynamic>".
    """
    if not recent or recent[-1] != ("str", "call"):
        return None
    i = len(recent) - 2
    if recent[i] == ("op", 0x4E) and recent[i - 1] == ("str", "ExternalInterface") \
            and recent[i - 2] == ("op", 0x4E) and recent[i - 3] == ("str", "external") \
            and recent[i - 4][0] == "getvar" and recent[i - 5] == ("str", "flash"):
        i -= 6
    elif recent[i][0] == "getvar" and recent[i - 1] == ("str", "ExternalInterface"):
        i -= 2
    else:
        return None
    if i < 1 or recent[i][0] != "num":
        return "<dynamic>"
    kind, value = recent[i - 1]
    if kind != "str":
        return "<dynamic>"
    # Generic dispatchers carry the real action in their first argument.
    if value in DISPATCHERS and int(recent[i][1]) >= 2 and i >= 2:
        akind, avalue = recent[i - 2]
        return f"{value}:{avalue if akind == 'str' else '<dynamic>'}"
    return value


def scan_actions(buf, pos, end, found):
    """Linear AVM1 scan. Function bodies are inline, so a flat walk covers them."""
    pool = []
    recent = []  # flat stream of recent pushed values and ops
    while pos < end:
        op = buf[pos]
        pos += 1
        if op == 0:
            continue
        length = 0
        if op >= 0x80:
            length = struct.unpack_from("<H", buf, pos)[0]
            pos += 2
        body_end = pos + length
        if op == ACT_CONSTANT_POOL:
            n = struct.unpack_from("<H", buf, pos)[0]
            p = pos + 2
            pool = []
            for _ in range(n):
                s, p = read_cstr(buf, p)
                pool.append(s)
        elif op == ACT_PUSH:
            recent.extend(decode_push(buf, pos, body_end, pool))
        elif op == ACT_GET_VARIABLE:
            recent.append(("getvar", None))
        elif op == ACT_CALL_METHOD:
            name = external_call_name(recent)
            if name is not None:
                found.add(("ExternalInterface", name))
            recent.append(("op", op))
        elif op == ACT_CALL_FUNCTION:
            # fscommand compiles to GetURL2 in most cases; keep for completeness
            recent.append(("op", op))
        elif op == ACT_GET_URL:
            url, _ = read_cstr(buf, pos)
            if url.lower().startswith("fscommand:"):
                found.add(("fscommand", url[len("fscommand:"):]))
        elif op in (ACT_DEFINE_FUNCTION, ACT_DEFINE_FUNCTION2):
            # Header only; skip into the body so the walk continues inside it.
            recent.append(("op", op))
            pos = body_end
            continue
        else:
            recent.append(("op", op))
        if len(recent) > 64:
            del recent[:-32]
        pos = body_end


def movie_calls(path):
    with open(path, "rb") as f:
        data = f.read()
    body = swf_body(data)
    found = set()
    for start, end in iter_action_blocks(body, skip_header(body), len(body)):
        scan_actions(body, start, end, found)
    return found


def main(argv):
    if len(argv) < 2:
        print(f"usage: {argv[0]} MOVIE.gfx [...]", file=sys.stderr)
        return 2
    for path in argv[1:]:
        for kind, name in sorted(movie_calls(path), key=lambda kn: (kn[0], kn[1] or "")):
            print(f"{path}\t{kind}\t{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
