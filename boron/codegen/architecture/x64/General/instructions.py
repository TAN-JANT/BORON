from __future__ import annotations
from . import operands, encoded_bytes, registers, exceptions
from boron.codegen.architecture.instructions import baseinstr
from typing import Sequence, overload, TypeVar


def check_same_size(*op_sizes):
    sizes = {size for size in op_sizes}
    if len(sizes) != 1:
        return False
    return True


def check_rex_compatible(*regs):
    for r in regs:
        if r.is_rex_incompatible():
            return False
    return True


def check_rex_incompatible(*regs):
    for r in regs:
        if not r.is_rex_incompatible():
            return False
    return True


def check_rex_incompatible_with_rex(mnemonic: str, *regs):
    if not check_rex_compatible(*regs) and not check_rex_incompatible(
        *regs
    ):  # if some are compatible and some are incompatible this is an error
        raise exceptions.IllegalEncodingError(
            f"{mnemonic}: registers incompatible with REX prefix cannot be used with instructions that require REX prefix"
        )


def LOCK(instr: INSTRUCTION) -> INSTRUCTION:
    if not instr.supports_lock:
        raise Exception(f"{instr.mnemonic} does not support LOCK")

    instr.set_legacy_prefix(encoded_bytes.LOCK_PREFIX)
    return instr


def REP(instr: INSTRUCTION) -> INSTRUCTION:
    if not instr.supports_rep:
        raise Exception(f"{instr.mnemonic} does not support LOCK")

    instr.set_legacy_prefix(encoded_bytes.REP_PREFIX)
    return instr


def REPNE(instr: INSTRUCTION) -> INSTRUCTION:
    if not instr.supports_repne:
        raise Exception(f"{instr.mnemonic} does not support LOCK")

    instr.set_legacy_prefix(encoded_bytes.REPNE_PREFIX)
    return instr


class PrefixHandler:
    @staticmethod
    def emit(
        *,
        legacy_prefix: encoded_bytes.EncodedByte | None = None,
        segment_override: encoded_bytes.EncodedByte | None = None,
        operand_size: bool = False,
        address_size: bool = False,
        rex: encoded_bytes.REX_Byte | None = None,
    ) -> list[encoded_bytes.EncodedByte]:

        encoded: list[encoded_bytes.EncodedByte] = []

        if legacy_prefix:
            encoded.append(legacy_prefix)

        if segment_override is not None:
            encoded.append(segment_override)

        if operand_size:
            encoded.append(encoded_bytes.opcode_size_prefix)

        if address_size:
            encoded.append(encoded_bytes.opcode_addr_prefix)

        if rex is not None:
            encoded.append(rex)

        return encoded


class Opcode:
    def __init__(self, bytes: bytearray, modrm_extension: int | None = None):
        self.bytes = bytes
        self.modrm_extension = modrm_extension


class INSTRUCTION(baseinstr):
    legacy_prefix: encoded_bytes.EncodedByte | None = None
    supports_lock = False
    supports_rep = False
    supports_repne = False

    def __init__(self, mnemonic: str):
        self.mnemonic = mnemonic
        self.legacy_prefix = None
        self.supports_lock = False
        self.supports_rep = False
        self.supports_repne = False

    def emit(self) -> Sequence[encoded_bytes.EncodedByte]:
        raise NotImplementedError

    @overload
    def requires_rex(self, operand: operands.GPRegister) -> bool: ...
    @overload
    def requires_rex(self, operand: operands.RegMemBase) -> bool: ...

    def requires_rex(self, operand: operands.GPRegister | operands.RegMemBase) -> bool:
        if isinstance(operand, operands.GPRegister):
            return operand.requires_rex
        else:
            return operand.requires_rex()

    def set_legacy_prefix(self, prefix: encoded_bytes.EncodedByte):
        if self.legacy_prefix is not None:
            raise Exception(f"Multiple legacy prefixes on {self.mnemonic} not allowed")
        self.legacy_prefix = prefix

    def has_memory_operand(self) -> bool:
        return False  # override in instructions with memory operands


class R_RM_INSTRUCTION(INSTRUCTION):
    def __init__(
        self,
        mnemonic: str,
        reg: operands.GPRegister,
        rm: operands.RegMemBase,
        opcode: Opcode,
    ):
        super().__init__(mnemonic)
        self.reg = reg
        self.rm = rm
        self.opcode = opcode

    def emit(self):
        encoded: list[encoded_bytes.EncodedByte] = []
        modrm = encoded_bytes.MODRM_Byte(self.rm.mod, self.reg.get_code(), self.rm.code)
        sib = self.rm.SIB
        disp = self.rm.displacement
        rex = encoded_bytes.REX_Byte(
            1 if self.reg.requires_rex_w_bit else 0,
            self.reg.is_expanded(),
            self.rm.X,
            self.rm.B,
        )
        encoded.extend(
            PrefixHandler.emit(
                legacy_prefix=self.legacy_prefix,
                segment_override=self.rm.segment_override,
                address_size=self.rm.requires_mandatory,  # if it has 32 bit reg inside this is true
                operand_size=self.reg.requires_mandatory,  # if it is 16 bit this is true
                rex=rex if self.reg.requires_rex or self.rm.requires_rex() else None,
            )
        )
        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        encoded.append(modrm)
        if sib is not None:
            encoded.append(sib)
        if disp is not None:
            encoded.append(disp)

        return encoded

    def has_memory_operand(self) -> bool:
        return True


