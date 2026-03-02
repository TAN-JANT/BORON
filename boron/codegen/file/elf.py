import struct
from enum import IntEnum
from . import Builder, section, ARCH

from enum import IntEnum

class RelocationType(IntEnum):
    NONE         = 0    # No relocation
    
    # ---- x86 (32‑bit) ----
    R_386_32     = 1    # S + A (absolute 32‑bit)
    R_386_PC32   = 2    # S + A − P (PC‑relative)
    R_386_GOT32  = 3    # G + A (GOT)
    R_386_PLT32  = 4    # L + A − P (PLT relative)
    R_386_COPY   = 5
    R_386_GLOB_DAT = 6
    R_386_JMP_SLOT = 7
    R_386_RELATIVE = 8
    R_386_GOTOFF  = 9
    R_386_GOTPC   = 10
    R_386_16 = 20
    R_386_PC16 = 21
    R_386_8 = 22
    R_386_PC8 = 23

    # ---- x86_64 (64‑bit) ----
    R_X86_64_NONE    = 0
    R_X86_64_64      = 1
    R_X86_64_PC32    = 2
    R_X86_64_GOT32   = 3
    R_X86_64_PLT32   = 4
    R_X86_64_COPY    = 5
    R_X86_64_GLOB_DAT = 6
    R_X86_64_JUMP_SLOT = 7
    R_X86_64_RELATIVE  = 8
    R_X86_64_GOTPCREL  = 9
    R_X86_64_32      = 10
    R_X86_64_32S     = 11
    R_X86_64_16 =12
    R_X86_64_PC16 = 13
    R_X86_64_8 = 14
    R_X86_64_PC8= 15
    R_X86_64_PC64 = 24


RELOC_TABLE = {
    ARCH.x86: {
        (section.RelocationType.ABSOLUTE,    4): RelocationType.R_386_32, 
        (section.RelocationType.ABSOLUTE,    2): RelocationType.R_386_16,
        (section.RelocationType.ABSOLUTE,    1): RelocationType.R_386_8,

        (section.RelocationType.RELATIVE, 4): RelocationType.R_386_PC32,
        (section.RelocationType.RELATIVE, 2): RelocationType.R_386_PC16,
        (section.RelocationType.RELATIVE, 1):  RelocationType.R_386_PC8,
    },

    ARCH.x64: {
        (section.RelocationType.ABSOLUTE,    8): RelocationType.R_X86_64_64,
        (section.RelocationType.ABSOLUTE,    4): RelocationType.R_X86_64_32,
        (section.RelocationType.ABSOLUTE,    2): RelocationType.R_X86_64_16,
        (section.RelocationType.ABSOLUTE,    1):  RelocationType.R_X86_64_8,

        (section.RelocationType.RELATIVE, 4): RelocationType.R_X86_64_PC32,
        (section.RelocationType.RELATIVE, 2): RelocationType.R_X86_64_PC16,
        (section.RelocationType.RELATIVE, 1):  RelocationType.R_X86_64_PC8,
        (section.RelocationType.RELATIVE, 8): RelocationType.R_X86_64_PC64,
    }
}

class ELFClass(IntEnum):
    ELF32 = 1
    ELF64 = 2


class ELFData(IntEnum):
    MSB = 0
    LSB = 1


class ELFType(IntEnum):
    REL = 1


class ELFMachine(IntEnum):
    X86 = 3
    X86_64 = 62


class SectionType(IntEnum):
    NULL = 0
    PROGBITS = 1
    SYMTAB = 2
    STRTAB = 3
    RELA = 4
    NOBITS = 8

class ELFSectionFlag:
    WRITE      = 0x1
    ALLOC      = 0x2
    EXECINSTR  = 0x4




