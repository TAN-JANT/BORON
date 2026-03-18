from dataclasses import dataclass
from typing import Callable, List, Optional, Literal
from .prefixes import PrefixState, seg_prefixes,PrefixSupports
from .rules import Rule, CTX, Instruction

REG8 = [
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
REG8R = [
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

REG16 = [
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


REG64 = [
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

REG32 = [
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


@dataclass
class ByteTableEntry:
    name: str
    decoder: Callable


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


def get_reg_table(size: int, rex_present: bool):
    if size == 1:  # 8-bit
        return REG8R if rex_present else REG8
    if size == 2:  # 16-bit
        return REG16
    if size == 4:  # 32-bit
        return REG32
    if size == 8:  # 64-bit
        return REG64
    raise ValueError("invalid register size")


class GeneralRule(Rule):
    def __init__(self) -> None:
        super().__init__()
        self.start_idx: int = 0
        self.table = ByteTable(self)

    def apply(self, ctx: CTX,current_state:PrefixState) -> bool:
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
                entry.decoder(ctx,current_state)
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

    def get_r_operand(self, current_state:PrefixState, reg: int, size: int):
        rex = current_state.rex
        if rex and rex.r:
            reg |= 8

        table = get_reg_table(size, rex is not None)
        return table[reg]

    def get_rm_operand(self, ctx: CTX, current_state:PrefixState,mod: int, rm: int, size: int):
        rex = current_state.rex

        if rex and rex.b:
            rm |= 8

        table = get_reg_table(size, rex is not None)
        base_table = REG32 if current_state.addr_size else REG64 

        # register mode
        if mod == 0b11:
            return table[rm]
        ptr_list = {
            1:"BYTE  PTR ",
            2:"WORD  PTR ",
            4:"DWORD PTR ",
            8:"QWORD PTR "
        }
        parts = []

        # SIB
        if rm & 0b111 == 0b100:
            sib = ctx.code[ctx.index]
            ctx.index += 1

            scale = (sib >> 6) & 3
            index = (sib >> 3) & 7
            base = sib & 7

            if rex:
                if rex.x:
                    index |= 8
                if rex.b:
                    base |= 8

            scale_val = [1, 2, 4, 8][scale]

            if index != 4:
                parts.append(f"{base_table[index]}*{scale_val}")

            if base != 5 or mod != 0:
                parts.insert(0, base_table[base])

            if base == 5 and mod == 0:
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
        self,
        ctx: CTX,
        current_state:PrefixState,
        lock=False,
        rep=False,
        segment=False,
        op_size=False,
        addr_size=False,
        rex=False,
    ) -> list[int]:

        # Prefix groups
        group1 = []  # LOCK / REP
        group2 = []  # SEG
        group3 = []  # OP_SIZE / ADDR_SIZE
        group4 = []  # REX
        valid_prefix_bytes = []

        for p in current_state.prefix_list:
            invalid = False
            if p == 0xF0 and not lock:
                invalid = True
                current_state.lock = False
            elif p in (0xF2, 0xF3) and not rep:
                invalid = True
                current_state.repeat = None
            elif p in seg_prefixes and not segment:
                invalid = True
                current_state.segment = None
            elif p == 0x66 and not op_size:
                invalid = True
                current_state.op_size = False
            elif p == 0x67 and not addr_size:
                invalid = True
                current_state.addr_size = False
            elif 0x40 <= p <= 0x4F and not rex:
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

    def get_operand_size(self, current_state:PrefixState, is8: bool) -> int:
        if is8:
            return 1

        rex = current_state.rex

        if rex and rex.w:
            return 8

        if current_state.op_size:
            return 2

        return 4

    def decode_r_rm_instruction(
        self, ctx: CTX,  current_state:PrefixState ,name: str, direction: bool, is8: bool = False,
        supports: PrefixSupports = PrefixSupports()
    ):
        modrm = ctx.code[ctx.index]
        mod = (modrm >> 6) & 3
        reg = (modrm >> 3) & 7
        rm = modrm & 7
        ctx.index += 1

        size = self.get_operand_size(current_state,is8)
        r_op = self.get_r_operand(current_state,reg, size)
        rm_op = self.get_rm_operand(ctx, current_state,mod, rm, size)

        if direction:
            op1, op2 = r_op, rm_op
        else:
            op1, op2 = rm_op, r_op

        prefix_bytes = []

        prefix_bytes.extend(
            self.emit_invalid_prefixes(
                ctx,
                current_state,
                lock=supports.lock,
                rep=supports.repeat,
                segment=supports.segment,
                op_size=supports.op_size,
                addr_size=supports.addr_size,
                rex=supports.rex,
            )
        )

        rex = current_state.rex
        expr = f"{name} {op1}, {op2}"
        if rex:
            if rex.w == 0 and rex.x == 0 and rex.r == 0 and rex.b == 0:
                expr = "REX " + expr
            if mod == 0b11:
                if rex.x:
                    expr = "REX.X " + expr
                if current_state.addr_size:
                    expr = "addr32 " + expr
            if mod != 0b11 and reg != 0b100:
                if rex.x:
                    expr = "REX.X " + expr
        if current_state.op_size and size != 2:
            expr = "data16 " + expr

        instr_bytes = (
            bytearray(prefix_bytes)
            + bytearray(ctx.code[self.start_idx : ctx.index])
        )
        ctx.disassembled.append(Instruction(expr, instr_bytes))

    def decode_unary_no_modrm(self, ctx: CTX,  current_state:PrefixState ,name: str, is8: bool = False,
        supports: PrefixSupports = PrefixSupports()):

        size = self.get_operand_size(current_state,is8)
        r_op = self.get_r_operand(current_state,0, size) 

        prefix_bytes = []

        prefix_bytes.extend(
            self.emit_invalid_prefixes(
                ctx,
                current_state,
                lock=supports.lock,
                rep=supports.repeat,
                segment=supports.segment,
                op_size=supports.op_size,
                addr_size=supports.addr_size,
                rex=supports.rex,
            )
        )

        if size == 1:
            imm = int.from_bytes(
                    ctx.code[ctx.index : ctx.index + 1], "little", signed=True
            )
            ctx.index += 1

        elif size == 2:
            imm = int.from_bytes(
                    ctx.code[ctx.index : ctx.index + 2], "little", signed=True
            )
            ctx.index += 2

        else:
            imm = int.from_bytes(
                    ctx.code[ctx.index : ctx.index + 4], "little", signed=True
            )
            ctx.index += 4

        rex = current_state.rex
        expr = f"{name} {r_op}, {imm}"
        if rex:
            if rex.r == 0 and not is8:
                expr = f"REX " + expr

        if current_state.addr_size:
            expr = "addr32" + expr

        if current_state.op_size and size != 2:
            expr = "data16 " + expr

        instr_bytes = (
            bytearray(prefix_bytes)
            + bytearray(ctx.code[self.start_idx : ctx.index])
        )
        ctx.disassembled.append(Instruction(expr, instr_bytes))

    """
    def decode_group(self, ctx: CTX,current_state:PrefixState, group_name: str, is8: bool = False):
        if self.table.contains_group(group_name):
            raise ValueError(f"Unknown group: {group_name}")

        modrm = ctx.code[ctx.index]
        reg = (modrm >> 3) & 0b111

        group = self.table.get_group(group_name)
        op_entry = group.get_op(reg)
        op_entry.decoder(ctx)
    """
    def decode_placeholder(self, ctx): ...


class ByteTable:
    def __init__(self,rule:GeneralRule):
        # 0x00–0xFF → 256 eleman
        self.table: List[ByteTableEntry] = [ByteTableEntry("INV",rule.decode_placeholder)] * 0x100
        names = ["ADD", "OR", "ADC", "SBB", "AND", "SUB", "XOR"]
        for i in range(0,7):
            for j in range(6):
                is8     = (j % 2) == 0
                opcode  = i*8 + j
                unary   = j > 3
                lock    = j < 2
                direction = not lock
                name    = names[i]
                if unary:

                    self.table[opcode] = ByteTableEntry(
                        name,
                        lambda ctx, state, name=name, is8=is8, lock=lock: rule.decode_unary_no_modrm(
                            ctx,
                            state,
                            name,
                            is8,
                            PrefixSupports(lock, False, True, True, True, True),
                        ),
                    )
                self.table[opcode] = ByteTableEntry(
                    name,
                    lambda ctx, state, name=name, direction=direction, is8=is8, lock=lock: rule.decode_r_rm_instruction(
                        ctx,
                        state,
                        name,
                        direction,
                        is8,
                        PrefixSupports(lock, False, True, True, True, True),
                    ),
                )

        for j in range(0,7):
            is8     = (j % 2) == 0
            opcode  = 0x38 + j
            unary   = j > 3
            direction = j>= 2
            if unary:
                self.table[opcode] = ByteTableEntry(
                        "CMP",
                        lambda ctx, state, is8=is8: rule.decode_unary_no_modrm(
                            ctx,
                            state,
                            "CMP",
                            is8,
                            PrefixSupports(False, False, True, True, True, True),
                        ),
                    )
            self.table[opcode] = ByteTableEntry(
                "CMP",
                lambda ctx, state, name="CMP", direction=direction, is8=is8: rule.decode_r_rm_instruction(
                    ctx,
                    state,
                    name,
                    direction,
                    is8,
                    PrefixSupports(False, False, True, True, True, True),
                ),
            )

    def contains(self, op: int) -> bool:
        if not (0 <= op <= 0xFF):
            return False
        return True

    def get(self, op: int) -> ByteTableEntry:
        if not self.contains(op):
            raise KeyError(f"Opcode {op:02X} not in table")
        return self.table[op]
    def contains_group(self,name:str)->bool:
        return False
    def get_group(self,name:str)->Optional[GroupEntry]:
        return None
