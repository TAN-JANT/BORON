from . import operands,encoded_bytes,registers
from typing import Literal, Sequence

class Opcode:
    def __init__(self, bytes: list[int], modrm_extension: int | None = None):
        self.bytes = bytes
        self.modrm_extension = modrm_extension

class Instruction:
    def emit(self) -> Sequence[encoded_bytes.EncodedByte]:
        raise NotImplementedError


class R_RM_Instruction(Instruction):
    def __init__(self, reg:operands.GPRegister , rm:operands.RegMemBase, opcode: Opcode):
        self.reg = reg
        self.rm = rm
        self.opcode = opcode

    def emit(self):
        encoded :list[encoded_bytes.EncodedByte] = []
        modrm = encoded_bytes.MODRM_Byte(self.rm.mod,self.reg.get_code(),self.rm.code)
        sib = self.rm.SIB 
        imm = self.rm.immediate
        if self.rm.segment_override is not None:
            encoded.append(self.rm.segment_override)
        if self.reg.is_32bit():
            encoded.append(encoded_bytes.opcode_size_prefix)#16 -> 32
        if self.rm.requires_mandatory:
            encoded.append(encoded_bytes.opcode_addr_prefix)

        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        encoded.append(modrm)
        if sib is not None:
            encoded.append(sib)
        if imm is not None:
            encoded.append(imm)

        return encoded

class R_R_Instruction(Instruction):

    def __init__(
        self, reg1: operands.GPRegister, reg2: operands.GPRegister, opcode: Opcode
    ):
        self.reg1 = reg1
        self.reg2 = reg2

        if self.reg1.size != self.reg2.size:
            raise ValueError("Register sizes must match")
        self.opcode = opcode

    def emit(self):
        encoded: list[encoded_bytes.EncodedByte] = []
        modrm = encoded_bytes.MODRM_Byte(0b11, self.reg1.get_code(), self.reg2.get_code())

        if self.reg1.requires_mandatory or self.reg2.requires_mandatory:
            encoded.append(encoded_bytes.opcode_size_prefix)

        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        encoded.append(modrm)

        return encoded
    
class R_IMM_Instruction(Instruction):
    def __init__(self, reg:operands.GPRegister , imm:operands.Immediate, opcode: Opcode):
        self.reg = reg
        self.imm = imm
        self.opcode = opcode

    def emit(self):
        encoded :list[encoded_bytes.EncodedByte] = []

        if self.reg.requires_mandatory:
            encoded.append(encoded_bytes.opcode_size_prefix)
 
        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        if self.opcode.modrm_extension is not None:
            encoded.append(encoded_bytes.MODRM_Byte(0b11,self.opcode.modrm_extension,self.reg.get_code()))
        encoded.append(self.imm.emit())

        return encoded


class RM_IMM_Instruction(Instruction):
    def __init__(self, rm:operands.RegMemBase , imm:operands.Immediate, opcode: Opcode):
        self.rm = rm
        self.imm = imm
        self.opcode = opcode
        
        
        if ( imm.size > 4):
            raise ValueError("Immediate size must be 4 bytes or less")

    def emit(self):
        encoded :list[encoded_bytes.EncodedByte] = []
        modrm = encoded_bytes.MODRM_Byte(self.rm.mod,self.opcode.modrm_extension if self.opcode.modrm_extension is not None else 0,self.rm.code)
        sib = self.rm.SIB
        imm = self.imm.emit()
        rm_imm = self.rm.immediate
        if self.rm.segment_override is not None:
            encoded.append(self.rm.segment_override)
        if self.rm.size == 4:
            encoded.append(encoded_bytes.opcode_size_prefix) # 16 -> 32
        if self.rm.requires_mandatory:
            encoded.append(encoded_bytes.opcode_addr_prefix)


        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        encoded.append(modrm)
        
        if sib is not None:
            encoded.append(sib)
        if rm_imm is not None:
            encoded.append(rm_imm)
        encoded.append(imm)

        return encoded

class R_INSTRUCTION(Instruction):
    def __init__(self, reg:operands.GPRegister , opcode: Opcode):
        self.reg = reg
        self.opcode = opcode

    def emit(self):
        encoded :list[encoded_bytes.EncodedByte] = []
        if self.reg.requires_mandatory:
            encoded.append(encoded_bytes.opcode_size_prefix)

        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        if self.opcode.modrm_extension is not None:
            encoded.append(encoded_bytes.MODRM_Byte(0b11,self.opcode.modrm_extension,self.reg.get_code()))

        return encoded

