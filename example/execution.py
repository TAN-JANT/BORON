from boron.assembler.x64.General.instructions import INSTRUCTIONS
from boron.assembler.x64.General.registers import GPRegisters
from boron.assembler.x64.General import operands
from ctypes import c_int64
from boron.codegen.executer import Executer
from boron.codegen.builder import Builder
from boron.codegen.section import Section,SectionFlags,SectionKind,SymbolBinding
import time

def python_loop(n):
    rbx = 0
    while n > 0:
        rbx += 1
        n -= 1
    return rbx

def compare():
    N = 100_000_000
    print(f"--- {N:,} döngü için performans analizi ---\n")

    # 1. PYTHON TESTİ
    start_py = time.perf_counter()
    python_loop(N)
    py_duration = time.perf_counter() - start_py
    print(f"Python Süresi:             {py_duration:.6f} sn")

    # 2. BORON (ASM) TESTİ
    # Ölçüm başlangıcı (Derleme dahil)
    start_asm_total = time.perf_counter()

    # --- Derleme (Assembly) Aşaması ---
    asm_builder = Builder()
    text = asm_builder.add_section(Section(".text", SectionKind.CODE, SectionFlags.EXEC | SectionFlags.READ))
    text.add_label("_start", SymbolBinding.GLOBAL)
    text.add(INSTRUCTIONS.XOR.R_R(GPRegisters.rbx, GPRegisters.rbx))
    text.add_label("loop", SymbolBinding.GLOBAL)
    text.add(INSTRUCTIONS.INC.R(GPRegisters.rbx))
    text.add(INSTRUCTIONS.DEC.R(GPRegisters.rdi))
    text.add(INSTRUCTIONS.JNZ.REL(operands.SYMBOL("loop", 4, True)))
    text.add(INSTRUCTIONS.RET())

    asm_executer = Executer(asm_builder)
    asm_executer.assemble() 
    
    compile_finished = time.perf_counter()
    asm_compile_only = compile_finished - start_asm_total

    # --- Sadece Çalıştırma Aşaması ---
    start_run_only = time.perf_counter()
    asm_executer.call("_start", [c_int64], None, (N,))
    asm_run_only = time.perf_counter() - start_run_only

    # Toplam Süre
    asm_total_duration = time.perf_counter() - start_asm_total

    print("-" * 45)
    print(f"Boron Derleme Süresi:      {asm_compile_only:.6f} sn")
    print(f"Boron Saf Çalışma Süresi:  {asm_run_only:.6f} sn")
    print(f"Boron Toplam Süre:         {asm_total_duration:.6f} sn")
    print("-" * 45)

    # KAT HESAPLAMALARI
    ratio_total = py_duration / asm_total_duration
    ratio_run = py_duration / asm_run_only

    print(f"Hız Farkı (Toplam):        {ratio_total:.2f}x")
    print(f"Hız Farkı (Saf Çalışma):   {ratio_run:.2f}x")

if __name__ == "__main__":
    compare()