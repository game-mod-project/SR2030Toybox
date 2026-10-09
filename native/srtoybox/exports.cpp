// 테스트(tests/test_toybox.py)와 불러오는 쪽(srhook)이 쓰는 C 인터페이스. 글은 UTF-8, 버퍼가 작거나 대상이 없으면 -1.
#include <windows.h>

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "command.h"
#include "features.h"
#include "game.h"
#include "input.h"
#include "locate.h"
#include "log.h"
#include "overlay.h"
#include "prologue.h"
#include "regions.h"
#include "runner.h"
#include "settings.h"
#include "sigs.h"
#include "ui.h"
#include "values.h"

#define EXPORT extern "C" __declspec(dllexport)

namespace {

int put(const std::string &text, char *out, int size)
{
    if (out == nullptr || size <= 0 || text.size() + 1 > static_cast<size_t>(size))
        return -1;
    memcpy(out, text.c_str(), text.size() + 1);
    return static_cast<int>(text.size());
}

// 서명마다의 결과를 글로: 한 줄에 "<찾을 것>\t<서명 글>\t<맞은 횟수>\t<처음 맞은 자리>\t<읽어 낸 값>\t<둘째 값>"(뒤의 넷은 16진수).
std::string rows_text(const SigRow *rows, int n)
{
    std::string text;
    char numbers[80];
    for (int i = 0; i < n; i++) {
        snprintf(numbers, sizeof(numbers), "\t%x\t%x\t%x\t%x\n", static_cast<unsigned>(rows[i].count), rows[i].at, rows[i].value,
                 rows[i].value2);
        text += std::string(rows[i].name) + '\t' + rows[i].text + numbers;
    }
    return text;
}

// 보내는 대신 적어 두는 Sink. 시계는 부르는 쪽이 돌린다.
struct RecordingSink : Sink {
    unsigned long long now = 0;
    std::string log;

    void line(const char *what, int value) { log += std::to_string(now) + ' ' + what + ' ' + std::to_string(value) + '\n'; }
    void mods(bool on) override { line("MODS", on ? 1 : 0); }
    void key(Act act, int value) override { line(act == Act::Down ? "DOWN" : act == Act::Up ? "UP" : "CHAR", value); }
    unsigned long long now_ms() override { return now; }
};

}  // namespace

EXPORT int srtoybox_feature_count(void)
{
    return FEATURE_COUNT;
}

// 한 줄: id, 탭, 이름, 명령, 값 있음(0/1), 기본값, 최소, 최대, 확인(0/1), 설명, 대상(none/player/picked) — 탭 문자로 나눈다
EXPORT int srtoybox_feature_info(int index, char *out, int size)
{
    if (index < 0 || index >= FEATURE_COUNT)
        return -1;
    const Feature &f = FEATURES[index];
    static const char *const targets[] = {"none", "player", "picked"};
    const std::string line = std::string(f.id) + '\t' + f.tab + '\t' + f.label + '\t' + f.command + '\t' + (f.has_value ? "1" : "0")
        + '\t' + std::to_string(f.def) + '\t' + std::to_string(f.min) + '\t' + std::to_string(f.max) + '\t'
        + (f.confirm ? "1" : "0") + '\t' + f.help + '\t' + targets[static_cast<int>(f.target)];
    return put(line, out, size);
}

EXPORT int srtoybox_command(const char *id, long long value, int region, char *out, int size)
{
    const Feature *f = id == nullptr ? nullptr : find_feature(id);
    const std::string command = f == nullptr ? std::string() : build_command(*f, value, region);
    return command.empty() ? -1 : put(command, out, size);
}

EXPORT int srtoybox_plan(const char *command, char *out, int size)
{
    const std::vector<Action> plan = plan_command(command == nullptr ? "" : command);
    return plan.empty() ? -1 : put(describe(plan), out, size);
}

