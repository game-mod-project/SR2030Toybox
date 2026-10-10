#include "game.h"

#include <windows.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <mutex>

#include "features.h"
#include "log.h"
#include "products.h"
#include "regions.h"

namespace {

const int MAX_REGIONS = 1024;   // 지역 표의 칸 수
const int MAX_NUMBER = 12900;   // 지역 번호의 상한(게임의 번호 → 지역 표가 이 크기다)
const int MAX_ITEMS = 65536;    // 기술 · 부대 설계 표의 자리 수의 상한(선행의 번호가 16비트다)
const int MAX_NODES = 4096;     // 지역 하나의 연구 목록에서 따라가는 노드의 상한
const char *const NOT_PLAYING = "게임이 진행 중이 아닙니다";

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
MoreLayout g_more;        // 더 쓰는 값의 자리(못 찾은 묶음의 것은 0)
int g_more_groups;        // 찾은 묶음의 비트
char g_more_why[MORE_GROUPS][MORE_WHY];   // 묶음마다 못 찾은 까닭
ResearchLayout g_research;    // 연구의 자리
bool g_research_found;        // 그것을 찾았다
char g_research_why[200];     // 못 찾은 까닭
void *g_recompute;            // 게임의 "지역의 효과를 다시 셈"

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

// 게임의 "지역의 효과를 다시 셈"을 부른다. 예외는 잡아 code 에 적는다.
bool guarded_recompute(Recompute recompute, void *world, int index, unsigned long *code)
{
    __try {
        recompute(world, index);
        return true;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        *code = GetExceptionCode();
        return false;
    }
}

// 그 주소가 프로세스 힙에서 받은 size 바이트짜리 블록인가. 게임이 보유 묶음을 받는 힙이 ToyBox 가 받을 힙과 같은지 볼 때 쓴다 —
// 다른 힙의 블록을 걸면 게임이 그것을 풀 때 깨진다. 힙의 블록이 아닌 주소를 넘겨도 죽지 않게 예외를 잡는다.
bool heap_block(uint64_t address, size_t size)
{
    __try {
        const HANDLE heap = GetProcessHeap();
        void *const block = reinterpret_cast<void *>(address);
        return HeapValidate(heap, 0, block) != 0 && HeapSize(heap, 0, block) == size;
    } __except (EXCEPTION_EXECUTE_HANDLER) {
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

// 칸(1바이트나 4바이트)의 비트들만 켜거나 끈다 — 원자적으로. 그 칸의 다른 비트는 읽어서 되쓰지 않으므로, 그 순간 게임이 그것들을
// 바꿔도 덮어쓰지 않는다(보유 묶음의 한 바이트에는 여덟 나라의 비트가 함께 있다). 쓴 뒤 그 비트들을 다시 읽어 본다(아니면 한 번 더).
bool poke_bits(uint64_t address, uint32_t mask, bool on, size_t size)
{
    for (int attempt = 0; attempt < 2; attempt++) {
        if (!writable(address, size))
            return false;
        __try {
            if (size == 1 && on)
                InterlockedOr8(reinterpret_cast<char *>(address), static_cast<char>(mask));
            else if (size == 1)
                InterlockedAnd8(reinterpret_cast<char *>(address), static_cast<char>(~mask));
            else if (on)
                InterlockedOr(reinterpret_cast<LONG *>(address), static_cast<LONG>(mask));
            else
                InterlockedAnd(reinterpret_cast<LONG *>(address), static_cast<LONG>(~mask));
        } __except (EXCEPTION_EXECUTE_HANDLER) {
            return false;
        }
        uint32_t back = 0;
        if (peek(reinterpret_cast<const void *>(address), &back, size) && (back & mask) == (on ? mask : 0u))
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
void log_unmatched(const SigRow &row, int number)
{
    if (row.count != 1)
        log_line("맞지 않은 서명: %s #%d (%s)", row.name, number, row.count == 0 ? "안 맞음" : "여러 번 맞음");
}

void log_unmatched(const SigRow *rows, int n)
{
    for (int i = 0; i < n; i++)
        log_unmatched(rows[i], i % STATE_SIGS + 1);
}

// 그 번호의 나라(이번 판에 실제로 있는 것)의 객체와 인덱스. 없으면 false.
bool find_region(const uint8_t *base, const GameAddresses &at, int number, uint64_t *object, int *index)
{
    int32_t count = 0;
    if (number <= 0 || !peek_at(base, at.region_count, &count) || count < 1 || count >= MAX_REGIONS)
        return false;
    std::vector<uint64_t> table(static_cast<size_t>(count) + 1);
    if (!peek(base + at.region_table, table.data(), table.size() * sizeof(uint64_t)))
        return false;
    for (int i = 1; i <= count; i++) {
        Region r = {};
        if (peek_region(table[static_cast<size_t>(i)], &r) && usable(r, i) && in_play(r) && r.number == number) {
            *object = table[static_cast<size_t>(i)];
            *index = i;
            return true;
        }
    }
    return false;
}

// 플레이어와 그 번호의 나라: 두 객체의 주소와 인덱스. 판정은 Wrote 로(Done 이면 넷을 채웠다).
Wrote find_pair(const uint8_t *base, const GameAddresses &at, int number, bool writing, uint64_t *mine, int *me, uint64_t *theirs,
                int *them)
{
    int32_t index = 0;
    const GameState s = read_player(base, at, mine);
    if (!s.in_game || (writing && s.multiplayer) || !peek_at(base, at.player_index, &index) || index < 1 || index >= MAX_REGIONS)
        return Wrote::NotInGame;
    *me = index;
    if (number == s.player || !find_region(base, at, number, theirs, them))
        return Wrote::NoTarget;
    return Wrote::Done;
}

// 한 나라와의 관계가 놓인 여섯 칸의 주소: [0 … 2] 플레이어 객체의 그 나라 칸(관계 표 둘 · 전쟁 명분), [3 … 5] 그 나라 객체의 플레이어 칸.
void relation_cells(const MoreLayout &more, uint64_t mine, int me, uint64_t theirs, int them, uint64_t *cells)
{
    const uint32_t tables[3] = {more.relation[0], more.relation[1], more.casus};
    for (int i = 0; i < 3; i++) {
        cells[i] = mine + tables[i] + 4ull * static_cast<uint64_t>(them);
        cells[3 + i] = theirs + tables[i] + 4ull * static_cast<uint64_t>(me);
    }
}

// float 여러 칸을 쓴다. 쓰기 전에 모든 칸이 읽기 · 쓰기 쪽인지 본다 — 반쪽만 쓰고 멈추는 일을 줄인다. done 에 쓴 칸의 수.
Wrote poke_floats(const uint64_t *cells, const float *values, int n, int *done)
{
    *done = 0;
    for (int i = 0; i < n; i++)
        if (!writable(cells[i], sizeof(float)))
            return Wrote::Failed;
    for (int i = 0; i < n; i++) {
        if (!poke(cells[i], &values[i], sizeof(float)))
            return Wrote::Failed;
        ++*done;
    }
    return Wrote::Done;
}

// 값을 쓸 수 없는 까닭(found: 그 묶음의 자리를 찾았는가, why: 못 찾은 까닭). g_lock 을 쥔 채로 부른다.
std::string off_text(bool found, const char *why)
{
    if (!g_located || !reading_wanted())
        return "게임 상태를 읽을 수 있을 때만 씁니다.";
    if (!found)
        return std::string("이 게임 판에서는 쓸 수 없습니다 (") + why + ")";
    if (!write_wanted())
        return "값 쓰기를 껐습니다 (SRTOYBOX_WRITE=0)";
    if (g_write_failed)
        return "값 쓰기가 실패해 껐습니다. 게임을 다시 시작하면 다시 시도합니다.";
    return std::string();
}

// 묶음의 비트 → 까닭이 든 줄(0 지식, 1 여론, 2 관계). 묶음이 아니면 -1.
int more_index(int group)
{
    return group == MORE_TECH ? 0 : group == MORE_OPINION ? 1 : group == MORE_RELATIONS ? 2 : -1;
}

// 지금의 "게임"과 더 쓰는 값의 자리. 그 묶음을 쓸 수 없으면 false.
bool more_ready(int group, const uint8_t **base, GameAddresses *at, MoreLayout *more)
{
    if (!game_more_off(group).empty())
        return false;
    std::lock_guard<std::mutex> lock(g_lock);
    *base = g_base;
    *at = g_at;
    *more = g_more;
    return true;
}

// 더 쓰는 값의 쓰기가 실패했다: 이번 실행에서는 값 쓰기 전체를 끄고 로그에 적는다.
Wrote write_failed(const std::string &what, int cells, int done)
{
    {
        std::lock_guard<std::mutex> lock(g_lock);
        g_write_failed = true;
    }
    if (done > 0)
        log_line("값 쓰기 실패 (%s, %d칸 가운데 %d칸을 쓴 뒤) — 값 쓰기를 끕니다", what.c_str(), cells, done);
    else
        log_line("값 쓰기 실패 (%s) — 값 쓰기를 끕니다", what.c_str());
    return Wrote::Failed;
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
        log_line("값 쓰기 실패 (%s) — 값 쓰기를 끕니다", slot < 0 ? "국고" : product_label(slot).c_str());
    }
    return wrote;
}

// 연구의 스냅숏과, 그것을 쓸 때 필요한 주소들.
struct Shot {
    ResearchTables tables;
    std::vector<uint64_t> tech_owners, design_owners;   // tables 의 행과 같은 순서: 보유 묶음의 주소(없으면 0)
    std::vector<uint64_t> tech_cells, design_cells;     // 〃 레코드에서 그 포인터가 든 칸의 주소
    std::vector<uint64_t> nodes;                        // tables.queue 와 같은 순서: 노드의 주소
    uint64_t world = 0;                                 // 세계 객체의 주소
    int me = 0;                                         // 플레이어의 인덱스
    bool multiplayer = false;
};

// 레코드의 한 칸.
template <class T>
T field(const uint8_t *record, uint32_t offset)
{
    T value;
    memcpy(&value, record + offset, sizeof(T));
    return value;
}

// 보유 묶음에서 플레이어(me)와 고른 나라(them. 없으면 0)의 비트, 그리고 플레이어를 뺀 보유 나라의 수. 묶음이 없으면(0) 아무도 없다.
bool owners_of(uint64_t owners, int me, int them, bool *mine, bool *picked, int *others)
{
    *mine = *picked = false;
    *others = 0;
    if (owners == 0)
        return true;
    uint8_t bits[OWNERS_BYTES];
    if (!peek(reinterpret_cast<const void *>(owners), bits, sizeof(bits)))
        return false;
    int count = 0;
    for (uint8_t byte : bits)
        for (; byte != 0; byte = static_cast<uint8_t>(byte & (byte - 1)))
            count++;
    *mine = (bits[me / 8] >> (me % 8) & 1) != 0;
    *picked = them > 0 && (bits[them / 8] >> (them % 8) & 1) != 0;
    *others = count - (*mine ? 1 : 0);
    return true;
}

// 표 둘과 플레이어의 연구 목록을 읽는다. 게임을 진행 중이 아니면 why 는 NOT_PLAYING 이다(멀티플레이는 진행 중으로 읽고 표시만 한다).
bool shoot(const uint8_t *base, const GameAddresses &at, const ResearchLayout &r, int picked, Shot *shot, std::string *why)
{
    uint64_t player = 0, other = 0, tech_table = 0, design_table = 0, node = 0;
    int32_t me = 0, tech_count = 0, design_count = 0;
    int them = 0;
    const GameState s = read_player(base, at, &player);
    if (!s.in_game || !peek_at(base, at.player_index, &me) || me < 1 || me >= MAX_REGIONS) {
        *why = NOT_PLAYING;
        return false;
    }
    if (picked > 0 && picked != s.player && !find_region(base, at, picked, &other, &them))
        them = 0;
    if (!peek_at(base, r.tech_count, &tech_count) || !peek_at(base, r.design_count, &design_count)
        || !peek_at(base, r.tech_table, &tech_table) || !peek_at(base, r.design_table, &design_table)) {
        *why = "표의 전역을 읽을 수 없습니다";
        return false;
    }
    if (tech_count < 2 || tech_count > MAX_ITEMS || design_count < 2 || design_count > MAX_ITEMS || tech_table == 0 || design_table == 0) {
        *why = "표가 없거나 자리 수가 범위 밖입니다";
        return false;
    }
    shot->me = me;
    shot->multiplayer = s.multiplayer;
    shot->world = reinterpret_cast<uint64_t>(base) + r.world;
    ResearchTables &t = shot->tables;
    t.tech_slots = tech_count;
    t.design_slots = design_count;

    std::vector<uint8_t> raw(static_cast<size_t>(tech_count) * TECH_SIZE);
    if (!peek(reinterpret_cast<const void *>(tech_table), raw.data(), raw.size())) {
        *why = "기술 표를 읽을 수 없습니다";
        return false;
    }
    for (int i = 1; i < tech_count; i++) {
        const uint8_t *record = raw.data() + static_cast<size_t>(i) * TECH_SIZE;
        if (record[TECH_KIND] == 0)
            continue;                           // 빈 자리
        TechRow row;
        row.id = i;
        row.kind = record[TECH_KIND];
        row.level = record[TECH_LEVEL];
        for (int n = 0; n < TECH_NEED_COUNT; n++)
            row.needs[n] = field<uint16_t>(record, TECH_NEEDS + 2 * static_cast<uint32_t>(n));
        const uint64_t owners = field<uint64_t>(record, TECH_OWNERS);
        if (!owners_of(owners, me, them, &row.mine, &row.picked, &row.others)) {
            *why = "기술 " + std::to_string(i) + " 의 보유 묶음을 읽을 수 없습니다";
            return false;
        }
        row.housed = owners != 0;
        t.techs.push_back(row);
        shot->tech_owners.push_back(owners);
        shot->tech_cells.push_back(tech_table + static_cast<uint64_t>(i) * TECH_SIZE + TECH_OWNERS);
    }

    raw.assign(static_cast<size_t>(design_count) * DESIGN_SIZE, 0);
    if (!peek(reinterpret_cast<const void *>(design_table), raw.data(), raw.size())) {
        *why = "부대 설계 표를 읽을 수 없습니다";
        return false;
    }
    for (int i = 1; i < design_count; i++) {
        const uint8_t *record = raw.data() + static_cast<size_t>(i) * DESIGN_SIZE;
        if (field<uint64_t>(record, DESIGN_NAME) == 0)
            continue;                           // 빈 자리
        DesignRow row;
        row.id = i;
        row.cls = record[DESIGN_CLASS];
        row.year = record[DESIGN_YEAR];
        row.open = field<uint16_t>(record, DESIGN_OPEN) != 0;
        row.held = (field<uint32_t>(record, DESIGN_HOLD_A) & DESIGN_HOLD_A_BIT) != 0
            || (field<uint32_t>(record, DESIGN_HOLD_B) & DESIGN_HOLD_B_BIT) != 0;
        for (int n = 0; n < DESIGN_NEED_COUNT; n++)
            row.needs[n] = field<uint16_t>(record, DESIGN_NEEDS + 2 * static_cast<uint32_t>(n));
        const uint64_t owners = field<uint64_t>(record, DESIGN_OWNERS);
        if (!owners_of(owners, me, them, &row.mine, &row.picked, &row.others)) {
            *why = "부대 설계 " + std::to_string(i) + " 의 보유 묶음을 읽을 수 없습니다";
            return false;
        }
        row.housed = owners != 0;
        t.designs.push_back(row);
        shot->design_owners.push_back(owners);
        shot->design_cells.push_back(design_table + static_cast<uint64_t>(i) * DESIGN_SIZE + DESIGN_OWNERS);
    }

    // 플레이어의 연구 목록: 머리 노드부터 "다음"을 따라간다
    if (!peek(reinterpret_cast<const void *>(shot->world + r.lists + static_cast<uint64_t>(me) * LIST_STEP), &node, sizeof(node))) {
        *why = "연구 목록을 읽을 수 없습니다";
        return false;
    }
    while (node != 0) {
        uint8_t record[NODE_FLAGS + 8];
        if (shot->nodes.size() >= static_cast<size_t>(MAX_NODES)) {
            *why = "연구 목록이 끝나지 않습니다";
            return false;
        }
        if (!peek(reinterpret_cast<const void *>(node), record, sizeof(record))) {
            *why = "연구 목록의 노드를 읽을 수 없습니다";
            return false;
        }
        QueueRow row;
        row.id = field<int32_t>(record, NODE_ID);
        row.kind = record[NODE_KIND];
        row.flags[0] = field<uint32_t>(record, NODE_FLAGS);
        row.flags[1] = field<uint32_t>(record, NODE_FLAGS + 4);
        t.queue.push_back(row);
        shot->nodes.push_back(node);
        node = field<uint64_t>(record, NODE_NEXT);
    }
    research_mark_queued(&t);
    return true;
}

// 바꿀 항목 하나: 보유 묶음의 주소(없으면 0)와 레코드에서 그 포인터가 든 칸.
struct Item {
    bool tech;
    int id;
    uint64_t owners, cell;
};

// 계획의 번호들(오름차순)에 묶음과 칸의 주소를 붙인다. rows 도 번호순이다.
template <class Row>
void attach(const std::vector<int> &ids, const std::vector<Row> &rows, const std::vector<uint64_t> &owners,
            const std::vector<uint64_t> &cells, bool tech, std::vector<Item> *items)
{
    size_t k = 0;
    for (size_t i = 0; i < rows.size() && k < ids.size(); i++)
        if (rows[i].id == ids[k]) {
            items->push_back({tech, ids[k], owners[i], cells[i]});
            k++;
        }
}

// 쓰기가 막혔다: 어디서(where), 몇 칸 가운데 몇 칸을 쓴 뒤인지 적는다.
Wrote research_failed(ResearchDone *done, const std::string &where)
{
    done->why = where;
    return Wrote::Failed;
}

std::string item_name(const Item &item)
{
    return std::string(item.tech ? "기술 " : "부대 설계 ") + std::to_string(item.id);
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

GameMore read_more(const uint8_t *base, const GameAddresses &at, const MoreLayout &more)
{
    GameMore v;
    uint64_t object = 0;
    if (!read_player(base, at, &object).in_game || (more.tech != 0 && !peek_in(object, more.tech, &v.tech)))
        return v;
    for (int i = 0; i < 3; i++)
        if (more.opinion[i] != 0 && !peek_in(object, more.opinion[i], &v.opinion[i]))
            return v;
    v.ok = true;
    return v;
}

Relation read_relation(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, int number)
{
    Relation r;
    uint64_t mine = 0, theirs = 0, cells[6];
    int me = 0, them = 0;
    if (more.relation[0] == 0 || more.relation[1] == 0 || more.casus == 0
        || find_pair(base, at, number, false, &mine, &me, &theirs, &them) != Wrote::Done)
        return r;
    relation_cells(more, mine, me, theirs, them, cells);
    for (int i = 0; i < 3; i++)
        if (!peek(reinterpret_cast<const void *>(cells[i]), &r.mine[i], sizeof(float))
            || !peek(reinterpret_cast<const void *>(cells[3 + i]), &r.theirs[i], sizeof(float)))
            return r;
    r.ok = true;
    return r;
}

Wrote write_tech(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, float value)
{
    uint64_t object = 0;
    if (more.tech == 0)
        return Wrote::Off;
    if (!std::isfinite(value) || value < 0.0f)
        return Wrote::BadValue;
    const GameState s = read_player(base, at, &object);
    if (!s.in_game || s.multiplayer)
        return Wrote::NotInGame;
    return poke(object + more.tech, &value, sizeof(value)) ? Wrote::Done : Wrote::Failed;
}

Wrote write_opinion(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, int *done)
{
    uint64_t object = 0;
    *done = 0;
    if (more.opinion[0] == 0 || more.opinion[1] == 0 || more.opinion[2] == 0)
        return Wrote::Off;
    const GameState s = read_player(base, at, &object);
    if (!s.in_game || s.multiplayer)
        return Wrote::NotInGame;
    const uint64_t cells[3] = {object + more.opinion[0], object + more.opinion[1], object + more.opinion[2]};
    const float best[3] = {1.0f, 1.0f, 1.0f};
    return poke_floats(cells, best, 3, done);
}

Wrote write_relation(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, int number, float level, int *done)
{
    uint64_t mine = 0, theirs = 0, cells[6];
    int me = 0, them = 0;
    *done = 0;
    if (more.relation[0] == 0 || more.relation[1] == 0 || more.casus == 0)
        return Wrote::Off;
    if (!std::isfinite(level) || level < -1.0f || level > 1.0f)
        return Wrote::BadValue;
    const Wrote found = find_pair(base, at, number, true, &mine, &me, &theirs, &them);
    if (found != Wrote::Done)
        return found;
    relation_cells(more, mine, me, theirs, them, cells);
    const float values[6] = {level, level, 0.0f, level, level, 0.0f};
    return poke_floats(cells, values, 6, done);
}

bool read_research(const uint8_t *base, const GameAddresses &at, const ResearchLayout &research, int picked, ResearchTables *out,
                   std::string *why)
{
    Shot shot;
    std::string reason;
    bool ok = shoot(base, at, research, picked, &shot, &reason);
    if (ok && shot.multiplayer) {
        ok = false;
        reason = "멀티플레이에서는 연구를 읽지 않습니다";
    }
    if (why != nullptr)
        *why = reason;
    if (ok)
        *out = std::move(shot.tables);
    return ok;
}

Wrote write_research(const uint8_t *base, const GameAddresses &at, const ResearchLayout &research, Recompute recompute, Research action,
                     const ResearchWhat &what, ResearchDone *done)
{
    *done = ResearchDone();
    Shot shot;
    if (!shoot(base, at, research, 0, &shot, &done->why))
        return done->why == NOT_PLAYING ? Wrote::NotInGame : Wrote::Unreadable;
    if (shot.multiplayer)
        return Wrote::NotInGame;

    // 새 묶음을 걸 수 있는가: 이미 있는 묶음 하나가 프로세스 힙의 OWNERS_BYTES 짜리 블록이어야 한다(게임이 그 힙에서 그 크기로 받는다는 뜻)
    uint64_t sample = 0;
    for (uint64_t owners : shot.tech_owners)
        sample = sample != 0 ? sample : owners;
    for (uint64_t owners : shot.design_owners)
        sample = sample != 0 ? sample : owners;
    bool can_house = sample != 0 && heap_block(sample, OWNERS_BYTES);

    const HANDLE heap = GetProcessHeap();
    std::vector<Item> items;
    std::vector<void *> fresh;                  // 새로 받은 묶음. 앞에서부터 차례로 건다
    size_t hung = 0;                            // 그 가운데 이미 건 것의 수(건 것은 게임의 것이다 — 풀지 않는다)
    const auto release = [&]() {
        for (size_t i = hung; i < fresh.size(); i++)
            HeapFree(heap, 0, fresh[i]);
        fresh.clear();
        hung = 0;
    };
    ResearchPlan plan;
    for (int pass = 0; pass < 2; pass++) {      // 묶음을 받지 못하면, 묶음이 없는 항목을 건너뛰는 계획으로 한 번 더
        plan = research_plan(shot.tables, action, what, can_house);
        items.clear();
        attach(plan.techs, shot.tables.techs, shot.tech_owners, shot.tech_cells, true, &items);
        attach(plan.designs, shot.tables.designs, shot.design_owners, shot.design_cells, false, &items);
        bool short_of = false;
        for (const Item &item : items)
            if (item.owners == 0 && !short_of) {
                void *const block = HeapAlloc(heap, HEAP_ZERO_MEMORY, OWNERS_BYTES);
                if (block == nullptr)
                    short_of = true;
                else
                    fresh.push_back(block);
            }
        if (!short_of)
            break;
        release();
        can_house = false;
    }
    done->plan = plan;
    done->skipped = plan.skipped;

    // 쓰기 전에: 모든 칸이 읽기 · 쓰기 쪽인가(반쪽만 쓰고 멈추지 않게)
    const uint64_t byte = static_cast<uint64_t>(shot.me) / 8;
    const uint8_t mask = static_cast<uint8_t>(1u << (shot.me % 8));
    done->cells = static_cast<int>(items.size() + fresh.size() + 2 * plan.nodes.size());
    for (const Item &item : items)
        if (item.owners != 0 ? !writable(item.owners + byte, 1) : !writable(item.cell, sizeof(uint64_t))) {
            release();
            return research_failed(done, item_name(item) + (item.owners != 0 ? " 의 보유 묶음" : " 의 묶음 칸"));
        }
    for (int n : plan.nodes)
        if (!writable(shot.nodes[static_cast<size_t>(n)] + NODE_FLAGS, 2 * sizeof(uint32_t))) {
            release();
            return research_failed(done, "연구 목록의 노드");
        }

    // 묶음(없는 항목만) → 비트
    for (Item &item : items) {
        if (item.owners == 0) {
            const uint64_t block = reinterpret_cast<uint64_t>(fresh[hung]);
            if (!poke(item.cell, &block, sizeof(block))) {
                release();
                return research_failed(done, item_name(item) + " 의 묶음 칸");
            }
            hung++;
            item.owners = block;
            done->housed++;
            done->written++;
        }
        if (!poke_bits(item.owners + byte, mask, action == Research::Complete, 1)) {
            release();
            return research_failed(done, item_name(item) + " 의 보유 묶음");
        }
        done->written++;
    }

    // 대기열에서 뺀다: 노드의 깃발 둘에 "뺐다"를 켠다(다른 비트는 그대로)
    for (int n : plan.nodes)
        for (uint32_t side = 0; side < 2; side++) {
            if (!poke_bits(shot.nodes[static_cast<size_t>(n)] + NODE_FLAGS + 4 * side, NODE_GONE, true, sizeof(uint32_t)))
                return research_failed(done, "연구 목록의 노드");
            done->written++;
        }

    // 기술의 효과는 지역마다 미리 계산해 둔 표로 쓰인다 — 기술의 보유가 바뀌었으면 플레이어 지역의 것을 다시 셈하게 한다
    if (!plan.techs.empty() && recompute != nullptr) {
        if (!guarded_recompute(recompute, reinterpret_cast<void *>(shot.world), shot.me, &done->code))
            return Wrote::Crashed;
        done->recomputed = true;
    }
    return Wrote::Done;
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
    const bool values = state && locate_values(base, size, &layout, value_rows, value_why, sizeof(value_why))
        && locate_fits(at, layout, value_why, sizeof(value_why));

    // 새 찾기: 더 쓰는 값(기술 수준 · 세계 시장 여론 · 관계) — 묶음마다 따로 찾는다. 값 묶음을 찾았으면 그 칸들과 겹치지 않아야 한다
    MoreLayout more = {};
    SigRow more_rows[MORE_WANTED * STATE_SIGS];
    char more_why[MORE_GROUPS][MORE_WHY] = {};
    const int groups = state ? locate_more(base, size, values ? &layout : nullptr, &more, more_rows, more_why) : 0;

    // 새 찾기: 연구 — 기술 · 부대 설계의 표, 지역별 연구 목록, 지역의 효과를 다시 셈하는 함수. 일곱을 모두, 서명도 셋씩 모두 맞아야 한다.
    // 값 묶음을 찾았으면 그 세계 자료 포인터와 겹치지 않아야 한다(겹치면 연구 묶음만 버린다)
    ResearchLayout research = {};
    char research_why[160] = "";
    const bool researching = state && locate_research(base, size, at, &research, nullptr, research_why, sizeof(research_why))
        && (!values || locate_research_fits(research, layout, research_why, sizeof(research_why)));
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
        g_more = more;
        g_more_groups = groups;
        memcpy(g_more_why, more_why, sizeof(g_more_why));
        g_research = research;
        g_research_found = researching;
        snprintf(g_research_why, sizeof(g_research_why), "%s", research_why);
        g_recompute = researching ? const_cast<uint8_t *>(base) + research.recompute : nullptr;
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
    static const char *const MISSING[MORE_GROUPS] = {"기술 수준을 쓸 수 없습니다 (%s)", "세계 시장 여론을 쓸 수 없습니다 (%s)",
                                                     "관계를 쓸 수 없습니다 (%s)"};
    if (groups != 0) {
        char found[160] = "";
        size_t used = 0;
        const auto add = [&](const char *format, uint32_t a, uint32_t b, uint32_t c) {
            used += static_cast<size_t>(snprintf(found + used, sizeof(found) - used, format, used == 0 ? "" : " · ", a, b, c));
        };
        if (groups & MORE_TECH)
            add("%s기술 수준 +0x%X", more.tech, 0, 0);
        if (groups & MORE_OPINION)
            add("%s세계 시장 여론 +0x%X +0x%X +0x%X", more.opinion[0], more.opinion[1], more.opinion[2]);
        if (groups & MORE_RELATIONS)
            add("%s관계 +0x%X +0x%X 전쟁 명분 +0x%X", more.relation[0], more.relation[1], more.casus);
        log_line(write_wanted() ? "값을 더 씁니다 (%s)" : "값을 더 쓰지 않습니다 (SRTOYBOX_WRITE=0. %s)", found);
    }
    for (int g = 0; g < MORE_GROUPS; g++)
        if ((groups & (1 << g)) == 0)
            log_line(MISSING[g], more_why[g]);
    for (int i = 0; i < MORE_WANTED * STATE_SIGS; i++)   // 찾은 묶음에서만: 셋 가운데 둘로 찾았을 때 맞지 않은 하나
        if ((groups & (1 << locate_more_group(i / STATE_SIGS))) != 0)
            log_unmatched(more_rows[i], i % STATE_SIGS + 1);
    if (researching)
        log_line(write_wanted() ? "연구를 씁니다 (기술 표 +0x%X · 부대 설계 표 +0x%X · 연구 목록 +0x%X · 다시 셈 +0x%X)"
                                : "연구를 쓰지 않습니다 (SRTOYBOX_WRITE=0. 기술 표 +0x%X · 부대 설계 표 +0x%X · 연구 목록 +0x%X · 다시 셈 +0x%X)",
                 research.tech_table, research.design_table, research.lists, research.recompute);
    else
        log_line("연구를 쓸 수 없습니다 (%s)", research_why);
    if (can_call)
        log_line("옛 방식(내장 치트)으로 도는 기능이 %d개 남아 있습니다 (명령 처리 함수 +0x%X)", cheat_feature_count(), at.handler);
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
    g_more = MoreLayout();
    g_more_groups = 0;
    for (int g = 0; g < MORE_GROUPS; g++)
        snprintf(g_more_why[g], MORE_WHY, "값의 자리를 주지 않았습니다");
    g_research = ResearchLayout();
    g_research_found = false;
    g_recompute = nullptr;
    snprintf(g_research_why, sizeof(g_research_why), "연구의 자리를 주지 않았습니다");
}

void game_set_research_for_test(const ResearchLayout *layout, void *recompute)
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_research = layout != nullptr ? *layout : ResearchLayout();
    g_research_found = layout != nullptr;
    g_recompute = layout != nullptr ? recompute : nullptr;
    g_write_failed = false;
}

void game_set_values_for_test(const ValueLayout *layout)
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_layout = layout != nullptr ? *layout : ValueLayout();
    g_values = layout != nullptr;
    g_write_failed = false;
}

void game_set_more_for_test(const MoreLayout *layout)
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_more = layout != nullptr ? *layout : MoreLayout();
    g_more_groups = (g_more.tech != 0 ? MORE_TECH : 0)
        | (g_more.opinion[0] != 0 && g_more.opinion[1] != 0 && g_more.opinion[2] != 0 ? MORE_OPINION : 0)
        | (g_more.relation[0] != 0 && g_more.relation[1] != 0 && g_more.casus != 0 ? MORE_RELATIONS : 0);
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
    return off_text(g_values, g_values_why);
}

bool game_writes()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_located && reading_wanted() && write_wanted() && !g_write_failed;
}

std::string game_more_off(int group)
{
    const int index = more_index(group);
    std::lock_guard<std::mutex> lock(g_lock);
    return index < 0 ? std::string("없는 묶음입니다") : off_text((g_more_groups & group) != 0, g_more_why[index]);
}

GameMore game_more()
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    MoreLayout more = {};
    {
        std::lock_guard<std::mutex> lock(g_lock);
        if (!g_located || !reading_wanted())
            return GameMore();
        base = g_base;
        at = g_at;
        more = g_more;
    }
    return read_more(base, at, more);
}

