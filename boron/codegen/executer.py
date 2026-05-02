from .section import Relocation, Section, Symbol, SectionFlags, RelocationType
from .builder import Builder
import sys
import ctypes
import mmap


# --------------------------------------------------
# PLATFORM CONSTANTS
# --------------------------------------------------
if sys.platform == "win32":
    MEM_COMMIT = 0x1000
    MEM_RESERVE = 0x2000
    PAGE_READWRITE = 0x04
    PAGE_EXECUTE_READWRITE = 0x40
else:
    PROT_READ = 0x01
    PROT_WRITE = 0x02
    PROT_EXEC = 0x04
    MAP_ANONYMOUS = 0x20 if sys.platform == "linux" else 0x1000
    MAP_PRIVATE = 0x02


# --------------------------------------------------
# MEMORY MANAGER
# --------------------------------------------------
class MemoryManager:
    PAGE_SIZE = 4096

    @staticmethod
    def align_up(value, alignment):
        return (value + alignment - 1) & ~(alignment - 1)

    @staticmethod
    def get_native_flags(flags: SectionFlags):
        is_r = SectionFlags.READ in flags
        is_w = SectionFlags.WRITE in flags
        is_x = SectionFlags.EXEC in flags

        if sys.platform == "win32":
            if is_x:
                return 0x40 if is_w else 0x20
            return 0x04 if is_w else 0x02
        else:
            p = 0
            if is_r:
                p |= PROT_READ
            if is_w:
                p |= PROT_WRITE
            if is_x:
                p |= PROT_EXEC
            return p


# --------------------------------------------------
# EXECUTER
# --------------------------------------------------
class Executer:
    def __init__(self, builder: Builder):
        self.builder = builder
        self.base_addr = None
        self.offsets = {}
        self.symbols = {}
        self._mmap = None

    # --------------------------------------------------
    # ASSEMBLE
    # --------------------------------------------------
    def assemble(self):
        PAGE = MemoryManager.PAGE_SIZE

        symbols = {}
        offsets = {}
        relocations = []

        # ==============================
        # 1. PAGE-SAFE LAYOUT
        # ==============================
        total_size = 0

        for section_name, section in self.builder.sections.items():

            total_size = MemoryManager.align_up(total_size, PAGE)

            offsets[section] = total_size

            sec_size = max(len(section.content), section.size)
            sec_size = MemoryManager.align_up(sec_size, PAGE)

            total_size += sec_size

            for sym in section.symbols:
                if sym.name in symbols:
                    raise ValueError(f"Duplicate symbol {sym.name}")
                if not sym.defined:
                    raise ValueError(f"Undefined symbol {sym.name}")

                symbols[sym.name] = (section, sym)

            for rel in section.relocations:
                relocations.append((section, rel))

        # ==============================
        # 2. ALLOCATE MEMORY
        # ==============================
        if sys.platform == "win32":
            base_addr = ctypes.windll.kernel32.VirtualAlloc(
                0,
                total_size,
                MEM_COMMIT | MEM_RESERVE,
                PAGE_READWRITE
            )
        else:
            self._mmap = mmap.mmap(
                -1,
                total_size,
                mmap.MAP_PRIVATE | MAP_ANONYMOUS,
                PROT_READ | PROT_WRITE
            )
            base_addr = ctypes.addressof(ctypes.c_char.from_buffer(self._mmap))

        if not base_addr:
            raise MemoryError("Allocation failed")

        # ==============================
        # 3. WRITE SECTIONS
        # ==============================
        for sec, off in offsets.items():
            if sec.content:
                ctypes.memmove(
                    base_addr + off,
                    bytes(sec.content),
                    len(sec.content)
                )

        # ==============================
        # 4. RELOCATIONS
        # ==============================
        for sec, rel in relocations:
            target_sec, target_sym = symbols[rel.symbol.name]

            target_addr = base_addr + offsets[target_sec] + target_sym.offset
            patch_addr = base_addr + offsets[sec] + rel.offset

            value = target_addr

            if rel.type == RelocationType.RELATIVE:
                value = target_addr - patch_addr - rel.symbol.size

            size_map = {
                1: ctypes.c_uint8,
                2: ctypes.c_uint16,
                4: ctypes.c_uint32,
                8: ctypes.c_uint64,
            }

            if rel.symbol.size not in size_map:
                raise ValueError("Unsupported relocation size")

            ctype = size_map[rel.symbol.size]
            ctypes.cast(patch_addr, ctypes.POINTER(ctype)).contents.value = value

        # ==============================
        # 5. PERMISSIONS (NO BROKEN mprotect)
        # ==============================
        if sys.platform != "win32":
            libc = ctypes.CDLL(None, use_errno=True) # use_errno=True önemli
            libc.mprotect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
            libc.mprotect.restype = ctypes.c_int

        for sec, off in offsets.items():
            flags = MemoryManager.get_native_flags(sec.flags)

            addr = base_addr + off

            size = max(len(sec.content), sec.size)
            size = MemoryManager.align_up(size, PAGE)

            if sys.platform == "win32":
                old = ctypes.c_ulong()
                ctypes.windll.kernel32.VirtualProtect(
                    addr,
                    size,
                    flags,
                    ctypes.byref(old)
                )
            else:
                if libc.mprotect(addr, size, flags) != 0:
                    err = ctypes.get_errno()
                    raise RuntimeError(f"mprotect failed errno={err},{addr},{size},{flags}")

        # ==============================
        # 6. STORE STATE
        # ==============================
        self.base_addr = base_addr
        self.offsets = offsets
        self.symbols = symbols

    # --------------------------------------------------
    # CALL FUNCTION
    # --------------------------------------------------
    def call(self, symbol_name, argtypes=None, restype=None, args=()):
        if self.base_addr is None:
            raise RuntimeError("assemble() not called")

        if symbol_name not in self.symbols:
            raise ValueError("Symbol not found")

        sec, sym = self.symbols[symbol_name]

        addr = self.base_addr + self.offsets[sec] + sym.offset

        func_type = ctypes.CFUNCTYPE(restype, *(argtypes or []))
        func = func_type(addr)

        return func(*args)