class R_RM_IMM_INSTRUCTION(INSTRUCTION):
    def __init__(
        self,
        mnemonic: str,
        reg: operands.GPRegister,
        rm: operands.RegMemBase,
        imm: operands.Immediate,
        opcode: Opcode,
    ):
        super().__init__(mnemonic)
        self.reg = reg
        self.rm = rm
        self.opcode = opcode
        self.imm = imm

    def emit(self):
        encoded: list[encoded_bytes.EncodedByte] = []
        modrm = encoded_bytes.MODRM_Byte(self.rm.mod, self.reg.get_code(), self.rm.code)
        sib = self.rm.SIB
        disp = self.rm.displacement
        rex = encoded_bytes.REX_Byte(
            1 if self.reg.requires_rex_w_bit else 0,
            self.reg.is_expanded(),
            self.rm.X,
            self.rm.B,
        )
        encoded.extend(
            PrefixHandler.emit(
                legacy_prefix=self.legacy_prefix,
                segment_override=self.rm.segment_override,
                address_size=self.rm.requires_mandatory,  # if it has 32 bit reg inside this is true
                operand_size=self.reg.requires_mandatory,  # if it is 16 bit this is true
                rex=rex if self.reg.requires_rex or self.rm.requires_rex() else None,
            )
        )
        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        encoded.append(modrm)
        if sib is not None:
            encoded.append(sib)
        if disp is not None:
            encoded.append(disp)
        encoded.append(self.imm.emit())

        return encoded

    def has_memory_operand(self) -> bool:
        return True


class R_R_INSTRUCTION(INSTRUCTION):
    def __init__(
        self,
        mnemonic: str,
        reg1: operands.GPRegister,
        reg2: operands.GPRegister,
        opcode: Opcode,
    ):
        super().__init__(mnemonic)
        self.reg1 = reg1
        self.reg2 = reg2

        if not check_same_size(reg1.size, reg2.size):
            raise exceptions.OperandSizeMismatchError(mnemonic, reg1, reg2)

        self.opcode = opcode

    def emit(self):
        encoded: list[encoded_bytes.EncodedByte] = []
        modrm = encoded_bytes.MODRM_Byte(
            0b11, self.reg1.get_code(), self.reg2.get_code()
        )
        rex = encoded_bytes.REX_Byte(
            1 if self.reg1.requires_rex_w_bit or self.reg2.requires_rex_w_bit else 0,
            self.reg1.is_expanded(),
            0,
            self.reg2.is_expanded(),
        )
        check_rex_incompatible_with_rex(self.mnemonic, self.reg1, self.reg2)
        encoded.extend(
            PrefixHandler.emit(
                legacy_prefix=self.legacy_prefix,
                operand_size=self.reg1.requires_mandatory,
                address_size=False,
                rex=rex if self.reg1.requires_rex or self.reg2.requires_rex else None,
            )
        )
        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        encoded.append(modrm)

        return encoded


class R_R_IMM_INSTRUCTION(INSTRUCTION):
    def __init__(
        self,
        mnemonic: str,
        reg1: operands.GPRegister,
        reg2: operands.GPRegister,
        imm: operands.Immediate,
        opcode: Opcode,
    ):
        super().__init__(mnemonic)
        self.reg1 = reg1
        self.reg2 = reg2
        self.imm = imm

        if self.reg1.size != self.reg2.size:
            raise exceptions.OperandSizeMismatchError(mnemonic, reg1, reg2)
        self.opcode = opcode

    def emit(self):
        encoded: list[encoded_bytes.EncodedByte] = []
        modrm = encoded_bytes.MODRM_Byte(
            0b11, self.reg1.get_code(), self.reg2.get_code()
        )
        rex = encoded_bytes.REX_Byte(
            1 if self.reg1.requires_rex_w_bit or self.reg2.requires_rex_w_bit else 0,
            self.reg1.is_expanded(),
            0,
            self.reg2.is_expanded(),
        )
        check_rex_incompatible_with_rex(self.mnemonic, self.reg1, self.reg2)
        encoded.extend(
            PrefixHandler.emit(
                legacy_prefix=self.legacy_prefix,
                operand_size=self.reg1.requires_mandatory,
                address_size=False,
                rex=rex if self.reg1.requires_rex or self.reg2.requires_rex else None,
            )
        )
        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        encoded.append(modrm)
        encoded.append(self.imm.emit())

        return encoded


class R_IMM_INSTRUCTION(INSTRUCTION):
    def __init__(
        self,
        mnemonic: str,
        reg: operands.GPRegister,
        imm: operands.Immediate,
        opcode: Opcode,
    ):
        super().__init__(mnemonic)
        self.reg = reg
        self.imm = imm
        self.opcode = opcode

    def emit(self):
        encoded: list[encoded_bytes.EncodedByte] = []
        rex = encoded_bytes.REX_Byte(
            1 if self.reg.requires_rex_w_bit else 0, self.reg.is_expanded(), 0, 0
        )

        encoded.extend(
            PrefixHandler.emit(
                legacy_prefix=self.legacy_prefix,
                operand_size=self.reg.requires_mandatory,
                address_size=False,
                rex=rex if self.reg.requires_rex else None,
            )
        )

        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        if self.opcode.modrm_extension is not None:
            encoded.append(
                encoded_bytes.MODRM_Byte(
                    0b11, self.opcode.modrm_extension, self.reg.get_code()
                )
            )
        encoded.append(self.imm.emit())

        return encoded


