from .section import Relocation,Section,Symbol,SectionFlags,RelocationType
from .builder import Builder
from boron import ARCH
import sys
import ctypes

if sys.platform == "win32":
    # Windows Sabitleri
    MEM_COMMIT = 0x1000
    MEM_RESERVE = 0x2000
    PAGE_READWRITE = 0x04
    PAGE_EXECUTE_READWRITE = 0x40  # Gerekirse
    PAGE_EXECUTE_READ = 0x20
else:
    # Linux ve macOS (POSIX) Sabitleri
    import mmap
    PROT_READ = 0x01
    PROT_WRITE = 0x02
    PROT_EXEC = 0x04
    MAP_ANONYMOUS = 0x20 if sys.platform == "linux" else 0x1000 # macOS için farklıdır
    MAP_PRIVATE = 0x02


import sys
import ctypes
import mmap

class MemoryManager:
    PAGE_SIZE = 4096

    @staticmethod
    def align_up(value, alignment) -> int:
        return (value + alignment - 1) & ~(alignment - 1)

    @staticmethod
    def get_native_flags(flags: SectionFlags):
        is_r = SectionFlags.READ in flags
        is_w = SectionFlags.WRITE in flags
        is_x = SectionFlags.EXEC in flags

        if sys.platform == "win32":
            # [Windows Memory Protection Constants](https://learn.microsoft.com)
            if is_x:
                return 0x40 if is_w else 0x20 # PAGE_EXECUTE_READWRITE : PAGE_EXECUTE_READ
            return 0x04 if is_w else 0x02     # PAGE_READWRITE : PAGE_READONLY
        else:
            # [POSIX mmap/mprotect flags](https://man7.org)
            p = 0
            if is_r: p |= mmap.PROT_READ
            if is_w: p |= mmap.PROT_WRITE
            if is_x: p |= mmap.PROT_EXEC
            return p


class Executer:
    def __init__(self, builder: Builder):
        self.builder = builder

    def execute(self,entry_symbol:str="_start") -> None:
        """
        1: Generate the binary data for each section.
        2: Resolve relocations.
        3: check for undefined symbols. and raise an error if any are found.
        4: allocate memory for the sections.
        5: write section binaries into memory.
        6: apply relocations with the allocated memory address.
        7: set memory permissions according to section flags.
        8: jump to the entry point.
        """
        symbols :dict[str,tuple[Section,Symbol]]= {} # all symbols gathered together
        binary  = bytearray()
        offsets :dict[Section,int]= {} # self.builder.sections -> memory offset of the section
        relocations :list[tuple[Section,Relocation]]= [] # all relocations gathered together
        for section_name,section in self.builder.sections.items():
            binary += section.content
            for symbol in section.symbols:
                if symbol.name in symbols:
                    raise ValueError(f"Duplicate symbol '{symbol.name}' found in section '{section_name}'")
                # check for undefined symbols
                if not symbol.defined:
                    raise ValueError(f"Undefined symbol '{symbol.name}' found in section '{section_name}'")# TODO: add more exception classes
                symbols[symbol.name] = (section, symbol)
            for reloc in section.relocations:
                relocations.append((section, reloc))

        # allocate memory for the sections (Platform-independent)

        total_alloc_size = 0

        for name, sec in self.builder.sections.items():
            # Align sections
            total_alloc_size = MemoryManager.align_up(total_alloc_size, MemoryManager.PAGE_SIZE)
            offsets[sec] = total_alloc_size
            total_alloc_size += max(sec.size, len(sec.content))

        # Memory allocation (Platform-specific)
        if sys.platform == "win32":
            # [VirtualAlloc Documentation](https://learn.microsoft.com)
            base_addr = ctypes.windll.kernel32.VirtualAlloc(
                0, total_alloc_size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE
            )
        else:
            # [POSIX mmap Documentation](https://man7.org)
            m = mmap.mmap(-1, total_alloc_size, mmap.MAP_PRIVATE | MAP_ANONYMOUS, PROT_READ | PROT_WRITE) # allocating with all permissions, we will change it later
            base_addr = ctypes.addressof(ctypes.c_char.from_buffer(m))

        if not base_addr:
            raise MemoryError("Could not allocate memory for execution.")

        # 5: Write sections into memory
        for sec, offset in offsets.items():
            if sec.content:
                dest_ptr = base_addr + offset
                ctypes.memmove(dest_ptr, bytes(sec.content), len(sec.content))

        # 6: Apply relocations
        for reloc_sec, reloc in relocations:
            if reloc.symbol.name not in symbols or not reloc.symbol.defined:
                raise ValueError(f"Relocation references undefined symbol '{reloc.symbol.name}' in section '{reloc_sec.name}'")

            target_sec, target_sym = symbols[reloc.symbol.name]
            target_addr = base_addr + offsets[target_sec] + target_sym.offset
            patch_addr = base_addr + offsets[reloc_sec] + reloc.offset

            value = target_addr
            if reloc.type == RelocationType.RELATIVE:
                value = (target_addr - patch_addr - reloc.symbol.size)

            if reloc.symbol.size == 1:
                ctype = ctypes.c_uint8
                mask = 0xFF
            elif reloc.symbol.size == 2:
                ctype = ctypes.c_uint16
                mask = 0xFFFF
            elif reloc.symbol.size == 4:
                ctype = ctypes.c_uint32
                mask = 0xFFFFFFFF
            elif reloc.symbol.size == 8:
                ctype = ctypes.c_uint64
                mask = 0xFFFFFFFFFFFFFFFF
            else:
                raise ValueError(f"Unsupported symbol size '{reloc.symbol.size}' in section '{reloc_sec.name}'")

            # relocation
            ctype.from_address(patch_addr).value = value & mask

        # 7: Apply specific section permissions (RO, RX, RW)
        for sec, offset in offsets.items():
            native_flags = MemoryManager.get_native_flags(sec.flags)
            target_addr = base_addr + offset
            # İzinler sayfa boyutunda uygulanmalıdır
            aligned_size = MemoryManager.align_up(sec.size, MemoryManager.PAGE_SIZE)

            if sys.platform == "win32":
                old_protect = ctypes.c_ulong()
                ctypes.windll.kernel32.VirtualProtect(target_addr, aligned_size, native_flags, ctypes.byref(old_protect))
            else:
                libc = ctypes.CDLL(None)
                # [mprotect](https://linux.die.net) çağrısı ile izinleri kilitle
                if libc.mprotect(target_addr, aligned_size, native_flags) != 0:
                    raise RuntimeError("Failed to set memory permissions (mprotect).")

        # 8: Jump to entry point
        if entry_symbol not in symbols or not symbols[entry_symbol][1].defined:
            raise ValueError(f"Entry symbol '{entry_symbol}' is undefined.")
        entry_sec, entry_sym = symbols[entry_symbol]
        entry_addr = base_addr + offsets[entry_sec] + entry_sym.offset
        entry_func_type = ctypes.CFUNCTYPE(None)  # Assuming the entry point is a void function with no arguments
        entry_func = entry_func_type(entry_addr)
        entry_func()
