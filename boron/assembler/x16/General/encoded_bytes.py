from boron.assembler.encoded_bytes import EncodedByte,IMM_Byte,Opcode_Byte,MODRM_Byte,Prefix_Byte,SIB_Byte,SYMBOL_Byte
from .registers import SegmentRegisters
from enum import Enum

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