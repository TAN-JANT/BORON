from boron.assembler.x86_64 import GeneralPurposeRegister,operands,instructions,GPRegisters,encoded_bytes
import mmap
import ctypes
import struct


if __name__ == "__main__":
    encodeds = [
        instructions.MOV_Instruction.R_IMM(
            GPRegisters.al, operands.Immediate(1, 1)
        ),
        instructions.MOV_Instruction.R_IMM(
            GPRegisters.rdi, operands.Immediate(1, 4)
        ),
        instructions.MOV_Instruction.R_IMM(
            GPRegisters.rsi, operands.SYMBOL("SYM1", 8)
        ),
        instructions.MOV_Instruction.R_IMM(
            GPRegisters.rdx, operands.SYMBOL("SYM2", 4)
        ),
        instructions.SyscallInstruction(),
        instructions.MOV_Instruction.R_IMM(
            GPRegisters.rax, operands.Immediate(31, 4)
        ),
        instructions.DEC_Instruction.R(GPRegisters.rax),
        instructions.RET_Instruction()
    ]

    # -----------------------------
    # BYTEARRAY OLUŞTUR 
    # -----------------------------
    b = bytearray()
    b += bytes("Tanjant", "utf-8")
    b += bytes([0x00])

    string_offset = 0                     # string başı
    code_offset = len(b)                  # kod stringten sonra başlıyor

    symbol_positions = {}

    for encoded in encodeds:
        for part in encoded.emit():
            if isinstance(part, encoded_bytes.SYMBOL_Byte):
                if part.name not in symbol_positions:
                    symbol_positions[part.name] = []
                symbol_positions[part.name].append((len(b), part.size))
                b += b"\x00" * part.size
            else:
                b += part.emit()


    # -----------------------------
    # ŞİMDİ BELLEĞE YÜKLE
    # -----------------------------
    size = len(b)

    mem = mmap.mmap(
        -1,
        size,
        prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC
    )

    # mmap içine kopyala
    mem.write(b)

    # bellek adresini öğren
    base_addr = ctypes.addressof(ctypes.c_char.from_buffer(mem))

    string_addr = base_addr + string_offset


    for a in symbol_positions:
        for (pos, size) in symbol_positions[a]:
            addr = 0
            if a == "SYM1":
                addr = string_addr
            elif a == "SYM2":
                addr = code_offset  # "OHA!!\x00" uzunluğu 6 
            else:
                raise ValueError(f"Unknown symbol: {a}")

            mem.seek(pos)
            mem.write(addr.to_bytes(size, byteorder="little"))

    code_addr = base_addr + code_offset

    func_type = ctypes.CFUNCTYPE(ctypes.c_uint64)
    func = func_type(code_addr)

    print(func())
    mem.close()