class RM_IMM_INSTRUCTION(INSTRUCTION):
    def __init__(
        self,
        mnemonic: str,
        rm: operands.RegMemBase,
        imm: operands.Immediate,
        opcode: Opcode,
    ):
        super().__init__(mnemonic)
        self.rm = rm
        self.imm = imm
        self.opcode = opcode
        self.W = rm.size == 8
        if imm.size > 4:
            raise exceptions.InvalidImmediateError(mnemonic, imm)

    def emit(self):
        encoded: list[encoded_bytes.EncodedByte] = []
        modrm = encoded_bytes.MODRM_Byte(
            self.rm.mod,
            (
                self.opcode.modrm_extension
                if self.opcode.modrm_extension is not None
                else 0
            ),
            self.rm.code,
        )
        sib = self.rm.SIB
        imm = self.imm.emit()
        disp = self.rm.displacement
        rex = encoded_bytes.REX_Byte(1 if self.W else 0, 0, self.rm.X, self.rm.B)

        encoded.extend(
            PrefixHandler.emit(
                legacy_prefix=self.legacy_prefix,
                segment_override=self.rm.segment_override,
                address_size=self.rm.requires_mandatory,  # if it has 32 bit reg inside this is true
                operand_size=self.rm.size == 2,  # if it is 16 bit this is true
                rex=rex if self.rm.requires_rex() else None,
            )
        )
        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        encoded.append(modrm)
        if sib is not None:
            encoded.append(sib)
        if disp is not None:
            encoded.append(disp)
        encoded.append(imm)

        return encoded

    def has_memory_operand(self) -> bool:
        return True


class R_INSTRUCTION(INSTRUCTION):
    def __init__(self, mnemonic: str, reg: operands.GPRegister, opcode: Opcode):
        super().__init__(mnemonic)
        self.reg = reg
        self.opcode = opcode

    def emit(self):
        encoded: list[encoded_bytes.EncodedByte] = []
        rex = encoded_bytes.REX_Byte(
            1 if self.reg.requires_rex_w_bit else 0, self.reg.is_expanded(), 0, 0
        )
        encoded.extend(
            PrefixHandler.emit(
                legacy_prefix=self.legacy_prefix,
                operand_size=self.reg.requires_mandatory,
                address_size=False,
                rex=rex if self.reg.requires_rex else None,
            )
        )
        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        if self.opcode.modrm_extension is not None:
            encoded.append(
                encoded_bytes.MODRM_Byte(
                    0b11, self.opcode.modrm_extension, self.reg.get_code()
                )
            )

        return encoded


class RM_INSTRUCTION(INSTRUCTION):
    def __init__(self, mnemonic: str, rm: operands.RegMemBase, opcode: Opcode):
        super().__init__(mnemonic)
        self.rm = rm
        self.opcode = opcode

    def emit(self):
        encoded: list[encoded_bytes.EncodedByte] = []
        modrm = encoded_bytes.MODRM_Byte(
            self.rm.mod,
            (
                self.opcode.modrm_extension
                if self.opcode.modrm_extension is not None
                else 0
            ),
            self.rm.code,
        )
        sib = self.rm.SIB
        disp = self.rm.displacement
        rex = encoded_bytes.REX_Byte(0, 0, self.rm.X, self.rm.B)
        encoded.extend(
            PrefixHandler.emit(
                legacy_prefix=self.legacy_prefix,
                segment_override=self.rm.segment_override,
                address_size=self.rm.requires_mandatory,  # if it has 32 bit reg inside this is true
                operand_size=self.rm.size == 2,  # if it is 16 bit this is true
                rex=rex if self.rm.requires_rex() else None,
            )
        )
        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        encoded.append(modrm)
        if sib is not None:
            encoded.append(sib)
        if disp is not None:
            encoded.append(disp)
        return encoded

    def has_memory_operand(self) -> bool:
        return True


class I_INSTRUCTION(INSTRUCTION):
    def __init__(self, mnemonic: str, imm: operands.Immediate, opcode: Opcode):
        super().__init__(mnemonic)
        self.imm = imm
        self.opcode = opcode

    def emit(self):
        encoded: list[encoded_bytes.EncodedByte] = []
        encoded.extend(PrefixHandler.emit(legacy_prefix=self.legacy_prefix))
        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        encoded.append(self.imm.emit())
        return encoded


class SREG_R_INSTRUCTION(INSTRUCTION):
    def __init__(
        self,
        mnemonic: str,
        sreg: operands.SRegister,
        reg: operands.GPRegister,
        opcode: Opcode,
    ):
        super().__init__(mnemonic)
        self.sreg = sreg
        self.reg = reg
        if self.reg.is_64bit():
            self.reg = registers.GeneralPurposeRegister(
                self.reg.code,
                size=4,
                requires_expand=self.reg.requires_expand,
                requires_rex=self.reg.requires_expand,
                rex_incompatible=False,
                requires_mandatory=False,
                requires_rex_w_bit=False,
            )
        self.opcode = opcode

    def emit(self):
        encoded: list[encoded_bytes.EncodedByte] = []
        rex = encoded_bytes.REX_Byte(0, 0, 0, self.reg.is_expanded())
        encoded.extend(PrefixHandler.emit(rex=rex if self.reg.requires_rex else None))
        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        encoded.append(
            encoded_bytes.MODRM_Byte(0b11, self.sreg.get_code(), self.reg.get_code())
        )
        return encoded


class SREG_RM_INSTRUCTION(INSTRUCTION):
    def __init__(
        self,
        mnemonic: str,
        sreg: operands.SRegister,
        rm: operands.RegMemBase,
        opcode: Opcode,
    ):
        super().__init__(mnemonic)
        self.sreg = sreg
        self.rm = rm
        self.opcode = opcode

    def emit(self):
        encoded: list[encoded_bytes.EncodedByte] = []
        rex = encoded_bytes.REX_Byte(0, 0, self.rm.X, self.rm.B)
        disp = self.rm.displacement
        encoded.extend(
            PrefixHandler.emit(
                legacy_prefix=self.legacy_prefix,
                segment_override=self.rm.segment_override,
                address_size=self.rm.requires_mandatory,  # if it has 32 bit reg inside this is true
                operand_size=False,
                rex=rex if self.rm.requires_rex() else None,
            )
        )
        encoded.append(encoded_bytes.Opcode_Byte(self.opcode.bytes))
        encoded.append(
            encoded_bytes.MODRM_Byte(self.rm.mod, self.sreg.get_code(), 0b100)
        )
        if self.rm.SIB is not None:
            encoded.append(self.rm.SIB)
        if disp is not None:
            encoded.append(disp)
        return encoded

    def has_memory_operand(self) -> bool:
        return True


