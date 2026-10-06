#include "command.h"

namespace {

const int VK_SHIFT_ = 0x10, VK_CONTROL_ = 0x11, VK_RETURN_ = 0x0D, VK_ESCAPE_ = 0x1B, VK_S_ = 0x53;
const int KEY_MS = 50;          // 키를 누르고 있는 시간
const int CHAR_MS = 30;         // 글자 사이
const int AFTER_KEY_MS = 100;   // 키를 뗀 뒤
const int AFTER_MODS_MS = 200;  // 수정키를 뗀 뒤, 키 상태표를 되돌리기 전(게임이 보낸 메시지를 다 읽을 때까지)
const int SETTLE_MS = 300;      // 창이 뜨거나 명령이 처리될 시간
const size_t MAX_COMMAND = 64;

void press(std::vector<Action> &plan, int vk, int after_ms)
{
    plan.push_back({Act::Down, vk});
    plan.push_back({Act::Wait, KEY_MS});
    plan.push_back({Act::Up, vk});
    plan.push_back({Act::Wait, after_ms});
}

void enter_line(std::vector<Action> &plan, const std::string &text)
{
    for (unsigned char c : text) {
        plan.push_back({Act::Char, c});
        plan.push_back({Act::Wait, CHAR_MS});
    }
    press(plan, VK_RETURN_, SETTLE_MS);
}

}  // namespace

std::string build_command(const Feature &f, long long value)
{
    std::string out = f.command;
    if (f.has_value) {
        const long long v = value < f.min ? f.min : value > f.max ? f.max : value;
        out += ' ';
        out += std::to_string(v);
    }
    return out;
}

std::vector<Action> plan_command(const std::string &command)
{
    std::vector<Action> plan;
    if (command.empty() || command.size() > MAX_COMMAND)
        return plan;
    for (unsigned char c : command)
        if (c < 0x20 || c > 0x7E)
            return plan;

    plan.push_back({Act::Mods, 1});
    plan.push_back({Act::Down, VK_CONTROL_});
    plan.push_back({Act::Down, VK_SHIFT_});
    plan.push_back({Act::Down, VK_S_});
    plan.push_back({Act::Wait, KEY_MS});
    plan.push_back({Act::Up, VK_S_});
    plan.push_back({Act::Wait, AFTER_KEY_MS});
    plan.push_back({Act::Up, VK_SHIFT_});
    plan.push_back({Act::Up, VK_CONTROL_});
    plan.push_back({Act::Wait, AFTER_MODS_MS});
    plan.push_back({Act::Mods, 0});
    plan.push_back({Act::Wait, SETTLE_MS});
    enter_line(plan, "cheat allowcheats");   // 두 번 넣어도 치트는 켜진 채다 [확인: 게임] — 그래서 매번 보낸다
    enter_line(plan, command);
    press(plan, VK_ESCAPE_, SETTLE_MS);      // 설정 창은 ESC 로 닫힌다 [확인: 게임]
    return plan;
}

std::string describe(const std::vector<Action> &plan)
{
    static const char *const names[] = {"MODS", "DOWN", "UP", "CHAR", "WAIT"};
    std::string out;
    for (const Action &a : plan) {
        out += names[static_cast<int>(a.act)];
        out += ' ';
        out += std::to_string(a.value);
        out += '\n';
    }
    return out;
}