// 명령들(줄바꿈으로 나눈다)을 한꺼번에 대기열에 넣고 가짜 시계로 끝까지 돌린다.
// 줄마다 "<밀리초> <동작> <값>". 받지 못한 명령은 맨 앞에 "REJECT <명령>".
EXPORT int srtoybox_simulate(const char *commands, int tick_ms, char *out, int size)
{
    Runner runner;
    RecordingSink sink;
    const std::string all = commands == nullptr ? "" : commands;
    std::string rejected;
    size_t pos = 0;
    while (pos < all.size()) {
        size_t end = all.find('\n', pos);
        if (end == std::string::npos)
            end = all.size();
        const std::string one = all.substr(pos, end - pos);
        if (!runner.enqueue(one))
            rejected += "REJECT " + one + '\n';
        pos = end + 1;
    }
    for (int guard = 0; runner.busy() && guard < 1000000; guard++) {
        runner.tick(sink);
        sink.now += static_cast<unsigned long long>(tick_ms > 0 ? tick_ms : 1);
    }
    return put(rejected + sink.log, out, size);
}

EXPORT int srtoybox_settings_normalize(const char *ini, char *out, int size)
{
    return put(format_settings(parse_settings(ini == nullptr ? "" : ini)), out, size);
}

EXPORT int srtoybox_settings_store(const char *ini)
{
    return save_settings(parse_settings(ini == nullptr ? "" : ini)) ? 1 : 0;
}

EXPORT int srtoybox_settings_file(char *out, int size)
{
    return put(format_settings(load_settings()), out, size);
}

EXPORT int srtoybox_prologue_length(const unsigned char *code, int size, int want)
{
    return prologue_length(code, size, want);
}

// 테스트: 서명 글들(줄바꿈으로 나눈다)을 image 의 [begin, end) 에서 맞춰 본다.
// 서명마다 한 줄 "<맞은 횟수> <처음 맞은 자리> <값0> <값1>"(16진수. 글이 틀리면 "bad"),
// 끝 줄은 투표 "vote <찾았는가 0/1> <한 번만 맞은 수> <값0> <값1>".
EXPORT int srtoybox_sig_find(const unsigned char *image, unsigned long long size, unsigned begin, unsigned end, const char *sigs,
                             int need, char *out, int out_size)
{
    std::vector<Sig> parsed;
    std::vector<int> where;      // 줄 → parsed 의 칸. 틀린 글이면 -1
    const std::string all = sigs == nullptr ? "" : sigs;
    for (size_t pos = 0; pos <= all.size(); ) {
        size_t stop = all.find('\n', pos);
        if (stop == std::string::npos)
            stop = all.size();
        Sig sig = {};
        if (sig_parse(all.substr(pos, stop - pos).c_str(), &sig)) {
            where.push_back(static_cast<int>(parsed.size()));
            parsed.push_back(sig);
        } else {
            where.push_back(-1);
        }
        pos = stop + 1;
    }
    std::vector<SigHit> hits(parsed.size());
    const SigRange range = {begin, end};
    if (image != nullptr && !parsed.empty())
        sig_scan(image, static_cast<size_t>(size), &range, 1, parsed.data(), static_cast<int>(parsed.size()), hits.data());
    std::string text;
    char line[96];
    for (int at : where) {
        if (at < 0) {
            text += "bad\n";
            continue;
        }
        const SigHit &hit = hits[static_cast<size_t>(at)];
        snprintf(line, sizeof(line), "%x %x %llx %llx\n", static_cast<unsigned>(hit.count), hit.at, hit.value[0], hit.value[1]);
        text += line;
    }
    uint64_t value[SIG_CAPTURES] = {};
    int matched = 0;
    const bool found = !parsed.empty()
        && sig_vote(parsed.data(), hits.data(), static_cast<int>(parsed.size()), need, value, &matched);
    snprintf(line, sizeof(line), "vote %d %d %llx %llx", found ? 1 : 0, matched, value[0], value[1]);
    return put(text + line, out, out_size);
}

// 옛 찾기(전환 기간에만): 명령 처리 함수 · this · 옵션 묶음을 치트 닻으로. 0 이면 out 의 그 셋을 채웠다. -1 이면 error 에 까닭.
EXPORT int srtoybox_locate_legacy(const unsigned char *image, unsigned long long size, GameAddresses *out, char *error, int error_size)
{
    GameAddresses found = {};
    const char *why = locate_legacy(image, static_cast<size_t>(size), &found);
    if (why != nullptr) {
        put(why, error, error_size);
        return -1;
    }
    if (out != nullptr)
        *out = found;
    return 0;
}

