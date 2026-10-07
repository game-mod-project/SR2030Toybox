#include "locate.h"

#include <excpt.h>

#include <cstring>

namespace {

struct Section {
    uint32_t rva, size;
    bool code;        // 실행 구역
    bool constant;    // 읽기 전용 자료(문자열이 여기 있다. 쓸 수 있는 구역에는 사용자가 친 글이 남을 수 있어 닻을 찾지 않는다)
};

struct Image {
    const uint8_t *p;
    size_t size;
    Section sections[32];
    int count;
    uint32_t pdata, pdata_size;

    bool has(uint64_t rva, uint64_t n) const { return rva + n <= size; }
    uint16_t u16(uint32_t rva) const { uint16_t v; memcpy(&v, p + rva, sizeof(v)); return v; }
    uint32_t u32(uint32_t rva) const { uint32_t v; memcpy(&v, p + rva, sizeof(v)); return v; }
    int32_t i32(uint32_t rva) const { int32_t v; memcpy(&v, p + rva, sizeof(v)); return v; }
};

bool parse(Image &im)
{
    if (!im.has(0, 0x40) || im.u16(0) != 0x5A4D)                        // "MZ"
        return false;
    const uint32_t nt = im.u32(0x3C);
    if (!im.has(nt, 24 + 112 + 16 * 8) || im.u32(nt) != 0x00004550)     // "PE\0\0"
        return false;
    const uint32_t sections = im.u16(nt + 6), optional_size = im.u16(nt + 20), optional = nt + 24;
    if (im.u16(optional) != 0x20B || optional_size < 112 + 4 * 8)       // PE32+
        return false;
    im.pdata = im.u32(optional + 112 + 3 * 8);                          // 예외 디렉터리 = 함수 표(.pdata)
    im.pdata_size = im.u32(optional + 112 + 3 * 8 + 4);
    if (im.pdata_size < 12 || !im.has(im.pdata, im.pdata_size))
        return false;
    im.count = 0;
    for (uint32_t i = 0; i < sections && im.count < 32; i++) {
        const uint64_t header = static_cast<uint64_t>(optional) + optional_size + 40ull * i;
        if (!im.has(header, 40))
            return false;
        const uint32_t h = static_cast<uint32_t>(header), flags = im.u32(h + 36);
        Section s;
        s.size = im.u32(h + 8);
        s.rva = im.u32(h + 12);
        s.code = (flags & 0x20000000) != 0;                             // IMAGE_SCN_MEM_EXECUTE
        s.constant = !s.code && (flags & 0x80000000) == 0;              // IMAGE_SCN_MEM_WRITE 가 아니다
        if (s.size == 0)
            continue;
        if (!im.has(s.rva, s.size))
            return false;
        im.sections[im.count++] = s;
    }
    return im.count > 0;
}

// 서명: 16진수 바이트와 '?'(아무 바이트)를 빈칸으로 나눠 적는다. 예: "48 8D 0D ? ? ? ?"
struct Pattern {
    uint8_t bytes[40];
    bool any[40];
    uint32_t length;
};

Pattern pattern(const char *text)
{
    Pattern p = {};
    for (const char *c = text; *c != '\0' && p.length < 40; ) {
        if (*c == ' ') {
            c++;
        } else if (*c == '?') {
            p.any[p.length++] = true;
            c++;
        } else {
            unsigned value = 0;
            for (int i = 0; i < 2; i++, c++)
                value = value * 16 + static_cast<unsigned>(*c <= '9' ? *c - '0' : (*c | 0x20) - 'a' + 10);
            p.bytes[p.length++] = static_cast<uint8_t>(value);
        }
    }
    return p;
}

bool matches(const Image &im, uint64_t rva, const Pattern &pt)
{
    if (!im.has(rva, pt.length))
        return false;
    for (uint32_t i = 0; i < pt.length; i++)
        if (!pt.any[i] && im.p[rva + i] != pt.bytes[i])
            return false;
    return true;
}

// [from, to) 에서 처음 맞는 자리. 없으면 0.
uint32_t find(const Image &im, uint32_t from, uint32_t to, const Pattern &pt)
{
    for (uint64_t rva = from; rva < to; rva++)
        if (matches(im, rva, pt))
            return static_cast<uint32_t>(rva);
    return 0;
}

// 실행 구역 전체에서 맞는 자리의 수. first 에 가장 앞의 것.
int count_in_code(const Image &im, const Pattern &pt, uint32_t *first)
{
    int n = 0;
    for (int s = 0; s < im.count; s++) {
        const Section &sec = im.sections[s];
        if (!sec.code || sec.size < pt.length)
            continue;
        for (uint32_t rva = sec.rva; rva <= sec.rva + sec.size - pt.length; rva++)
            if (im.p[rva] == pt.bytes[0] && matches(im, rva, pt) && n++ == 0)
                *first = rva;
    }
    return n;
}

// RIP 상대 주소가 든 명령이 가리키는 곳. at: 명령의 시작, disp: 변위의 자리, length: 명령의 길이.
uint32_t target(const Image &im, uint32_t at, uint32_t disp, uint32_t length)
{
    return static_cast<uint32_t>(static_cast<int64_t>(at) + length + im.i32(at + disp));
}

// 읽기 전용 자료에서 NUL 로 끝나는 글의 수. first 에 가장 앞의 것.
int count_string(const Image &im, const char *text, uint32_t *first)
{
    const uint32_t length = static_cast<uint32_t>(strlen(text)) + 1;
    int n = 0;
    for (int s = 0; s < im.count; s++) {
        const Section &sec = im.sections[s];
        if (!sec.constant || sec.size < length)
            continue;
        for (uint32_t rva = sec.rva; rva <= sec.rva + sec.size - length; rva++)
            if (im.p[rva] == static_cast<uint8_t>(text[0]) && memcmp(im.p + rva, text, length) == 0 && n++ == 0)
                *first = rva;
    }
    return n;
}

// where 를 가리키는 lea r64,[rip+d] (48|4C 8D 05|0D|…|3D d32)의 수. first 에 가장 앞의 것.
int count_lea_to(const Image &im, uint32_t where, uint32_t *first)
{
    int n = 0;
    for (int s = 0; s < im.count; s++) {
        const Section &sec = im.sections[s];
        if (!sec.code || sec.size < 7)
            continue;
        for (uint32_t rva = sec.rva; rva <= sec.rva + sec.size - 7; rva++)
            if ((im.p[rva] == 0x48 || im.p[rva] == 0x4C) && im.p[rva + 1] == 0x8D && (im.p[rva + 2] & 0xC7) == 0x05
                && target(im, rva, 3, 7) == where && n++ == 0)
                *first = rva;
    }
    return n;
}

// where 를 부르는 call rel32 (E8 d32)의 수. first 에 가장 앞의 것.
int count_calls_to(const Image &im, uint32_t where, uint32_t *first)
{
    int n = 0;
    for (int s = 0; s < im.count; s++) {
        const Section &sec = im.sections[s];
        if (!sec.code || sec.size < 5)
            continue;
        for (uint32_t rva = sec.rva; rva <= sec.rva + sec.size - 5; rva++)
            if (im.p[rva] == 0xE8 && target(im, rva, 1, 5) == where && n++ == 0)
                *first = rva;
    }
    return n;
}

// rva 가 든 함수의 시작. 함수 표의 한 항목은 함수의 한 조각일 수 있다(큰 함수는 조각이 여럿이다) —
// chained unwind 를 뿌리까지 따라간다. 못 찾으면 0.
uint32_t function_root(const Image &im, uint32_t rva)
{
    uint32_t lo = 0, hi = im.pdata_size / 12, entry = 0;                // 항목은 시작 주소순이다
    while (lo < hi) {
        const uint32_t mid = lo + (hi - lo) / 2, e = im.pdata + 12 * mid;
        if (rva < im.u32(e)) {
            hi = mid;
        } else if (rva >= im.u32(e + 4)) {
            lo = mid + 1;
        } else {
            entry = e;
            break;
        }
    }
    if (entry == 0)
        return 0;
    uint32_t begin = im.u32(entry), unwind = im.u32(entry + 8);
    for (int depth = 0; depth < 32; depth++) {
        if (!im.has(unwind, 4))
            return 0;
        if (((im.p[unwind] >> 3) & 4) == 0)                             // UNW_FLAG_CHAININFO 가 없으면 뿌리다
            return begin;
        const uint32_t parent = unwind + 4 + 2 * ((im.p[unwind + 2] + 1u) & ~1u);   // 풀기 코드(짝수 개로 맞춘다) 뒤에 부모 항목
        if (!im.has(parent, 12))
            return 0;
        begin = im.u32(parent);
        unwind = im.u32(parent + 8);
    }
    return 0;
}

// 그 치트 문자열을 쓰는 자리(lea) 뒤 span 바이트 안에서 서명이 맞는 곳. 쓰는 자리가 여럿이면 앞에서부터 본다.
// 문자열이 하나가 아니거나 어디에도 맞지 않으면 0.
uint32_t find_in_cheat(const Image &im, const char *text, uint32_t span, const Pattern &pt)
{
    uint32_t string = 0;
    if (count_string(im, text, &string) != 1)
        return 0;
    for (int s = 0; s < im.count; s++) {
        const Section &sec = im.sections[s];
        if (!sec.code || sec.size < 7)
            continue;
        for (uint32_t rva = sec.rva; rva <= sec.rva + sec.size - 7; rva++)
            if ((im.p[rva] == 0x48 || im.p[rva] == 0x4C) && im.p[rva + 1] == 0x8D && (im.p[rva + 2] & 0xC7) == 0x05
                && target(im, rva, 3, 7) == string) {
                const uint32_t hit = find(im, rva, rva + span, pt);
                if (hit != 0)
                    return hit;
            }
    }
    return 0;
}

const char *search(const uint8_t *image, size_t size, GameAddresses *out)
{
    Image im = {};
    im.p = image;
    im.size = size;
    GameAddresses a = {};
    uint32_t anchor = 0, use = 0, call = 0, at = 0;
    if (image == nullptr || !parse(im))
        return "실행 파일의 머리말을 읽을 수 없습니다";

    // 1. 닻 문자열 → 그것을 쓰는 자리 → 그 자리가 든 함수
    if (count_string(im, "cheat allowcheats", &anchor) != 1)
        return "닻 문자열(cheat allowcheats)이 하나가 아닙니다";
    if (count_lea_to(im, anchor, &use) != 1)
        return "닻 문자열을 쓰는 자리가 하나가 아닙니다";
    if ((a.handler = function_root(im, use)) == 0)
        return "명령 처리 함수의 시작을 찾지 못했습니다";

    // 2. 함수 머리: cmp byte ptr [멀티플레이],0 과 or dword ptr [옵션],40h
    if ((at = find(im, a.handler, a.handler + 0x60, pattern("80 3D ? ? ? ? 00"))) == 0)
        return "함수 머리에 멀티플레이 검사가 없습니다";
    a.multiplayer = target(im, at, 2, 7);
    if ((at = find(im, a.handler, a.handler + 0x60, pattern("83 0D ? ? ? ? 40"))) == 0)
        return "함수 머리에 치트 허용 비트를 세우는 명령이 없습니다";
    a.options = target(im, at, 2, 7);

    // 3. 부르는 곳은 하나이고, 바로 앞에서 lea rcx,[this]
    if (count_calls_to(im, a.handler, &call) != 1)
        return "명령 처리 함수를 부르는 곳이 하나가 아닙니다";
    if (call < 7 || !matches(im, call - 7, pattern("48 8D 0D ? ? ? ?")))
        return "부르는 곳 바로 앞에 this 를 채우는 명령이 없습니다";
    a.context = target(im, call - 7, 3, 7);

    // 4. 부르는 함수의 머리: cmp dword ptr [프로그램 상태],6
    const uint32_t caller = function_root(im, call);
    if (caller == 0 || (at = find(im, caller, caller + 0x40, pattern("83 3D ? ? ? ? 06"))) == 0)
        return "부르는 함수의 머리에 프로그램 상태 검사가 없습니다";
    a.program_state = target(im, at, 2, 7);

    // 5. georgew · georgeww: mov rax,[플레이어 포인터] / movsd xmm0,[rax+…] — 둘이 같은 포인터를 써야 한다
    const Pattern read_pointer = pattern("48 8B 05 ? ? ? ? F2 0F 10 80");
    if ((at = find_in_cheat(im, "cheat georgew", 0x40, read_pointer)) == 0)
        return "cheat georgew 에서 플레이어 포인터를 읽는 명령을 찾지 못했습니다";
    a.player_pointer = target(im, at, 3, 7);
    if ((at = find_in_cheat(im, "cheat georgeww", 0x40, read_pointer)) == 0 || target(im, at, 3, 7) != a.player_pointer)
        return "georgew 와 georgeww 가 같은 플레이어 포인터를 쓰지 않습니다";

    // 6. populate: movsxd rax,[인덱스] / lea r15,[월드] / mov rcx,[r15+rax*8+지역 표]
    if ((at = find_in_cheat(im, "cheat populate", 0x40, pattern("48 63 05 ? ? ? ? 4C 8D 3D ? ? ? ?"))) == 0)
        return "cheat populate 에서 플레이어 인덱스를 읽는 명령을 찾지 못했습니다";
    a.player_index = target(im, at, 3, 7);
    const uint32_t world = target(im, at + 7, 3, 7);
    if ((at = find(im, at, at + 0x40, pattern("49 8B 8C C7 ? ? ? ?"))) == 0)
        return "cheat populate 에서 지역 표를 읽는 명령을 찾지 못했습니다";
    a.region_table = world + im.u32(at + 4);

    // 7. becomeregion: 인덱스를 쓰는 곳이 populate 가 읽는 곳과 같아야 하고, 그 뒤의 훑기에서 지역 수와 지역 표
    if ((at = find_in_cheat(im, "cheat becomeregion", 0x100, pattern("0F B7 4A 04 33 D2 89 0D ? ? ? ? 89 0D ? ? ? ? 48 63 C1"))) == 0)
        return "cheat becomeregion 에서 플레이어 인덱스를 쓰는 명령을 찾지 못했습니다";
    if (target(im, at + 6, 2, 6) != a.player_index)
        return "becomeregion 이 쓰는 곳과 populate 가 읽는 곳이 다릅니다";
    if ((at = find(im, at, at + 0x90, pattern("44 8B 0D ? ? ? ? 45 33 F6 45 85 C9 0F 88 ? ? ? ? 48 8D 0D ? ? ? ?"))) == 0)
        return "지역 수를 읽는 명령을 찾지 못했습니다";
    a.region_count = target(im, at, 3, 7);
    if (target(im, at + 19, 3, 7) != a.region_table)
        return "지역 표의 주소가 두 곳에서 다릅니다";

    // 8. 게임 진입: mov [모드 상태],2 / mov [프로그램 상태],1 — 둘째 주소가 4 에서 얻은 것과 같아야 한다
    if (count_in_code(im, pattern("C7 05 ? ? ? ? 02 00 00 00 C7 05 ? ? ? ? 01 00 00 00"), &at) != 1)
        return "게임 진입에서 상태를 쓰는 자리가 하나가 아닙니다";
    a.mode_state = target(im, at, 2, 10);
    if (target(im, at + 10, 2, 10) != a.program_state)
        return "프로그램 상태의 주소가 두 곳에서 다릅니다";

    const uint32_t all[] = {a.handler, a.context, a.multiplayer, a.options, a.program_state, a.mode_state, a.player_index,
                            a.player_pointer, a.region_table, a.region_count};
    for (uint32_t rva : all)
        if (rva == 0 || !im.has(rva, 8))
            return "찾은 주소가 실행 파일 밖입니다";
    if (!im.has(static_cast<uint64_t>(a.region_table), 8 * 1024))
        return "찾은 주소가 실행 파일 밖입니다";
    *out = a;
    return nullptr;
}

}  // namespace

// 올라와 있는 실행 파일에는 읽을 수 없는 쪽이 있을 수 있다(보호된 구역). 그때도 죽지 않는다 — 여기서 예외가 새면 게임이 뜨다가 죽는다.
// __try 가 든 함수에는 소멸자가 있는 지역 변수를 둘 수 없어 찾는 일(search)과 따로 뗐다.
const char *locate_game(const uint8_t *image, size_t size, GameAddresses *out)
{
    __try {
        return search(image, size, out);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return "실행 파일에 읽을 수 없는 곳이 있습니다";
    }
}
