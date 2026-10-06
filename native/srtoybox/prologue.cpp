#include "prologue.h"

namespace {

// 명령 하나의 길이. 모르거나 size 를 넘으면 0.
int insn_length(const unsigned char *p, int size)
{
    int n = 0;
    if (n < size && (p[n] & 0xF0) == 0x40)   // REX
        n++;
    if (n >= size)
        return 0;
    const unsigned char op = p[n];
    if (op >= 0x50 && op <= 0x57)            // push reg
        return n + 1;
    if (op == 0x89 || op == 0x8B || op == 0x8D) {   // mov r/m, r · mov r, r/m · lea
        if (n + 1 >= size)
            return 0;
        const unsigned char modrm = p[n + 1];
        const int mod = modrm >> 6, rm = modrm & 7;
        int len = n + 2;
        if (mod == 0 && rm == 5)             // RIP 상대 주소 — 옮기면 가리키는 곳이 달라진다
            return 0;
        if (mod != 3 && rm == 4) {           // SIB 가 따라온다
            if (len >= size || (mod == 0 && (p[len] & 7) == 5))   // 기준 레지스터 없는 32비트 변위는 다루지 않는다
                return 0;
            len++;
        }
        len += mod == 1 ? 1 : mod == 2 ? 4 : 0;
        return len <= size ? len : 0;
    }
    if (n == 1 && p[0] == 0x48 && (op == 0x83 || op == 0x81) && n + 1 < size && p[n + 1] == 0xEC) {   // sub rsp, imm
        const int len = op == 0x83 ? 4 : 7;
        return len <= size ? len : 0;
    }
    return 0;
}

}  // namespace

int prologue_length(const unsigned char *code, int size, int want)
{
    int total = 0;
    while (total < want) {
        const int n = insn_length(code + total, size - total);
        if (n == 0)
            return 0;
        total += n;
    }
    return total;
}
