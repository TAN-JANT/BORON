from __future__ import annotations
from typing import Literal
from dataclasses import dataclass

@dataclass(frozen=True)
class GeneralPurposeRegister:
    code : int
    size : Literal[1,2,4]     = 1
    requires_mandatory  : bool  = False

    def make_8bit(self):
        return GeneralPurposeRegister(
            self.code,
            size=1,
            requires_mandatory=self.requires_mandatory,
        )

    def make_16bit(self):
        return GeneralPurposeRegister(
            self.code,
            size=2,
            requires_mandatory=True,
        )

    def make_32bit(self):
        return GeneralPurposeRegister(
            self.code,
            size=4,
            requires_mandatory=True,
        )

    def is_8bit(self): return self.size == 1
    def is_16bit(self): return self.size == 2
    def is_32bit(self): return self.size == 4
    def get_code(self): return self.code

@dataclass
class SegmentRegister:
    def __init__(self,code:int):
        self.code = code

class SegmentRegisters:
    es = SegmentRegister(0)
    cs = SegmentRegister(1)
    ss = SegmentRegister(2)
    ds = SegmentRegister(3)
    fs = SegmentRegister(4)
    gs = SegmentRegister(5)
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
    ah = GeneralPurposeRegister(0b100).make_8bit()
    ch = GeneralPurposeRegister(0b101).make_8bit()
    dh = GeneralPurposeRegister(0b110).make_8bit()
    bh = GeneralPurposeRegister(0b111).make_8bit()

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
    list = [
        al,
        cl,
        dl,
        bl,
        ah,
        ch,
        dh,
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
    ]
