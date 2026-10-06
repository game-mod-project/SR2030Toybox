#include "game.h"

#include <windows.h>

#include <algorithm>
#include <cstring>
#include <mutex>

#include "log.h"

namespace {

const int MAX_REGIONS = 1024;   // 지역 표의 칸 수
const int MAX_NUMBER = 12900;   // 지역 번호의 상한(게임의 번호 → 지역 표가 이 크기다)

std::mutex g_lock;
const uint8_t *g_base;
GameAddresses g_at;
bool g_located, g_told;
void *g_handler;    // 명령 처리 함수
void *g_context;    // 그 첫 인자(게임이 넘기는 것과 같은 전역 객체)

typedef void (*Handler)(void *context, const char *line);

// 구조적 예외(잘못된 주소 접근 등)를 잡는다. __try 가 든 함수에는 소멸자가 있는 지역 변수를 둘 수 없어 따로 뗐다.
bool guarded_call(Handler handler, void *context, const char *line, unsigned long *code)
{
    __try {
        handler(context, line);
        return true;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        *code = GetExceptionCode();
        return false;
    }
}

// 안전한 읽기: 낡은 포인터를 만나도 죽지 않는다.
bool peek(const void *address, void *out, size_t size)
{
    SIZE_T got = 0;
    return ReadProcessMemory(GetCurrentProcess(), address, out, size, &got) != 0 && got == size;
}

// base 에서 offset 만큼 떨어진 값 하나.
template <class T>
bool peek_at(const uint8_t *base, uint64_t offset, T *out)
{
    return peek(base + offset, out, sizeof(T));
}

// 지역 객체의 머리: +0 살아 있는가(dword), +4 자기 인덱스(word), +8 지역 번호(word)
struct Region {
    uint32_t alive;
    int index, number;
};

bool peek_region(uint64_t pointer, Region *out)
{
    uint8_t raw[10];
    uint16_t index = 0, number = 0;
    if (pointer == 0 || !peek(reinterpret_cast<const void *>(pointer), raw, sizeof(raw)))
        return false;
    memcpy(&out->alive, raw, 4);
    memcpy(&index, raw + 4, 2);
    memcpy(&number, raw + 8, 2);
    out->index = index;
    out->number = number;
    return true;
}

bool usable(const Region &r, int index)
{
    return r.alive != 0 && r.index == index && r.number > 0 && r.number < MAX_NUMBER;
}

bool located(const uint8_t **base, GameAddresses *at)
{
    std::lock_guard<std::mutex> lock(g_lock);
    *base = g_base;
    *at = g_at;
    return g_located;
}

}  // namespace

GameState read_game(const uint8_t *base, const GameAddresses &at)
{
    GameState s;
    uint8_t multiplayer = 0;
    uint32_t options = 0;
    int32_t program = 0, mode = 0, index = 0, count = 0;
    uint64_t pointer = 0, slot = 0;
    if (base == nullptr || !peek_at(base, at.multiplayer, &multiplayer) || !peek_at(base, at.options, &options)
        || !peek_at(base, at.program_state, &program) || !peek_at(base, at.mode_state, &mode)
        || !peek_at(base, at.player_index, &index) || !peek_at(base, at.player_pointer, &pointer)
        || !peek_at(base, at.region_count, &count))
        return s;
    s.known = true;
    s.multiplayer = multiplayer != 0;
    s.cheats_on = (options & 0x40) != 0;
    if (mode != 2 || program != 1 || pointer == 0)
        return s;   // 게임 밖(메뉴 · 로비). 인덱스는 낡은 값이 남으므로 보지 않는다

    // 게임 안이라면 읽은 값들이 서로 맞아야 한다. 안 맞으면 구조가 바뀐 빌드일 수 있다 — 모르는 것으로 친다
    Region player = {};
    if (index < 1 || index >= MAX_REGIONS || count < 1 || count >= MAX_REGIONS
        || !peek_at(base, at.region_table + 8ull * static_cast<uint64_t>(index), &slot) || slot != pointer
        || !peek_region(pointer, &player) || !usable(player, index)) {
        s.known = false;
        return s;
    }
    s.in_game = true;
    s.player = player.number;
    return s;
}

std::vector<int> read_regions(const uint8_t *base, const GameAddresses &at)
{
    std::vector<int> out;
    int32_t count = 0;
    if (!read_game(base, at).in_game || !peek_at(base, at.region_count, &count) || count < 1 || count >= MAX_REGIONS)
        return out;   // 지역 수는 방금 다시 읽은 값이다 — 그 사이에 바뀌었을 수 있다
    std::vector<uint64_t> table(static_cast<size_t>(count) + 1);
    if (!peek(base + at.region_table, table.data(), table.size() * sizeof(uint64_t)))
        return out;
    for (int i = 1; i <= count; i++) {
        Region r = {};
        if (peek_region(table[static_cast<size_t>(i)], &r) && usable(r, i))
            out.push_back(r.number);
    }
    std::sort(out.begin(), out.end());
    return out;
}

void game_init()
{
    const uint8_t *base = reinterpret_cast<const uint8_t *>(GetModuleHandleW(nullptr));
    const IMAGE_DOS_HEADER *dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(base);
    const IMAGE_NT_HEADERS64 *nt = reinterpret_cast<const IMAGE_NT_HEADERS64 *>(base + dos->e_lfanew);
    GameAddresses at = {};
    const char *why = locate_game(base, nt->OptionalHeader.SizeOfImage, &at);
    {
        std::lock_guard<std::mutex> lock(g_lock);
        g_base = base;
        g_at = at;
        g_located = why == nullptr;
        g_told = false;
        g_handler = why == nullptr ? const_cast<uint8_t *>(base) + at.handler : nullptr;
        g_context = why == nullptr ? const_cast<uint8_t *>(base) + at.context : nullptr;
    }
    if (why == nullptr)
        log_line("게임 상태를 읽습니다 (명령 처리 함수 +0x%X)", at.handler);
    else
        log_line("게임 상태를 읽을 수 없습니다 (%s) — 글쇠 방식", why);
}

GameState game_state()
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    if (!located(&base, &at))
        return GameState();
    const GameState s = read_game(base, at);
    if (!s.known) {
        std::lock_guard<std::mutex> lock(g_lock);
        if (!g_told) {
            g_told = true;
            log_line("게임에서 읽은 값이 서로 맞지 않습니다 — 글쇠 방식");
        }
    }
    return s;
}

std::vector<int> game_regions()
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    return located(&base, &at) ? read_regions(base, at) : std::vector<int>();
}

void game_set_for_test(const uint8_t *base, const GameAddresses *at, void *handler)
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_base = base;
    g_at = at != nullptr ? *at : GameAddresses();
    g_located = base != nullptr && at != nullptr;
    g_told = false;
    g_handler = g_located ? handler : nullptr;
    g_context = g_located ? const_cast<uint8_t *>(base) + g_at.context : nullptr;
}

bool game_can_call()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_located && g_handler != nullptr;
}

bool game_call(const char *line, unsigned long *code)
{
    Handler handler = nullptr;
    void *context = nullptr;
    {
        std::lock_guard<std::mutex> lock(g_lock);
        handler = reinterpret_cast<Handler>(g_handler);
        context = g_context;
    }
    *code = 0;
    return handler != nullptr && guarded_call(handler, context, line, code);
}
