from __future__ import annotations
from typing import Literal
from dataclasses import dataclass, replace

@dataclass(frozen=True)
class GeneralPurposeRegister:
    name: str
    code: int
    size: Literal[1, 2, 4, 8] = 1
    requires_expand: bool = False
    requires_rex: bool = False
    rex_incompatible: bool = False
    requires_mandatory: bool = False
    requires_rex_w_bit: bool = False

    def require_expand(self):
        return replace(self, requires_expand=True, requires_rex=True)

    def require_rex(self):
        return replace(self, requires_rex=True)

    def make_rex_incompatible(self):
        return replace(self, rex_incompatible=True)

    def make_8bit(self):
        return replace(self, size=1)

    def make_16bit(self):
        return replace(self, size=2, requires_mandatory=True)

    def make_32bit(self):
        return replace(self, size=4)

    def make_64bit(self):
        return replace(self, size=8, requires_rex=True, requires_rex_w_bit=True)

    
    def is_8bit(self): return self.size == 1
    def is_16bit(self): return self.size == 2
    def is_32bit(self): return self.size == 4
    def is_64bit(self): return self.size == 8
    def is_rex_incompatible(self): return self.rex_incompatible
    def is_requires_rex(self): return self.requires_rex
    def is_requires_W(self): return self.requires_rex_w_bit 
    def is_expanded(self): return self.requires_expand
    def get_code(self): return self.code

@dataclass(frozen=True)
class SegmentRegister:
    name: str
    code: int

    def get_code(self): return self.code

class SegmentRegisters:
    es = SegmentRegister("es", 0)
    cs = SegmentRegister("cs", 1)
    ss = SegmentRegister("ss", 2)
    ds = SegmentRegister("ds", 3)
    fs = SegmentRegister("fs", 4)
    gs = SegmentRegister("gs", 5)
    
    list = [es, cs, ss, ds, fs, gs]