#######################################


class SYSCALL_INSTRUCTION(INSTRUCTION):
    def __init__(self, mnemonic: str = "syscall"):
        super().__init__(mnemonic)

    def emit(self):
        return [encoded_bytes.Opcode_Byte(bytearray([0x0F, 0x05]))]


class MOV_INSTRUCTION:
    @staticmethod
    def R_RM(reg: operands.GPRegister, rm: operands.RegMemBase) -> R_RM_INSTRUCTION:
        # r -> rm
        if reg.is_8bit():
            return R_RM_INSTRUCTION("mov", reg, rm, Opcode(bytearray([0x88])))
        return R_RM_INSTRUCTION("mov", reg, rm, Opcode(bytearray([0x89])))

    @staticmethod
    def RM_R(rm: operands.RegMemBase, reg: operands.GPRegister) -> R_RM_INSTRUCTION:
        # rm -> r
        if reg.is_8bit():
            return R_RM_INSTRUCTION("mov", reg, rm, Opcode(bytearray([0x8A])))
        return R_RM_INSTRUCTION("mov", reg, rm, Opcode(bytearray([0x8B])))

    @staticmethod
    def R_IMM(reg: operands.GPRegister, imm: operands.Immediate) -> R_IMM_INSTRUCTION:
        if reg.is_64bit() and imm.size == 4:
            return R_IMM_INSTRUCTION("mov", reg, imm, Opcode(bytearray([0xC7]), 0))
        if reg.is_8bit():
            return R_IMM_INSTRUCTION(
                "mov", reg, imm, Opcode(bytearray([0xB0 + reg.get_code()]))
            )
        return R_IMM_INSTRUCTION(
            "mov", reg, imm, Opcode(bytearray([0xB8 + reg.get_code()]))
        )

    @staticmethod
    def RM_IMM(rm: operands.RegMemBase, imm: operands.Immediate):
        if imm.size == 1:
            return RM_IMM_INSTRUCTION("mov", rm, imm, Opcode(bytearray([0xC6]), 0))
        return RM_IMM_INSTRUCTION("mov", rm, imm, Opcode(bytearray([0xC7]), 0))

    @staticmethod
    def R_R(dst: operands.GPRegister, src: operands.GPRegister) -> R_R_INSTRUCTION:
        if not check_same_size(dst.size, src.size):
            raise exceptions.OperandSizeMismatchError("mov", dst, src)
        if dst.is_8bit():
            return R_R_INSTRUCTION("mov", dst, src, Opcode(bytearray([0x8A])))
        return R_R_INSTRUCTION("mov", dst, src, Opcode(bytearray([0x8B])))

    @staticmethod
    def SReg_R(
        sreg: operands.SRegister, reg: operands.GPRegister
    ) -> SREG_R_INSTRUCTION:
        if sreg.get_code() == 1:
            raise exceptions.IllegalEncodingError(
                "mov: cannot move CS register to general purpose register"
            )
        return SREG_R_INSTRUCTION(
            "mov", sreg, reg, Opcode(bytearray([0x8C]), sreg.code)
        )


class ALU_FAMILY:
    supports_lock = False
    supports_rep = False
    supports_repne = False
    T = TypeVar("T", bound=INSTRUCTION)

    def _require_opcode(self, opcode, mnemonic, *ops):
        if opcode is None:
            raise exceptions.IllegalInstrutcionError(mnemonic, *ops)
        return opcode

    def _inherit_support(self, instruction: T) -> T:
        instruction.supports_lock = (
            self.supports_lock and instruction.has_memory_operand()
        )
        instruction.supports_rep = self.supports_rep
        instruction.supports_repne = self.supports_repne
        return instruction

    def support_lock(self):
        self.supports_lock = True
        return self

    def support_rep(self):
        self.supports_rep = True
        return self

    def support_repne(self):
        self.supports_repne = True
        return self


class Unary_ALU_INSTRUCTION(ALU_FAMILY):
    def __init__(
        self,
        *,
        rm_8: Opcode | None,
        rm: Opcode | None,  # same opcode for rm and r
        mnemonic: str = "ALU",
    ):
        self.rm_8 = rm_8
        self.rm = rm
        self.mnemonic = mnemonic

    def RM(self, rm: operands.RegMemBase) -> RM_INSTRUCTION:

        opcode = self._require_opcode(
            (self.rm_8 if rm.size == 1 else self.rm), self.mnemonic, rm
        )
        return self._inherit_support(RM_INSTRUCTION(self.mnemonic, rm, opcode))

    def R(self, r: operands.GPRegister, mnemonic: str) -> R_INSTRUCTION:
        opcode = self._require_opcode(
            (self.rm_8 if r.size == 1 else self.rm), self.mnemonic, r
        )
        return self._inherit_support(R_INSTRUCTION(self.mnemonic, r, opcode))


