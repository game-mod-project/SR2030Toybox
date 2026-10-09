#include "game.h"

#include <windows.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <mutex>

#include "features.h"
#include "log.h"

namespace {

const int MAX_REGIONS = 1024;   // 지역 표의 칸 수
const int MAX_NUMBER = 12900;   // 지역 번호의 상한(게임의 번호 → 지역 표가 이 크기다)

std::mutex g_lock;
const uint8_t *g_base;
GameAddresses g_at;
bool g_located, g_told;
void *g_handler;          // 명령 처리 함수
void *g_context;          // 그 첫 인자(게임이 넘기는 것과 같은 전역 객체)
ValueLayout g_layout;     // 값의 자리
bool g_values;            // 그것을 찾았다
char g_values_why[200];   // 못 찾은 까닭
bool g_write_failed;      // 값 쓰기가 실패했다 — 이번 실행에서는 더 쓰지 않는다

typedef void (*Handler)(void *context, const char *line);

bool env_is_zero(const char *name)
{
    char value[8];
    return GetEnvironmentVariableA(name, value, sizeof(value)) == 1 && value[0] == '0';
}

// 탈출구: SRTOYBOX_READ=0 이면 게임을 읽지 않는다 — 1단계처럼 단추가 늘 켜져 있고 글쇠 방식으로 동작한다.
// ToyBox 가 게임 안인데도 "게임 밖"으로 잘못 알아(다른 빌드, 보지 못한 화면) 단추가 꺼진 채 풀리지 않을 때 쓴다.
bool reading_wanted()
{
    static const bool wanted = !env_is_zero("SRTOYBOX_READ");
    return wanted;
}

// 탈출구: SRTOYBOX_WRITE=0 이면 게임의 메모리에 쓰지 않는다(자리는 찾아 로그에 적는다).
bool write_wanted()
{
    static const bool wanted = !env_is_zero("SRTOYBOX_WRITE");
    return wanted;
}

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

// 객체(주소)에서 offset 만큼 떨어진 값 하나.
template <class T>
bool peek_in(uint64_t object, uint64_t offset, T *out)
{
    return peek(reinterpret_cast<const void *>(object + offset), out, sizeof(T));
}

// 읽기 · 쓰기 쪽(PAGE_READWRITE)에 통째로 든 자리인가. WriteProcessMemory 는 실행 쪽(PAGE_EXECUTE_READ)이면 보호를 풀고
// 쓴다 — 낡은 포인터가 코드를 가리켜도 쓰지 않게 먼저 가린다.
bool writable(uint64_t address, size_t size)
{
    MEMORY_BASIC_INFORMATION info;
    if (VirtualQuery(reinterpret_cast<const void *>(address), &info, sizeof(info)) == 0)
        return false;
    const uint64_t end = reinterpret_cast<uint64_t>(info.BaseAddress) + info.RegionSize;
    return info.State == MEM_COMMIT && info.Protect == PAGE_READWRITE && address + size <= end;
}

// 안전한 쓰기: 쓰고, 다시 읽어 그 값인지 본다. 게임이 그 사이에 같은 칸을 고쳤을 수 있으므로 한 번 더 해 본다.
bool poke(uint64_t address, const void *data, size_t size)
{
    uint8_t back[8] = {};
    void *const where = reinterpret_cast<void *>(address);
    if (size > sizeof(back))
        return false;
    for (int attempt = 0; attempt < 2; attempt++) {
        SIZE_T done = 0;
        if (!writable(address, size) || !WriteProcessMemory(GetCurrentProcess(), where, data, size, &done) || done != size)
            return false;
        if (peek(where, back, size) && memcmp(back, data, size) == 0)
            return true;
    }
    return false;
}

// 지역 객체의 머리: +0 상태(dword), +4 자기 인덱스(word), +8 지역 번호(word).
// 상태는 2030 - 세계에서 읽은 분포로 본 것이다 [확인: 실행 / 뜻은 추정]: 0 쓸 수 없다, 1 유엔, 2 사람이 고른 나라,
// 3 AI 가 맡은 나라(223개), 5 이번 판에 없는 지역(서독 · 소련 · 네브래스카 등 128개).
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

// 이번 판에 실제로 있는 나라인가(사람이나 AI 가 맡고 있다). 창의 나라 목록에는 이것만 올린다 —
// 없는 지역에 "이 나라로 플레이" 같은 치트를 넣게 두지 않는다.
bool in_play(const Region &r)
{
    return r.alive == 2 || r.alive == 3;
}

// 게임의 상태와, 진행 중이면 플레이어 지역 객체의 주소(object).
GameState read_player(const uint8_t *base, const GameAddresses &at, uint64_t *object)
{
    GameState s;
    uint8_t multiplayer = 0;
    uint32_t options = 0;
    int32_t program = 0, mode = 0, index = 0, count = 0;
    uint64_t pointer = 0, slot = 0;
    if (base == nullptr || !peek_at(base, at.multiplayer, &multiplayer)
        || (at.options != 0 && !peek_at(base, at.options, &options))
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
    *object = pointer;
    return s;
}

// 이 물자를 이번 판에서 쓰는가: 세계 자료 객체의 그 칸(float)이 0 보다 크다. 읽을 수 없으면 false.
bool slot_used(const uint8_t *base, const ValueLayout &layout, int slot)
{
    uint64_t world = 0;
    float used = 0;
    return peek_at(base, layout.world_pointer, &world) && world != 0
        && peek_in(world, layout.used_first + static_cast<uint64_t>(layout.used_step) * static_cast<uint64_t>(slot), &used)
        && std::isfinite(used) && used > 0.0f;
}

bool located(const uint8_t **base, GameAddresses *at)
{
    std::lock_guard<std::mutex> lock(g_lock);
    *base = g_base;
    *at = g_at;
    return g_located && reading_wanted();
}

// 맞지 않은 서명을 로그에 적는다 — 셋 가운데 둘로 찾았어도, 다음 업데이트에서 깨질 것을 미리 안다.
void log_unmatched(const SigRow *rows, int n)
{
    for (int i = 0; i < n; i++)
        if (rows[i].count != 1)
            log_line("맞지 않은 서명: %s #%d (%s)", rows[i].name, i % STATE_SIGS + 1, rows[i].count == 0 ? "안 맞음" : "여러 번 맞음");
}

// 프로세스의 게임에 값 하나를 쓴다. slot 이 음수면 국고.
Wrote write(int slot, double value)
{
    if (!game_values_off().empty())
        return Wrote::Off;
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    ValueLayout layout = {};
    {
        std::lock_guard<std::mutex> lock(g_lock);
        base = g_base;
        at = g_at;
        layout = g_layout;
    }
    const Wrote wrote = slot < 0 ? write_treasury(base, at, layout, value) : write_stock(base, at, layout, slot, static_cast<float>(value));
    if (wrote == Wrote::Failed) {
        {
            std::lock_guard<std::mutex> lock(g_lock);
            g_write_failed = true;
        }
        if (slot < 0)
            log_line("값 쓰기 실패 (국고) — 값 쓰기를 끕니다");
        else
            log_line("값 쓰기 실패 (재고 칸 %d) — 값 쓰기를 끕니다", slot);
    }
    return wrote;
}

}  // namespace

GameState read_game(const uint8_t *base, const GameAddresses &at)
{
    uint64_t object = 0;
    return read_player(base, at, &object);
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
        if (peek_region(table[static_cast<size_t>(i)], &r) && usable(r, i) && in_play(r))
            out.push_back(r.number);
    }
    std::sort(out.begin(), out.end());
    return out;
}

