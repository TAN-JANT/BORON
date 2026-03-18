from boron.assembler.encoded_bytes import EncodedByte,IMM_Byte,Opcode_Byte,MODRM_Byte,Prefix_Byte,SIB_Byte,SYMBOL_Byte
from enum import Enum

class REX_Byte(EncodedByte):
    """
    Represents an x86-64 REX prefix byte.
    """
    def __init__(self, W: int, R: int, X: int, B: int):
        self.W = W & 1
        self.R = R & 1
        self.X = X & 1
        self.B = B & 1

    def emit(self) -> bytes:
        value = 0x40 | (self.W << 3) | (self.R << 2) | (self.X << 1) | self.B
        return bytes([value])

opcode_size_prefix = Prefix_Byte(bytes([0x66]))
opcode_addr_prefix = Prefix_Byte(bytes([0x67]))

class SEG_PREFIX(Enum):
    es = Prefix_Byte(bytes([0x26]))
    cs = Prefix_Byte(bytes([0x2E]))
    ss = Prefix_Byte(bytes([0x36]))
    ds = Prefix_Byte(bytes([0x3E]))
    fs = Prefix_Byte(bytes([0x64]))
    gs = Prefix_Byte(bytes([0x65]))

LOCK_PREFIX = Prefix_Byte(bytes([0xF0]))
REP_PREFIX = Prefix_Byte(bytes([0xF3]))
REPNE_PREFIX = Prefix_Byte(bytes([0xF2]))