class Binary_ALU_INSTRUCTION(ALU_FAMILY):
    T = TypeVar("T", bound=INSTRUCTION)

    def __init__(
        self,
        *,
        r_rm_8: Opcode | None,
        r_rm: Opcode | None,
        rm_r_8: Opcode | None,
        rm_r: Opcode | None,
        r_r_8: Opcode | None,
        r_r: Opcode | None,
        r_imm: Opcode | None,
        r_imm8: Opcode | None,
        r64_imm8: Opcode | None,
        rm_imm: Opcode | None,
        rm64_imm8: Opcode | None,
        rm_imm8: Opcode | None,
        mnemonic: str = "alu",
    ):
        self.r_rm_8 = r_rm_8
        self.r_rm = r_rm
        self.rm_r_8 = rm_r_8
        self.rm_r = rm_r
        self.r_r_8 = r_r_8
        self.r_r = r_r
        self.r_imm = r_imm
        self.r_imm8 = r_imm8
        self.rm_imm = rm_imm
        self.rm_imm8 = rm_imm8
        self.r64_imm8 = r64_imm8
        self.rm64_imm8 = rm64_imm8
        self.mnemonic = mnemonic
        super().__init__()

    def R_RM(
        self, reg: operands.GPRegister, rm: operands.RegMemBase
    ) -> R_RM_INSTRUCTION:
        if not check_same_size(reg.size, rm.size):
            raise exceptions.OperandSizeMismatchError(self.mnemonic, reg, rm)
        opcode = self._require_opcode(
            (self.r_rm_8 if rm.size == 1 else self.r_rm), self.mnemonic, rm
        )
        return self._inherit_support(R_RM_INSTRUCTION(self.mnemonic, reg, rm, opcode))

    def RM_R(
        self, rm: operands.RegMemBase, reg: operands.GPRegister
    ) -> R_RM_INSTRUCTION:
        if not check_same_size(reg.size, rm.size):
            raise exceptions.OperandSizeMismatchError(self.mnemonic, reg, rm)
        opcode = self._require_opcode(
            (self.rm_r_8 if rm.size == 1 else self.rm_r), self.mnemonic, rm
        )
        return self._inherit_support(R_RM_INSTRUCTION(self.mnemonic, reg, rm, opcode))

    def R_IMM(
        self, reg: operands.GPRegister, imm: operands.Immediate
    ) -> R_IMM_INSTRUCTION:
        if imm.size > 4:
            raise exceptions.InvalidImmediateError(self.mnemonic, imm)
        if reg.is_8bit():
            if imm.size != reg.size:
                raise exceptions.OperandSizeMismatchError(self.mnemonic, reg, imm)
            return self._inherit_support(
                R_IMM_INSTRUCTION(
                    self.mnemonic,
                    reg,
                    imm,
                    self._require_opcode(self.r_imm8, self.mnemonic, reg, imm),
                )
            )
        if imm.size == 1 and reg.size == 8:
            return self._inherit_support(
                R_IMM_INSTRUCTION(
                    self.mnemonic,
                    reg,
                    imm,
                    self._require_opcode(self.r64_imm8, self.mnemonic, reg, imm),
                )
            )
        if imm.size != reg.size:
            raise exceptions.OperandSizeMismatchError(self.mnemonic, reg, imm)
        return self._inherit_support(
            R_IMM_INSTRUCTION(
                self.mnemonic,
                reg,
                imm,
                self._require_opcode(self.r_imm, self.mnemonic, reg, imm),
            )
        )

    def RM_IMM(self, rm: operands.RegMemBase, imm: operands.Immediate):
        if imm.size > 4:
            raise exceptions.InvalidImmediateError(self.mnemonic, imm)
        if imm.size == 1 and rm.size == 8:
            return self._inherit_support(
                RM_IMM_INSTRUCTION(
                    self.mnemonic,
                    rm,
                    imm,
                    self._require_opcode(self.rm64_imm8, self.mnemonic, rm, imm),
                )
            )
        if imm.size != rm.size:
            raise exceptions.OperandSizeMismatchError(self.mnemonic, rm, imm)
        opcode = self._require_opcode(
            self.rm_imm8 if rm.size == 1 else self.rm_imm, self.mnemonic, rm, imm
        )
        return self._inherit_support(RM_IMM_INSTRUCTION(self.mnemonic, rm, imm, opcode))

    def R_R(
        self, dst: operands.GPRegister, src: operands.GPRegister
    ) -> R_R_INSTRUCTION:
        if dst.size != src.size:
            raise exceptions.OperandSizeMismatchError(self.mnemonic, dst, src)
        opcode = self._require_opcode(
            self.r_r_8 if dst.is_8bit() else self.r_r, self.mnemonic
        )
        return self._inherit_support(R_R_INSTRUCTION(self.mnemonic, dst, src, opcode))


class Ternary_ALU_INSTRUCTION(ALU_FAMILY):
    T = TypeVar("T", bound=INSTRUCTION)

    def __init__(
        self,
        *,
        r_rm_imm8: Opcode | None,
        r_rm_imm: Opcode | None,
        r_r_imm8: Opcode | None,
        r_r_imm: Opcode | None,
        mnemonic: str = "alu",
    ):
        self.r_rm_imm8 = r_rm_imm8
        self.r_rm_imm = r_rm_imm
        self.r_r_imm8 = r_r_imm8
        self.r_r_imm = r_r_imm
        self.mnemonic = mnemonic

    def R_RM_IMM(self, reg: operands.GPRegister, rm: operands.RegMemBase, imm):
        if imm.size > 4:
            raise exceptions.InvalidImmediateError(self.mnemonic, imm)
        if reg.size != rm.size:
            raise exceptions.OperandSizeMismatchError(self.mnemonic, reg, rm)
        opcode = self._require_opcode(
            self.r_rm_imm8 if imm.size == 1 else self.r_rm_imm, self.mnemonic
        )
        return self._inherit_support(
            R_RM_IMM_INSTRUCTION(self.mnemonic, reg, rm, imm, opcode)
        )

    def R_R_IMM(self, reg1: operands.GPRegister, reg2: operands.GPRegister, imm):
        if imm.size > 4:
            raise exceptions.InvalidImmediateError(self.mnemonic, imm)
        if reg1.size != reg2.size:
            raise exceptions.OperandSizeMismatchError(self.mnemonic, reg1, reg2)
        opcode = self._require_opcode(
            self.r_r_imm8 if imm.size == 1 else self.r_r_imm, self.mnemonic
        )

        return self._inherit_support(
            R_R_IMM_INSTRUCTION(self.mnemonic, reg1, reg2, imm, opcode)
        )


