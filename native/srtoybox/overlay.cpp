#include "overlay.h"

#include <windows.h>

#include <d3d11.h>
#include <dxgi1_2.h>

#include <cstddef>
#include <cstring>
#include <string>

#include "imgui.h"
#include "imgui_impl_dx11.h"
#include "imgui_impl_win32.h"
#include "input.h"
#include "log.h"
#include "prologue.h"
#include "settings.h"
#include "ui.h"

namespace {

typedef HRESULT(STDMETHODCALLTYPE *PresentFn)(IDXGISwapChain *, UINT, UINT);
typedef HRESULT(STDMETHODCALLTYPE *Present1Fn)(IDXGISwapChain1 *, UINT, UINT, const DXGI_PRESENT_PARAMETERS *);
typedef HRESULT(STDMETHODCALLTYPE *ResizeFn)(IDXGISwapChain *, UINT, UINT, UINT, DXGI_FORMAT, UINT);

const int SLOT_PRESENT = 8, SLOT_RESIZE = 13, SLOT_PRESENT1 = 22;   // IDXGISwapChain · IDXGISwapChain1 의 가상 함수 번호

const int COVER = 14;   // 깨끗한 진입로가 덮는 바이트 수: 다른 훅이 함수 머리에 심는 점프(5 ~ 14바이트)를 넘겨야 한다

// 가상 함수 표의 한 칸. 같은 함수에 다른 프로그램(Steam 오버레이 등)도 끼어든다 — 표의 칸을 바꾸거나, 함수의 머리에 점프를 심는다.
struct Slot {
    void **entry;       // 표의 그 칸
    void *ours;         // 우리 함수
    void *found;        // 끼어들 때 그 칸에 있던 것 — 원래 함수이거나, 표에 먼저 끼어든 다른 훅
    void *clean;        // 깨끗한 진입로: 원래 함수의 첫 명령들(파일에서 읽은 것)을 실행하고 그 뒤로 이어 간다. 누가 심은 점프도 건너뛴다
    BYTE head[8];       // 끼어들 때 우리 함수의 첫 바이트(누가 우리 함수의 머리에 점프를 심었는지 알아본다)
};

Slot g_present, g_present1, g_resize;
IDXGISwapChain *g_swap;                  // 게임의 swap chain (처음 걸린 것)
ID3D11Device *g_device;
ID3D11DeviceContext *g_context;
ID3D11RenderTargetView *g_target;
UINT g_width, g_height;                  // 게임이 그리는 면(뒷면)의 크기. 게임 창의 크기와 다를 수 있다
bool g_ready, g_failed;
std::string g_ini_path;
const char *g_refusal;                   // 끼어들지 않은 까닭(로그에 적는다)
thread_local bool t_inside, t_resizing;  // 이 스레드가 지금 우리 훅 안에 있다(재진입을 알아본다)

void *refuse(const char *why)
{
    g_refusal = why;
    return nullptr;
}

// 다음에 부를 것. 끼어들 때 있던 것을 부르는 것은 우리가 맨 위일 때뿐이다.
// 아래 셋 가운데 하나면 다른 훅이 이미 돌았거나 우리를 원래 함수로 알고 되부른 것이다 — 깨끗한 진입로로 진짜 함수에 바로 간다:
//   재진입 / 표의 칸이 우리 것이 아니게 됐다 / 우리 함수의 머리에 누가 점프를 심었다.
// Steam 오버레이는 진짜 Present 의 머리에 점프를 심어 두고, 표에서 본 우리 함수를 "원래 함수"로 부른다. 그때 진짜 함수를
// 그대로 부르면 그 점프를 타고 오버레이로 되돌아가 서로 맴돌다 스택이 바닥난다
// [확인: Steam 으로 띄운 게임이 두 번 죽었다, 2026-10-06. tests/toybox_overlay_probe.py 의 inline 이 그 상황이다].
void *next(const Slot &slot, bool nested)
{
    if (nested || *slot.entry != slot.ours || memcmp(slot.ours, slot.head, sizeof(slot.head)) != 0)
        return slot.clean;
    return slot.found;
}

std::string utf8(const std::wstring &w)
{
    if (w.empty())
        return std::string();
    const int n = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), static_cast<int>(w.size()), nullptr, 0, nullptr, nullptr);
    std::string out(static_cast<size_t>(n), '\0');
    WideCharToMultiByte(CP_UTF8, 0, w.c_str(), static_cast<int>(w.size()), &out[0], n, nullptr, nullptr);
    return out;
}

