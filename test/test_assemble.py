import pytest


def test_instructions():
    from boron.assembler.x64.General.instructions import INSTRUCTIONS
    from boron.assembler.x64.General.operands import Immediate,RegMem,Relative,SIB
    from boron.assembler.x64.General.registers import GPRegisters,SegmentRegisters
    # 1 - SYSCALL   2 - PUSHF
    # 3 - POPF      4 - CLI
    # 5 - STI       6 - RET
    # 7 - LEA       8 - SHR
    # 9 - SHL       10 - MOV
    # 11 - ADD      12 - SUB
    # 13 - MUL      14 - IMUL
    # 15 - AND      16 - XOR
    # 17 - OR       18 - CMP
    # 19 - INC      20 - DEC
    # 21 - PUSH     22 - POP
    # 23 - CALL     24 - JMP
    i = 0
    for correct,case in [
        #SYSCALL
        (b"\x0f\x05",INSTRUCTIONS.SYSCALL()),
        #PUSHF
        (b"\x9c",INSTRUCTIONS.PUSHF()),
        #POPF
        (b"\x9d",INSTRUCTIONS.POPF()),
        #CLI
        (b"\xfa",INSTRUCTIONS.CLI()),
        #STI
        (b"\xfb",INSTRUCTIONS.STI()),
        #RET
        (b"\xc3",INSTRUCTIONS.RET()),
        #LEA
        (b"\x8d\x05\x0a\x00\x00\x00",INSTRUCTIONS.LEA(GPRegisters.eax,Relative(Immediate(10,4)))),
        (b"\x48\x8d\x05\x0a\x00\x00\x00",INSTRUCTIONS.LEA(GPRegisters.rax,Relative(Immediate(10,4)))),
        (b"\x48\x8d\x04\xd1",INSTRUCTIONS.LEA(GPRegisters.rax,SIB().no_offset(GPRegisters.rcx,GPRegisters.rdx,3))),
        # 8 - SHR (Örnek: shr rax, 1; shr rax, 32)
        (b"\x48\xd3\xe8", INSTRUCTIONS.SHR.R_R(GPRegisters.rax)),
        (b"\x48\xd1\xe8", INSTRUCTIONS.SHR.R_IMM(GPRegisters.rax, Immediate(1, 1))),
        (b"\x48\xc1\xe8\x20", INSTRUCTIONS.SHR.R_IMM(GPRegisters.rax, Immediate(32, 1))),
        # 9 - SHL
        (b"\x48\xd3\xe0", INSTRUCTIONS.SHL.R_R(GPRegisters.rax)),
        (b"\x48\xd1\xe0", INSTRUCTIONS.SHL.R_IMM(GPRegisters.rax, Immediate(1, 1))),
        # 10 - MOV
        (b"\xb8\x23\x23\xff\xaa", INSTRUCTIONS.MOV.R_IMM(GPRegisters.eax, Immediate(0xAAFF2323, 4))),
        (b"\x48\xc7\xc0\x23\x23\xff\xaa", INSTRUCTIONS.MOV.R_IMM(GPRegisters.rax, Immediate(0xAAFF2323, 4))),
        (b"\x48\xb9\xff\xff\x00\x23\x23\xff\xaa\x00", INSTRUCTIONS.MOV.R_IMM(GPRegisters.rcx, Immediate(0xAAFF232300FFFF, 8))),
        # 11 - ADD
        (b"\x49\x81\xc2\xea\x07\x00\x00", INSTRUCTIONS.ADD.R_IMM(GPRegisters.r10, Immediate(2026, 4))),
        # 12 - SUB
        (b"\x48\x83\xe8\x0a", INSTRUCTIONS.SUB.R_IMM(GPRegisters.rax, Immediate(10, 1))),
        (b"\x48\x2b\xc3", INSTRUCTIONS.SUB.R_R(GPRegisters.rax, GPRegisters.rbx)),
        # 13 - MUL (Unsigned) 
        (b"\x48\xf7\xe3", INSTRUCTIONS.MUL.R(GPRegisters.rbx)),
        # 14 - IMUL (Signed)
        (b"\x48\x0f\xaf\xc3", INSTRUCTIONS.IMUL.BINARY().R_R(GPRegisters.rax, GPRegisters.rbx)),
        # 15 - AND
        (b"\x48\x83\xe0\x0f", INSTRUCTIONS.AND.R_IMM(GPRegisters.rax, Immediate(0x0F, 1))),
        # 16 - XOR
        (b"\x48\x33\xc0", INSTRUCTIONS.XOR.R_R(GPRegisters.rax, GPRegisters.rax)),
        # 17 - OR
        (b"\x48\x0b\xc3", INSTRUCTIONS.OR.R_R(GPRegisters.rax, GPRegisters.rbx)),
        # 18 - CMP
        (b"\x48\x83\xf8\x00", INSTRUCTIONS.CMP.R_IMM(GPRegisters.rax, Immediate(0, 1))),
        # 19 - INC
        (b"\x48\xff\xc0", INSTRUCTIONS.INC.R(GPRegisters.rax)),
        # 20 - DEC
        (b"\x48\xff\xc8", INSTRUCTIONS.DEC.R(GPRegisters.rax)),
        # 21 - PUSH
        (b"\x50", INSTRUCTIONS.PUSH.R(GPRegisters.rax)),
        (b"\x41\x50", INSTRUCTIONS.PUSH.R(GPRegisters.r8)),
        # 22 - POP
        (b"\x58", INSTRUCTIONS.POP.R(GPRegisters.rax)),
        # 23 - CALL
        (b"\xff\xd0", INSTRUCTIONS.CALL.R(GPRegisters.rax)),
        # 24 - JMP
        (b"\xff\xe0", INSTRUCTIONS.JMP.R(GPRegisters.rax)),
        # 25 - IMUL (Unary/Specific)
        (b"\x48\x0f\xaf\x9c\x48\xea\x07\x00\x00", INSTRUCTIONS.IMUL.BINARY().R_RM(GPRegisters.rbx,SIB().normal(GPRegisters.rax,GPRegisters.rcx,Immediate(2026,4),1).set_size(8))),
    ]:
        out = bytes()
        for part in case.emit():
            out += part.emit()
        if not out == correct:
            raise ValueError(f"{i} - Instruction: {case} | Output: {out.hex()} != Correct: {correct.hex()}")
        i+= 1

    print("All instructions verified successfully.")

