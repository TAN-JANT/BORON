from __future__ import annotations
from typing import Literal
from dataclasses import dataclass

@dataclass(frozen=True)
class GeneralPurposeRegister:
    code : int
    size : Literal[1,2,4,8]     = 1
    requires_expand     : bool  = False
    requires_rex        : bool  = False
    rex_incompatible : bool  = False
    requires_mandatory  : bool  = False
    requires_rex_w_bit  : bool  = False

    def require_expand(self):
        return GeneralPurposeRegister(
            self.code,
            self.size,
            requires_expand=True,
            requires_rex=self.requires_rex,
            rex_incompatible=self.rex_incompatible,
            requires_mandatory=self.requires_mandatory,
            requires_rex_w_bit=self.requires_rex_w_bit
        )

    def require_rex(self):
        return GeneralPurposeRegister(
            self.code,
            self.size,
            requires_expand=self.requires_expand,
            requires_rex=True,
            rex_incompatible=self.rex_incompatible,
            requires_mandatory=self.requires_mandatory,
            requires_rex_w_bit=self.requires_rex_w_bit
        )

    def make_rex_incompatible(self):
        return GeneralPurposeRegister(
            self.code,
            self.size,
            requires_expand=self.requires_expand,
            requires_rex=self.requires_rex,
            rex_incompatible=True,
            requires_mandatory=self.requires_mandatory,
            requires_rex_w_bit=self.requires_rex_w_bit
        )

    def make_8bit(self):
        return GeneralPurposeRegister(
            self.code,
            size=1,
            requires_expand=self.requires_expand,
            requires_rex=self.requires_rex,
            rex_incompatible=self.rex_incompatible,
            requires_mandatory=self.requires_mandatory,
            requires_rex_w_bit=self.requires_rex_w_bit
        )

    def make_16bit(self):
        return GeneralPurposeRegister(
            self.code,
            size=2,
            requires_expand=self.requires_expand,
            requires_rex=self.requires_rex,
            rex_incompatible=self.rex_incompatible,
            requires_mandatory=True,
            requires_rex_w_bit=self.requires_rex_w_bit
        )

    def make_32bit(self):
        return GeneralPurposeRegister(
            self.code,
            size=4,
            requires_expand=self.requires_expand,
            requires_rex=self.requires_rex,
            rex_incompatible=self.rex_incompatible,
            requires_mandatory=self.requires_mandatory,
            requires_rex_w_bit=self.requires_rex_w_bit
        )

    def make_64bit(self):
        return GeneralPurposeRegister(
            self.code,
            size=8,
            requires_expand=self.requires_expand,
            requires_rex=True,
            rex_incompatible=self.rex_incompatible,
            requires_mandatory=self.requires_mandatory,
            requires_rex_w_bit=True
        )

    def is_8bit(self): return self.size == 1
    def is_16bit(self): return self.size == 2
    def is_32bit(self): return self.size == 4
    def is_64bit(self): return self.size == 8
    def is_rex_incompatible(self): return self.rex_incompatible
    def is_requires_rex(self): return self.requires_rex
    def is_requires_W(self): return self.requires_rex_w_bit 
    def is_expanded(self): return self.requires_expand
    def get_code(self): return self.code

@dataclass
class SegmentRegister:
    def __init__(self,code:int):
        self.code = code
    def get_code(self): return self.code

class SegmentRegisters:
    es      = SegmentRegister(0)
    cs      = SegmentRegister(1)
    ss      = SegmentRegister(2)
    ds      = SegmentRegister(3)
    fs      = SegmentRegister(4)
    gs      = SegmentRegister(5)
    list = [
        es,
        cs,
        ss,
        ds,
        fs,
        gs,
    ]

