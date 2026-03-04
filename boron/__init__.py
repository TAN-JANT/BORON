
from enum import Enum,auto
class ARCH(Enum):
    x64 = auto()
    x86 = auto()
from . import codegen,assembler
