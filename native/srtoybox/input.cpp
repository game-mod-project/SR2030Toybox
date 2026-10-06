#include "input.h"

#include <windowsx.h>

#include <mutex>

#include "imgui.h"
#include "imgui_impl_win32.h"
#include "overlay.h"
#include "runner_win.h"
#include "settings.h"
#include "ui.h"

extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);

namespace {

const UINT_PTR TIMER_ID = 0x7B0C0001;   // 게임의 타이머와 겹치지 않을 값
WNDPROC g_original;
bool g_unicode, g_timer;

// 게임 창의 문자 방식(A/W)대로 넘긴다 — 글자 메시지의 변환이 달라지지 않게
LRESULT pass(HWND h, UINT m, WPARAM w, LPARAM l)
{
    return g_unicode ? CallWindowProcW(g_original, h, m, w, l) : CallWindowProcA(g_original, h, m, w, l);
}

int mods_now()
{
    return (GetKeyState(VK_CONTROL) < 0 ? HOTKEY_CTRL : 0) | (GetKeyState(VK_SHIFT) < 0 ? HOTKEY_SHIFT : 0)
        | (GetKeyState(VK_MENU) < 0 ? HOTKEY_ALT : 0);
}

bool is_key(UINT m) { return m >= WM_KEYFIRST && m <= WM_KEYLAST; }
bool is_mouse(UINT m) { return m >= WM_MOUSEFIRST && m <= WM_MOUSELAST; }

LRESULT CALLBACK wrapped(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (!g_timer)
        g_timer = SetTimer(h, TIMER_ID, 10, nullptr) != 0;   // 이 함수는 창을 가진 스레드에서 불린다 — 타이머도 그 스레드의 것이 된다
    if (m == WM_TIMER && w == TIMER_ID) {
        runner_tick(h);
        return 0;
    }
    if (is_key(m) && runner_injecting())
        return pass(h, m, w, l);                             // 실행기가 넣는 중이다 — 설정 창이 가로채지 않는다
    if (m == WM_KEYDOWN || m == WM_SYSKEYDOWN) {
        const int vk = static_cast<int>(w);
        if (ui_capturing_hotkey()) {
            ui_capture_key(vk, mods_now());
            return 0;
        }
        if (!(l & 0x40000000) && ui_is_hotkey(vk, mods_now())) {   // 누르고 있어서 반복되는 것은 세지 않는다
            ui_toggle();
            return 0;
        }
    }
    // WM_MOUSELEAVE 는 넘기지 않는다: 화면 밖 검증에서는 실제 마우스가 창 밖이라, 넘기면 ImGui 가 마우스 위치를 지운다
    if ((is_key(m) || is_mouse(m)) && ui_visible() && overlay_ready()) {
        bool swallow = false;
        {
            std::lock_guard<std::recursive_mutex> lock(ui_mutex());
            ImGuiIO &io = ImGui::GetIO();
            const bool positioned = is_mouse(m) && m != WM_MOUSEWHEEL && m != WM_MOUSEHWHEEL;   // 휠의 좌표는 화면 좌표다
            if (positioned)
                io.AddMousePosEvent(static_cast<float>(GET_X_LPARAM(l)), static_cast<float>(GET_Y_LPARAM(l)));
            ImGui_ImplWin32_WndProcHandler(h, m, w, l);
            if (is_mouse(m))   // 창 위인지는 사각형으로 직접 가린다 — ImGui 의 판단(WantCaptureMouse)은 한 프레임 늦다
                swallow = (positioned && ui_hit(GET_X_LPARAM(l), GET_Y_LPARAM(l))) || io.WantCaptureMouse;
            else
                swallow = io.WantCaptureKeyboard;
        }
        if (swallow)
            return 0;
    }
    return pass(h, m, w, l);
}

}  // namespace

void input_install(HWND game)
{
    g_unicode = IsWindowUnicode(game) != FALSE;
    if (g_unicode) {
        g_original = reinterpret_cast<WNDPROC>(GetWindowLongPtrW(game, GWLP_WNDPROC));
        SetWindowLongPtrW(game, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(wrapped));
    } else {
        g_original = reinterpret_cast<WNDPROC>(GetWindowLongPtrA(game, GWLP_WNDPROC));
        SetWindowLongPtrA(game, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(wrapped));
    }
}
