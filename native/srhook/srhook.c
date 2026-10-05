/* Supreme Ruler 2030 한글 표시용 디코딩 훅.
 *
 * 게임은 문자열을 그릴 때 MultiByteToWideChar(1252), 폭을 잴 때 MultiByteToWideChar(CP_UTF8) 을 부른다.
 * 이 DLL 은 WTSAPI32.dll 이름으로 게임 폴더에 놓여 먼저 로드되고(원래 함수는 시스템 DLL 로 전달),
 * 게임 실행 파일의 임포트 테이블에서 MultiByteToWideChar 를 SR-UTF8 디코더로 바꿔 끼운다.
 * 실행 파일 자체는 건드리지 않는다. 언어가 SRHOOK_LANG 일 때만 동작한다.
 * 그 밖에 검증 도구(scripts/gamedrive.py)용으로 마우스 위치를 대신 알려 주는 기능이 있다(아래 srhook_get_cursor_pos).
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>

#include "srdecode.h"

#ifndef SRHOOK_LANG
#define SRHOOK_LANG "LOCALKO"
#endif

typedef int(WINAPI *MBTOWC)(UINT, DWORD, LPCCH, int, LPWSTR, int);

static MBTOWC g_real;         /* 이 DLL 자신의 임포트(진짜 함수). DllMain 에서 채운다 */
static volatile LONG g_state; /* 0 미확인, 1 켜짐, 2 꺼짐 */

static int language_matches(void)
{
    static const HKEY roots[2] = {HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE}; /* 게임과 같은 우선순위 */
    char buf[64];
    int r;

    for (r = 0; r < 2; r++) {
        DWORD size = sizeof(buf) - 1, type = 0;
        HKEY key;
        LSTATUS st;
        if (RegOpenKeyExA(roots[r], "Software\\BattleGoat\\Supreme Ruler 2030", 0, KEY_READ, &key) != ERROR_SUCCESS)
            continue;
        st = RegQueryValueExA(key, "Language File", NULL, &type, (BYTE *)buf, &size);
        RegCloseKey(key);
        if (st == ERROR_SUCCESS && type == REG_SZ) {
            buf[size] = 0;
            return _stricmp(buf, SRHOOK_LANG) == 0;
        }
    }
    return 0;
}

static int enabled(void)
{
    LONG state = g_state;
    if (state == 0) {
        char env[4];
        DWORD n = GetEnvironmentVariableA("SRHOOK", env, sizeof(env)); /* 1/0 으로 강제 */
        if (n == 1 && (env[0] == '0' || env[0] == '1'))
            state = env[0] == '1' ? 1 : 2;
        else
            state = language_matches() ? 1 : 2;
        g_state = state;
    }
    return state == 1;
}

__declspec(dllexport) int WINAPI srhook_mbtowc(UINT cp, DWORD flags, LPCCH src, int cb, LPWSTR dst, int cch)
{
    size_t n, need, wrote;
    int with_nul = cb < 0;

    if ((cp != 1252 && cp != CP_UTF8) || src == NULL || cb == 0 || cch < 0 || !enabled())
        return g_real(cp, flags, src, cb, dst, cch);

    n = with_nul ? strlen(src) : (size_t)cb;
    need = sr_decode((const unsigned char *)src, n, cp == CP_UTF8, NULL, 0) + (with_nul ? 1 : 0);
    if (cch == 0)
        return (int)need;
    if (dst == NULL) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return 0;
    }
    /* 버퍼가 모자라도 들어가는 만큼은 채운다: 게임이 ASCII 문자열에 널 자리 없이 호출하고 스스로 널을 붙인다 */
    wrote = sr_decode((const unsigned char *)src, n, cp == CP_UTF8, dst, (size_t)cch);
    if (need > (size_t)cch) {
        SetLastError(ERROR_INSUFFICIENT_BUFFER);
        return 0;
    }
    if (with_nul)
        dst[wrote] = 0;
    return (int)need;
}

/* 검증용 마우스 위치. 게임은 마우스가 가리키는 곳을 메시지가 아니라 GetCursorPos 로 읽는다(툴팁, 버튼 강조,
 * 지도 가장자리 스크롤). 창을 화면 밖에 두고 검증할 때는 실제 마우스가 창 위에 있을 수 없으므로, 검증 도구
 * (scripts/gamedrive.py)가 공유 메모리에 적어 준 "창 안 좌표"를 화면 좌표로 바꿔 돌려준다. 실제 마우스는 건드리지 않는다.
 * 환경 변수 SRHOOK_CURSOR=1 로 띄운 게임에만 끼운다 — 평소 실행에서는 아무것도 바꾸지 않는다.
 * (ScreenToClient 쪽을 바꾸면 안 된다: 게임이 그 함수를 다른 계산에도 써서 마우스가 엉뚱한 곳에 있는 것으로 된다.) */
