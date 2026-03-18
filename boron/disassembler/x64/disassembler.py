from .rules import Rule,Instruction,CTX
from .General import GeneralRule
from .prefixes import PrefixRule,PrefixState

class Disassembler:
    def __init__(self,code:bytearray):
        self.ctx = CTX([],code,0)
        self.prefix_state = PrefixState([])
        self.rules = [
            PrefixRule(),
            GeneralRule(),
        ]
    
    def disassemble(self):
        # Disassembler loop
        while self.ctx.index < len(self.ctx.code):
            matched = False
            for rule in self.rules:
                if rule.apply(self.ctx,self.prefix_state):
                    matched = True
                    
                    break
            
            if not matched:
                # opcode matched değilse DB ekle
                self.ctx.disassembled.append(
                    Instruction(f"db 0x{self.ctx.code[self.ctx.index]:02X}",
                                self.ctx.code[self.ctx.index:self.ctx.index+1])
                )
                self.ctx.index += 1
