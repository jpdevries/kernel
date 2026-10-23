#!/usr/bin/env python3
"""Disassembler for Adobe Pixel Bender bytecode (.pbj).

Usage: python3 pbjdis.py file.pbj [file2.pbj ...]

Prints the kernel header (metadata, parameters, inputs) followed by one
line of pseudo-code per instruction. Registers are written f<n> (float)
and i<n> (int); every register is a 4-component vector.
"""
import struct
import sys

OPS = {
    0x00: "nop", 0x01: "add", 0x02: "sub", 0x03: "mul", 0x04: "rcp",
    0x05: "div", 0x06: "atan2", 0x07: "pow", 0x08: "mod", 0x09: "min",
    0x0A: "max", 0x0B: "step", 0x0C: "sin", 0x0D: "cos", 0x0E: "tan",
    0x0F: "asin", 0x10: "acos", 0x11: "atan", 0x12: "exp", 0x13: "exp2",
    0x14: "log", 0x15: "log2", 0x16: "sqrt", 0x17: "rsqrt", 0x18: "abs",
    0x19: "sign", 0x1A: "floor", 0x1B: "ceil", 0x1C: "fract", 0x1D: "mov",
    0x1E: "float2int", 0x1F: "int2float", 0x20: "matmatmul",
    0x21: "vecmatmul", 0x22: "matvecmul", 0x23: "normalize",
    0x24: "length", 0x25: "distance", 0x26: "dot", 0x27: "cross",
    0x28: "equal", 0x29: "notEqual", 0x2A: "lessThan",
    0x2B: "lessThanEqual", 0x2C: "not", 0x2D: "and", 0x2E: "or",
    0x2F: "xor", 0x30: "sampleNearest", 0x31: "sampleLinear",
    0x32: "loadConst", 0x33: "select", 0x34: "if", 0x35: "else",
    0x36: "endif", 0x37: "float2bool", 0x38: "bool2float",
    0x39: "int2bool", 0x3A: "bool2int", 0x3B: "vectorEqual",
    0x3C: "vectorNotEqual", 0x3D: "any", 0x3E: "all",
    0x3F: "smoothStep",
}

# Binary ops written as infix: dst op= src
INFIX = {"add": "+", "sub": "-", "mul": "*", "div": "/"}
# Comparison ops write a bool into the int "condition" register
COMPARE = {"lessThan": "<", "lessThanEqual": "<=", "equal": "==",
           "notEqual": "!=", "and": "&&", "or": "||", "xor": "^^"}

TYPES = {1: "float", 2: "float2", 3: "float3", 4: "float4",
         5: "float2x2", 6: "float3x3", 7: "float4x4", 8: "int",
         9: "int2", 10: "int3", 11: "int4", 12: "string", 13: "bool",
         14: "bool2", 15: "bool3", 16: "bool4"}
COMP = "xyzw"


def reg(r):
    return ("i%d" % (r & 0x7FFF)) if r & 0x8000 else ("f%d" % r)


def mask_str(m):
    return "".join(c for i, c in enumerate(COMP) if m & (8 >> i))


def swz_str(s, n):
    return "".join(COMP[(s >> (6 - 2 * i)) & 3] for i in range(n))


class Reader:
    def __init__(self, data):
        self.d, self.p = data, 0

    def u8(self):
        v = self.d[self.p]; self.p += 1; return v

    def u16(self):
        v = struct.unpack_from("<H", self.d, self.p)[0]; self.p += 2; return v

    def i32(self):
        v = struct.unpack_from("<i", self.d, self.p)[0]; self.p += 4; return v

    def f32be(self):
        v = struct.unpack_from(">f", self.d, self.p)[0]; self.p += 4; return v

    def i32be(self):
        v = struct.unpack_from(">i", self.d, self.p)[0]; self.p += 4; return v

    def cstr(self):
        e = self.d.index(0, self.p)
        s = self.d[self.p:e].decode("latin-1"); self.p = e + 1; return s

    def value(self, t):
        if 1 <= t <= 7:
            n = {1: 1, 2: 2, 3: 3, 4: 4, 5: 4, 6: 9, 7: 16}[t]
            v = [round(self.f32be(), 6) for _ in range(n)]
        elif 8 <= t <= 11:
            v = [self.u16() for _ in range(t - 7)]
        elif t == 12:
            return repr(self.cstr())
        else:
            v = [self.u16() for _ in range(t - 12)]
        return v[0] if len(v) == 1 else v

    def done(self):
        return self.p >= len(self.d)


