from __future__ import annotations
from typing import Literal
from .registers import GeneralPurposeRegister as GPRegister
from .registers import SegmentRegister as SRegister
from .registers import GPRegisters
from warnings import warn
from .encoded_bytes import EncodedByte,SIB_Byte,SEG_PREFIX,IMM_Byte,SYMBOL_Byte

def fits_int(value: int | None, bits: int, signed: bool = True) -> bool:
    if value is None:
        return True

    if signed:
        min_val = -(1 << (bits - 1))
        max_val = (1 << (bits - 1)) - 1
    else:
        min_val = 0
        max_val = (1 << bits) - 1

    return min_val <= value <= max_val

class Immediate:
    def __init__(self, value: int, size: Literal[1, 2, 4, 8], signed: bool = False):
        self.value = value
        self.size = size
        self.signed = signed

    def emit(self) -> IMM_Byte:
        return IMM_Byte(self.value, self.size,self.signed)

class SYMBOL(Immediate):
    def __init__(self,name:str,size: Literal[1, 2, 4, 8]):
        super().__init__(0,size,False)
        self.name = name
    
    def emit(self) -> SYMBOL_Byte:
        return SYMBOL_Byte(self.name,self.size)

class RegMemBase:
    def __init__(self):
        self.mod: int = 0b00
        self.code: int = 0b00
        self.immediate: EncodedByte | None = None
        self.SIB :SIB_Byte|None= None
        self.requires_mandatory = False
        self.segment_override   = None
        self.size : Literal[1, 2, 4] = 1

    def set_size(self,size: Literal[1, 2, 4]):
        self.size = size
        return self

    def add_segment_override(self,SReg:SEG_PREFIX):
        self.segment_override   = SReg.value
        return self

class SIB(RegMemBase):
    def __init__(self):
        super().__init__()
        self.base: GPRegister | None = None
        self.index: GPRegister | None = None
        self.scale: int | None = None
        self.offset: int | None = None
        self.__base_code: int | None = None
        self.__index_code: int | None = None
        self.requires_mandatory = True
        self.code = 0b100

    # [disp32]
    def just_offset(self, offset: Immediate | None):
        if offset is not None and offset.size > 4:
            raise ValueError("Offset value must fit in 32 bit")

        self.__base_code = 0b101
        self.__index_code = 0b100
        self.scale = 0b00
        self.offset = 0 if offset is None else offset.value
        self.mod = 0b00
        self.immediate = IMM_Byte(self.offset, 4)
        self.SIB = SIB_Byte(self.__base_code,self.scale,self.__index_code)
        return self

    # [index * scale + disp]
    def no_base(
        self,
        index: GPRegister,
        offset: Immediate | None,
        scale: Literal[0b00, 0b01, 0b10, 0b11] = 0b00,
    ):
        if not index.is_32bit():
            raise ValueError("Index register must be 32 bit")

        if index.get_code() == 0b100:
            return self.just_offset(offset)

        if offset and offset.size > 4:
            raise ValueError("Offset value must fit in 32 bit")

        if index.is_32bit():
            self.requires_mandatory = True

        self.__base_code = 0b101
        self.__index_code = index.get_code()
        self.scale = scale
        self.offset = offset.value if offset else 0

        if offset is None:
            self.immediate = None
            self.mod = 0b00
            self.SIB = SIB_Byte(self.__base_code,self.scale,self.__index_code)
            return self

        if offset.size <= 1:
            self.immediate = IMM_Byte(self.offset, 1)
            self.mod = 0b01
            self.SIB = SIB_Byte(self.__base_code,self.scale,self.__index_code)
            return self

        if offset.size <= 4:
            self.immediate = IMM_Byte(self.offset, 4)
            self.mod = 0b10
            self.SIB = SIB_Byte(self.__base_code,self.scale,self.__index_code)
            return self

        raise ValueError("Offset value must fit in 32 bit")

    # [base + disp]
    def no_index(self, base: GPRegister, offset: Immediate | None):
        if not base.is_32bit():
            raise ValueError("Base register must be 32 bit")
        self.base = base
        self.__base_code = base.get_code()
        self.__index_code = 0b100
        self.scale = 0b00
        self.offset = offset.value if offset else 0


        if offset is None or offset.value == 0:
            self.immediate = None
            self.mod = 0b00
        elif offset.size <= 1:
            self.immediate = IMM_Byte(self.offset, 1)
            self.mod = 0b01
        elif offset.size <= 4:
            self.immediate = IMM_Byte(self.offset, 4)
            self.mod = 0b10
        else:
            raise ValueError("Offset value must fit in 32 bit")
        self.SIB = SIB_Byte(self.__base_code,self.scale,self.__index_code)
        return self

    # [base + index * scale]
    def no_offset(
        self,
        base: GPRegister,
        index: GPRegister,
        scale: Literal[0b00, 0b01, 0b10, 0b11] = 0b00,
    ):
        if not index.is_32bit():
            raise ValueError("Index register must be 32 bit")
        if not base.is_32bit():
            raise ValueError("Base register must be 32 bit")
        if not base.size == index.size:
            raise ValueError("Base and Index register sizes must match")
        
        if index.get_code() == 0b100:
            raise ValueError("Index register cannot be stack pointer")

        self.base = base
        self.index = index
        self.scale = scale
        self.offset = 0

        self.__base_code = base.get_code()
        self.__index_code = index.get_code()

        self.mod = 0b00 if self.__base_code != 0b101 else 0b01
        self.SIB = SIB_Byte(self.__base_code,self.scale,self.__index_code)
        return self

    # [base + index * scale + disp]
    def normal(
        self,
        base: GPRegister,
        index: GPRegister,
        offset: Immediate | None,
        scale: Literal[0b00, 0b01, 0b10, 0b11] = 0b00,
    ):
        if not (index.is_32bit()):
            raise ValueError("Index register must be 32 bit")
        if not (base.is_32bit()):
            raise ValueError("Base register must be 32 bit")
        if not base.size == index.size:
            raise ValueError("Base and Index register sizes must match")

        if index.get_code() == 0b100:
            raise ValueError("Index register cannot be stack pointer")

        if offset and offset.size > 4:
            raise ValueError("Offset value must fit in 32 bit")

        self.base = base
        self.index = index
        self.scale = scale
        self.offset = offset.value if offset else 0

        self.__base_code = base.get_code()
        self.__index_code = index.get_code()

        if offset is None or offset.value == 0:
            self.immediate = None
            self.mod = 0b00
        elif offset.size == 1:
            self.immediate = IMM_Byte(self.offset, 1)
            self.mod = 0b01
        else:
            self.immediate = IMM_Byte(self.offset, 4)
            self.mod = 0b10
        self.SIB = SIB_Byte(self.__base_code,self.scale,self.__index_code)
        return self

