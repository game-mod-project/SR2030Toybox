#include "locate.h"

#include <excpt.h>

#include <cstdio>
#include <cstring>

#include "sigs.h"

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

// 옛 찾기: 닻 문자열 → 그것을 쓰는 자리 → 그 자리가 든 함수(명령 처리 함수) → 머리의 옵션 묶음, 부르는 곳의 this.
// 상태 전역(멀티플레이 표시 · 플레이어 · 지역 표 …)은 여기서 읽지 않는다 — 새 찾기(search_state)의 일이다.
const char *search_legacy(const uint8_t *image, size_t size, GameAddresses *out)
{
    Image im = {};
    im.p = image;
    im.size = size;
    GameAddresses a = *out;
    uint32_t anchor = 0, use = 0, call = 0, at = 0;
    if (image == nullptr || !parse(im))
        return "실행 파일의 머리말을 읽을 수 없습니다";

    if (count_string(im, "cheat allowcheats", &anchor) != 1)
        return "닻 문자열(cheat allowcheats)이 하나가 아닙니다";
    if (count_lea_to(im, anchor, &use) != 1)
        return "닻 문자열을 쓰는 자리가 하나가 아닙니다";
    if ((a.handler = function_root(im, use)) == 0)
        return "명령 처리 함수의 시작을 찾지 못했습니다";

    // 함수 머리: or dword ptr [옵션],40h
    if ((at = find(im, a.handler, a.handler + 0x60, pattern("83 0D ? ? ? ? 40"))) == 0)
        return "함수 머리에 치트 허용 비트를 세우는 명령이 없습니다";
    a.options = target(im, at, 2, 7);

    // 부르는 곳은 하나이고, 바로 앞에서 lea rcx,[this]
    if (count_calls_to(im, a.handler, &call) != 1)
        return "명령 처리 함수를 부르는 곳이 하나가 아닙니다";
    if (call < 7 || !matches(im, call - 7, pattern("48 8D 0D ? ? ? ?")))
        return "부르는 곳 바로 앞에 this 를 채우는 명령이 없습니다";
    a.context = target(im, call - 7, 3, 7);

    const uint32_t all[] = {a.handler, a.context, a.options};
    for (uint32_t rva : all)
        if (rva == 0 || !im.has(rva, 8))
            return "찾은 주소가 실행 파일 밖입니다";
    *out = a;
    return nullptr;
}

// 게임 상태를 읽는 데 쓰는 전역 일곱. 서명은 모두 치트 명령 처리 함수 밖의 코드에서 뽑았다(uv run srkit sig-mine <RVA>):
// build 21347933 에서 저마다 실행 구역에 한 번만 맞고, 찾을 것마다 세 서명이 서로 다른 함수에 있다(docs/11-game-internals.md).
// 프로그램 상태와 모드 상태의 셋째 서명은 같은 자리(게임 진입의 mov [모드 상태],2 / mov [프로그램 상태],1)를 읽는다.
const struct Wanted {
    const char *name;                       // GameAddresses 의 필드 이름(srkit locate 와 테스트가 본다)
    const char *label;                      // 로그에 나오는 이름
    uint32_t GameAddresses::*field;
    uint32_t bytes;                         // 그 주소에서 이만큼은 실행 파일 안이어야 한다
    const char *sigs[STATE_SIGS];
} STATE[STATE_WANTED] = {
    {"multiplayer", "멀티플레이 표시", &GameAddresses::multiplayer, 1,
     {"80 3D [rip+1] 00 74 18 8B 47 3C", "80 3D [rip+1] 00 0F B6 FA 74 47", "80 3D [rip+1] 00 74 13 8B 41 14"}},
    {"program_state", "프로그램 상태", &GameAddresses::program_state, 4,
     {"83 3D [rip+1] 01 75 08 48 8B CB", "83 3D [rip+1] 06 48 8B F2 4C 8B F9",
      "C7 05 ? ? ? ? 02 00 00 00 C7 05 [rip+4] 01 00 00 00"}},
    {"mode_state", "모드 상태", &GameAddresses::mode_state, 4,
     {"83 3D [rip+1] 02 48 8B D9 75 40", "83 3D [rip+1] 00 48 8B D9 75 21",
      "C7 05 [rip+4] 02 00 00 00 C7 05 ? ? ? ? 01 00 00 00"}},
    {"player_index", "플레이어 인덱스", &GameAddresses::player_index, 4,
     {"44 3B 05 [rip] 49 63 C8 74 16", "44 8B 35 [rip] 45 84 ED 74 05", "44 8B 0D [rip] 45 33 C0 33 D2"}},
    {"player_pointer", "플레이어 포인터", &GameAddresses::player_pointer, 8,
     {"48 8B 15 [rip] 8B 42 6C 85 C0", "48 8B 0D [rip] 48 85 C9 74 58", "4C 8B 35 [rip] FF C7 3B 7D 38"}},
    {"region_table", "지역 표", &GameAddresses::region_table, 8 * 1024,
     {"4C 8D 05 [rip] 49 8B 10 48 85 D2", "48 8D 0D [rip] 90 48 8B 31 48 85 F6", "48 8D 0D [rip] 48 8B 0C C1 48 85 C9"}},
    {"region_count", "지역 수", &GameAddresses::region_count, 4,
     {"44 8B 35 [rip] 44 8B DF 8B D6", "44 8B 0D [rip] 8B D7 45 85 C9", "44 8B 15 [rip] 43 8D 04 0C 99"}},
};