class GPRegisters:
    # --- 8-bit ---
    al = GeneralPurposeRegister("al", 0b000).make_8bit()
    cl = GeneralPurposeRegister("cl", 0b001).make_8bit()
    dl = GeneralPurposeRegister("dl", 0b010).make_8bit()
    bl = GeneralPurposeRegister("bl", 0b011).make_8bit()

    # --- high-8 registers (REX incompatible) ---
    ah = GeneralPurposeRegister("ah", 0b100).make_8bit().make_rex_incompatible()
    ch = GeneralPurposeRegister("ch", 0b101).make_8bit().make_rex_incompatible()
    dh = GeneralPurposeRegister("dh", 0b110).make_8bit().make_rex_incompatible()
    bh = GeneralPurposeRegister("bh", 0b111).make_8bit().make_rex_incompatible()

    # --- low-8 (requires REX) ---
    spl = GeneralPurposeRegister("spl", 0b100).make_8bit().require_rex()
    bpl = GeneralPurposeRegister("bpl", 0b101).make_8bit().require_rex()
    sil = GeneralPurposeRegister("sil", 0b110).make_8bit().require_rex()
    dil = GeneralPurposeRegister("dil", 0b111).make_8bit().require_rex()

    # --- 16-bit ---
    ax = GeneralPurposeRegister("ax", 0b000).make_16bit()
    cx = GeneralPurposeRegister("cx", 0b001).make_16bit()
    dx = GeneralPurposeRegister("dx", 0b010).make_16bit()
    bx = GeneralPurposeRegister("bx", 0b011).make_16bit()
    sp = GeneralPurposeRegister("sp", 0b100).make_16bit()
    bp = GeneralPurposeRegister("bp", 0b101).make_16bit()
    si = GeneralPurposeRegister("si", 0b110).make_16bit()
    di = GeneralPurposeRegister("di", 0b111).make_16bit()

    # --- 32-bit ---
    eax = GeneralPurposeRegister("eax", 0b000).make_32bit()
    ecx = GeneralPurposeRegister("ecx", 0b001).make_32bit()
    edx = GeneralPurposeRegister("edx", 0b010).make_32bit()
    ebx = GeneralPurposeRegister("ebx", 0b011).make_32bit()
    esp = GeneralPurposeRegister("esp", 0b100).make_32bit()
    ebp = GeneralPurposeRegister("ebp", 0b101).make_32bit()
    esi = GeneralPurposeRegister("esi", 0b110).make_32bit()
    edi = GeneralPurposeRegister("edi", 0b111).make_32bit()

    # --- 64-bit ---
    rax = GeneralPurposeRegister("rax", 0b000).make_64bit()
    rcx = GeneralPurposeRegister("rcx", 0b001).make_64bit()
    rdx = GeneralPurposeRegister("rdx", 0b010).make_64bit()
    rbx = GeneralPurposeRegister("rbx", 0b011).make_64bit()
    rsp = GeneralPurposeRegister("rsp", 0b100).make_64bit()
    rbp = GeneralPurposeRegister("rbp", 0b101).make_64bit()
    rsi = GeneralPurposeRegister("rsi", 0b110).make_64bit()
    rdi = GeneralPurposeRegister("rdi", 0b111).make_64bit()

    # --- Extended Registers ---
    r8   = GeneralPurposeRegister("r8",   0b000).make_64bit().require_expand()
    r8d  = GeneralPurposeRegister("r8d",  0b000).make_32bit().require_expand()
    r8w  = GeneralPurposeRegister("r8w",  0b000).make_16bit().require_expand()
    r8b  = GeneralPurposeRegister("r8b",  0b000).make_8bit().require_expand().require_rex()

    r9   = GeneralPurposeRegister("r9",   0b001).make_64bit().require_expand()
    r9d  = GeneralPurposeRegister("r9d",  0b001).make_32bit().require_expand()
    r9w  = GeneralPurposeRegister("r9w",  0b001).make_16bit().require_expand()
    r9b  = GeneralPurposeRegister("r9b",  0b001).make_8bit().require_expand().require_rex()

    # (Repeat pattern for r10-r15...)
    r10  = GeneralPurposeRegister("r10",  0b010).make_64bit().require_expand()
    r10d = GeneralPurposeRegister("r10d", 0b010).make_32bit().require_expand()
    r10w = GeneralPurposeRegister("r10w", 0b010).make_16bit().require_expand()
    r10b = GeneralPurposeRegister("r10b", 0b010).make_8bit().require_expand().require_rex()

    r11  = GeneralPurposeRegister("r11",  0b011).make_64bit().require_expand()
    r11d = GeneralPurposeRegister("r11d", 0b011).make_32bit().require_expand()
    r11w = GeneralPurposeRegister("r11w", 0b011).make_16bit().require_expand()
    r11b = GeneralPurposeRegister("r11b", 0b011).make_8bit().require_expand().require_rex()

    r12  = GeneralPurposeRegister("r12",  0b100).make_64bit().require_expand()
    r12d = GeneralPurposeRegister("r12d", 0b100).make_32bit().require_expand()
    r12w = GeneralPurposeRegister("r12w", 0b100).make_16bit().require_expand()
    r12b = GeneralPurposeRegister("r12b", 0b100).make_8bit().require_expand().require_rex()

    r13  = GeneralPurposeRegister("r13",  0b101).make_64bit().require_expand()
    r13d = GeneralPurposeRegister("r13d", 0b101).make_32bit().require_expand()
    r13w = GeneralPurposeRegister("r13w", 0b101).make_16bit().require_expand()
    r13b = GeneralPurposeRegister("r13b", 0b101).make_8bit().require_expand().require_rex()

    r14  = GeneralPurposeRegister("r14",  0b110).make_64bit().require_expand()
    r14d = GeneralPurposeRegister("r14d", 0b110).make_32bit().require_expand()
    r14w = GeneralPurposeRegister("r14w", 0b110).make_16bit().require_expand()
    r14b = GeneralPurposeRegister("r14b", 0b110).make_8bit().require_expand().require_rex()

    r15  = GeneralPurposeRegister("r15",  0b111).make_64bit().require_expand()
    r15d = GeneralPurposeRegister("r15d", 0b111).make_32bit().require_expand()
    r15w = GeneralPurposeRegister("r15w", 0b111).make_16bit().require_expand()
    r15b = GeneralPurposeRegister("r15b", 0b111).make_8bit().require_expand().require_rex()

    # The list is still populated with these instances
    list = [
        al, cl, dl, bl, ah, ch, dh, bh, spl, bpl, sil, dil,
        ax, cx, dx, bx, sp, bp, si, di,
        eax, ecx, edx, ebx, esp, ebp, esi, edi,
        rax, rcx, rdx, rbx, rsp, rbp, rsi, rdi,
        r8, r8d, r8w, r8b, r9, r9d, r9w, r9b,
        r10, r10d, r10w, r10b, r11, r11d, r11w, r11b,
        r12, r12d, r12w, r12b, r13, r13d, r13w, r13b,
        r14, r14d, r14w, r14b, r15, r15d, r15w, r15b,
    ]