class Relative(RegMemBase):
    def __init__(self, offset: Immediate):
        super().__init__()
        if offset.size > 4:
            raise ValueError("Relative offset must fit 32 bit")
        self.requires_mandatory = True
        self.mod = 0b00
        self.code = 0b101
        self.immediate = IMM_Byte(offset.value, 4)

class RegMem(RegMemBase):
    def __init__(self):
        super().__init__()
        self.mod  = 0b00
        self.code = 0b000

    def make_SIB(self) -> SIB:
        return SIB()

    def make_REL(self,offset:Immediate) -> Relative:
        return Relative(offset)

    def just_offset(self,offset:Immediate):
        if offset.size > 2 :
            raise ValueError("Offset value must be 2 bytes or less!")
        if offset.signed :
            warn("This is not relative addressing using signed offset may cause some unexpected behaivour!")

        self.code = 0b110
        self.mod  = 0b00
        offset.size = 2
        self.immediate = offset.emit()
        return self

    def no_offset(self,reg1:GPRegister,reg2:GPRegister|None):
        if reg2 is None:
            if reg1 == GPRegisters.bp:
                self.mod = 0b01
                self.immediate = IMM_Byte(0,1)
                self.code = 0b110
                return self

            if reg1 not in [GPRegisters.bx,GPRegisters.bp,GPRegisters.si,GPRegisters.di]:
                raise ValueError("Illegal register use")

            self.mod  = 0b00
            self.code = {
                GPRegisters.bx : 0b111,
                GPRegisters.di : 0b101,
                GPRegisters.si : 0b100,
            }[reg1]

            return self
        match {reg1,reg2}:
            case s if s == {GPRegisters.bx, GPRegisters.si}:
                self.code = 0b000
            case s if s == {GPRegisters.bx, GPRegisters.di}:
                self.code = 0b001
            case s if s == {GPRegisters.bp, GPRegisters.si}:
                self.code = 0b010
            case s if s == {GPRegisters.bp, GPRegisters.di}:
                self.code = 0b011
            case _:
                raise ValueError("Illegal register pair")
        self.mod = 0b00
        return self

    def with_offset(self,reg1:GPRegister,reg2:GPRegister|None,imm:Immediate):
        if imm.size > 2:
            raise ValueError("...")
        self.mod = 0b01 if imm.size == 1 else 0b10
        if reg2 is None:
            if reg1 not in [GPRegisters.bx,GPRegisters.bp,GPRegisters.si,GPRegisters.di]:
                raise ValueError("Illegal register use")

            self.code = {
                GPRegisters.bx: 0b111,
                GPRegisters.di: 0b101,
                GPRegisters.si: 0b100,
            }[reg1]

            return self
        match {reg1,reg2}:
            case s if s == {GPRegisters.bx, GPRegisters.si}:
                self.code = 0b000
            case s if s == {GPRegisters.bx, GPRegisters.di}:
                self.code = 0b001
            case s if s == {GPRegisters.bp, GPRegisters.si}:
                self.code = 0b010
            case s if s == {GPRegisters.bp, GPRegisters.di}:
                self.code = 0b011
            case _:
                raise ValueError("Illegal register pair")

        return self