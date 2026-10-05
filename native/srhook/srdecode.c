#include "srdecode.h"

#define PARA 0xB6     /* 줄바꿈 기호: 엔진이 바이트로 직접 비교한다 */
#define ESC_CONT 0xFF /* 연속 바이트 0xB6 대체 */

static const unsigned short CP1252_HIGH[32] = {
    0x20AC, 0x0081, 0x201A, 0x0192, 0x201E, 0x2026, 0x2020, 0x2021,
    0x02C6, 0x2030, 0x0160, 0x2039, 0x0152, 0x008D, 0x017D, 0x008F,
    0x0090, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2013, 0x2014,
    0x02DC, 0x2122, 0x0161, 0x203A, 0x0153, 0x009D, 0x017E, 0x0178,
};

static unsigned cp1252(unsigned char b)
{
    return (b >= 0x80 && b <= 0x9F) ? CP1252_HIGH[b - 0x80] : b;
}

static int is_cont(unsigned char b)
{
    return (b >= 0x80 && b <= 0xBF && b != PARA) || b == ESC_CONT;
}

static unsigned cont(unsigned char b)
{
    return (b == ESC_CONT ? PARA : b) & 0x3F;
}

#define EMIT(u)                           \
    do {                                  \
        if (dst && count < cap)           \
            dst[count] = (wchar_t)(u);    \
        count++;                          \
    } while (0)

size_t sr_decode(const unsigned char *s, size_t n, int measure, wchar_t *dst, size_t cap)
{
    size_t count = 0, i = 0;
    int multibyte = 0; /* 앞에서 멀티바이트 문자가 나왔는가 (= 한글이 섞인 문자열인가) */

    if (measure && n == 1 && s[0] >= 0x80 && s[0] != PARA) {
        unsigned char b = s[0];
        if (b >= 0xE0 && b <= 0xEF)
            EMIT(SR_PH_CELL);
        else if (is_cont(b))
            EMIT(SR_PH_ZERO);
        else
            EMIT(cp1252(b));
        return count;
    }

    while (i < n) {
        unsigned char b = s[i];
        if (b < 0x80 || b == PARA) {
            EMIT(b);
            i++;
            continue;
        }
        if (b >= 0xC2 && b <= 0xDF && i + 1 < n && is_cont(s[i + 1])) {
            EMIT(((b & 0x1Fu) << 6) | cont(s[i + 1]));
            i += 2;
            multibyte = 1;
            continue;
        }
        if (b >= 0xE0 && b <= 0xEF) {
            if (i + 2 < n && is_cont(s[i + 1]) && is_cont(s[i + 2])) {
                unsigned cp = ((b & 0x0Fu) << 12) | (cont(s[i + 1]) << 6) | cont(s[i + 2]);
                if (cp >= 0x800 && !(cp >= 0xD800 && cp <= 0xDFFF)) {
                    EMIT(cp);
                    i += 3;
                    multibyte = 1;
                    continue;
                }
            } else if (i + 2 == n && is_cont(s[i + 1])) {
                i += 2; /* 음절 중간에서 잘린 꼬리는 버린다 */
                continue;
            } else if (i + 1 == n && multibyte) {
                /* 한글 문자열의 맨 끝에 리드 바이트만 남음(게임이 칸에 맞춰 자른 것) → 버린다.
                 * 한글이 없는 문자열이면 원본 이름의 끝 글자(Bogotá)이므로 아래에서 CP1252 로 살린다. */
                i += 1;
                continue;
            }
        }
        if (b >= 0xF0 && b <= 0xF4 && i + 3 < n && is_cont(s[i + 1]) && is_cont(s[i + 2]) && is_cont(s[i + 3])) {
            unsigned cp = ((b & 0x07u) << 18) | (cont(s[i + 1]) << 12) | (cont(s[i + 2]) << 6) | cont(s[i + 3]);
            if (cp >= 0x10000 && cp <= 0x10FFFF) {
                cp -= 0x10000;
                EMIT(0xD800 | (cp >> 10));
                EMIT(0xDC00 | (cp & 0x3FF));
                i += 4;
                multibyte = 1;
                continue;
            }
        }
        EMIT(cp1252(b)); /* 유효한 시퀀스가 아니면 원본 데이터(CP1252) 문자로 본다 */
        i++;
    }
    return count;
}
