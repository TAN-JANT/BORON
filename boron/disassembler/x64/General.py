from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Optional, Literal
from .prefixes import PrefixState, seg_prefixes, PrefixSupports,REX
from .rules import Rule, CTX, Instruction

GPREG8 = [
    "al",
    "cl",
    "dl",
    "bl",
    "ah",
    "ch",
    "dh",
    "bh",
    "r8b",
    "r9b",
    "r10b",
    "r11b",
    "r12b",
    "r13b",
    "r14b",
    "r15b",
]
GPREG8R = [
    "al",
    "cl",
    "dl",
    "bl",
    "spl",
    "bpl",
    "sil",
    "dil",
    "r8b",
    "r9b",
    "r10b",
    "r11b",
    "r12b",
    "r13b",
    "r14b",
    "r15b",
]

GPREG16 = [
    "ax",
    "cx",
    "dx",
    "bx",
    "sp",
    "bp",
    "si",
    "di",
    "r8w",
    "r9w",
    "r10w",
    "r11w",
    "r12w",
    "r13w",
    "r14w",
    "r15w",
]


GPREG64 = [
    "rax",
    "rcx",
    "rdx",
    "rbx",
    "rsp",
    "rbp",
    "rsi",
    "rdi",
    "r8",
    "r9",
    "r10",
    "r11",
    "r12",
    "r13",
    "r14",
    "r15",
]

GPREG32 = [
    "eax",
    "ecx",
    "edx",
    "ebx",
    "esp",
    "ebp",
    "esi",
    "edi",
    "r8d",
    "r9d",
    "r10d",
    "r11d",
    "r12d",
    "r13d",
    "r14d",
    "r15d",
]

GPREGS = {
    1: GPREG8,
    2: GPREG16,
    4: GPREG32,
    8: GPREG64,
}


class Decoder:
    def decode(self, rule: GeneralRule, ctx: CTX, current_state: PrefixState):
        raise NotImplementedError


class PlaceHolder_Decoder(Decoder):
    def decode(self, rule: GeneralRule, ctx: CTX, current_state: PrefixState):
        raise NotImplementedError


class R_RM_Decoder(Decoder):
    def __init__(self, name: str, direction: bool, is8: bool, supports: PrefixSupports):
        self.name = name
        self.direction = direction
        self.is8 = is8
        self.supports = supports

    def decode(self, rule: GeneralRule, ctx: CTX, current_state: PrefixState):
        modrm = ctx.code[ctx.index]
        mod = (modrm >> 6) & 3
        reg = (modrm >> 3) & 7
        rm = modrm & 7
        ctx.index += 1

        size = rule.get_operand_size(current_state, self.is8)
        r_op = rule.get_r_operand(current_state, reg, size)
        rm_op = rule.get_rm_operand(ctx, current_state, mod, rm, size)

        if self.direction:
            op1, op2 = r_op, rm_op
        else:
            op1, op2 = rm_op, r_op

        prefix_bytes = []

        prefix_bytes.extend(
            rule.emit_invalid_prefixes(ctx, current_state, self.supports)
        )

        rex = current_state.rex
        expr = f"{self.name} {op1}, {op2}"
        if rex:
            if rex.w == 0 and rex.x == 0 and rex.r == 0 and rex.b == 0 and not self.is8:
                expr = rule.format_rex(rex) + " " + expr
            elif mod == 0b11:
                if rex.x:
                    expr = rule.format_rex(rex) + " " + expr

                if current_state.addr_size:
                    expr = "addr32 " + expr
            elif mod != 0b11 and reg != 0b100:
                expr = rule.format_rex(rex) + " " + expr
        if current_state.op_size and size != 2:
            expr = "data16 " + expr

        instr_bytes = bytearray(prefix_bytes) + bytearray(
            ctx.code[rule.start_idx : ctx.index]
        )
        ctx.disassembled.append(Instruction(expr, instr_bytes))


class PUSH_POP_Decoder(Decoder):
    def __init__(self, name: str, reg: int):
        super().__init__()
        self.name = name
        self.supports = PrefixSupports(False, False, False, False, True, False)
        self.reg = reg

    def decode(self, rule: GeneralRule, ctx: CTX, current_state: PrefixState):
        prefix_bytes = []
        prefix_bytes.extend(
            rule.emit_invalid_prefixes(ctx, current_state, self.supports)
        )
        regmap = rule.get_reg_table(current_state, False)

        expr = f"{self.name} {regmap[self.reg]}"

        instr_bytes = bytearray(prefix_bytes) + bytearray(
            ctx.code[rule.start_idx : ctx.index]
        )
        ctx.disassembled.append(Instruction(expr, instr_bytes))


