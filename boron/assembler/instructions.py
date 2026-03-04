from . import encoded_bytes 
from typing import Sequence, Union

class baseinstr:
    def emit(self) -> Sequence[encoded_bytes.EncodedByte]|encoded_bytes.EncodedByte:
        raise NotImplementedError
    def __len__(self):
        try:
            return sum([i for i in self.emit()]) # type: ignore
        except:
            return 0;
    def try_shrink(self):
        raise NotImplementedError
class Alignment(baseinstr):
    """Represents an alignment instruction. Does not emit any bytes."""
    def __init__(self, alignment: int):
        self.alignment = alignment
    # emit remains unimplemented
    pass

class RawData(baseinstr):
    """Represents raw bytes to be emitted directly."""
    def __init__(self, data: bytes):
        self.data = data