class LEA_INSTRUCTION(R_RM_INSTRUCTION):
    def __init__(self, reg: operands.GPRegister, rm: operands.RegMemBase):
        super().__init__("lea", reg, rm, Opcode(bytearray([0x8D])))


class RET_INSTRUCTION(INSTRUCTION):
    def __init__(self, mnemonic: str = "ret"):
        super().__init__(mnemonic)

    def emit(self):
        return [encoded_bytes.Opcode_Byte(bytearray([0xC3]))]


class PUSH_INSTRUCTION:
    @staticmethod
    def R(reg: operands.GPRegister) -> R_INSTRUCTION:
        if not (reg.is_16bit() or reg.is_64bit()):
            raise exceptions.InvalidRegisterError("push", reg)
        return R_INSTRUCTION("push", reg, Opcode(bytearray([0x50 + reg.code])))

    @staticmethod
    def I(imm: operands.Immediate) -> I_INSTRUCTION:
        if imm.size > 4:
            raise exceptions.InvalidImmediateError("push", imm)
        if imm.size == 1:
            return I_INSTRUCTION("push", imm, Opcode(bytearray([0x6A])))
        if not (imm.size == 2 or imm.size == 4):
            raise exceptions.InvalidImmediateError("push", imm)
        return I_INSTRUCTION("push", imm, Opcode(bytearray([0x68])))

    @staticmethod
    def RM(rm: operands.RegMemBase) -> RM_INSTRUCTION:
        if not (rm.size == 2 or rm.size == 8):
            raise exceptions.IllegalEncodingError(
                "push: only 16 or 64 bit operands allowed"
            )
        return RM_INSTRUCTION("push", rm, Opcode(bytearray([0xFF])))


class POP_INSTRUCTION:
    @staticmethod
    def R(reg: operands.GPRegister) -> R_INSTRUCTION:
        if not (reg.is_16bit() or reg.is_64bit()):
            raise exceptions.InvalidRegisterError("pop", reg)
        return R_INSTRUCTION("pop", reg, Opcode(bytearray([0x58 + reg.code])))

    @staticmethod
    def RM(rm: operands.RegMemBase) -> RM_INSTRUCTION:
        if not (rm.size == 2 or rm.size == 8):
            raise exceptions.IllegalEncodingError(
                "pop: only 16 or 64 bit operands allowed"
            )
        return RM_INSTRUCTION("pop", rm, Opcode(bytearray([0x8F]), modrm_extension=0))


class PUSHF_INSTRUCTION(INSTRUCTION):
    def __init__(self, mnemonic: str = "pushf"):
        super().__init__(mnemonic)

    def emit(self):
        return [encoded_bytes.Opcode_Byte(bytearray([0x9C]))]


class POPF_INSTRUCTION(INSTRUCTION):
    def __init__(self, mnemonic: str = "popf"):
        super().__init__(mnemonic)

    def emit(self):
        return [encoded_bytes.Opcode_Byte(bytearray([0x9D]))]


class SHR_INSTRUCTION:
    @staticmethod
    def R_IMM(reg: operands.GPRegister, imm: operands.Immediate) -> R_IMM_INSTRUCTION:
        if imm.size > 1:
            raise exceptions.InvalidImmediateError("shr", imm)
        if imm.value == 1:
            if reg.is_8bit():
                return R_IMM_INSTRUCTION("shr", reg, imm, Opcode(bytearray([0xD0]), 5))
            return R_IMM_INSTRUCTION("shr", reg, imm, Opcode(bytearray([0xD1]), 5))
        if reg.is_8bit():
            return R_IMM_INSTRUCTION("shr", reg, imm, Opcode(bytearray([0xC0]), 5))
        return R_IMM_INSTRUCTION("shr", reg, imm, Opcode(bytearray([0xC1]), 5))

    @staticmethod
    def R_R(
        reg: operands.GPRegister, CL: operands.GPRegister = registers.GPRegisters.cl
    ) -> R_INSTRUCTION:
        if CL != registers.GPRegisters.cl:
            raise exceptions.InvalidRegisterError("shr", CL)
        if reg.is_8bit():
            return R_INSTRUCTION("shr", reg, Opcode(bytearray([0xD2]), 5))
        return R_INSTRUCTION("shr", reg, Opcode(bytearray([0xD3]), 5))


class SHL_INSTRUCTION:
    @staticmethod
    def R_IMM(
        reg: operands.GPRegister,
        imm: operands.Immediate = operands.Immediate(1, 1, False),
    ) -> R_IMM_INSTRUCTION:
        if imm.size > 1:
            raise exceptions.InvalidImmediateError("shr", imm)
        if imm.value == 1:
            if reg.is_8bit():
                return R_IMM_INSTRUCTION("shl", reg, imm, Opcode(bytearray([0xD0]), 4))
            return R_IMM_INSTRUCTION("shl", reg, imm, Opcode(bytearray([0xD1]), 4))
        if reg.is_8bit():
            return R_IMM_INSTRUCTION("shl", reg, imm, Opcode(bytearray([0xC0]), 4))
        return R_IMM_INSTRUCTION("shl", reg, imm, Opcode(bytearray([0xC1]), 4))

    @staticmethod
    def R_R(
        reg: operands.GPRegister, CL: operands.GPRegister = registers.GPRegisters.cl
    ) -> R_INSTRUCTION:
        if CL != registers.GPRegisters.cl:
            raise exceptions.InvalidRegisterError("shl", CL)
        if reg.is_8bit():
            return R_INSTRUCTION("shl", reg, Opcode(bytearray([0xD2]), 4))
        return R_INSTRUCTION("shl", reg, Opcode(bytearray([0xD3]), 4))