def fmt(v):
    if isinstance(v, float):
        return ("%.6f" % v).rstrip("0").rstrip(".") if v != int(v) else "%.1f" % v
    return str(v)


def disassemble(path):
    r = Reader(open(path, "rb").read())
    out, indent = [], 0
    while not r.done():
        op = r.u8()
        if op == 0xA5:
            out.append("// pbj version %d" % r.i32())
        elif op == 0xA4:
            n = r.u16()
            name = r.d[r.p:r.p + n].decode(); r.p += n
            out.append("kernel %s" % name)
        elif op == 0xA0:
            t = r.u8(); k = r.cstr()
            out.append("  meta %s = %s" % (k, fmt(r.value(t))))
        elif op == 0xA1:
            q = r.u8(); t = r.u8(); rg = r.u16(); m = r.u8(); name = r.cstr()
            if t in (5, 6, 7):
                where = reg(rg) + " (matrix)"
            else:
                where = "%s.%s" % (reg(rg), mask_str(m))
            out.append("  %s %s %s  -> %s" % ("in " if q == 1 else "out", TYPES.get(t, t), name, where))
        elif op == 0xA2:
            t = r.u8(); k = r.cstr()
            out.append("      %s: %s" % (k, fmt(r.value(t))))
        elif op == 0xA3:
            idx = r.u8(); ch = r.u8(); name = r.cstr()
            out.append("  input image%d %s  -> tex%d" % (ch, name, idx))
        else:
            out.append("  " * indent + "  " + instr(op, r))
            if op == 0x34:
                indent += 1
            elif op == 0x36:
                indent -= 1
    return "\n".join(out)


def instr(op, r):
    name = OPS.get(op, "op_%02x" % op)
    start = r.p
    if op == 0x32:  # load constant
        dst = r.u16(); m = r.u8()
        val = r.i32be() if dst & 0x8000 else round(r.f32be(), 6)
        return "%s.%s = %s" % (reg(dst), mask_str(m >> 4), fmt(val))
    if op in (0x30, 0x31):  # texture sample
        dst = r.u16(); m = r.u8(); src = r.u16(); sw = r.u8(); tex = r.u8()
        return "%s.%s = %s(tex%d, %s.%s)" % (reg(dst), mask_str(m >> 4), name, tex, reg(src), swz_str(sw, 2))
    if op == 0x34:  # if
        r.p += 3; src = r.u16(); sw = r.u8(); r.u8()
        return "if (%s.%s) {" % (reg(src), swz_str(sw, 1))
    if op == 0x35:
        r.p += 7; return "} else {"
    if op == 0x36:
        r.p += 7; return "}"
    if op == 0x33:  # select: dst = cond ? a : b   (12 bytes)
        dst = r.u16(); m = r.u8(); c = r.u16(); csw = r.u8(); r.u8()
        a = r.u16(); asw = r.u8(); b = r.u16(); bsw = r.u8()
        n = (m & 3) + 1
        return "%s.%s = %s.%s ? %s.%s : %s.%s" % (reg(dst), mask_str(m >> 4), reg(c), swz_str(csw, 1),
                                                  reg(a), swz_str(asw, n), reg(b), swz_str(bsw, n))
    dst = r.u16(); m = r.u8(); src = r.u16(); sw = r.u8(); z = r.u8()
    size = (m & 3) + 1
    matrix = (m >> 2) & 3
    dm = mask_str(m >> 4)
    d = "%s.%s" % (reg(dst), dm) if dm else reg(dst)
    s = "%s.%s" % (reg(src), swz_str(sw, size))
    if matrix:
        s = "%s(matrix%d)" % (reg(src), matrix + 1)
    if name == "mov":
        return "%s = %s" % (d, s)
    if name in INFIX:
        return "%s %s= %s" % (d, INFIX[name], s)
    if name in COMPARE:
        # result goes to the bool register (written as dst); left operand is dst
        return "%s = (%s.%s %s %s)" % (d, reg(dst), swz_str(sw, size) if False else dm or "x", COMPARE[name], s)
    if name in ("atan2", "pow", "mod", "min", "max", "step", "dot", "distance", "cross"):
        return "%s = %s(%s, %s)" % (d, name, d, s)
    return "%s = %s(%s)" % (d, name, s)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print("=" * 70)
        print("// " + p)
        print(disassemble(p))
