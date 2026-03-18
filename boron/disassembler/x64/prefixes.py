from dataclasses import dataclass
from typing import Optional

from boron.disassembler.x64.rules import CTX
from .rules import Rule
seg_prefixes = {
            0x26: "ES",
            0x2E: "CS",
            0x36: "SS",
            0x3E: "DS",
            0x64: "FS",
            0x65: "GS",
        }
@dataclass
class REX:
    w: bool = False
    r: bool = False
    x: bool = False
    b: bool = False


@dataclass
class PrefixState:
    prefix_list: list[int]
    lock: bool = False
    repeat: Optional[str] = None
    segment: Optional[str] = None
    rex: Optional[REX] = None
    op_size: bool = False
    addr_size: bool = False

    def reset(self):
        self.prefix_list.clear()
        self.lock = False
        self.repeat = None
        self.segment = None
        self.rex = None
        self.op_size = False
        self.addr_size = False

@dataclass
class PrefixSupports:
    lock        :bool = False
    repeat      :bool = False
    segment     :bool = False
    rex         :bool = False
    op_size     :bool = False
    addr_size   :bool = False





class PrefixRule(Rule):
    def parse_rex(self, byte: int) -> REX:
        return REX(
            w=bool((byte >> 3) & 1),
            r=bool((byte >> 2) & 1),
            x=bool((byte >> 1) & 1),
            b=bool(byte & 1),
        )
    def apply(self, ctx: CTX,current_state:PrefixState):
        byte = ctx.code[ctx.index]
        if byte == 0xF0:
            current_state.lock = True
            current_state.prefix_list.append(byte)
            ctx.index += 1
            return True
        elif byte == 0xF2:
            current_state.repeat = "REPNE"
            current_state.prefix_list.append(byte)
            ctx.index += 1
            return True
        elif byte == 0xF3:
            current_state.repeat = "REP"
            current_state.prefix_list.append(byte)
            ctx.index += 1
            return True
        elif byte in seg_prefixes:
            current_state.segment = seg_prefixes[byte]
            current_state.prefix_list.append(byte)
            ctx.index += 1
            return True
        elif byte == 0x66:
            current_state.op_size = True
            current_state.prefix_list.append(byte)
            ctx.index += 1
            return True
        elif byte == 0x67:
            current_state.addr_size = True
            current_state.prefix_list.append(byte)
            ctx.index += 1
            return True
        elif 0x40 <= byte <= 0x4F:
            current_state.rex = self.parse_rex(byte)
            current_state.prefix_list.append(byte)
            ctx.index += 1
            return True
        return False

