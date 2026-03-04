from . import x16, x64, instructions,encoded_bytes
from enum import Enum, auto
from ..codegen import section, builder,file
from ..codegen.builder import ARCH




IS64 = [ARCH.x64]


class FILE(Enum):
    ELF = auto()


class SECTION:
    def __init__(
        self,
        name: str,
        kind: section.SectionKind,
        flags: section.SectionFlags,
        alignment: int = 1,
    ):
        self.name = name
        self.kind = kind
        self.flags = flags
        self.alignment = alignment
        self.content: list[tuple[int, instructions.baseinstr]] = []
        self.size = 0
        self.symbols : list[section.Symbol] = []

    def add(self, instr: instructions.baseinstr):
        """
        Add an instruction or directive to the section.
        Computes offset and updates section size.
        """

        # ALIGNMENT
        if isinstance(instr, instructions.Alignment):
            align = instr.alignment
            if align <= 0:
                raise ValueError("Alignment must be > 0")

            padding = (-self.size) % align
            if padding:
                pad = instructions.RawData(b"\x00" * padding)
                self.content.append((self.size, pad))
                self.size += len(pad)
            return

        # RAW DATA
        if isinstance(instr, instructions.RawData):
            self.content.append((self.size, instr))
            self.size += len(instr)
            return

        # NORMAL INSTRUCTION
        self.content.append((self.size, instr))
        self.size += len(instr)

        def reserve_space(self, size: int):
            """
            Reserve space in the section (for bss)
            """
            self.size += size

    def emit_data(self, size: int, *values):
        """
        Emits raw data into the section, packing strings, integers, or raw bytes.
        """
        data_bytes = bytearray()

        for v in values:
            # STRING PACKING (NASM STYLE)
            if isinstance(v, str):
                b = v.encode("utf-8")
                for i in range(0, len(b), size):
                    chunk = b[i : i + size]
                    chunk = chunk.ljust(size, b"\x00")  # padding to `size`
                    data_bytes += chunk

            # RAW BYTES
            elif isinstance(v, (bytes, bytearray)):
                data_bytes += v

            # INTEGER
            elif isinstance(v, int):
                data_bytes += v.to_bytes(size, "little", signed=False)

            else:
                raise TypeError(f"Unsupported db/dd/dq value: {v}")

        # Wrap the raw data in a RawData instruction

        instr = instructions.RawData(data_bytes)
        self.content.append((self.size, instr))
        self.size += len(data_bytes)

    def db(self, *vals):
        return self.emit_data(1, *vals)

    def dw(self, *vals):
        return self.emit_data(2, *vals)

    def dd(self, *vals):
        return self.emit_data(4, *vals)

    def dq(self, *vals):
        return self.emit_data(8, *vals)

    def add_label(
        self, name: str, binding: section.SymbolBinding = section.SymbolBinding.LOCAL
    ):
        """
        Add a label at the current offset.
        """
        sym = section.Symbol(name=name, size=self.size, binding=binding)
        self.symbols.append(sym)
        return sym

    def add_symbol(self, name: str, size: int = 0, offset: int = 0):
        """
        Add a symbol without creating a label.
        """
        sym = section.Symbol(name, offset=offset, size=size)
        self.symbols.append(sym)
        return sym

    def try_shrink(self):
        for _,i in self.content:
            if isinstance(i, instructions.RawData):
                continue
            if isinstance(i, instructions.Alignment):
                continue
            if isinstance(i, instructions.baseinstr):
                e = i.emit()
                if not isinstance(e,list):
                    e = [e]
                
                for byte in e:
                    if isinstance(byte,encoded_bytes.SYMBOL_Byte):
                        if byte.is_relative:
                            for s in self.symbols:
                                if s.name == byte.name:
                                    if -128 < s.offset - _ < 128:
                                        try:
                                            i.try_shrink()
                                        except:
                                            pass
                                    break
                            
                        continue
                continue
    def __repr__(self):

        flags = str(self.flags) if self.flags else "NONE"
        sym_str = ", ".join(
            f"{s.name}( {s.offset} , {s.binding.name} )" for s in self.symbols
        )

        return (
            f"<Section {self.name!r} kind={self.kind.name}\n"
            f"  flags={flags}\n"
            f"  align={self.alignment}\n"
            f"  size={self.size} bytes\n"
            f"  symbols=[{sym_str}]>"
        )


class ASSEMBLER:
    def __init__(self, arch: ARCH, lsb: bool):
        self.arch = arch
        self.sections: list[SECTION] = []
        self.lsb = lsb

    def add_section(self, section: SECTION):
        self.sections.append(section)
        return section

    def build(self, filetype: FILE)->bytes:
        self.builder = builder.Builder(self.arch, self.arch in IS64, self.lsb)
        for i in self.sections:
            i.try_shrink()
            current_section = section.Section(i.name, i.kind, i.flags, i.alignment)
            for j in i.symbols:
                current_section.symbols.append(j)
            for _,j in i.content:
                if isinstance(j, instructions.RawData):
                    current_section.emit_data(len(j.data), j.data)
                    continue
                if isinstance(j, instructions.Alignment):
                    continue
                if isinstance(j, instructions.baseinstr):
                    current_section.add(j)
            self.builder.add_section(current_section)
    
        match filetype:
            case FILE.ELF:
                self.elf = file.elf.ELFFile(self.builder)
                return self.elf.build()