class IMM_Unary_Decoder(Decoder):
    def __init__(
        self,
        name: str,
        implicit_registers: list[int],
        is8: bool,
        supports: PrefixSupports,
    ) -> None:
        super().__init__()
        self.name = name
        self.implicit_registers = implicit_registers
        self.supports = supports
        self.is8 = is8

    def decode(self, rule: GeneralRule, ctx: CTX, current_state: PrefixState):
        prefix_bytes = []
        prefix_bytes.extend(
            rule.emit_invalid_prefixes(ctx, current_state, self.supports)
        )
        reg_table = rule.get_reg_table(current_state, self.is8)
        imm = rule.get_imm_operand(ctx,current_state,self.is8,False)
        expr = f"{self.name} {','.join([reg_table[r] for r in self.implicit_registers])}{', 'if self.implicit_registers else ''}{imm}"
        rex = current_state.rex
        if rex:
            if rex.w == 0:
                expr = rule.format_rex(rex) + " " + expr
        instr_bytes = bytearray(prefix_bytes) + bytearray(
            ctx.code[rule.start_idx : ctx.index]
        )
        ctx.disassembled.append(Instruction(expr, instr_bytes))



@dataclass
class ByteTableEntry:
    name: str
    decoder: Decoder


@dataclass
class GroupOpEntry:
    name: str
    decoder: Callable


class GroupEntry:
    def __init__(self, name: str, ops: List[GroupOpEntry]):
        self.group_name = name
        self.ops = ops

    def get_op(self, reg_bits: int) -> GroupOpEntry:
        return self.ops[reg_bits]