class CLI_INSTRUCTION(INSTRUCTION):
    def __init__(self, mnemonic: str = "cli"):
        super().__init__(mnemonic)

    def emit(self):
        return [encoded_bytes.Opcode_Byte(bytearray([0xFA]))]


class STI_INSTRUCTION(INSTRUCTION):
    def __init__(self, mnemonic: str = "sti"):
        super().__init__(mnemonic)

    def emit(self):
        return [encoded_bytes.Opcode_Byte(bytearray([0xFB]))]


class JMP_INSTRUCTION:
    @staticmethod
    def REL(rel: operands.Immediate) -> I_INSTRUCTION:
        if rel.size not in [1,4]:
            raise exceptions.InvalidImmediateError("jmp", rel)
        if rel.size == 1:
            return I_INSTRUCTION("jmp", rel, Opcode(bytearray([0xEB])))
        return I_INSTRUCTION("jmp", rel, Opcode(bytearray([0xE9])))
    @staticmethod
    def RM(rm: operands.RegMemBase) -> RM_INSTRUCTION:
        return RM_INSTRUCTION(
            "jmp",
            rm,
            Opcode(bytearray([0xFF]), modrm_extension=0b100),
        )

    @staticmethod
    def R(reg: operands.GPRegister) -> R_INSTRUCTION:
        return R_INSTRUCTION(
            "jmp",
            reg,
            Opcode(bytearray([0xFF]), modrm_extension=0b100),
        )

class CALL_INSTRUCTION:
    @staticmethod
    def REL(rel : operands.Immediate) -> I_INSTRUCTION:
        if rel.size != 4:
            raise exceptions.InvalidImmediateError("call", rel)
        return I_INSTRUCTION("call", rel, Opcode(bytearray([0xE8])))
    @staticmethod
    def RM(rm: operands.RegMemBase) -> RM_INSTRUCTION:
        return RM_INSTRUCTION(
            "call",
            rm,
            Opcode(bytearray([0xFF]), modrm_extension=0b011),
        )

    @staticmethod
    def R(reg: operands.GPRegister) -> R_INSTRUCTION:
        return R_INSTRUCTION(
            "jmp",
            reg,
            Opcode(bytearray([0xFF]), modrm_extension=0b011),
        )

class IMUL_INSTRUCTION:
    supports_lock = False
    supports_rep = False
    supports_repne = False
    T = TypeVar("T", bound=ALU_FAMILY)

    @classmethod
    def UNARY(cls) -> Unary_ALU_INSTRUCTION:
        # imul r/m
        return cls._inherit_support(
            Unary_ALU_INSTRUCTION(
                rm_8=Opcode(bytearray([0xF6]), modrm_extension=0b101),
                rm=Opcode(bytearray([0xF7]), modrm_extension=0b101),
            )
        )

    @classmethod
    def BINARY(cls) -> Binary_ALU_INSTRUCTION:
        # imul r, r/m
        return cls._inherit_support(
            Binary_ALU_INSTRUCTION(
                r_rm_8=None,  # not valid
                r_rm=Opcode(bytearray([0x0F, 0xAF])),
                rm_r_8=None,
                rm_r=None,
                r_r_8=None,
                r_r=Opcode(
                    bytearray([0x0F, 0xAF])
                ),  # same opcode for r,r and rm,r imul r , r/m  (imul r,r / imul r,rm)
                r_imm=None,
                r_imm8=None,
                r64_imm8=None,
                rm_imm=None,
                rm_imm8=None,
                rm64_imm8=None,
                mnemonic="imul",
            )
        )

    @classmethod
    def TERNARY(cls) -> Ternary_ALU_INSTRUCTION:
        # imul r, r/m, imm
        return cls._inherit_support(
            Ternary_ALU_INSTRUCTION(
                r_rm_imm8=Opcode(bytearray([0x6B])),
                r_r_imm8=Opcode(bytearray([0x6B])),
                r_rm_imm=Opcode(bytearray([0x69])),
                r_r_imm=Opcode(bytearray([0x69])),
            )
        )

    @classmethod
    def _inherit_support(cls, instruction: T) -> T:
        instruction.supports_lock = cls.supports_lock
        instruction.supports_rep = cls.supports_rep
        instruction.supports_repne = cls.supports_repne
        return instruction


