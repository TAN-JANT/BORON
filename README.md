# BORON Assembler

## UNDER DEVELOPMENT BUT YOU CAN TRY IT

### What is Boron ?
> ### Boron is a hobby project aims for an assembler in python
> Theres just only avaliable raw assemble for some x64 and x16 instructions


#### GPRegisters
> A class for general purpose registers 

``` python
from boron.assembler.x86_64 import GPRegisters # x64 registers like rax,rcx
rax = GPRegisters.rax
```

for x16 bit

```python
from boron.assembler.x16 import GPRegisters # x64 registers like ax,cx
ax = GPRegisters.ax
```

#### instructions

```python
from boron.assembler.x86_64 import instructions
