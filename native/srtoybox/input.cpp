#include "input.h"

#include <windowsx.h>

#include <mutex>

#include "imgui.h"
#include "imgui_impl_win32.h"
#include "keeper.h"
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
// 실제 키보드에서 온 글쇠 메시지에는 스캔 코드가 있다. 실행기(runner_win.cpp)와 검증 도구(gamedrive.py)가 보내는 것에는 없다
bool from_keyboard(LPARAM l) { return ((l >> 16) & 0xFF) != 0; }

// ANSI 창에서는 한글 한 글자가 WM_CHAR 두 번(코드 페이지의 앞 · 뒤 바이트)으로 온다. ImGui 의 Win32 백엔드는 한 바이트씩
// 바꿔서 깨뜨리므로, 설정 창이 글을 받는 동안에는 여기서 둘을 합쳐 한 글자로 넘긴다. 삼켰으면 true.
bool take_dbcs(ImGuiIO &io, WPARAM w)
{
    static unsigned char lead;
    if (!io.WantTextInput) {
        lead = 0;
        return false;
    }
    const unsigned char byte = static_cast<unsigned char>(w);
    if (lead != 0) {
        const unsigned unit = dbcs_combine(lead, byte, CP_ACP);
        lead = 0;
        if (unit != 0)
            io.AddInputCharacterUTF16(static_cast<ImWchar16>(unit));
        return true;
    }
    if (IsDBCSLeadByteEx(CP_ACP, byte)) {
        lead = byte;
        return true;
    }
    return false;
}
bool is_mouse(UINT m) { return m >= WM_MOUSEFIRST && m <= WM_MOUSELAST; }

LRESULT CALLBACK wrapped(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (!g_timer)
        g_timer = SetTimer(h, TIMER_ID, 10, nullptr) != 0;   // 이 함수는 창을 가진 스레드에서 불린다 — 타이머도 그 스레드의 것이 된다
    if (m == WM_TIMER && w == TIMER_ID) {
        runner_tick(h);
        keeper_tick(GetTickCount64());                       // 값 쓰기 요청과 최소 유지. 게임의 함수 안에서 다시 온 틱이면 스스로 쉰다
        return 0;
    }
    const bool injecting = is_key(m) && runner_injecting();
    if (injecting && !from_keyboard(l))
        return pass(h, m, w, l);                             // 실행기가 넣는 글쇠다 — 설정 창이 가로채지 않는다
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
            int x = GET_X_LPARAM(l), y = GET_Y_LPARAM(l);
            LPARAM drawn = l;                                // ImGui 에는 그리는 좌표로 알려 준다. 게임에는 받은 그대로 넘긴다
            if (positioned) {
                overlay_to_drawn(h, &x, &y);
                drawn = MAKELPARAM(x, y);
                io.AddMousePosEvent(static_cast<float>(x), static_cast<float>(y));
            }
            if (!g_unicode && m == WM_CHAR && take_dbcs(io, w)) {
                swallow = true;
            } else {
                ImGui_ImplWin32_WndProcHandler(h, m, w, drawn);
                if (is_mouse(m))   // 창 위인지는 사각형으로 직접 가린다 — ImGui 의 판단(WantCaptureMouse)은 한 프레임 늦다
                    swallow = (positioned && ui_hit(x, y)) || io.WantCaptureMouse;
                else
                    swallow = io.WantCaptureKeyboard;
            }
        }
        if (swallow)
            return 0;
    }
    // 실행기가 넣는 동안 사용자가 누른 글쇠는 게임에 넘기지 않는다 — 치트를 받아 적는 줄에 섞인다.
    // 뗌은 넘긴다(게임이 그 글쇠를 눌린 채로 알지 않게). Alt 조합(WM_SYS*)도 넘긴다(Alt+F4 등)
    if (injecting && (m == WM_KEYDOWN || m == WM_CHAR || m == WM_DEADCHAR || m == WM_UNICHAR))
        return 0;
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
    // 타이머는 창 스레드에서 걸어야 해서 감싼 프로시저가 처음 불릴 때 건다. 그때까지 기다리지 않게 빈 메시지로 한 번 깨운다 —
    // 최소 유지는 사용자가 아무것도 누르지 않아도 돌아야 한다.
    PostMessageW(game, WM_NULL, 0, 0);
}

unsigned dbcs_combine(unsigned char lead, unsigned char trail, unsigned codepage)
{
    const char bytes[2] = {static_cast<char>(lead), static_cast<char>(trail)};
    wchar_t unit = 0;
    return MultiByteToWideChar(codepage, MB_ERR_INVALID_CHARS, bytes, 2, &unit, 1) == 1 ? static_cast<unsigned>(unit) : 0;
}
