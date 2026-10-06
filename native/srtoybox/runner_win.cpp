#include "runner_win.h"

#include <mutex>

#include "runner.h"

namespace {

std::mutex g_lock;      // 단추(그리는 스레드)와 틱(창 스레드)이 함께 만진다
Runner g_runner;
BYTE g_before[2];       // 넣기 전의 Ctrl · Shift 상태

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

}  // namespace

bool runner_enqueue(const std::string &command)
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_runner.enqueue(command);
}

void runner_tick(HWND hwnd)
{
    std::lock_guard<std::mutex> lock(g_lock);
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
