import mmap
import ctypes

from boron.assembler.x64.General import instructions, operands
from boron.assembler.x64.General.registers import GPRegisters
from boron.codegen.executer import Executer


# message
hello = b"Hello, world!\n"
hello_len = len(hello)

# assembly program (code ONLY)
program = [
    # lea rsi, [rip + OFFSET]
    instructions.INSTRUCTIONS.LEA(
        GPRegisters.rsi,
        operands.Relative(
            operands.Immediate(
                # size of instructions below (before string)
                47,
                4
            )
        )
    ),

    # write(1, buf, len)
    instructions.INSTRUCTIONS.MOV.R_IMM(
        GPRegisters.rdx,
        operands.Immediate(hello_len, 8)
    ),
    instructions.INSTRUCTIONS.MOV.R_IMM(
        GPRegisters.rax,
        operands.Immediate(1, 8)
    ),
    instructions.INSTRUCTIONS.MOV.R_IMM(
        GPRegisters.rdi,
        operands.Immediate(1, 8)
    ),
    instructions.INSTRUCTIONS.SYSCALL(),

    # exit(0)
    instructions.INSTRUCTIONS.MOV.R_IMM(
        GPRegisters.rax,
        operands.Immediate(60, 8)
    ),
    instructions.INSTRUCTIONS.XOR.R_R(
        GPRegisters.rdi,
        GPRegisters.rdi
    ),
    instructions.INSTRUCTIONS.SYSCALL(),
]





# assemble instructions to bytes
code = b""

for instr in program:        
    for i in instr.emit():

        code += i.emit()
# append string AFTER code
payload = code + hello
print("payload:",payload)

# allocate RWX memory
mem = mmap.mmap(
    -1,
    len(payload),
    prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC,
    flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS,
)

# copy payload into memory
mem.write(payload)

# execute
addr = ctypes.c_void_p.from_buffer(mem)
entry = ctypes.CFUNCTYPE(None)(ctypes.addressof(addr))
entry()