// 게임의 첫 Present 에서 한 번. 게임이 그리는 창이 곧 주 창이다.
bool init(IDXGISwapChain *swap)
{
    DXGI_SWAP_CHAIN_DESC desc;
    DWORD pid = 0;
    if (FAILED(swap->GetDesc(&desc)) || desc.OutputWindow == nullptr)
        return false;
    GetWindowThreadProcessId(desc.OutputWindow, &pid);
    if (pid != GetCurrentProcessId())
        return false;
    if (FAILED(swap->GetDevice(__uuidof(ID3D11Device), reinterpret_cast<void **>(&g_device)))) {
        g_failed = true;
        log_line("DirectX 11 장치가 아닙니다 — ToyBox 는 그리지 않습니다");
        return false;
    }
    g_device->GetImmediateContext(&g_context);

    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO &io = ImGui::GetIO();
    const std::wstring dir = settings_dir();
    g_ini_path = dir.empty() ? std::string() : utf8(dir + L"\\imgui.ini");
    io.IniFilename = g_ini_path.empty() ? nullptr : g_ini_path.c_str();
    io.ConfigFlags |= ImGuiConfigFlags_NoMouseCursorChange;   // 게임의 마우스 커서를 건드리지 않는다

    wchar_t windir[MAX_PATH];
    std::wstring font;
    if (GetWindowsDirectoryW(windir, MAX_PATH) > 0)
        font = std::wstring(windir) + L"\\Fonts\\malgun.ttf";
    if (!font.empty() && GetFileAttributesW(font.c_str()) != INVALID_FILE_ATTRIBUTES)
        io.Fonts->AddFontFromFileTTF(utf8(font).c_str(), 18.0f, nullptr, io.Fonts->GetGlyphRangesKorean());
    else
        log_line("맑은 고딕(malgun.ttf)이 없습니다 — 한글이 깨져 보입니다");
    ImGui::StyleColorsDark();

    if (!ImGui_ImplWin32_Init(desc.OutputWindow) || !ImGui_ImplDX11_Init(g_device, g_context)) {
        g_failed = true;
        log_line("ImGui 초기화에 실패했습니다 — ToyBox 는 그리지 않습니다");
        return false;
    }
    g_swap = swap;
    g_width = desc.BufferDesc.Width;
    g_height = desc.BufferDesc.Height;
    g_ready = true;
    input_install(desc.OutputWindow);
    log_line("창 준비됨 (%ux%u)", desc.BufferDesc.Width, desc.BufferDesc.Height);
    return true;
}

void draw(IDXGISwapChain *swap)
{
    std::lock_guard<std::recursive_mutex> lock(ui_mutex());
    if (g_failed || (!g_ready && !init(swap)) || swap != g_swap || !ui_visible())
        return;
    if (g_target == nullptr) {
        ID3D11Texture2D *back = nullptr;
        if (FAILED(swap->GetBuffer(0, __uuidof(ID3D11Texture2D), reinterpret_cast<void **>(&back))))
            return;
        D3D11_TEXTURE2D_DESC size;
        back->GetDesc(&size);
        const HRESULT hr = g_device->CreateRenderTargetView(back, nullptr, &g_target);
        back->Release();
        if (FAILED(hr)) {
            g_target = nullptr;
            return;
        }
        g_width = size.Width;       // 크기가 바뀌면 hooked_resize 가 g_target 을 놓으므로 여기를 다시 지난다
        g_height = size.Height;
    }
    ImGui_ImplDX11_NewFrame();
    ImGui_ImplWin32_NewFrame();
    // ImGui 는 게임 창의 크기를 화면 크기로 안다. 게임이 창과 다른 크기로 그리면(화면에 늘려 보인다) 그리는 면의 크기로 고쳐 준다
    ImGui::GetIO().DisplaySize = ImVec2(static_cast<float>(g_width), static_cast<float>(g_height));
    ImGui::NewFrame();
    ui_draw();
    ImGui::Render();

    ID3D11RenderTargetView *old_target = nullptr;   // 게임이 걸어 둔 렌더 대상을 돌려놓는다
    ID3D11DepthStencilView *old_depth = nullptr;
    g_context->OMGetRenderTargets(1, &old_target, &old_depth);
    g_context->OMSetRenderTargets(1, &g_target, nullptr);
    ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());
    g_context->OMSetRenderTargets(1, &old_target, old_depth);
    if (old_target != nullptr)
        old_target->Release();
    if (old_depth != nullptr)
        old_depth->Release();
}

