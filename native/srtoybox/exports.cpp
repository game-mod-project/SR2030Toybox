// 테스트(tests/test_toybox.py)와 불러오는 쪽(srhook)이 쓰는 C 인터페이스. 글은 UTF-8, 버퍼가 작거나 대상이 없으면 -1.
#include <windows.h>

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
#include "ui.h"

#define EXPORT extern "C" __declspec(dllexport)

namespace {

int put(const std::string &text, char *out, int size)
{
    if (out == nullptr || size <= 0 || text.size() + 1 > static_cast<size_t>(size))
        return -1;
    memcpy(out, text.c_str(), text.size() + 1);
    return static_cast<int>(text.size());
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

// 실행 파일의 이미지(RVA 대로 펼친 것)에서 주소를 찾는다. 0 이면 out 을 채웠다. -1 이면 error 에 까닭.
EXPORT int srtoybox_locate(const unsigned char *image, unsigned long long size, GameAddresses *out, char *error, int error_size)
{
    GameAddresses found = {};
    const char *why = locate_game(image, static_cast<size_t>(size), &found);
    if (why != nullptr) {
        put(why, error, error_size);
        return -1;
    }
    if (out != nullptr)
        *out = found;
    return 0;
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


// srhook 이 이 DLL 을 불러온 뒤 한 번 부른다(불러온 스레드에서). 게임의 창은 기다리지 않는다 — 첫 Present 에서 얻는다.
EXPORT void WINAPI srtoybox_start(void)
{
    log_line("시작 (프로세스 %lu)", GetCurrentProcessId());
    ui_init();
    game_init();          // 화면에 끼어들기 전에 끝낸다 — 창이 뜰 때는 게임을 읽을 수 있는지가 이미 정해져 있다
    overlay_install();
}