GameValues read_values(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout)
{
    GameValues v;
    uint64_t object = 0;
    if (!read_player(base, at, &object).in_game || !peek_in(object, layout.treasury, &v.treasury))
        return v;
    for (int i = 0; i < STOCK_SLOTS; i++) {
        const uint64_t slot = layout.stock_first + static_cast<uint64_t>(layout.stock_step) * static_cast<uint64_t>(i);
        if (!peek_in(object, slot, &v.stock[i]) || !std::isfinite(v.stock[i]))
            return v;   // 재고 칸이 수가 아니면 구조가 바뀐 것일 수 있다 — 모르는 것으로 친다(쓰지 않는 물자의 칸이어도)
    }
    uint64_t world = 0;
    float probe = 0;
    if (!peek_at(base, layout.world_pointer, &world) || world == 0 || !peek_in(world, layout.used_first, &probe))
        return v;       // 세계 자료를 읽을 수 없다 — 어느 물자를 쓰는지 모른다
    for (int i = 0; i < STOCK_SLOTS; i++)
        v.used[i] = slot_used(base, layout, i);
    v.ok = true;
    return v;
}

Wrote write_treasury(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout, double value)
{
    uint64_t object = 0;
    if (!std::isfinite(value))
        return Wrote::BadValue;
    const GameState s = read_player(base, at, &object);
    if (!s.in_game || s.multiplayer)
        return Wrote::NotInGame;
    return poke(object + layout.treasury, &value, sizeof(value)) ? Wrote::Done : Wrote::Failed;
}

Wrote write_stock(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout, int slot, float value)
{
    uint64_t object = 0;
    if (slot < 0 || slot >= STOCK_SLOTS || !std::isfinite(value) || value < 0.0f)
        return Wrote::BadValue;
    const GameState s = read_player(base, at, &object);
    if (!s.in_game || s.multiplayer)
        return Wrote::NotInGame;
    if (!slot_used(base, layout, slot))
        return Wrote::NotUsed;
    const uint64_t where = object + layout.stock_first + static_cast<uint64_t>(layout.stock_step) * static_cast<uint64_t>(slot);
    return poke(where, &value, sizeof(value)) ? Wrote::Done : Wrote::Failed;
}

void game_init()
{
    if (!reading_wanted()) {
        log_line("게임 상태를 읽지 않습니다 (SRTOYBOX_READ=0) — 글쇠 방식");
        return;
    }
    const uint8_t *base = reinterpret_cast<const uint8_t *>(GetModuleHandleW(nullptr));
    const IMAGE_DOS_HEADER *dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(base);
    const IMAGE_NT_HEADERS64 *nt = reinterpret_cast<const IMAGE_NT_HEADERS64 *>(base + dos->e_lfanew);
    game_init_from(base, nt->OptionalHeader.SizeOfImage);
}

