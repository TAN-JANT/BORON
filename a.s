section .data
    msg db "Hello, world!", 10  ; 10, yeni satır karakteridir

section .text
    global _start

_start:
    
    ; sys_write(stdout, msg, msg_len)
    mov rax, 1                  ; sistem çağrısı: sys_write
    mov rdi, 1                  ; dosya tanımlayıcı: stdout
    mov rsi, msg                ; yazılacak dize adresi
    mov rdx, 14                 ; dize uzunluğu
    syscall
    jmp _start

    ; sys_exit(0)
    mov rax, 60                 ; sistem çağrısı: sys_exit
    xor rdi, rdi                ; çıkış kodu: 0
    syscall
