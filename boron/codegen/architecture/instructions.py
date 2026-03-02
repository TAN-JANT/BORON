from . import encoded_bytes 
from typing import Sequence
class baseinstr:
   def emit(self) -> Sequence[encoded_bytes.EncodedByte]|encoded_bytes.EncodedByte:
        raise NotImplementedError
