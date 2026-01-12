from abc import ABC, abstractmethod
from typing import Literal
from enum import Enum


class EncodedByte(ABC):
    """Base class for all encodable byte objects."""
    @abstractmethod
    def emit(self) -> bytes:
        """Return the final encoded bytes."""
        pass


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


class SIB_Byte(EncodedByte):
    """
    Represents an x86 SIB (Scale-Index-Base) byte.
    """
    def __init__(self, base: int, scale: Literal[0b00,0b01,0b10,0b11], index: int):
        self.base = base & 0b111
        self.scale = scale & 0b11
        self.index = index & 0b111

    def emit(self) -> bytes:
        value = (self.scale << 6) | (self.index << 3) | self.base
        return bytes([value])


class MODRM_Byte(EncodedByte):
    """
    Represents an x86 ModR/M byte.
    """
    def __init__(self, mod: int, reg: int, rm: int):
        self.mod = mod & 0b11
        self.reg = reg & 0b111
        self.rm = rm & 0b111

    def emit(self) -> bytes:
        value = (self.mod << 6) | (self.reg << 3) | self.rm
        return bytes([value])


class Opcode_Byte(EncodedByte):
    """
    Represents a single-byte opcode.
    """
    def __init__(self, opcode: list[int]):
        self.opcode = bytes([i & 0xFF for i in opcode])

    def emit(self) -> bytes:
        return self.opcode


class IMM_Byte(EncodedByte):
    """
    Represents an immediate value of arbitrary byte size.
    """
    def __init__(self, value: int, size: int,signed: bool = False):
        self.value = value
        self.size = size  # bytes: 1,2,4,8...
        self.signed = signed

    def emit(self) -> bytes:
        return self.value.to_bytes(self.size, byteorder="little", signed=self.signed)
    
class SYMBOL_Byte(IMM_Byte):
    """
    Represents a place holder.
    """
    def __init__(self, name:str, size: int):
        value = 0  # Placeholder value; actual address resolution happens later
        self.name = name
        super().__init__(value, size)


class Prefix_Byte(EncodedByte):
    def __init__(self,value:bytes):
        self.value = value
    def emit(self) -> bytes:
        return self.value
    

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