class GeneralRule(Rule):
    def __init__(self) -> None:
        super().__init__()
        self.start_idx: int = 0
        self.table = ByteTable(self)

    def apply(self, ctx: CTX, current_state: PrefixState) -> bool:
        self.start_idx = ctx.index
        opcode = byte = ctx.code[ctx.index]
        # E0x0F multi Byte opcodes (I Dont care yet...)
        if byte == 0x0F:
            return False
        if self.table.contains(opcode):
            entry = self.table.get(opcode)
            if entry.name == "INV":
                return False
            ctx.index += 1
            try:
                entry.decoder.decode(self, ctx, current_state)
                # save all processed bytes
                instr_bytes = bytearray(current_state.prefix_list)
                instr_bytes.extend(ctx.code[self.start_idx : ctx.index])
                ctx.disassembled[-1].bytes = instr_bytes
                current_state.reset()

                return True
            except Exception as e:

                print(f"error {opcode:02X}, {ctx.index}")
                ctx.index = self.start_idx
                raise e
        return False

    def get_r_operand(self, current_state: PrefixState, reg: int, size: int):
        rex = current_state.rex
        if rex and rex.r:
            reg |= 8

        table = self.get_reg_table(current_state, size == 1)
        return table[reg]

    def get_imm_operand(self, ctx: CTX, current_state:PrefixState,is8:bool, allowed64:bool=False) -> str:
        size = self.get_operand_size(current_state,is8)
        if size == 1:
            val = int.from_bytes(ctx.code[ctx.index:ctx.index + 1], "little", signed=True)
            ctx.index += 1
            return f"0x{val:X}"

        if size == 2:
            val = int.from_bytes(ctx.code[ctx.index:ctx.index + 2], "little", signed=True)
            ctx.index += 2
            return f"0x{val:X}"

        if size == 4:
            val = int.from_bytes(ctx.code[ctx.index:ctx.index + 4], "little", signed=True)
            ctx.index += 4
            return f"0x{val:X}"

        if size == 8:
            if not allowed64:
                val = int.from_bytes(ctx.code[ctx.index:ctx.index + 4], "little", signed=True)
                ctx.index += 4
                return f"0x{val:X}"
            val = int.from_bytes(ctx.code[ctx.index:ctx.index + 8], "little", signed=True)
            ctx.index += 8
            return f"0x{val:X}"

        raise ValueError("invalid imm size")

    def get_rm_operand(
        self, ctx: CTX, current_state: PrefixState, mod: int, rm: int, size: int
    ):
        rex = current_state.rex

        if rex and rex.b:
            rm |= 8

        table = self.get_reg_table(current_state, size == 1)
        base_table = GPREG32 if current_state.addr_size else GPREG64

        # register mode
        if mod == 0b11:
            return table[rm]
        ptr_list = {1: "BYTE  PTR ", 2: "WORD  PTR ", 4: "DWORD PTR ", 8: "QWORD PTR "}
        parts = []

        # SIB
        if rm & 0b111 == 0b100:
            sib = ctx.code[ctx.index]
            ctx.index += 1

            scale = (sib >> 6) & 3
            index = (sib >> 3) & 7
            raw_index = index
            base = sib & 7
            raw_base = base

            if rex:
                if rex.x:
                    index |= 8
                if rex.b:
                    base |= 8

            scale_val = [1, 2, 4, 8][scale]

            if raw_index != 4:
                parts.append(f"{base_table[index]}*{scale_val}")

            if raw_base != 5 or mod != 0:
                parts.insert(0, base_table[base])

            if raw_base == 5 and mod == 0:
                disp = int.from_bytes(
                    ctx.code[ctx.index : ctx.index + 4], "little", signed=True
                )
                ctx.index += 4
                parts.append(f"0x{disp:X}")

        else:
            if mod == 0 and rm & 7 == 5:
                disp = int.from_bytes(
                    ctx.code[ctx.index : ctx.index + 4], "little", signed=True
                )
                ctx.index += 4

                base = "rip" if not current_state.addr_size else "eip"

                parts.append(f"{base}+0x{disp:X}")

            else:
                parts.append(base_table[rm])

        # displacement
        if mod == 1:
            disp = int.from_bytes(
                ctx.code[ctx.index : ctx.index + 1], "little", signed=True
            )
            ctx.index += 1
            parts.append(f"0x{disp:X}")

        elif mod == 2:
            disp = int.from_bytes(
                ctx.code[ctx.index : ctx.index + 4], "little", signed=True
            )
            ctx.index += 4
            parts.append(f"0x{disp:X}")

        expr = "+".join(parts)

        mem = f"{ptr_list[size]}[{expr}]"

        if current_state.segment:
            mem = f"{current_state.segment}:{mem}"

        return mem

    def emit_invalid_prefixes(
        self, ctx: CTX, current_state: PrefixState, supports: PrefixSupports
    ) -> list[int]:

        # Prefix groups
        group1 = []  # LOCK / REP
        group2 = []  # SEG
        group3 = []  # OP_SIZE / ADDR_SIZE
        group4 = []  # REX
        valid_prefix_bytes = []

        for p in current_state.prefix_list:
            invalid = False
            if p == 0xF0 and not supports.lock:
                invalid = True
                current_state.lock = False
            elif p in (0xF2, 0xF3) and not supports.repeat:
                invalid = True
                current_state.repeat = None
            elif p in seg_prefixes and not supports.segment:
                invalid = True
                current_state.segment = None
            elif p == 0x66 and not supports.op_size:
                invalid = True
                current_state.op_size = False
            elif p == 0x67 and not supports.addr_size:
                invalid = True
                current_state.addr_size = False
            elif 0x40 <= p <= 0x4F and not supports.rex:
                invalid = True
                current_state.rex = None

            if invalid:
                ctx.disassembled.append(Instruction(f"DB {p:02X}", bytearray([p])))
                continue

            if p == 0xF0 or p in (0xF2, 0xF3):
                group1.append(p)
            elif p in seg_prefixes:
                group2.append(p)
            elif p in (0x66, 0x67):
                group3.append(p)
            elif 0x40 <= p <= 0x4F:
                group4.append(p)
            else:
                valid_prefix_bytes.append(p)

        valid_prefix_bytes = group1 + group2 + group3 + group4

        return valid_prefix_bytes

    def get_reg_table(self, current_state: PrefixState, is8: bool):
        size = self.get_operand_size(current_state, is8)
        rex_present = current_state.rex is not None
        if size == 1:  # 8-bit
            return GPREG8R if rex_present else GPREG8
        if size == 2:  # 16-bit
            return GPREG16
        if size == 4:  # 32-bit
            return GPREG32
        if size == 8:  # 64-bit
            return GPREG64
        raise ValueError("invalid register size")

    def get_operand_size(self, current_state: PrefixState, is8: bool) -> int:
        if is8:
            return 1

        rex = current_state.rex

        if rex and rex.w:
            return 8

        if current_state.op_size:
            return 2

        return 4
    
    def format_rex(self,rex:REX) -> str:
        parts = []
        if rex.w: parts.append("W")
        if rex.r: parts.append("R")
        if rex.x: parts.append("X")
        if rex.b: parts.append("B")

        # tek parça çıktı
        return "REX" + ("" if not parts else "." + "".join(parts))