class GPRegisters :
    # --- 8-bit ---
    al = GeneralPurposeRegister(0b000).make_8bit()
    cl = GeneralPurposeRegister(0b001).make_8bit()
    dl = GeneralPurposeRegister(0b010).make_8bit()
    bl = GeneralPurposeRegister(0b011).make_8bit()

    # --- high-8 registers (REX incompitable) ---
    ah = GeneralPurposeRegister(0b100).make_8bit().make_rex_incompatible()
    ch = GeneralPurposeRegister(0b101).make_8bit().make_rex_incompatible()
    dh = GeneralPurposeRegister(0b110).make_8bit().make_rex_incompatible()
    bh = GeneralPurposeRegister(0b111).make_8bit().make_rex_incompatible()

    # --- low-8 (requires REX ) ---
    spl = GeneralPurposeRegister(0b100).make_8bit().require_rex()
    bpl = GeneralPurposeRegister(0b101).make_8bit().require_rex()
    sil = GeneralPurposeRegister(0b110).make_8bit().require_rex()
    dil = GeneralPurposeRegister(0b111).make_8bit().require_rex()

    # --- 16-bit ---
    ax = GeneralPurposeRegister(0b000).make_16bit()
    cx = GeneralPurposeRegister(0b001).make_16bit()
    dx = GeneralPurposeRegister(0b010).make_16bit()
    bx = GeneralPurposeRegister(0b011).make_16bit()
    sp = GeneralPurposeRegister(0b100).make_16bit()
    bp = GeneralPurposeRegister(0b101).make_16bit()
    si = GeneralPurposeRegister(0b110).make_16bit()
    di = GeneralPurposeRegister(0b111).make_16bit()

    # --- 32-bit ---
    eax = GeneralPurposeRegister(0b000).make_32bit()
    ecx = GeneralPurposeRegister(0b001).make_32bit()
    edx = GeneralPurposeRegister(0b010).make_32bit()
    ebx = GeneralPurposeRegister(0b011).make_32bit()
    esp = GeneralPurposeRegister(0b100).make_32bit()
    ebp = GeneralPurposeRegister(0b101).make_32bit()
    esi = GeneralPurposeRegister(0b110).make_32bit()
    edi = GeneralPurposeRegister(0b111).make_32bit()

    # --- 64-bit ---
    rax = GeneralPurposeRegister(0b000).make_64bit()
    rcx = GeneralPurposeRegister(0b001).make_64bit()
    rdx = GeneralPurposeRegister(0b010).make_64bit()
    rbx = GeneralPurposeRegister(0b011).make_64bit()
    rsp = GeneralPurposeRegister(0b100).make_64bit()
    rbp = GeneralPurposeRegister(0b101).make_64bit()
    rsi = GeneralPurposeRegister(0b110).make_64bit()
    rdi = GeneralPurposeRegister(0b111).make_64bit()

    r8   = GeneralPurposeRegister(0b001).make_64bit().require_expand()
    r8d  = GeneralPurposeRegister(0b001).make_32bit().require_expand()
    r8w  = GeneralPurposeRegister(0b001).make_16bit().require_expand()
    r8b  = GeneralPurposeRegister(0b001).make_8bit().require_expand().require_rex()

    r9  = GeneralPurposeRegister(0b001).make_64bit().require_expand()
    r9d = GeneralPurposeRegister(0b001).make_32bit().require_expand()
    r9w = GeneralPurposeRegister(0b001).make_16bit().require_expand()
    r9b = GeneralPurposeRegister(0b001).make_8bit().require_expand().require_rex()

    r10  = GeneralPurposeRegister(0b010).make_64bit().require_expand()
    r10d = GeneralPurposeRegister(0b010).make_32bit().require_expand()
    r10w = GeneralPurposeRegister(0b010).make_16bit().require_expand()
    r10b = GeneralPurposeRegister(0b010).make_8bit().require_expand().require_rex()

    r11  = GeneralPurposeRegister(0b011).make_64bit().require_expand()
    r11d = GeneralPurposeRegister(0b011).make_32bit().require_expand()
    r11w = GeneralPurposeRegister(0b011).make_16bit().require_expand()
    r11b = GeneralPurposeRegister(0b011).make_8bit().require_expand().require_rex()

    r12  = GeneralPurposeRegister(0b100).make_64bit().require_expand()
    r12d = GeneralPurposeRegister(0b100).make_32bit().require_expand()
    r12w = GeneralPurposeRegister(0b100).make_16bit().require_expand()
    r12b = GeneralPurposeRegister(0b100).make_8bit().require_expand().require_rex()

    r13  = GeneralPurposeRegister(0b101).make_64bit().require_expand()
    r13d = GeneralPurposeRegister(0b101).make_32bit().require_expand()
    r13w = GeneralPurposeRegister(0b101).make_16bit().require_expand()
    r13b = GeneralPurposeRegister(0b101).make_8bit().require_expand().require_rex()

    r14  = GeneralPurposeRegister(0b110).make_64bit().require_expand()
    r14d = GeneralPurposeRegister(0b110).make_32bit().require_expand()
    r14w = GeneralPurposeRegister(0b110).make_16bit().require_expand()
    r14b = GeneralPurposeRegister(0b110).make_8bit().require_expand().require_rex()

    r15  = GeneralPurposeRegister(0b111).make_64bit().require_expand()
    r15d = GeneralPurposeRegister(0b111).make_32bit().require_expand()
    r15w = GeneralPurposeRegister(0b111).make_16bit().require_expand()
    r15b = GeneralPurposeRegister(0b111).make_8bit().require_expand().require_rex()

    list = [
        al,
        cl,
        dl,
        bl,
        ah,
        ch,
        dh,
        bh,
        spl,
        bpl,
        sil,
        dil,
        ax,
        cx,
        dx,
        bx,
        sp,
        bp,
        si,
        di,
        eax,
        ecx,
        edx,
        ebx,
        esp,
        ebp,
        esi,
        edi,
        rax,
        rcx,
        rdx,
        rbx,
        rsp,
        rbp,
        rsi,
        rdi,
        r8,
        r8d,
        r8w,
        r8b,
        r9,
        r9d,
        r9w,
        r9b,
        r10,
        r10d,
        r10w,
        r10b,
        r11,
        r11d,
        r11w,
        r11b,
        r12,
        r12d,
        r12w,
        r12b,
        r13,
        r13d,
        r13w,
        r13b,
        r14,
        r14d,
        r14w,
        r14b,
        r15,
        r15d,
        r15w,
        r15b,
    ]