void game_init_from(const uint8_t *base, size_t size)
{
    // 새 찾기: 게임 상태를 읽는 전역 일곱 — 내장 치트와 무관한 서명으로
    GameAddresses at = {};
    SigRow rows[STATE_WANTED * STATE_SIGS];
    char why[160] = "";
    const ULONGLONG started = GetTickCount64();
    const bool state = locate_state(base, size, &at, rows, why, sizeof(why));
    int matched = 0;
    for (const SigRow &row : rows)
        matched += row.count == 1 ? 1 : 0;

    // 새 찾기: 값을 읽고 쓰는 자리 — 같은 규칙의 서명으로. 상태를 읽지 못하면 값도 쓰지 않으므로 찾지 않는다
    ValueLayout layout = {};
    SigRow value_rows[VALUE_WANTED * STATE_SIGS];
    char value_why[160] = "";
    const bool values = state && locate_values(base, size, &layout, value_rows, value_why, sizeof(value_why));
    const unsigned long long took = GetTickCount64() - started;

    // 옛 찾기(전환 기간에만): 아직 내장 치트로 도는 기능의 직접 실행이 쓴다. 상태를 읽지 못하면 그 기능들도 글쇠 방식이라 찾지 않는다
    const char *legacy = state ? locate_legacy(base, size, &at) : "게임 상태를 읽지 못했습니다";
    const bool can_call = state && legacy == nullptr;
    {
        std::lock_guard<std::mutex> lock(g_lock);
        g_base = base;
        g_at = at;
        g_located = state;
        g_told = false;
        g_handler = can_call ? const_cast<uint8_t *>(base) + at.handler : nullptr;
        g_context = can_call ? const_cast<uint8_t *>(base) + at.context : nullptr;
        g_layout = layout;
        g_values = values;
        g_write_failed = false;
        snprintf(g_values_why, sizeof(g_values_why), "%s", value_why);
    }
    if (!state) {
        log_line("게임 상태를 읽을 수 없습니다 (%s) — 글쇠 방식", why);
        return;
    }
    log_line("게임 상태를 읽습니다 (서명 %d개 가운데 %d개, %llu ms)", STATE_WANTED * STATE_SIGS, matched, took);
    log_unmatched(rows, STATE_WANTED * STATE_SIGS);
    if (!values) {
        log_line("값을 쓸 수 없습니다 (%s)", value_why);
    } else {
        if (write_wanted())
            log_line("값을 씁니다 (국고 +0x%X, 재고 +0x%X 간격 0x%X × %d)", layout.treasury, layout.stock_first, layout.stock_step,
                     STOCK_SLOTS);
        else
            log_line("값을 쓰지 않습니다 (SRTOYBOX_WRITE=0. 국고 +0x%X, 재고 +0x%X 간격 0x%X × %d)", layout.treasury,
                     layout.stock_first, layout.stock_step, STOCK_SLOTS);
        log_unmatched(value_rows, VALUE_WANTED * STATE_SIGS);
    }
    if (can_call)
        log_line("옛 방식(내장 치트)으로 도는 기능이 %d개 남아 있습니다 (명령 처리 함수 +0x%X)", FEATURE_COUNT, at.handler);
    else
        log_line("명령 처리 함수를 찾지 못했습니다 (%s) — 내장 치트로 도는 기능은 글쇠 방식", legacy);
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

bool game_reads()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_located && reading_wanted();
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
    g_layout = ValueLayout();
    g_values = false;
    g_write_failed = false;
    snprintf(g_values_why, sizeof(g_values_why), "값의 자리를 주지 않았습니다");
}

void game_set_values_for_test(const ValueLayout *layout)
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_layout = layout != nullptr ? *layout : ValueLayout();
    g_values = layout != nullptr;
    g_write_failed = false;
}

bool game_can_call()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_located && g_handler != nullptr && reading_wanted();
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

std::string game_values_off()
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (!g_located || !reading_wanted())
        return "게임 상태를 읽을 수 있을 때만 씁니다.";
    if (!g_values)
        return std::string("이 게임 판에서는 쓸 수 없습니다 (") + g_values_why + ")";
    if (!write_wanted())
        return "값 쓰기를 껐습니다 (SRTOYBOX_WRITE=0)";
    if (g_write_failed)
        return "값 쓰기가 실패해 껐습니다. 게임을 다시 시작하면 다시 시도합니다.";
    return std::string();
}

GameValues game_values()
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    ValueLayout layout = {};
    {
        std::lock_guard<std::mutex> lock(g_lock);
        if (!g_located || !g_values || !reading_wanted())
            return GameValues();
        base = g_base;
        at = g_at;
        layout = g_layout;
    }
    return read_values(base, at, layout);
}

Wrote game_write_treasury(double value)
{
    return write(-1, value);
}

Wrote game_write_stock(int slot, float value)
{
    return slot < 0 ? Wrote::BadValue : write(slot, value);
}