// 새 찾기(상태 묶음, 서명으로). 0 이면 out 의 일곱 필드를 채웠다. -1 이면 error 에 까닭.
// rows 에는 서명마다 한 줄(rows_text). 필요 없으면 nullptr.
EXPORT int srtoybox_locate_state(const unsigned char *image, unsigned long long size, GameAddresses *out, char *error, int error_size,
                                 char *rows, int rows_size)
{
    GameAddresses found = {};
    SigRow table[STATE_WANTED * STATE_SIGS];
    char why[160] = "";
    const bool ok = locate_state(image, static_cast<size_t>(size), &found, table, why, sizeof(why));
    if (rows != nullptr)
        put(rows_text(table, STATE_WANTED * STATE_SIGS), rows, rows_size);
    if (!ok) {
        put(why, error, error_size);
        return -1;
    }
    if (out != nullptr)
        *out = found;
    return 0;
}

// 새 찾기(값 묶음, 서명으로). 0 이면 out 을 채웠다. -1 이면 error 에 까닭. rows 는 srtoybox_locate_state 와 같다.
EXPORT int srtoybox_locate_values(const unsigned char *image, unsigned long long size, ValueLayout *out, char *error, int error_size,
                                  char *rows, int rows_size)
{
    ValueLayout found = {};
    SigRow table[VALUE_WANTED * STATE_SIGS];
    char why[160] = "";
    const bool ok = locate_values(image, static_cast<size_t>(size), &found, table, why, sizeof(why));
    if (rows != nullptr)
        put(rows_text(table, VALUE_WANTED * STATE_SIGS), rows, rows_size);
    if (!ok) {
        put(why, error, error_size);
        return -1;
    }
    if (out != nullptr)
        *out = found;
    return 0;
}

EXPORT int srtoybox_stock_slots(void)
{
    return STOCK_SLOTS;
}

EXPORT unsigned srtoybox_function_root(const unsigned char *image, unsigned long long size, unsigned rva)
{
    return locate_function_root(image, static_cast<size_t>(size), rva);
}

// 테스트: 가짜 메모리에서 상태를 읽는다. "known=1 in_game=1 multiplayer=0 cheats=0 player=1499 regions=1106,1499"
EXPORT int srtoybox_game_state(const unsigned char *base, const GameAddresses *at, char *out, int size)
{
    if (at == nullptr)
        return -1;
    const GameState s = read_game(base, *at);
    std::string regions;
    for (int number : read_regions(base, *at))
        regions += (regions.empty() ? "" : ",") + std::to_string(number);
    return put("known=" + std::to_string(s.known) + " in_game=" + std::to_string(s.in_game) + " multiplayer="
               + std::to_string(s.multiplayer) + " cheats=" + std::to_string(s.cheats_on) + " player=" + std::to_string(s.player)
               + " regions=" + regions, out, size);
}

// 테스트: 이 프로세스의 "게임"을 가짜 메모리로 바꾼다(주소 찾기의 결과를 덮어쓴다).
EXPORT void srtoybox_test_game(const unsigned char *base, const GameAddresses *at, void *handler)
{
    game_set_for_test(base, at, handler);
}

// 테스트: 가짜 메모리에서 값을 읽는다. "ok=1 treasury=14430000000 used=100100010000 stock=1000,0,0,2500,…"
EXPORT int srtoybox_values_read(const unsigned char *base, const GameAddresses *at, const ValueLayout *layout, char *out, int size)
{
    if (at == nullptr || layout == nullptr)
        return -1;
    const GameValues v = read_values(base, *at, *layout);
    char number[40];
    snprintf(number, sizeof(number), "%.17g", v.treasury);
    std::string used, stock;
    for (int i = 0; i < STOCK_SLOTS; i++) {
        used += v.used[i] ? '1' : '0';
        char one[32];
        snprintf(one, sizeof(one), "%s%.9g", i == 0 ? "" : ",", static_cast<double>(v.stock[i]));
        stock += one;
    }
    return put("ok=" + std::to_string(v.ok) + " treasury=" + number + " used=" + used + " stock=" + stock, out, size);
}

// 테스트: 가짜 메모리에 쓴다. slot 이 -1 이면 국고, 아니면 그 칸의 재고. 돌려주는 값은 Wrote
// (0 썼다, 1 게임 밖, 2 쓰지 않는 물자, 3 쓸 수 없는 값이나 칸, 4 실패).
EXPORT int srtoybox_values_write(const unsigned char *base, const GameAddresses *at, const ValueLayout *layout, int slot, double value)
{
    if (at == nullptr || layout == nullptr)
        return -1;
    return static_cast<int>(slot == -1 ? write_treasury(base, *at, *layout, value)
                                       : write_stock(base, *at, *layout, slot, static_cast<float>(value)));
}