bool search_state(const uint8_t *image, size_t size, GameAddresses *out, SigRow *rows, char *why, size_t why_size)
{
    const int total = STATE_WANTED * STATE_SIGS;
    Image im = {};
    im.p = image;
    im.size = size;
    if (image == nullptr || !parse(im)) {
        snprintf(why, why_size, "실행 파일의 머리말을 읽을 수 없습니다");
        return false;
    }
    SigRange ranges[32];
    int range_count = 0;
    for (int s = 0; s < im.count; s++)
        if (im.sections[s].code) {
            ranges[range_count].begin = im.sections[s].rva;
            ranges[range_count].end = im.sections[s].rva + im.sections[s].size;
            range_count++;
        }
    Sig sigs[STATE_WANTED * STATE_SIGS];
    SigHit hits[STATE_WANTED * STATE_SIGS];
    for (int i = 0; i < total; i++)
        if (!sig_parse(STATE[i / STATE_SIGS].sigs[i % STATE_SIGS], &sigs[i])) {
            snprintf(why, why_size, "서명 표가 틀렸습니다 (%s)", STATE[i / STATE_SIGS].name);
            return false;
        }
    sig_scan(image, size, ranges, range_count, sigs, total, hits);
    if (rows != nullptr)
        for (int i = 0; i < total; i++) {
            rows[i].count = hits[i].count;
            rows[i].at = hits[i].at;
            rows[i].value = static_cast<uint32_t>(hits[i].value[0]);
        }
    GameAddresses found = *out;
    for (int w = 0; w < STATE_WANTED; w++) {
        uint64_t value[SIG_CAPTURES] = {};
        int matched = 0;
        if (!sig_vote(sigs + w * STATE_SIGS, hits + w * STATE_SIGS, STATE_SIGS, STATE_NEED, value, &matched)) {
            if (matched >= STATE_NEED)
                snprintf(why, why_size, "%s: 서명들이 서로 다른 주소를 냅니다", STATE[w].label);
            else
                snprintf(why, why_size, "%s: 서명 %d개 가운데 %d개", STATE[w].label, STATE_SIGS, matched);
            return false;
        }
        if (value[0] == 0 || value[0] >= size || !im.has(value[0], STATE[w].bytes)) {
            snprintf(why, why_size, "%s: 찾은 주소가 실행 파일 밖입니다", STATE[w].label);
            return false;
        }
        found.*(STATE[w].field) = static_cast<uint32_t>(value[0]);
    }
    *out = found;
    snprintf(why, why_size, "%s", "");
    return true;
}

}  // namespace

// 올라와 있는 실행 파일에는 읽을 수 없는 쪽이 있을 수 있다(보호된 구역). 그때도 죽지 않는다 — 여기서 예외가 새면 게임이 뜨다가 죽는다.
// __try 가 든 함수에는 소멸자가 있는 지역 변수를 둘 수 없어 찾는 일(search_legacy · search_state)과 따로 뗐다.
const char *locate_legacy(const uint8_t *image, size_t size, GameAddresses *out)
{
    __try {
        return search_legacy(image, size, out);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return "실행 파일에 읽을 수 없는 곳이 있습니다";
    }
}

// 서명을 맞추다 읽을 수 없는 쪽을 만나도 죽지 않는다(locate_legacy 와 같은 까닭). rows 의 이름과 글은 찾기 전에 채운다 —
// 머리말조차 못 읽은 이미지에서도 서명 표를 볼 수 있다(테스트와 srkit locate 가 쓴다).
bool locate_state(const uint8_t *image, size_t size, GameAddresses *out, SigRow *rows, char *why, size_t why_size)
{
    if (rows != nullptr)
        for (int i = 0; i < STATE_WANTED * STATE_SIGS; i++) {
            rows[i].name = STATE[i / STATE_SIGS].name;
            rows[i].text = STATE[i / STATE_SIGS].sigs[i % STATE_SIGS];
            rows[i].count = 0;
            rows[i].at = 0;
            rows[i].value = 0;
        }
    __try {
        return search_state(image, size, out, rows, why, why_size);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        snprintf(why, why_size, "실행 파일에 읽을 수 없는 곳이 있습니다");
        return false;
    }
}

uint32_t locate_function_root(const uint8_t *image, size_t size, uint32_t rva)
{
    __try {
        Image im = {};
        im.p = image;
        im.size = size;
        return image != nullptr && parse(im) ? function_root(im, rva) : 0;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        return 0;
    }
}
