from __future__ import annotations
from typing import Literal
from .registers import GeneralPurposeRegister as GPRegister
from .registers import SegmentRegister as SRegister
from .encoded_bytes import EncodedByte, IMM_Byte,SIB_Byte,SEG_PREFIX,SYMBOL_Byte
from boron.assembler.instructions import baseinstr

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

class RegMemBase:
    def __init__(self):
        self.mod: int = 0b00
        self.code: int = 0b00
        self.displacement: EncodedByte | None = None
        self.X = 0
        self.B = 0
        self.SIB :SIB_Byte|None= None
        self.requires_mandatory = False
        self.segment_override   : EncodedByte |None = None
        self.size : Literal[1, 2, 4, 8] = 1

    def set_size(self,size: Literal[1, 2, 4, 8]):
        self.size = size
        return self

    def add_segment_override(self,SReg:SEG_PREFIX):
        self.segment_override   = SReg.value
        return self

    def requires_rex(self) -> bool:
        return self.B == 1 or self.X == 1

class Immediate(baseinstr):
    def __init__(self, value: int, size: Literal[1, 2, 4, 8], signed: bool = False):
        self.value = value
        self.size = size
        self.signed = signed

    def emit(self) -> IMM_Byte:
        return IMM_Byte(self.value, self.size,self.signed)

class SYMBOL(Immediate):
    def __init__(self,name:str,size: Literal[1, 2, 4, 8],is_relative:bool=False,addend:int=0):
        super().__init__(0,size,False)
        self.name = name
        self.is_relative = is_relative
        self.addend = addend
        

    def emit(self) -> SYMBOL_Byte:
        return SYMBOL_Byte(self.name,self.size,self.is_relative,self.addend)

class SIB(RegMemBase):
    def __init__(self,size:int=1):
        super().__init__()
        self.base: GPRegister | None = None
        self.index: GPRegister | None = None
        self.scale: int | None = None
        self.offset: int | None = None
        self.__base_code: int | None = None
        self.__index_code: int | None = None
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
        self.X = 0
        self.B = 0
        self.displacement = IMM_Byte(self.offset, 4)
        self.SIB = SIB_Byte(self.__base_code,self.scale,self.__index_code)
        return self

    # [index * scale + disp]
    def no_base(
        self,
        index: GPRegister,
        offset: Immediate | None,
        scale: Literal[0b00, 0b01, 0b10, 0b11] = 0b00,
    ):
        if not (index.is_32bit() or index.is_64bit()):
            raise ValueError("Index register must be 32 bit or 64 bit")

        if index.get_code() == 0b100:
            return self.just_offset(offset)

        if offset and offset.size > 4:
            raise ValueError("Offset value must fit in 32 bit")

        if index.is_32bit():
            self.requires_mandatory = True

        self.__base_code = 0b101
        self.__index_code = index.get_code()
        self.X = index.is_expanded()
        self.B = 0
        self.scale = scale
        self.offset = offset.value if offset else 0

        if offset is None:
            self.displacement = None
            self.mod = 0b00
            self.SIB = SIB_Byte(self.__base_code,self.scale,self.__index_code)
            return self

        if offset.size <= 1:
            self.displacement = IMM_Byte(self.offset, 1)
            self.mod = 0b01
            self.SIB = SIB_Byte(self.__base_code,self.scale,self.__index_code)
            return self

        if offset.size <= 4:
            self.displacement = IMM_Byte(self.offset, 4)
            self.mod = 0b10
            self.SIB = SIB_Byte(self.__base_code,self.scale,self.__index_code)
            return self

        raise ValueError("Offset value must fit in 32 bit")

    # [base + disp]
    def no_index(self, base: GPRegister, offset: Immediate | None):
        if not (base.is_32bit() or base.is_64bit()):
            raise ValueError("Base register must be 32 bit or 64 bit")
        self.base = base
        self.__base_code = base.get_code()
        self.__index_code = 0b100
        self.B = base.is_expanded()
        self.X = 0
        self.scale = 0b00
        self.offset = offset.value if offset else 0
        if self.base.is_32bit():
            self.requires_mandatory = True

        if offset is None or offset.value == 0:
            self.displacement = None
            self.mod = 0b00
        elif offset.size <= 1:
            self.displacement = IMM_Byte(self.offset, 1)
            self.mod = 0b01
        elif offset.size <= 4:
            self.displacement = IMM_Byte(self.offset, 4)
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
        if not (index.is_32bit() or index.is_64bit()):
            raise ValueError("Index register must be 32 bit or 64 bit")
        if not (base.is_32bit() or base.is_64bit()):
            raise ValueError("Base register must be 32 bit or 64 bit")
        if not base.size == index.size:
            raise ValueError("Base and Index register sizes must match")
        
        if index.get_code() == 0b100 and not index.is_expanded():
            raise ValueError("Index register cannot be stack pointer")

        if index.is_32bit():
            self.requires_mandatory = True


        self.base = base
        self.index = index
        self.scale = scale
        self.offset = 0

        self.__base_code = base.get_code()
        self.__index_code = index.get_code()
        self.B = base.is_expanded()
        self.X = index.is_expanded()

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
        if not (index.is_32bit() or index.is_64bit()):
            raise ValueError("Index register must be 32 bit or 64 bit")
        if not (base.is_32bit() or base.is_64bit()):
            raise ValueError("Base register must be 32 bit or 64 bit")
        if not base.size == index.size:
            raise ValueError("Base and Index register sizes must match")

        if index.get_code() == 0b100 and not index.is_expanded():
            raise ValueError("Index register cannot be stack pointer")

        if offset and offset.size > 4:
            raise ValueError("Offset value must fit in 32 bit")

        if index.is_32bit():
            self.requires_mandatory = True
        self.base = base
        self.index = index
        self.scale = scale
        self.offset = offset.value if offset is not None else 0

        self.__base_code = base.get_code()
        self.__index_code = index.get_code()
        self.B = base.is_expanded()
        self.X = index.is_expanded()
        if offset is None or offset.value == 0:
            self.displacement = None
            self.mod = 0b00
        elif offset.size == 1:
            self.displacement = IMM_Byte(self.offset, 1)
            self.mod = 0b01
        else:
            self.displacement = IMM_Byte(self.offset, 4)
            self.mod = 0b10
        self.SIB = SIB_Byte(self.__base_code,self.scale,self.__index_code)
        return self

