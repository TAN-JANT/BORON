from __future__ import annotations
from dataclasses import dataclass
from ..General.registers import GPRegisters,GeneralPurposeRegister

@dataclass(frozen=True)
class SSERegister:
    code: int                 # low 3 bits
    size: int = 16            # 128-bit
    requires_expand: bool = False
    requires_rex: bool = False

    def require_expand(self):
        return SSERegister(
            code=self.code,
            size=self.size,
            requires_expand=True,
            requires_rex=True
        )

    def get_code(self): 
        return self.code

    def is_expanded(self): 
        return self.requires_expand

    def is_requires_rex(self): 
        return self.requires_rex

class SSERegisters:
    # --- XMM0–XMM7 (no REX needed) ---
    xmm0 = SSERegister(0b000)
    xmm1 = SSERegister(0b001)
    xmm2 = SSERegister(0b010)
    xmm3 = SSERegister(0b011)
    xmm4 = SSERegister(0b100)
    xmm5 = SSERegister(0b101)
    xmm6 = SSERegister(0b110)
    xmm7 = SSERegister(0b111)

    # --- XMM8–XMM15 (REX + expand) ---
    xmm8  = SSERegister(0b000).require_expand()
    xmm9  = SSERegister(0b001).require_expand()
    xmm10 = SSERegister(0b010).require_expand()
    xmm11 = SSERegister(0b011).require_expand()
    xmm12 = SSERegister(0b100).require_expand()
    xmm13 = SSERegister(0b101).require_expand()
    xmm14 = SSERegister(0b110).require_expand()
    xmm15 = SSERegister(0b111).require_expand()

    list = [
        xmm0, xmm1, xmm2, xmm3,
        xmm4, xmm5, xmm6, xmm7,
        xmm8, xmm9, xmm10, xmm11,
        xmm12, xmm13, xmm14, xmm15,
    ]