typedef struct {
    volatile LONG on;    /* 1 이면 아래 좌표를 쓴다 */
    LONG x, y;           /* hwnd 의 클라이언트 좌표 */
    volatile LONG reads; /* 게임이 마우스 위치를 물은 횟수(도구가 동작 확인에 쓴다) */
    ULONGLONG hwnd;
} SRCURSOR;              /* 공유 메모리 "Local\srkit.cursor.<프로세스 ID>" — gamedrive.py 의 구조체와 같아야 한다 */

static BOOL(WINAPI *g_real_gcp)(LPPOINT);
static SRCURSOR *g_cursor;
static volatile LONG g_cursor_init;

static SRCURSOR *cursor_shared(void)
{
    if (InterlockedCompareExchange(&g_cursor_init, 1, 0) == 0) {
        wchar_t name[48] = L"Local\\srkit.cursor.", digits[12];
        DWORD pid = GetCurrentProcessId();
        int n = 0, at = lstrlenW(name);
        HANDLE map;
        do {
            digits[n++] = (wchar_t)(L'0' + pid % 10);
            pid /= 10;
        } while (pid);
        while (n)
            name[at++] = digits[--n];
        name[at] = 0;
        map = CreateFileMappingW(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE, 0, sizeof(SRCURSOR), name);
        if (map != NULL)
            g_cursor = (SRCURSOR *)MapViewOfFile(map, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(SRCURSOR));
    }
    return g_cursor;
}

__declspec(dllexport) BOOL WINAPI srhook_get_cursor_pos(LPPOINT pt)
{
    SRCURSOR *c = cursor_shared();
    if (c != NULL) {
        InterlockedIncrement(&c->reads);
        if (pt != NULL && c->on) {
            POINT p;
            p.x = c->x;
            p.y = c->y;
            if (ClientToScreen((HWND)(ULONG_PTR)c->hwnd, &p)) {
                *pt = p;
                return TRUE;
            }
        }
    }
    return g_real_gcp(pt);
}

static void patch_import(HMODULE module, const char *dll, const char *name, void *replacement)
{
    BYTE *base = (BYTE *)module;
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    IMAGE_DATA_DIRECTORY dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    IMAGE_IMPORT_DESCRIPTOR *desc;

    if (dir.VirtualAddress == 0)
        return;
    for (desc = (IMAGE_IMPORT_DESCRIPTOR *)(base + dir.VirtualAddress); desc->Name; desc++) {
        IMAGE_THUNK_DATA *names, *slots;
        if (_stricmp((const char *)(base + desc->Name), dll) != 0 || desc->OriginalFirstThunk == 0)
            continue;
        names = (IMAGE_THUNK_DATA *)(base + desc->OriginalFirstThunk);
        slots = (IMAGE_THUNK_DATA *)(base + desc->FirstThunk);
        for (; names->u1.AddressOfData; names++, slots++) {
            DWORD old;
            if (IMAGE_SNAP_BY_ORDINAL(names->u1.Ordinal))
                continue;
            if (strcmp(((IMAGE_IMPORT_BY_NAME *)(base + names->u1.AddressOfData))->Name, name) != 0)
                continue;
            if (VirtualProtect(&slots->u1.Function, sizeof(void *), PAGE_READWRITE, &old)) {
                slots->u1.Function = (ULONG_PTR)replacement;
                VirtualProtect(&slots->u1.Function, sizeof(void *), old, &old);
            }
        }
    }
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        char env[4];
        DisableThreadLibraryCalls(instance);
        g_real = MultiByteToWideChar;
        g_real_gcp = GetCursorPos;
        patch_import(GetModuleHandleW(NULL), "KERNEL32.dll", "MultiByteToWideChar", (void *)srhook_mbtowc);
        if (GetEnvironmentVariableA("SRHOOK_CURSOR", env, sizeof(env)) == 1 && env[0] == '1' && cursor_shared() != NULL)
            patch_import(GetModuleHandleW(NULL), "USER32.dll", "GetCursorPos", (void *)srhook_get_cursor_pos);
    }
    return TRUE;
}
