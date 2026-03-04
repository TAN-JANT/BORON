# BORON Assembler

# _UNDER DEVELOPMENT_ - _TRY IT AT YOUR OWN RISK_

## What is Boron?
Boron is a hobby project that implements an x86-64 assembler in Python.  
You can dynamically assemble instructions at runtime and execute them immediately.

## Why Boron?

- **Live machine code generation:** Assemble instructions directly in Python and execute them on the fly.  
- **Full control:** Every instruction, operand, and offset is manipulable from Python objects.  
- **Learn by doing:** Experiment with instructions, syscalls, and memory layout without writing intermediate files.  
- **Transparent and hackable:** More comments and documentation will be added soon to help you understand the inner workings.

> Unlike NASM or GCC assemblers, Boron lets you **experiment and run machine code directly in Python**. Multi-file projects or libraries like libc still require the system linker, but single-file programs can be assembled and executed dynamically **(soon)**.

## Limitations

- **No built-in runtime execution yet:** You have to handle relocations manually.  
- **Relocatable ELF32/ELF64 files only:** COFF format and other outputs are not supported yet.  
- **Under active development:** Bugs and breaking changes are expected.
- **Not commented yet**: I will add comments to the code.

## Next steps

### Current Goals
- **Built-in runtime execution:** I will add an class for it.
- **More instructions:** I will add more x64 instructions. Currently Boron have a few instructions (24)
- **Documentation:** I will fill the documentation folder and comment the code.
### Future Goals
- **Other architecthtures:** I will add x16/x86 architecthure
- **More file formats:** Like coff
- **Disassembler:** From flat binary
- **Improvement of the readme:** I will add more examples.
- **And others**

## How to use Boron?

### Simple "Hello, World!"

```python
import mmap, ctypes
from boron.assembler.x64.General import instructions, operands
from boron.assembler.x64.General.registers import GPRegisters

# Message
hello = b"Hello, world!\n"
hello_len = len(hello)
hello_buf = ctypes.create_string_buffer(hello)  # buffer in memory
buf_addr = ctypes.addressof(hello_buf)         # raw byte address

# Assembly program
program = [
    # write(1, buf, len)
    instructions.INSTRUCTIONS.MOV.R_IMM(GPRegisters.rax, operands.Immediate(1, 8)),  # sys_write
    instructions.INSTRUCTIONS.MOV.R_IMM(GPRegisters.rdi, operands.Immediate(1, 8)),  # stdout
    instructions.INSTRUCTIONS.MOV.R_IMM(GPRegisters.rsi, operands.Immediate(buf_addr, 8)),
    instructions.INSTRUCTIONS.MOV.R_IMM(GPRegisters.rdx, operands.Immediate(hello_len, 8)),
    instructions.INSTRUCTIONS.SYSCALL(),

    # exit(0)
    instructions.INSTRUCTIONS.MOV.R_IMM(GPRegisters.rax, operands.Immediate(60, 8)),  
    instructions.INSTRUCTIONS.XOR.R_R(GPRegisters.rdi, GPRegisters.rdi),
    instructions.INSTRUCTIONS.SYSCALL(),
]

# Assemble to machine code
code = b""
for instr in program:
    for i in instr.emit():
        code += i.emit()

# Allocate executable memory and copy code
mem = mmap.mmap(-1, len(code), prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC,
                flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS)
mem.write(code)

# Execute
addr = ctypes.c_void_p.from_buffer(mem)
entry = ctypes.CFUNCTYPE(None)(ctypes.addressof(addr))
entry()
```

> Prints the string in `hello` directly. No NASM or linker required. Works on Linux.

> And yes that was for just a "Hello, World!" 

### simple "Hello, World!" but as a file

```python
from boron.codegen.builder import Builder
from boron.assembler.assembler import x64,ASSEMBLER,SECTION,ARCH,FILE
from boron.codegen.file import elf
from boron.codegen.section import SectionKind, SectionFlags, SymbolBinding
#required modules in boron

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

```
> It may be require admin permissions (sudo)
> you need to link it with ```ld out -o hello```

