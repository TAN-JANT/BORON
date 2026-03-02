from boron.codegen.architecture.instructions import baseinstr
from boron.codegen.architecture.encoded_bytes import SYMBOL_Byte
from enum import Enum, Flag, auto
from typing import Sequence
from dataclasses import dataclass

class RelocationType(Enum):
    ABSOLUTE = auto()
    RELATIVE = auto()


class SectionKind(Enum):
    CODE = auto()
    DATA = auto()
    BSS = auto()
    RODATA = auto()
    CUSTOM = auto()

class SectionFlags(Flag):
    READ = auto()
    WRITE = auto()
    EXEC = auto()

class SymbolBinding(Enum):
    LOCAL = auto()
    GLOBAL = auto()
    EXTERN = auto()

@dataclass
class Symbol:
    name: str
    offset: int = 0
    size: int = 0
    binding: SymbolBinding = SymbolBinding.LOCAL
    defined: bool = True

@dataclass
class Relocation:
    offset: int
    type: RelocationType
    symbol: Symbol
    addend: int = 0


class Section:
    def __init__(self, name: str,
                 kind: SectionKind,
                 flags: SectionFlags,
                 alignment: int = 1):
        self.name = name
        self.kind = kind
        self.flags = flags
        self.alignment = alignment

        self.content :bytearray = bytearray()
        self.size           = 0
        self.relocations    = []
        self.symbols        = []

    def add_relocation(self, offset: int, type: RelocationType, symbol: Symbol, addend: int = 0):
        reloc = Relocation(offset, type, symbol, addend)
        self.relocations.append(reloc)

    def reserve_space(self, size: int):
        """
        Reserve space in the section (for bss)
        """
        self.size += size

    def emit_data(self, size: int, *values):
        out = bytearray()

        for v in values:
            # STRING PACKING (NASM STYLE)
            if isinstance(v, str):
                b = v.encode("utf-8")
                for i in range(0, len(b), size):
                    chunk = b[i:i+size]
                    chunk = chunk.ljust(size, b"\x00")  # padding
                    out += chunk

            # RAW BYTES
            elif isinstance(v, (bytes, bytearray)):
                out += v

            # INTEGER
            elif isinstance(v, int):
                out += v.to_bytes(size, "little", signed=False)

            else:
                raise TypeError(f"Unsupported db/dd value: {v}")

        self.content += out
        self.size += len(out)

    def db(self,*vals): return self.emit_data(1,*vals)
    def dw(self,*vals): return self.emit_data(2,*vals)
    def dd(self,*vals): return self.emit_data(4,*vals)
    def dq(self,*vals): return self.emit_data(8,*vals)

    def add(self, instr: baseinstr):
        """
        Add an instruction to the section.
        Optionally create a relocation if the instruction references a symbol.
        """
        parts = instr.emit()
        if not isinstance(parts, (Sequence)):
            parts = [parts]
        

        for part in parts:
            if isinstance(part, SYMBOL_Byte):
                # Create a relocation for this symbol reference
                self.add_relocation(self.size,RelocationType.RELATIVE if part.is_relative else RelocationType.ABSOLUTE, Symbol(part.name, size=part.size), addend=0)
            self.content += part.emit()
            self.size += len(part)

        return self.size

    def add_label(self, name: str, binding: SymbolBinding = SymbolBinding.LOCAL):
        """
        Add a label at the current offset.
        """
        sym = Symbol(name=name, size=self.size,binding=binding,)
        self.symbols.append(sym)
        return sym

    def add_symbol(self, name: str, size: int = 0,offset:int = 0):
        """
        Add a symbol without creating a label.
        """
        sym = Symbol(name, offset=offset, size=size)
        self.symbols.append(sym)
        return sym

    def __repr__(self):

        flags = str(self.flags) if self.flags else "NONE"
        sym_str = ", ".join(f"{s.name}( {s.offset} , {s.binding.name} )" for s in self.symbols)
        reloc_str = ", ".join(f"{r.type.name}@{r.offset}->{r.symbol.name}" for r in self.relocations)

        return (
            f"<Section {self.name!r} kind={self.kind.name}\n"
            f"  flags={flags}\n" 
            f"  align={self.alignment}\n"
            f"  size={self.size} bytes\n"
            f"  symbols=[{sym_str}]\n"
            f"  relocations=[{reloc_str}]>"
        )