class INSTRUCTIONS:

    SYSCALL = SYSCALL_INSTRUCTION  # SYSCALL
    PUSHF = PUSHF_INSTRUCTION  # PUSHF
    POPF = POPF_INSTRUCTION  # POPF
    CLI = CLI_INSTRUCTION  # CLI , CLEAR INTERRUPTS
    STI = STI_INSTRUCTION  # STI , SET INTERRUPTS
    RET = RET_INSTRUCTION  # RET , RETURN
    LEA = LEA_INSTRUCTION  # LEA , LOAD EFFECTIVE ADDRESS
    SHR = SHR_INSTRUCTION  # SHR , SHIFT RIGHT , >>
    SHL = SHL_INSTRUCTION  # SHL , SHIFT LEFT  , <<
    MOV = MOV_INSTRUCTION  # MOV , MOVE DATA
    ADD = Binary_ALU_INSTRUCTION(
        r_rm_8=Opcode(bytearray([0x00])),
        r_rm=Opcode(bytearray([0x01])),
        rm_r_8=Opcode(bytearray([0x02])),
        rm_r=Opcode(bytearray([0x03])),
        r_r_8=Opcode(bytearray([0x02])),
        r_r=Opcode(bytearray([0x03])),
        r_imm=Opcode(bytearray([0x81]), 0b000),
        r_imm8=Opcode(bytearray([0x80]), 0b000),
        r64_imm8=Opcode(bytearray([0x83]), 0b000),
        rm_imm=Opcode(bytearray([0x81]), 0b000),
        rm_imm8=Opcode(bytearray([0x80]), 0b000),
        rm64_imm8=Opcode(bytearray([0x83]), 0b000),
    )
    SUB = Binary_ALU_INSTRUCTION(
        r_rm_8=Opcode(bytearray([0x28])),
        r_rm=Opcode(bytearray([0x29])),
        rm_r_8=Opcode(bytearray([0x2A])),
        rm_r=Opcode(bytearray([0x2B])),
        r_r_8=Opcode(bytearray([0x2A])),
        r_r=Opcode(bytearray([0x2B])),
        r_imm=Opcode(bytearray([0x81]), 0b101),
        r_imm8=Opcode(bytearray([0x80]), 0b101),
        r64_imm8=Opcode(bytearray([0x83]), 0b101),
        rm_imm=Opcode(bytearray([0x81]), 0b101),
        rm_imm8=Opcode(bytearray([0x80]), 0b101),
        rm64_imm8=Opcode(bytearray([0x83]), 0b101),
    )
    MUL = Unary_ALU_INSTRUCTION(
        rm_8=Opcode(bytearray([0xF6]), 0b010),
        rm=Opcode(bytearray([0xF7]), 0b010),
    )
    IMUL = IMUL_INSTRUCTION
    """
    DIV = Unary_ALU_INSTRUCTION(
        
    )
    IDIV = Unary_ALU_INSTRUCTION(

    )
    """
    AND = Binary_ALU_INSTRUCTION(
        r_rm_8=Opcode(bytearray([0x20])),
        r_rm=Opcode(bytearray([0x21])),
        rm_r_8=Opcode(bytearray([0x22])),
        rm_r=Opcode(bytearray([0x23])),
        r_r_8=Opcode(bytearray([0x22])),
        r_r=Opcode(bytearray([0x23])),
        r_imm=Opcode(bytearray([0x81]), 0b100),
        r_imm8=Opcode(bytearray([0x80]), 0b100),
        r64_imm8=Opcode(bytearray([0x83]), 0b100),
        rm_imm=Opcode(bytearray([0x81]), 0b100),
        rm_imm8=Opcode(bytearray([0x80]), 0b100),
        rm64_imm8=Opcode(bytearray([0x83]), 0b100),
    )
    XOR = Binary_ALU_INSTRUCTION(
        r_rm_8=Opcode(bytearray([0x30])),
        r_rm=Opcode(bytearray([0x31])),
        rm_r_8=Opcode(bytearray([0x32])),
        rm_r=Opcode(bytearray([0x33])),
        r_r_8=Opcode(bytearray([0x32])),
        r_r=Opcode(bytearray([0x33])),
        r_imm=Opcode(bytearray([0x81]), 0b110),
        r_imm8=Opcode(bytearray([0x80]), 0b110),
        r64_imm8=Opcode(bytearray([0x83]), 0b110),
        rm_imm=Opcode(bytearray([0x81]), 0b110),
        rm_imm8=Opcode(bytearray([0x80]), 0b110),
        rm64_imm8=Opcode(bytearray([0x83]), 0b110),
    )
    OR = Binary_ALU_INSTRUCTION(
        r_rm_8=Opcode(bytearray([0x08])),
        r_rm=Opcode(bytearray([0x09])),
        rm_r_8=Opcode(bytearray([0x0A])),
        rm_r=Opcode(bytearray([0x0B])),
        r_r_8=Opcode(bytearray([0x0A])),
        r_r=Opcode(bytearray([0x0B])),
        r_imm=Opcode(bytearray([0x81]), 0b001),
        r_imm8=Opcode(bytearray([0x80]), 0b001),
        r64_imm8=Opcode(bytearray([0x83]), 0b001),
        rm_imm=Opcode(bytearray([0x81]), 0b001),
        rm_imm8=Opcode(bytearray([0x80]), 0b001),
        rm64_imm8=Opcode(bytearray([0x83]), 0b001),
    )
    CMP = Binary_ALU_INSTRUCTION(
        r_rm_8=Opcode(bytearray([0x38])),
        r_rm=Opcode(bytearray([0x39])),
        rm_r_8=Opcode(bytearray([0x3A])),
        rm_r=Opcode(bytearray([0x3B])),
        r_r_8=Opcode(bytearray([0x3A])),
        r_r=Opcode(bytearray([0x3B])),
        r_imm=Opcode(bytearray([0x81]), 0b111),
        r_imm8=Opcode(bytearray([0x80]), 0b111),
        r64_imm8=Opcode(bytearray([0x83]), 0b111),
        rm_imm=Opcode(bytearray([0x81]), 0b111),
        rm_imm8=Opcode(bytearray([0x80]), 0b111),
        rm64_imm8=Opcode(bytearray([0x83]), 0b111),
    )
    INC = Unary_ALU_INSTRUCTION(
        rm_8=Opcode(bytearray([0xFE]), 0b000),
        rm=Opcode(bytearray([0xFF]), 0b000),
    )
    DEC = Unary_ALU_INSTRUCTION(
        rm_8=Opcode(bytearray([0xFE]), 0b001),
        rm=Opcode(bytearray([0xFF]), 0b001),
    )
    PUSH = PUSH_INSTRUCTION  # PUSH , PUSH TO STACK
    POP = POP_INSTRUCTION  # POP , POP FROM STACK
    CALL = CALL_INSTRUCTION
    JMP = JMP_INSTRUCTION
