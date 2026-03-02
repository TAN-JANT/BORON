from boron.codegen.architecture import x64
from .section import Section
from enum import Enum, auto

class ARCH(Enum):
	x64 = auto()
	x86 = auto()

class Builder:
    def __init__(self,arch:ARCH=ARCH.x64,is64:bool=True,lsb=True):
        self.is64 = is64
        self.lsb = lsb
        self.arch = arch
        self.sections = {}

    def add_section(self, section: Section):
        """
        Add a Section to the builder.
        If a section with the same name exists, raise an error.
        """
        if section.name in self.sections:
            raise ValueError(f"Section '{section.name}' already exists")
        self.sections[section.name] = section
        return section

    def get_section(self, name: str) -> Section:
        """
        Retrieve a section by name.
        """
        if name not in self.sections:
            raise KeyError(f"Section '{name}' does not exist")
        return self.sections[name]