HRESULT STDMETHODCALLTYPE hooked_present(IDXGISwapChain *swap, UINT sync, UINT flags)
{
    const bool nested = t_inside;
    if (!nested) {
        t_inside = true;
        if (!(flags & DXGI_PRESENT_TEST))
            draw(swap);
    }
    void *const target = next(g_present, nested);
    static bool told;
    if (target == g_present.clean && target != g_present.found && !told) {   // 문제가 생겼을 때 어떤 길을 탔는지 알 수 있게 한 번만 적는다
        told = true;
        log_line("다른 훅과 함께 돕니다 (%s)", nested ? "우리를 되불렀다" : *g_present.entry != g_present.ours ? "표의 칸이 바뀌었다"
                                                                                                          : "우리 함수의 머리에 점프가 심겼다");
    }
    const HRESULT hr = reinterpret_cast<PresentFn>(target)(swap, sync, flags);
    if (!nested)
        t_inside = false;
    return hr;
}

HRESULT STDMETHODCALLTYPE hooked_present1(IDXGISwapChain1 *swap, UINT sync, UINT flags, const DXGI_PRESENT_PARAMETERS *params)
{
    const bool nested = t_inside;   // Present 가 안에서 Present1 을 부르는 경우에도 한 번만 그린다
    if (!nested) {
        t_inside = true;
        if (!(flags & DXGI_PRESENT_TEST))
            draw(swap);
    }
    const HRESULT hr = reinterpret_cast<Present1Fn>(next(g_present1, nested))(swap, sync, flags, params);
    if (!nested)
        t_inside = false;
    return hr;
}

HRESULT STDMETHODCALLTYPE hooked_resize(IDXGISwapChain *swap, UINT count, UINT width, UINT height, DXGI_FORMAT format, UINT flags)
{
    const bool nested = t_resizing;
    if (!nested) {
        t_resizing = true;
        std::lock_guard<std::recursive_mutex> lock(ui_mutex());
        if (swap == g_swap && g_target != nullptr) {   // 뒷면을 쥐고 있으면 크기를 바꾸지 못한다
            g_target->Release();
            g_target = nullptr;
        }
    }
    const HRESULT hr = reinterpret_cast<ResizeFn>(next(g_resize, nested))(swap, count, width, height, format, flags);
    if (!nested)
        t_resizing = false;
    return hr;
}

HMODULE module_of(const void *address)
{
    HMODULE module = nullptr;
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                       reinterpret_cast<LPCWSTR>(address), &module);
    return module;
}

bool read_at(HANDLE file, ULONGLONG offset, void *out, DWORD size)
{
    LARGE_INTEGER pos;
    DWORD got = 0;
    pos.QuadPart = static_cast<LONGLONG>(offset);
    return SetFilePointerEx(file, pos, nullptr, FILE_BEGIN) && ReadFile(file, out, size, &got, nullptr) && got == size;
}

// 올라와 있는 DLL 이 디스크의 그 파일과 같은 판인가. 게임이 떠 있는 동안 파일이 바뀌면(Windows 업데이트) 다르다 —
// 그때 파일에서 읽은 바이트는 메모리의 함수와 아무 상관이 없다.
bool same_build(HMODULE module, const IMAGE_NT_HEADERS64 &file)
{
    const BYTE *const base = reinterpret_cast<const BYTE *>(module);
    const IMAGE_DOS_HEADER *const dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(base);
    if (dos->e_magic != IMAGE_DOS_SIGNATURE)
        return false;
    const IMAGE_NT_HEADERS64 *const loaded = reinterpret_cast<const IMAGE_NT_HEADERS64 *>(base + dos->e_lfanew);
    return loaded->Signature == IMAGE_NT_SIGNATURE && loaded->FileHeader.TimeDateStamp == file.FileHeader.TimeDateStamp
        && loaded->OptionalHeader.SizeOfImage == file.OptionalHeader.SizeOfImage
        && loaded->OptionalHeader.CheckSum == file.OptionalHeader.CheckSum;
}

