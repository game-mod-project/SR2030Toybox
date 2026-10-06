// 테스트(tests/test_toybox.py)가 쓰는 C 인터페이스. 글은 UTF-8, 버퍼가 작거나 대상이 없으면 -1.
#include <cstring>
#include <string>
#include <vector>

#include "command.h"
#include "features.h"
#include "runner.h"
#include "settings.h"

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

// 한 줄: id, 탭, 이름, 명령, 값 있음(0/1), 기본값, 최소, 최대, 확인(0/1), 설명 — 탭 문자로 나눈다
EXPORT int srtoybox_feature_info(int index, char *out, int size)
{
    if (index < 0 || index >= FEATURE_COUNT)
        return -1;
    const Feature &f = FEATURES[index];
    const std::string line = std::string(f.id) + '\t' + f.tab + '\t' + f.label + '\t' + f.command + '\t' + (f.has_value ? "1" : "0")
        + '\t' + std::to_string(f.def) + '\t' + std::to_string(f.min) + '\t' + std::to_string(f.max) + '\t'
        + (f.confirm ? "1" : "0") + '\t' + f.help;
    return put(line, out, size);
}

EXPORT int srtoybox_command(const char *id, long long value, char *out, int size)
{
    const Feature *f = id == nullptr ? nullptr : find_feature(id);
    return f == nullptr ? -1 : put(build_command(*f, value), out, size);
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

EXPORT int srtoybox_hotkey_name(int vk, int mods, char *out, int size)
{
    return put(hotkey_name(vk, mods), out, size);
}
