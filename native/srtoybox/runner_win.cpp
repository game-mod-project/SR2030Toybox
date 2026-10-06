#include "runner_win.h"

#include <mutex>

#include "game.h"
#include "log.h"
#include "runner.h"

namespace {

std::mutex g_lock;      // 단추(그리는 스레드)와 틱(창 스레드)이 함께 만진다
Runner g_runner;
BYTE g_before[2];       // 넣기 전의 Ctrl · Shift 상태
std::string g_notice;   // 실행하지 못한 까닭
bool g_faulted;         // 직접 실행 중 예외가 났다

// 탈출구: SRTOYBOX_DIRECT=0 이면 주소를 찾아도 명령은 글쇠 방식으로 넣는다.
bool direct_wanted()
{
    static const bool wanted = [] {
        char value[8];
        return !(GetEnvironmentVariableA("SRTOYBOX_DIRECT", value, sizeof(value)) == 1 && value[0] == '0');
    }();
    return wanted;
}

// scripts/gamedrive.py 가 밖에서 하는 일과 같다: 키 상태표에 수정키를 눌린 것으로 적고 메시지를 보낸다.
struct GameSink : Sink {
    HWND hwnd;
    explicit GameSink(HWND h) : hwnd(h) {}

    void mods(bool on) override
    {
        static const int keys[2] = {VK_CONTROL, VK_SHIFT};
        BYTE state[256];
        if (!GetKeyboardState(state))
            return;
        for (int i = 0; i < 2; i++) {
            bool down = true;
            if (on) {
                g_before[i] = state[keys[i]];
            } else if (GetForegroundWindow() == hwnd) {
                down = GetAsyncKeyState(keys[i]) < 0;   // 넣는 동안 사용자가 키를 떼거나 눌렀을 수 있다 — 실제 상태에 맞춘다
            } else {
                down = (g_before[i] & 0x80) != 0;       // 창이 뒤에 있으면 실제 키는 이 창의 것이 아니다 — 넣기 전으로
            }
            state[keys[i]] = static_cast<BYTE>((state[keys[i]] & 0x7F) | (down ? 0x80 : 0));
        }
        SetKeyboardState(state);
    }

    void key(Act act, int value) override
    {
        const WPARAM w = static_cast<WPARAM>(value);
        if (act == Act::Down)
            PostMessageW(hwnd, WM_KEYDOWN, w, 1);
        else if (act == Act::Up)
            PostMessageW(hwnd, WM_KEYUP, w, 0xC0000001);
        else
            PostMessageW(hwnd, WM_CHAR, w, 1);
    }

    unsigned long long now_ms() override { return GetTickCount64(); }
};

// 게임의 명령 처리 함수에 바로 넘긴다. 치트 허용이 꺼져 있으면 먼저 켠다 — 게임의 함수로(비트를 직접 세우지 않는다).
// g_lock 을 쥔 채로 부른다.
void run_direct(const std::string &command, bool cheats_on)
{
    unsigned long code = 0;
    const char *failed = nullptr;
    if (!cheats_on && !game_call("cheat allowcheats", &code))
        failed = "cheat allowcheats";
    else if (!game_call(command.c_str(), &code))
        failed = command.c_str();
    if (failed == nullptr) {
        log_line("직접 실행: %s", command.c_str());
        return;
    }
    // 게임의 상태가 어긋났을 수 있다. 치트를 더 넣지 않는다 — 글쇠 방식으로도
    g_faulted = true;
    g_runner.clear();
    g_notice = "직접 실행 중 오류가 났습니다. 저장하지 말고 게임을 다시 시작하십시오.";
    log_line("직접 실행 중 예외 0x%08lX (%s)", code, failed);
}

}  // namespace

bool runner_enqueue(const std::string &command)
{
    std::lock_guard<std::mutex> lock(g_lock);
    return !g_faulted && g_runner.enqueue(command);
}

void runner_tick(HWND hwnd)
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (g_faulted)
        return;
    if (g_runner.starting()) {
        const GameState game = game_state();
        if (game.known && (!game.in_game || game.multiplayer)) {
            g_runner.clear();   // 누른 뒤 게임에서 나갔다 — 메뉴에 글쇠를 넣지 않고, 게임 밖에서 함수를 부르지 않는다
            g_notice = "게임이 진행 중이 아니어서 실행하지 않았습니다.";
            return;
        }
        g_notice.clear();
        if (game.known && direct_wanted() && game_can_call()) {
            run_direct(g_runner.take(), game.cheats_on);
            return;
        }
    }
    GameSink sink(hwnd);
    g_runner.tick(sink);
}

bool runner_injecting()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_runner.busy();
}

int runner_pending()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return static_cast<int>(g_runner.pending());
}

std::string runner_last()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_runner.last();
}


std::string runner_notice()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_notice;
}

bool runner_faulted()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_faulted;
}

bool runner_direct()
{
    return direct_wanted() && game_can_call();
}