// 메모리의 DLL 은 다른 훅이 이미 고쳐 놓았을 수 있다(표의 칸, 함수의 머리). 디스크의 파일에서 원래 바이트를 읽는다.
// address 는 올라와 있는 DLL 안의 주소. 실행 파일이 아니라 시스템 DLL(dxgi.dll)을 읽는다.
bool read_image(const void *address, void *out, DWORD size, ULONGLONG *preferred_base, ULONGLONG *image_size)
{
    const HMODULE module = module_of(address);
    wchar_t path[MAX_PATH];
    const char *why = "DLL 파일에서 원래 함수를 읽지 못했습니다";
    const DWORD n = module == nullptr ? 0 : GetModuleFileNameW(module, path, MAX_PATH);
    if (n == 0 || n >= MAX_PATH)
        return refuse(why) != nullptr;
    const HANDLE file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING,
                                    FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE)
        return refuse(why) != nullptr;

    bool ok = false;
    IMAGE_DOS_HEADER dos = {};
    IMAGE_NT_HEADERS64 nt = {};
    const ULONGLONG rva = reinterpret_cast<ULONGLONG>(address) - reinterpret_cast<ULONGLONG>(module);
    const bool parsed = read_at(file, 0, &dos, sizeof(dos)) && dos.e_magic == IMAGE_DOS_SIGNATURE
        && read_at(file, static_cast<ULONGLONG>(dos.e_lfanew), &nt, sizeof(nt)) && nt.Signature == IMAGE_NT_SIGNATURE
        && nt.OptionalHeader.Magic == IMAGE_NT_OPTIONAL_HDR64_MAGIC;
    if (parsed && !same_build(module, nt)) {
        why = "올라와 있는 DLL 이 디스크의 파일과 다릅니다";
    } else if (parsed) {
        const ULONGLONG sections = static_cast<ULONGLONG>(dos.e_lfanew) + offsetof(IMAGE_NT_HEADERS64, OptionalHeader)
            + nt.FileHeader.SizeOfOptionalHeader;
        for (WORD i = 0; i < nt.FileHeader.NumberOfSections; i++) {
            IMAGE_SECTION_HEADER sec;
            if (!read_at(file, sections + i * sizeof(sec), &sec, sizeof(sec)))
                break;
            if (rva < sec.VirtualAddress || rva + size > static_cast<ULONGLONG>(sec.VirtualAddress) + sec.SizeOfRawData)
                continue;
            ok = read_at(file, sec.PointerToRawData + (rva - sec.VirtualAddress), out, size);
            *preferred_base = nt.OptionalHeader.ImageBase;
            *image_size = nt.OptionalHeader.SizeOfImage;
            break;
        }
    }
    CloseHandle(file);
    return ok || refuse(why) != nullptr;
}

// 표의 그 칸에 원래 들어 있던 함수. 파일에는 기준 주소에 맞춘 값이 적혀 있으므로 지금 올라온 주소로 옮긴다.
void *original_function(void **entry)
{
    ULONGLONG value = 0, preferred = 0, size = 0;
    if (!read_image(entry, &value, sizeof(value), &preferred, &size))
        return nullptr;
    const ULONGLONG base = reinterpret_cast<ULONGLONG>(module_of(entry));
    const ULONGLONG moved = value - preferred + base;
    return moved >= base && moved < base + size ? reinterpret_cast<void *>(moved) : refuse("가상 함수 표의 원래 값을 알 수 없습니다");
}