class ByteTable:
    def __init__(self, rule: GeneralRule):
        # 0x00–0xFF → 256 eleman
        self.table: List[ByteTableEntry] = [
            ByteTableEntry("INV", PlaceHolder_Decoder())
        ] * 0x100
        names = ["ADD", "OR", "ADC", "SBB", "AND", "SUB", "XOR"]
        for i in range(0, 7):
            for j in range(6):
                is8 = (j % 2) == 0
                opcode = i * 8 + j
                unary = j > 3
                lock = j < 2
                direction = not lock
                name = names[i]
                if unary:

                    self.table[opcode] = ByteTableEntry(
                        name,
                        IMM_Unary_Decoder(
                            name,
                            [0],
                            is8,
                            PrefixSupports(lock, False, False, True, True, False),
                        ),
                    )
                    continue
                self.table[opcode] = ByteTableEntry(
                    name,
                    R_RM_Decoder(
                        name,
                        direction,
                        is8,
                        PrefixSupports(lock, False, True, True, True, True),
                    ),
                )

        for j in range(0, 7):
            is8 = (j % 2) == 0
            opcode = 0x38 + j
            unary = j > 3
            direction = j >= 2
            if unary:
                self.table[opcode] = ByteTableEntry(
                    "CMP",
                    IMM_Unary_Decoder(
                            "CMP",
                            [0],
                            is8,
                            PrefixSupports(False, False, False, True, True, False),
                        ),
                )
                continue
            self.table[opcode] = ByteTableEntry(
                "CMP",
                R_RM_Decoder(
                    "CMP",
                    direction,
                    is8,
                    PrefixSupports(False, False, True, True, True, True),
                ),
            )

        self.table[0x63] = ByteTableEntry(
            "MOVSXD",
            R_RM_Decoder(
                "MOVSXD",
                True,
                False,
                PrefixSupports(False, False, True, True, False, True),
            ),
        )

        for j in range(2):
            opcode = 0x88 + j
            self.table[opcode] = ByteTableEntry(
                "MOV",
                R_RM_Decoder(
                    "MOV",
                    False,
                    j == 0,
                    PrefixSupports(False, False, True, True, True, True),
                ),
            )

        self.table[0x8A] = ByteTableEntry(
            "MOV",
            R_RM_Decoder(
                "MOV",
                True,
                True,
                PrefixSupports(False, False, True, True, True, True),
            ),
        )
        self.table[0x8B] = ByteTableEntry(
            "MOV",
            R_RM_Decoder(
                "MOV",
                True,
                False,
                PrefixSupports(False, False, True, True, False, True),
            ),
        )
        
        for j in range(0,8):
            opcode = 0x50 + j

            self.table[opcode] = ByteTableEntry(
                "PUSH",
                PUSH_POP_Decoder("PUSH",j)
            )
        
        for j in range(0,8):
            opcode = 0x58 + j

            self.table[opcode] = ByteTableEntry(
                "POP",
                PUSH_POP_Decoder("POP",j)
            )
        
        self.table[0x68] = ByteTableEntry(
            "PUSH",
            IMM_Unary_Decoder(
                "PUSH",
                [],
                False,
                PrefixSupports(False, False, False, False, True, False),
            ),
        )

    def contains(self, op: int) -> bool:
        return 0 <= op <= 0xFF and self.table[op].name != "INV"

    def get(self, op: int) -> ByteTableEntry:
        if not self.contains(op):
            raise KeyError(f"Opcode {op:02X} not in table")
        return self.table[op]

    def contains_group(self, name: str) -> bool:
        return False

    def get_group(self, name: str) -> Optional[GroupEntry]:
        return None