class Relative(RegMemBase):
    def __init__(self, offset: Immediate):
        super().__init__()
        if offset.size > 4:
            raise ValueError("Relative offset must fit 32 bit")

        self.mod = 0b00
        self.code = 0b101
        
        offset.size = 4
        self.displacement = offset.emit()

class RegMem(RegMemBase):
    def __init__(self):
        super().__init__()
        self.code = 0b00

    def make_SIB(self) -> SIB:
        return SIB()

    def make_REL(self, offset: Immediate) -> Relative:
        return Relative(offset)

    def no_offset(self, reg: GPRegister):
        if not (reg.is_32bit() or reg.is_64bit()):
            raise ValueError("Register must be 32 bit or 64 bit")
        if reg.is_32bit():
            self.requires_mandatory = True
        self.B = reg.is_expanded()
        if reg.get_code() == 0b100:
            raise ValueError("Stack pointer cant be used as R/M register")
        if reg.get_code() == 0b101:
            self.code = 0b101
            self.mod = 0b01
        return self

    def with_offset(self, reg: GPRegister, offset: Immediate):
        if not (reg.is_32bit() or reg.is_64bit()):
            raise ValueError("Register must be 32 bit or 64 bit")
        if reg.is_32bit():
            self.requires_mandatory = True
        self.B = reg.is_expanded()
        if reg.get_code() == 0b100:
            raise ValueError("Stack pointer cant be used as R/M register")

        self.code = reg.get_code()
        if offset.size <= 1:
            self.displacement = IMM_Byte(offset.value, 1)
            self.mod = 0b01
            return self
        if offset.size <= 4:
            self.displacement = IMM_Byte(offset.value, 4)
            self.mod = 0b10
            return self
        else:
            raise ValueError("Offset value must fit in 32 bit")