// 깨끗한 진입로를 만든다: 함수의 원래 첫 명령들(파일에서 읽은 것)을 그대로 실행한 뒤 함수의 그 다음 자리로 뛴다.
// 누가 함수 머리에 점프를 심어 놓았어도 이 길은 그것을 밟지 않는다. 옮길 수 없는 명령이 있으면 만들지 않는다(nullptr).
// patched 에는 메모리의 함수 머리가 파일과 다른지(= 누가 이미 고쳤는지)를 적는다.
void *make_clean_entry(void *function, bool *patched)
{
    BYTE head[32];
    ULONGLONG preferred = 0, size = 0;
    if (!read_image(function, head, sizeof(head), &preferred, &size))
        return nullptr;
    const int length = prologue_length(head, static_cast<int>(sizeof(head)), COVER);
    if (length == 0)
        return refuse("원래 함수의 머리를 옮길 수 없습니다");
    // 진입로는 함수의 length 번째 바이트로 뛴다. 거기서부터가 파일과 다르면(COVER 보다 긴 훅이 걸쳐 있다) 명령의 한가운데로 뛰게 된다
    if (memcmp(static_cast<const BYTE *>(function) + length, head + length, sizeof(head) - static_cast<size_t>(length)) != 0)
        return refuse("다른 훅이 원래 함수의 머리를 길게 고쳐 놓았습니다");
    BYTE *code = static_cast<BYTE *>(VirtualAlloc(nullptr, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));
    if (code == nullptr)
        return refuse("메모리를 얻지 못했습니다");
    const ULONGLONG rest = reinterpret_cast<ULONGLONG>(function) + static_cast<ULONGLONG>(length);
    static const BYTE jump[6] = {0xFF, 0x25, 0x00, 0x00, 0x00, 0x00};   // jmp [rip+0] — 바로 뒤의 8바이트가 갈 곳
    memcpy(code, head, static_cast<size_t>(length));
    memcpy(code + length, jump, sizeof(jump));
    memcpy(code + length + sizeof(jump), &rest, sizeof(rest));
    FlushInstructionCache(GetCurrentProcess(), code, 64);
    *patched = memcmp(function, head, static_cast<size_t>(length)) != 0;
    return code;
}

// 표의 한 칸을 바꿔 쓴다.
bool write_entry(void **entry, void *value)
{
    DWORD old = 0;
    if (!VirtualProtect(entry, sizeof(void *), PAGE_READWRITE, &old))
        return false;
    *entry = value;
    VirtualProtect(entry, sizeof(void *), old, &old);
    return true;
}

// 표의 한 칸에 끼어들 준비를 한다 — 넘길 곳을 다 적어 둘 뿐 표는 아직 고치지 않는다.
// 반환: 0 끼어들 수 없다, 1 된다, 2 되고 다른 훅이 먼저 있다(표의 칸이나 함수의 머리에).
int prepare_slot(Slot &slot, void **table, int index, void *ours)
{
    bool patched = false;
    void *const found = table[index];
    // 그 칸의 값이 표와 같은 DLL 안을 가리키면 그것이 원래 함수다. 아니면(표에 다른 훅이 있다) 파일에서 원래 값을 읽는다
    const bool in_table = module_of(found) != module_of(&table[index]);
    void *const function = in_table ? original_function(&table[index]) : found;
    void *const clean = function == nullptr ? nullptr : make_clean_entry(function, &patched);
    if (clean == nullptr)
        return 0;
    slot.entry = &table[index];
    slot.ours = ours;
    slot.found = found;
    slot.clean = clean;
    memcpy(slot.head, ours, sizeof(slot.head));
    return in_table || patched ? 2 : 1;
}

}  // namespace

std::recursive_mutex &ui_mutex()
{
    static std::recursive_mutex m;   // Present 안에서 창 메시지가 같은 스레드로 들어올 수 있어 재진입을 허용한다
    return m;
}

bool overlay_ready()
{
    std::lock_guard<std::recursive_mutex> lock(ui_mutex());
    return g_ready;
}

void overlay_to_drawn(HWND window, int *x, int *y)
{
    std::lock_guard<std::recursive_mutex> lock(ui_mutex());
    RECT client;
    if (g_width == 0 || g_height == 0 || !GetClientRect(window, &client) || client.right <= 0 || client.bottom <= 0)
        return;
    *x = MulDiv(*x, static_cast<int>(g_width), client.right);
    *y = MulDiv(*y, static_cast<int>(g_height), client.bottom);
}

