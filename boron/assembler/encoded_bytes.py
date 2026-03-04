from abc import ABC, abstractmethod
from typing import Literal


class EncodedByte(ABC):
    """Base class for all encodable byte objects."""
    @abstractmethod
    def emit(self) -> bytes:
        """Return the final encoded bytes."""
        pass

    def __len__(self):
        return len(self.emit())

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
    def __init__(self, opcode: bytearray):
        self.opcode = opcode

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
    def __init__(self, name:str, size: int, is_relative : bool=False,addend:int=0):
        value = 0  
        self.is_relative = is_relative
        self.name = name
        self.addend = addend
        super().__init__(value, size)

class Prefix_Byte(EncodedByte):
    def __init__(self,value:bytes):
        self.value = value
    def emit(self) -> bytes:
        return self.value

