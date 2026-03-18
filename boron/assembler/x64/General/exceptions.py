from boron.assembler.exceptions import AssemblerError

class OperandSizeMismatchError(AssemblerError):
    def __init__(self, mnemonic, *operands):
        super().__init__(
            f"{mnemonic}: operand size mismatch ({', '.join(str(op) + ':' + str(op.size) for op in operands)})"
        )

class InvalidRegisterError(AssemblerError):
    def __init__(self, mnemonic, register):
        super().__init__(f"{mnemonic}: invalid register '{register.name}' for this instruction")

class InvalidImmediateError(AssemblerError):
    def __init__(self, mnemonic, immediate):
        super().__init__(f"{mnemonic}: invalid immediate value '{immediate}' for this instruction")

class IllegalInstrutcionError(AssemblerError):
    def __init__(self, mnemonic, *operands):
        super().__init__(
            f"{mnemonic}: Illegal Instruction use ({', '.join(op.name + ':' + str(op.size) for op in operands)})"
        )


class IllegalEncodingError(AssemblerError):
    def __init__(self, msg:str):
        super().__init__(msg)