Relation game_relation(int number)
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    MoreLayout more = {};
    {
        std::lock_guard<std::mutex> lock(g_lock);
        if (!g_located || !reading_wanted())
            return Relation();
        base = g_base;
        at = g_at;
        more = g_more;
    }
    return read_relation(base, at, more, number);
}

Wrote game_write_tech(float value)
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    MoreLayout more = {};
    if (!more_ready(MORE_TECH, &base, &at, &more))
        return Wrote::Off;
    const Wrote wrote = write_tech(base, at, more, value);
    return wrote == Wrote::Failed ? write_failed("기술 수준", 1, 0) : wrote;
}

Wrote game_write_opinion()
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    MoreLayout more = {};
    int done = 0;
    if (!more_ready(MORE_OPINION, &base, &at, &more))
        return Wrote::Off;
    const Wrote wrote = write_opinion(base, at, more, &done);
    return wrote == Wrote::Failed ? write_failed("세계 시장 여론", 3, done) : wrote;
}

Wrote game_write_relation(int number, float level)
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    MoreLayout more = {};
    int done = 0;
    if (!more_ready(MORE_RELATIONS, &base, &at, &more))
        return Wrote::Off;
    const Wrote wrote = write_relation(base, at, more, number, level, &done);
    return wrote == Wrote::Failed
        ? write_failed("관계 — " + region_label(number) + " (" + std::to_string(number) + ")", 6, done) : wrote;
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

