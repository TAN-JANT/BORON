from dataclasses import dataclass

@dataclass
class Instruction:
    expr  : str
    bytes : bytearray

@dataclass
class CTX:
    disassembled :list[Instruction]
    code :bytearray
    index :int = 0


class Rule:
    def apply(self,ctx:CTX,current_state) -> bool:
        raise NotImplementedError()
    