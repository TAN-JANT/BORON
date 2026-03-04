from boron.codegen.builder import Builder
from boron.assembler.assembler import x64,ASSEMBLER,SECTION,ARCH,FILE
from boron.codegen.file import elf
from boron.codegen.section import SectionKind, SectionFlags, SymbolBinding
builder = ASSEMBLER(ARCH.x64,True)
msg = b"Hello, World!\n"
# TEXT SECTION
text = builder.add_section(
    SECTION(".text", SectionKind.CODE, SectionFlags.EXEC, alignment=0x1000)
)


a = text.add_label("_start", binding=SymbolBinding.GLOBAL)

# write syscall
# rax = 1 (sys_write)
text.add(x64.General.instructions.INSTRUCTIONS.MOV.R_IMM(
    x64.General.registers.GPRegisters.eax,
    x64.General.operands.Immediate(1,4)
))

# rdi = 1 (stdout)
text.add(x64.General.instructions.INSTRUCTIONS.MOV.R_IMM(
    x64.General.registers.GPRegisters.edi,
    x64.General.operands.Immediate(1,4)
))

# rsi = &msg
text.add(x64.General.instructions.INSTRUCTIONS.MOV.R_IMM(
    x64.General.registers.GPRegisters.rsi,
    x64.General.operands.SYMBOL("msg", 8, False, 0))
)
# rdx = len
text.add(x64.General.instructions.INSTRUCTIONS.MOV.R_IMM(
    x64.General.registers.GPRegisters.edx,
    x64.General.operands.Immediate(len(msg),4)  # "Hello, world!\n"
))

b = text.add(x64.General.instructions.INSTRUCTIONS.SYSCALL())

text.add(x64.General.instructions.INSTRUCTIONS.JMP.REL(x64.General.operands.SYMBOL("_start",4 ,True,0)))
# never reachs
# exit syscall
# rax = 60
text.add(x64.General.instructions.INSTRUCTIONS.MOV.R_IMM(
    x64.General.registers.GPRegisters.rax,
    x64.General.operands.Immediate(60,4)
))

# rdi = 0
text.add(x64.General.instructions.INSTRUCTIONS.MOV.R_IMM(
    x64.General.registers.GPRegisters.rdi,
    x64.General.operands.Immediate(0,4)
))

text.add(x64.General.instructions.INSTRUCTIONS.SYSCALL())


# DATA SECTION
data = builder.add_section(
    SECTION(".data", SectionKind.DATA,
            SectionFlags.READ | SectionFlags.WRITE,
            alignment=0x10)
)
data.add_label("msg", binding=SymbolBinding.LOCAL)
data.db(msg)

# WRITE FILE
with open("out", "wb") as f:
    out = builder.build(FILE.ELF)
    f.write(out)