// 테스트: 이 프로세스의 "게임"에 값의 자리를 준다(srtoybox_test_game 다음에 부른다). nullptr 이면 못 찾은 것으로.
EXPORT void srtoybox_test_values(const ValueLayout *layout)
{
    game_set_values_for_test(layout);
}

// 테스트: 게임이 뜰 때의 찾기(game_init_from)를 그 이미지에 돌린다. 이미지는 srtoybox_test_game(nullptr, …) 로 비울 때까지 살아 있어야 한다.
EXPORT void srtoybox_test_init(const unsigned char *image, unsigned long long size)
{
    game_init_from(image, static_cast<size_t>(size));
}

// 테스트: 이 프로세스의 "게임"에 대해 아는 것. 비트 1 = 상태를 읽는다, 2 = 명령 처리 함수를 부를 수 있다, 4 = 값을 쓸 수 있다.
EXPORT int srtoybox_game_flags(void)
{
    return (game_reads() ? 1 : 0) | (game_can_call() ? 2 : 0) | (game_values_off().empty() ? 4 : 0);
}

EXPORT int srtoybox_values_off(char *out, int size)
{
    return put(game_values_off(), out, size);
}

EXPORT int srtoybox_region_label(int number, char *out, int size)
{
    return put(region_label(number), out, size);
}

// 테스트: 창의 나라 목록. 첫 줄 "picked=<번호>", 이어서 한 줄에 "<번호>\t<이름>".
EXPORT int srtoybox_region_view(const int *numbers, int count, int player, int picked, const char *filter, char *out, int size)
{
    const std::vector<int> all(numbers, numbers + (numbers == nullptr || count < 0 ? 0 : count));
    const RegionView view = region_view(all, player, picked, filter);
    std::string text = "picked=" + std::to_string(view.picked) + '\n';
    for (int number : view.rows)
        text += std::to_string(number) + '\t' + region_label(number) + '\n';
    return put(text, out, size);
}

EXPORT unsigned srtoybox_dbcs(unsigned char lead, unsigned char trail, unsigned codepage)
{
    return dbcs_combine(lead, trail, codepage);
}

// 테스트: 설정 창이 지난 프레임에 그린 것들(ui.h 의 ui_report).
EXPORT int srtoybox_ui_report(char *out, int size)
{
    return put(ui_report(), out, size);
}

EXPORT int srtoybox_hotkey_name(int vk, int mods, char *out, int size)
{
    return put(hotkey_name(vk, mods), out, size);
}

// 테스트: 값 계산(values.h). stock 이 0 이면 국고, 아니면 재고. change: 0 더하기, 1 이 값으로, 2 바닥.
// 돌려주는 값은 Verdict: 0 쓴다(*out 에 쓸 값), 1 바꿀 것이 없다, 2 쓰지 않는다. 인자가 틀리면 -1.
EXPORT int srtoybox_value(int stock, double now, int change, double amount, double *out)
{
    if (change < 0 || change > 2 || out == nullptr)
        return -1;
    double next = 0;
    float next_stock = 0;       // (small 은 windows.h 가 매크로로 쓴다)
    const Verdict verdict = stock != 0 ? stock_value(static_cast<float>(now), static_cast<Change>(change), amount, &next_stock)
                                       : treasury_value(now, static_cast<Change>(change), amount, &next);
    if (verdict == Verdict::Write)
        *out = stock != 0 ? static_cast<double>(next_stock) : next;
    return static_cast<int>(verdict);
}

EXPORT int srtoybox_short_number(double value, char *out, int size)
{
    return put(short_number(value), out, size);
}


// srhook 이 이 DLL 을 불러온 뒤 한 번 부른다(불러온 스레드에서). 게임의 창은 기다리지 않는다 — 첫 Present 에서 얻는다.
EXPORT void WINAPI srtoybox_start(void)
{
    log_line("시작 (프로세스 %lu)", GetCurrentProcessId());
    ui_init();
    game_init();          // 화면에 끼어들기 전에 끝낸다 — 창이 뜰 때는 게임을 읽을 수 있는지가 이미 정해져 있다
    overlay_install();
}