bool overlay_install()
{
    const HINSTANCE instance = GetModuleHandleW(nullptr);
    WNDCLASSEXW wc = {};
    wc.cbSize = sizeof(wc);
    wc.lpfnWndProc = DefWindowProcW;
    wc.hInstance = instance;
    wc.lpszClassName = L"srtoybox.probe";
    RegisterClassExW(&wc);
    const HWND probe = CreateWindowExW(0, wc.lpszClassName, L"", WS_OVERLAPPEDWINDOW, 0, 0, 64, 64, nullptr, nullptr, instance, nullptr);
    if (probe == nullptr) {
        log_line("임시 창을 만들지 못했습니다 (%lu)", GetLastError());
        return false;
    }

    DXGI_SWAP_CHAIN_DESC desc = {};
    desc.BufferCount = 1;
    desc.BufferDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    desc.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
    desc.OutputWindow = probe;
    desc.SampleDesc.Count = 1;
    desc.Windowed = TRUE;
    IDXGISwapChain *swap = nullptr;
    ID3D11Device *device = nullptr;
    ID3D11DeviceContext *context = nullptr;
    HRESULT hr = D3D11CreateDeviceAndSwapChain(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, 0, nullptr, 0, D3D11_SDK_VERSION, &desc,
                                               &swap, &device, nullptr, &context);
    if (FAILED(hr))
        hr = D3D11CreateDeviceAndSwapChain(nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0, nullptr, 0, D3D11_SDK_VERSION, &desc, &swap,
                                           &device, nullptr, &context);
    int present = 0, resize = 0;
    if (SUCCEEDED(hr)) {
        void **table = *reinterpret_cast<void ***>(swap);
        present = prepare_slot(g_present, table, SLOT_PRESENT, reinterpret_cast<void *>(hooked_present));
        if (present != 0)
            resize = prepare_slot(g_resize, table, SLOT_RESIZE, reinterpret_cast<void *>(hooked_resize));
        // 둘 다 될 때만 표를 고친다. 그리기만 하고 크기 바꾸기를 놓치면 뒷면을 쥔 채 놓지 못해 게임이 화면 크기를 못 바꾼다.
        // 크기 바꾸기부터 고친다 — Present 를 고치자마자 그리기 시작해도 놓을 길이 이미 있다
        if (resize != 0 && !write_entry(g_resize.entry, g_resize.ours))
            resize = refuse("가상 함수 표를 고칠 수 없습니다") != nullptr;
        if (resize != 0 && !write_entry(g_present.entry, g_present.ours)) {
            write_entry(g_resize.entry, g_resize.found);
            resize = refuse("가상 함수 표를 고칠 수 없습니다") != nullptr;
        }
        IDXGISwapChain1 *swap1 = nullptr;
        if (resize != 0 && SUCCEEDED(swap->QueryInterface(__uuidof(IDXGISwapChain1), reinterpret_cast<void **>(&swap1)))) {
            void **table1 = *reinterpret_cast<void ***>(swap1);
            if (prepare_slot(g_present1, table1, SLOT_PRESENT1, reinterpret_cast<void *>(hooked_present1)) == 0
                || (!write_entry(g_present1.entry, g_present1.ours) && refuse("가상 함수 표를 고칠 수 없습니다") == nullptr))
                log_line("Present1 에는 끼어들지 못했습니다 (%s) — 게임이 그것으로 화면을 내보내면 창이 보이지 않습니다", g_refusal);
            swap1->Release();
        }
        context->Release();
        device->Release();
        swap->Release();
    }
    DestroyWindow(probe);
    UnregisterClassW(wc.lpszClassName, instance);
    const bool ok = present != 0 && resize != 0;
    if (ok)
        log_line("화면에 끼어들었습니다%s", present == 2 ? " (다른 훅이 먼저 있습니다)" : "");
    else if (FAILED(hr))
        log_line("화면에 끼어들지 못했습니다 (0x%08lX) — ToyBox 는 동작하지 않습니다", static_cast<unsigned long>(hr));
    else
        log_line("화면에 끼어들지 못했습니다 (%s) — ToyBox 는 동작하지 않습니다", g_refusal != nullptr ? g_refusal : "까닭을 알 수 없습니다");
    return ok;
}