std::string game_research_off()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return off_text(g_research_found, g_research_why);
}

bool game_research(int picked, ResearchTables *out, std::string *why)
{
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    ResearchLayout research = {};
    {
        std::lock_guard<std::mutex> lock(g_lock);
        if (!g_located || !g_research_found || !reading_wanted()) {
            if (why != nullptr)
                *why = !g_located || !reading_wanted() ? "게임 상태를 읽을 수 없습니다" : g_research_why;
            return false;
        }
        base = g_base;
        at = g_at;
        research = g_research;
    }
    return read_research(base, at, research, picked, out, why);
}

Wrote game_write_research(Research action, const ResearchWhat &what, ResearchDone *done)
{
    *done = ResearchDone();
    if (!game_research_off().empty())
        return Wrote::Off;
    const uint8_t *base = nullptr;
    GameAddresses at = {};
    ResearchLayout research = {};
    Recompute recompute = nullptr;
    {
        std::lock_guard<std::mutex> lock(g_lock);
        base = g_base;
        at = g_at;
        research = g_research;
        recompute = reinterpret_cast<Recompute>(g_recompute);
    }
    const Wrote wrote = write_research(base, at, research, recompute, action, what, done);
    if (wrote == Wrote::Failed) {
        {
            std::lock_guard<std::mutex> lock(g_lock);
            g_write_failed = true;
        }
        if (done->written > 0)
            log_line("연구 쓰기 실패 (%s, %d칸 가운데 %d칸을 쓴 뒤) — 값 쓰기를 끕니다", done->why.c_str(), done->cells, done->written);
        else
            log_line("연구 쓰기 실패 (%s) — 값 쓰기를 끕니다", done->why.c_str());
    }
    return wrote;
}