class RM_INSTRUCTION(Instruction):
    def __init__(self, rm:operands.RegMemBase , opcode: Opcode):
        self.rm = rm
        self.opcode = opcode

    def emit(self):
        encoded :list[encoded_bytes.EncodedByte] = []
        modrm = encoded_bytes.MODRM_Byte(self.rm.mod,self.opcode.modrm_extension if self.opcode.modrm_extension is not None else 0,self.rm.code)
        sib = self.rm.SIB
        if self.rm.segment_override is not None:
            encoded.append(self.rm.segment_override)
        if self.rm.size == 4:
            encoded.append(encoded_bytes.opcode_size_prefix) # 16 -> 32
        if self.rm.requires_mandatory:
            encoded.append(encoded_bytes.opcode_addr_prefix)

        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        encoded.append(modrm)
        if sib is not None:
            encoded.append(sib)

        return encoded

class I_INSTRUCTION(Instruction):
    def __init__(self, imm: operands.Immediate, opcode: Opcode):
        self.imm = imm
        self.opcode = opcode

    def emit(self):
        encoded: list[encoded_bytes.EncodedByte] = []
        if self.imm.size == 4:
            encoded.append(encoded_bytes.opcode_size_prefix) # 16 -> 32

        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        encoded.append(self.imm.emit())

        return encoded

#######################################

class INC_Instruction:
    @staticmethod
    def R(reg:operands.GPRegister)->R_INSTRUCTION:
        if reg.is_8bit():
            return R_INSTRUCTION(reg,Opcode([0xFE],0b000))
        return R_INSTRUCTION(reg,Opcode([0xFF],0b000))
    @staticmethod
    def RM(rm:operands.RegMemBase)->RM_INSTRUCTION:
        if rm.size ==1:
            return RM_INSTRUCTION(rm,Opcode([0xFE],0b000))
        return RM_INSTRUCTION(rm,Opcode([0xFF],0b000))

class DEC_Instruction:
    @staticmethod
    def R(reg:operands.GPRegister )->R_INSTRUCTION:
        if reg.is_8bit():
            return R_INSTRUCTION(reg,Opcode([0xFE],0b001))
        return R_INSTRUCTION(reg,Opcode([0xFF],0b001))
    @staticmethod
    def RM(rm:operands.RegMemBase)->RM_INSTRUCTION:
        if rm.size ==1:
            return RM_INSTRUCTION(rm,Opcode([0xFE],0b001))
        return RM_INSTRUCTION(rm,Opcode([0xFF],0b001))

class MOV_Instruction:
    @staticmethod
    def R_RM(reg:operands.GPRegister , rm:operands.RegMemBase)->R_RM_Instruction:
        # r -> rm
        if reg.is_8bit():
            return R_RM_Instruction(reg,rm,Opcode([0x8A]))
        return R_RM_Instruction(reg,rm,Opcode([0x8B]))

    @staticmethod
    def RM_R(rm:operands.RegMemBase , reg:operands.GPRegister)->R_RM_Instruction:
        # rm -> r
        if reg.is_8bit():
            return R_RM_Instruction(reg,rm,Opcode([0x88]))
        return R_RM_Instruction(reg,rm,Opcode([0x89]))

    @staticmethod
    def R_IMM(reg:operands.GPRegister , imm:operands.Immediate)->R_IMM_Instruction:
        if reg.is_8bit():
            return R_IMM_Instruction(reg,imm,Opcode([0xB0 + reg.get_code()]))
        return R_IMM_Instruction(reg,imm,Opcode([0xB8 + reg.get_code()]))

    @staticmethod
    def RM_IMM(rm:operands.RegMemBase, imm:operands.Immediate, is64=False):
        if imm.size == 1:
            return RM_IMM_Instruction(rm, imm, Opcode([0xC6], 0))
        return RM_IMM_Instruction(rm, imm, Opcode([0xC7], 0))
    @staticmethod
    def R_R(dst: operands.GPRegister, src: operands.GPRegister) -> R_R_Instruction:
        if dst.size != src.size:
            raise ValueError("Register sizes must match")
        if dst.is_8bit():
            return R_R_Instruction(dst, src, Opcode([0x8A]))
        return R_R_Instruction(dst, src, Opcode([0x8B]))