class ELFFile:
    ELF64_RELA_FMT = "<QQq"
    ELF32_RELA_FMT = "<IIi"

    ELF64_RELA_SIZE = struct.calcsize(ELF64_RELA_FMT)
    ELF32_RELA_SIZE = struct.calcsize(ELF32_RELA_FMT)

    def __init__(self, builder: Builder):
        self.builder = builder
        self.is64 = builder.is64
        self.header_size = 64 if self.is64 else 52
        self.sections: dict[str, section.Section] = self.builder.sections
        self.rela_sections: dict[str, section.Section] = {}

        # section header format
        if self.is64:
            self.shdr_fmt = "<IIQQQQIIQQ"
        else:
            self.shdr_fmt = "<IIIIIIIIII"
        self.shdr_size = struct.calcsize(self.shdr_fmt)

    # ---------------- Binary Builder ----------------

    def build(self) -> bytes:
        content = bytearray()
        section_headers = bytearray()

        # ----------------- Section name string table -----------------
        shstrtab = bytearray(b"\x00")  # first byte is NULL
        name_offsets = {}

        # Add standard sections
        name_offsets[".shstrtab"] = len(shstrtab)
        shstrtab += b".shstrtab\x00"

        name_offsets[".strtab"] = len(shstrtab)
        shstrtab += b".strtab\x00"

        name_offsets[".symtab"] = len(shstrtab)
        shstrtab += b".symtab\x00"

        # Add user sections and .rela names
        for sec_name, sec in self.sections.items():
            name_offsets[sec_name] = len(shstrtab)
            shstrtab += sec_name.encode() + b"\x00"

            if sec.relocations:
                rela_name = ".rela" + sec_name
                name_offsets[rela_name] = len(shstrtab)
                shstrtab += rela_name.encode() + b"\x00"
                self.rela_sections[rela_name] = sec

        # ----------------- Section ordering -----------------
        all_sections = ["NULL", ".shstrtab"] + list(self.sections.keys()) + list(self.rela_sections.keys()) + [".strtab", ".symtab"]
        section_index_map = {name: idx for idx, name in enumerate(all_sections)}

        # ----------------- Build symbol table -----------------
        strtab = bytearray(b"\x00")  # first byte NULL
        symtab_entries = []
        local_symbols = [(0, 0, 0, 0, 0, 0)]  # null symbol
        global_symbols = []
        local_symbol_map = {}
        global_symbol_map = {}

        for sec_idx, (sec_name, sec) in enumerate(self.sections.items(), start=2):
            for sym in sec.symbols:
                st_info = 0 if sym.binding == section.SymbolBinding.LOCAL else (1 << 4)
                st_other = 0
                st_shndx = 0 if not sym.defined else section_index_map[sec_name]
                st_value = sym.offset
                st_size = sym.size
                name_offset = len(strtab)
                strtab += sym.name.encode() + b"\x00"
                if sym.binding == section.SymbolBinding.LOCAL:
                    local_symbol_map[sym.name] = len(local_symbols)  # +1 for null symbol
                    local_symbols.append((name_offset, st_info, st_other, st_shndx, st_size ,st_value))
                else:
                    global_symbol_map[sym.name] = len(global_symbols) + 1  # +1 for null symbol
                    global_symbols.append((name_offset, st_info, st_other, st_shndx, st_size, st_value))
            # symtab_entries.append((name_offset, st_info, st_other, st_shndx, st_value, st_size))
        for sec in self.sections.values():
            for rel in sec.relocations:
                sym_name = rel.symbol.name

                # zaten local ise dokunma
                if sym_name in local_symbol_map:
                    continue

                # zaten global ise dokunma
                if sym_name in global_symbol_map:
                    continue

                # burada ise hiç tanımlı değil → extern üret
                self.add_undefined_global(sym_name, strtab, global_symbols, global_symbol_map)

        # ----------------- Append section contents -----------------
        section_offsets = {}
        offset = self.header_size  # start after ELF header

        for sec_name, sec in self.sections.items():
            section_offsets[sec_name] = offset
            content += sec.content
            offset += len(sec.content)

            # Relocation sections
        for rela_name, sec in self.rela_sections.items():
            section_offsets[rela_name] = offset
            for rel in sec.relocations:
                sym_name = rel.symbol.name
                sym_size = rel.symbol.size

                if sym_name in local_symbol_map:
                    sym_index = local_symbol_map[sym_name]
                else:
                    sym_index = global_symbol_map.get(sym_name, 0) + len(local_symbols) - 1
                    if sym_index < len(local_symbols) - 1:
                        raise ValueError(f"Symbol {sym_name} not found in symbol tables")

               # addend'i RELATIVE/ABSOLUTE göre ayarla
                addend = rel.addend
                
                if rel.type == section.RelocationType.RELATIVE:
                    addend -= rel.symbol.size  # RELATIVE için offset düzeltmesi

                # relocation type sadece sembol boyutuna göre
                r_type = RELOC_TABLE[self.builder.arch].get((rel.type, sym_size))
                if self.is64:
                    content += self.pack_rela64(rel.offset, sym_index, r_type, addend)
                    offset += self.ELF64_RELA_SIZE
                else:
                    content += self.pack_rela32(rel.offset, sym_index, r_type, addend)
                    offset += self.ELF32_RELA_SIZE
        # .strtab
        strtab_offset = offset
        content += strtab
        offset += len(strtab)

        # .symtab
        symtab_offset = offset
        symtab_content = bytearray()
        for i in range( len(local_symbols)):
            symtab_entries.append(local_symbols[i])
        for i in range( len(global_symbols)):
            symtab_entries.append(global_symbols[i])

        if self.is64:
            for ent in symtab_entries:
                symtab_content += struct.pack("<IBBHQQ", *ent)
        else:
            for ent in symtab_entries:
                symtab_content += struct.pack("<IIIBBH", *ent)
        print(f"Symtab content: {symtab_content.hex()}")
        content += symtab_content
        offset += len(symtab_content)

        # .shstrtab
        shstrtab_offset = offset
        content += shstrtab
        offset += len(shstrtab)

        # ----------------- Section headers -----------------
        # NULL section header
        section_headers += self._pack_shdr(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        # .shstrtab
        section_headers += self._pack_shdr(
            name_offsets[".shstrtab"],
            SectionType.STRTAB,
            0,
            0,
            shstrtab_offset,
            len(shstrtab),
            0,
            0,
            1,
            0,
        )

        # User sections
        for sec_name, sec in self.sections.items():
            section_headers += self._pack_shdr(
                name_offsets[sec_name],
                self._map_section_kind(sec.kind),
                self._map_section_flags(sec),
                0,
                section_offsets[sec_name],
                len(sec.content),
                0,
                0,
                sec.alignment,
                0,
            )

        # Relocation sections
        for rela_name, sec in self.rela_sections.items():
            section_headers += self._pack_shdr(
                name_offsets[rela_name],
                SectionType.RELA,
                0,
                0,
                section_offsets[rela_name],
                len(sec.relocations) * (self.ELF64_RELA_SIZE if self.is64 else self.ELF32_RELA_SIZE),
                section_index_map[".symtab"],
                section_index_map[sec.name],
                8 if self.is64 else 4,
                self.ELF64_RELA_SIZE if self.is64 else self.ELF32_RELA_SIZE,
            )
        print(f"strtab content: {strtab}")
        print(f"strtab content: {strtab.hex()}")
        # .strtab
        section_headers += self._pack_shdr(
            name_offsets[".strtab"],
            SectionType.STRTAB,
            0,
            0,
            strtab_offset,
            len(strtab),
            0,
            0,
            1,
            0,
        )

        # .symtab
        section_headers += self._pack_shdr(
            name_offsets[".symtab"],
            SectionType.SYMTAB,
            0,
            0,
            symtab_offset,
            len(symtab_content),
            section_index_map[".strtab"],
            len(local_symbols),  # local symbol count + null symbol
            8 if self.is64 else 4,
            24 if self.is64 else 16,
        )

        # ----------------- ELF header -----------------
        shoff = len(content)
        header = self._create_header(shoff + self.header_size, len(all_sections))

        return header + content + section_headers

    # ----------------- Relocation helpers -----------------
    def pack_rela64(self, offset, sym_index, r_type, addend):
        r_info = (sym_index << 32) | r_type
        return struct.pack(self.ELF64_RELA_FMT, offset, r_info, addend)

    def pack_rela32(self, offset, sym_index, r_type, addend):
        r_info = (sym_index << 8) | r_type
        return struct.pack(self.ELF32_RELA_FMT, offset, r_info, addend)

    # ----------------- Internal helpers -----------------
    def add_undefined_global(self, sym_name,strtab:bytearray, global_symbols:list[tuple[int,int,int,int,int,int]], global_symbol_map:dict[str,int]):
        name_offset = len(strtab)
        strtab.extend(sym_name.encode() + b"\x00")

        st_info = (1 << 4)  # GLOBAL
        st_other = 0
        st_shndx = 0        # SHN_UNDEF
        st_value = 0
        st_size = 0

        global_symbol_map[sym_name] = len(global_symbols) + 1
        global_symbols.append(
            (name_offset, st_info, st_other, st_shndx, st_value, st_size)
        )

    def _map_section_flags(self, sec: section.Section) -> int:
        flags = 0

        # CODE her zaman executable + alloc
        if sec.kind == section.SectionKind.CODE:
            flags |= ELFSectionFlag.ALLOC
            flags |= ELFSectionFlag.EXECINSTR

        # DATA bellekte olacak
        if sec.kind == section.SectionKind.DATA:
            flags |= ELFSectionFlag.ALLOC

        # RODATA bellekte ama yazılamaz
        if sec.kind == section.SectionKind.RODATA:
            flags |= ELFSectionFlag.ALLOC

        # BSS bellekte ama dosyada yok
        if sec.kind == section.SectionKind.BSS:
            flags |= ELFSectionFlag.ALLOC
            flags |= ELFSectionFlag.WRITE

        # explicit flags override
        if sec.flags & section.SectionFlags.WRITE:
            flags |= ELFSectionFlag.WRITE

        if sec.flags & section.SectionFlags.EXEC:
            flags |= ELFSectionFlag.EXECINSTR

        if sec.flags & section.SectionFlags.READ:
            flags |= ELFSectionFlag.ALLOC

        return flags

    def _pack_shdr(
        self,
        sh_name,
        sh_type,
        sh_flags,
        sh_addr,
        sh_offset,
        sh_size,
        sh_link,
        sh_info,
        sh_addralign,
        sh_entsize,
    ):
        return struct.pack(
            self.shdr_fmt,
            sh_name,
            sh_type,
            sh_flags,
            sh_addr,
            sh_offset,
            sh_size,
            sh_link,
            sh_info,
            sh_addralign,
            sh_entsize,
        )

    def _create_header(self, shoff: int, shnum: int) -> bytes:
        e_ident = bytearray(16)
        e_ident[0:4] = b"\x7fELF"
        e_ident[4] = ELFClass.ELF64 if self.is64 else ELFClass.ELF32
        e_ident[5] = ELFData.LSB if self.builder.lsb else ELFData.MSB
        e_ident[6] = 1
        e_ident[7] = 0

        endian = "<" if self.builder.lsb else ">"

        if self.is64:
            fmt = endian + "HHIQQQIHHHHHH"
            header = struct.pack(
                fmt,
                ELFType.REL,
                ELFMachine.X86_64 if self.builder.arch == ARCH.x64 else ELFMachine.X86,
                1,
                0,
                0,
                shoff,
                0,
                64,
                0,
                0,
                64,
                shnum,
                1,
            )
        else:
            fmt = endian + "HHIIIIIHHHHHH"
            header = struct.pack(
                fmt,
                ELFType.REL,
                ELFMachine.X86_64 if self.builder.arch == ARCH.x64 else ELFMachine.X86,
                1,
                0,
                0,
                shoff,
                0,
                52,
                0,
                0,
                40,
                shnum,
                1,
            )

        return bytes(e_ident) + header

    def _map_section_kind(self, kind: section.SectionKind) -> SectionType:
        if kind == section.SectionKind.BSS:
            return SectionType.NOBITS
        return SectionType.PROGBITS
