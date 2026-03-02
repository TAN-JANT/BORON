from boron.assembler.x64.General.registers import GPRegisters # x64 registers like rax,rcx
if __name__ == "__main__":
    print("rax register:")
    print(GPRegisters.rax)
    print("eax register:")
    print(GPRegisters.eax)
    print("racx register:")
    print(GPRegisters.rcx)
    print("ecx register:")
    print(GPRegisters.ecx)

    print("ax register:")
    print(GPRegisters.ax)