class ADD_Instruction:
    @staticmethod
    def R_RM(reg:operands.GPRegister , rm:operands.RegMemBase)->R_RM_Instruction:
        if rm.size != reg.size:
            raise ValueError("Operand sizes must match")
        if reg.is_8bit():
            return R_RM_Instruction(reg,rm,Opcode([0x02]))
        return R_RM_Instruction(reg,rm,Opcode([0x03]))

    @staticmethod
    def RM_R(rm:operands.RegMemBase , reg:operands.GPRegister)->R_RM_Instruction:
        if rm.size != reg.size:
            raise ValueError("Operand sizes must match")
        if reg.is_8bit():
            return R_RM_Instruction(reg,rm,Opcode([0x00]))
        return R_RM_Instruction(reg,rm,Opcode([0x01]))

    @staticmethod
    def R_IMM(reg:operands.GPRegister , imm:operands.Immediate)->R_IMM_Instruction:
        if reg.is_8bit():
            if imm.size != reg.size:
                raise ValueError("Operand sizes must match")
            return R_IMM_Instruction(reg,imm,Opcode([0x80],0b000))
        if imm.size == 1:
            return R_IMM_Instruction(reg,imm,Opcode([0x83],0b000))
        if imm.size != reg.size:
            raise ValueError("Operand sizes must match")
        return R_IMM_Instruction(reg,imm,Opcode([0x81],0b000))
    
    @staticmethod
    def RM_IMM(rm:operands.RegMemBase, imm:operands.Immediate):
        if imm.size == 1 and not rm.size ==1:
            return RM_IMM_Instruction(rm, imm, Opcode([0x83], 0))
        if imm.size != rm.size:
            raise ValueError("Operand sizes must match")
        if rm.size ==1:
            return RM_IMM_Instruction(rm, imm, Opcode([0x80], 0))
        return RM_IMM_Instruction(rm, imm, Opcode([0x81], 0))

    @staticmethod
    def R_R(dst: operands.GPRegister, src: operands.GPRegister) -> R_R_Instruction:
        if dst.size != src.size:
            raise ValueError("Register sizes must match")
        if dst.is_8bit():
            return R_R_Instruction(dst, src, Opcode([0x02]))
        return R_R_Instruction(dst, src, Opcode([0x03]))

class LEA_Instruction(R_RM_Instruction):
    def __init__(self, reg:operands.GPRegister , rm:operands.RegMemBase):
        super().__init__(reg,rm,Opcode([0x8D]))

class RET_Instruction(Instruction):
    def emit(self):
        return [encoded_bytes.Opcode_Byte([0xC3])]

class PUSH_Instruction:
    @staticmethod
    def R(reg:operands.GPRegister )->R_INSTRUCTION:
        if not(reg.is_16bit()):
            raise ValueError("You can push only 16 bit registers!")
        return R_INSTRUCTION(reg,Opcode([0x50+reg.code]))
    @staticmethod
    def I(imm:operands.Immediate)->I_INSTRUCTION:
        if imm.size == 1:
            return I_INSTRUCTION(imm,Opcode([0x6A]))
        if not(imm.size == 2 or imm.size == 4):
            raise ValueError("Immediate must be 1, 2 or 4 bytes")
        return I_INSTRUCTION(imm,Opcode([0x68]))
    @staticmethod
    def RM(rm:operands.RegMemBase)->RM_INSTRUCTION:
        if not (rm.size == 2 or rm.size == 8):
            raise ValueError("You can push only 16 or 64 bit registers!")
        return RM_INSTRUCTION(rm,Opcode([0xFF]))

class POP_Instruction:
    @staticmethod
    def R(reg:operands.GPRegister )->R_INSTRUCTION:
        if not(reg.is_16bit()):
            raise ValueError("You can pop with only 16 bit registers!")
        return R_INSTRUCTION(reg,Opcode([0x58+reg.code]))

    @staticmethod
    def RM(rm:operands.RegMemBase)->RM_INSTRUCTION:
        if not (rm.size == 2 or rm.size == 8):
            raise ValueError("You can pop with only 16 or 64 bit registers!")
        return RM_INSTRUCTION(rm,Opcode([0x8F],modrm_extension=0))

class PUSHF_Instruction(Instruction):
    def emit(self):
        return [encoded_bytes.Opcode_Byte([0x9C])]

class POPF_Instruction(Instruction):
    def emit(self):
        return [encoded_bytes.Opcode_Byte([0x9D])]

class SHR_Instruction:
    @staticmethod
    def R_IMM(reg:operands.GPRegister,imm:operands.Immediate) -> R_IMM_Instruction:
        if reg.is_8bit():
            return R_IMM_Instruction(reg,imm,Opcode([0xC0],5))
        return R_IMM_Instruction(reg,imm,Opcode([0xC1],5))
    
    @staticmethod
    def R_R(reg:operands.GPRegister,CL:operands.GPRegister=registers.GPRegisters.cl) -> R_INSTRUCTION:
        if CL != registers.GPRegisters.cl:
            raise ValueError("You can enter CL register only! (If you are curious search for documents)")
        if reg.is_8bit():
            return R_INSTRUCTION(reg,Opcode([0xD2],5))
        return R_INSTRUCTION(reg,Opcode([0xD3],5))