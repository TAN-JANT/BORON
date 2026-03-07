import pytest

def test_instructions():
    from boron.assembler.x64.General.instructions import INSTRUCTIONS
    from boron.assembler.x64.General.operands import Immediate,RegMem,Relative,SIB
    from boron.assembler.x64.General.registers import GPRegisters,SegmentRegisters
    out = bytes()
    i = INSTRUCTIONS.MOV.R_IMM(GPRegisters.eax,Immediate(0xAAFF2323,4))
    for j in i.emit():
        out += j.emit()
    if not out == (0xb82323ffaa).to_bytes(5):
        raise ValueError(f"{out} != {(0xb82323ffaa).to_bytes(5)}")
