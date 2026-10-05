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

static MBTOWC g_real;           /* 이 DLL 자신의 임포트(진짜 함수). DllMain 에서 채운다 */
static volatile LONG g_state;   /* 0 미확인, 1 켜짐, 2 꺼짐 */
static volatile LONG g_forced;  /* 환경 변수 SRHOOK 로 강제한 상태(1/2). 0 이면 게임 언어를 따른다 */
static volatile DWORD g_checked; /* 게임 언어를 마지막으로 확인한 시각(GetTickCount) */

#define SRHOOK_RECHECK_MS 500   /* 게임은 옵션 화면에서 언어를 바꾸면 재시작 없이 바로 전환한다. 그 변화를 따라간다 */

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
    DWORD now = GetTickCount();
    if (state == 0) {
        char env[4];
        DWORD n = GetEnvironmentVariableA("SRHOOK", env, sizeof(env)); /* 1/0 으로 강제 */
        if (n == 1 && (env[0] == '0' || env[0] == '1'))
            g_forced = env[0] == '1' ? 1 : 2;
    }
    if (state == 0 || (g_forced == 0 && now - g_checked >= SRHOOK_RECHECK_MS)) {
        state = g_forced ? g_forced : (language_matches() ? 1 : 2);
        g_checked = now;
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

#ifdef SRHOOK_TRACE
/* 진단용 빌드(srkit hook-build --trace): 게임의 레지스트리 접근을 %TEMP%\srhook-trace-<pid>.log 에 적는다.
 * 게임이 설정을 어디서 읽는지(직접 실행과 Steam 실행의 차이 등) 볼 때만 쓴다. 배포용 빌드에는 들어가지 않는다. */
static HANDLE g_log = INVALID_HANDLE_VALUE;
static CRITICAL_SECTION g_log_lock;
static struct {
    HKEY key;
    char path[160];
} g_keys[64];
static LONG g_key_next;

static void trace(const char *fmt, ...)
{
    char line[1024];
    DWORD n, wrote;
    va_list ap;
    va_start(ap, fmt);
    n = (DWORD)wvsprintfA(line, fmt, ap);
    va_end(ap);
    EnterCriticalSection(&g_log_lock);
    WriteFile(g_log, line, n, &wrote, NULL);
    LeaveCriticalSection(&g_log_lock);
}

static const char *key_name(HKEY key, char *scratch)
{
    int i;
    if (key == HKEY_CURRENT_USER)
        return "HKCU";
    if (key == HKEY_LOCAL_MACHINE)
        return "HKLM";
    if (key == HKEY_CLASSES_ROOT)
        return "HKCR";
    if (key == HKEY_USERS)
        return "HKU";
    for (i = 0; i < 64; i++)
        if (g_keys[i].key == key)
            return g_keys[i].path;
    wsprintfA(scratch, "key:%p", (void *)key);
    return scratch;
}

static void remember_key(HKEY key, const char *parent, const char *sub)
{
    int slot = (int)(InterlockedIncrement(&g_key_next) & 63);
    g_keys[slot].key = key;
    lstrcpynA(g_keys[slot].path, parent, 60);
    lstrcatA(g_keys[slot].path, "\\");
    lstrcpynA(g_keys[slot].path + lstrlenA(g_keys[slot].path), sub ? sub : "", 96);
}

static LSTATUS WINAPI trace_open(HKEY key, LPCSTR sub, DWORD options, REGSAM sam, PHKEY out)
{
    char scratch[32];
    const char *parent = key_name(key, scratch);
    LSTATUS st = RegOpenKeyExA(key, sub, options, sam, out);
    trace("open   %s\\%s sam=%lx -> %ld\r\n", parent, sub ? sub : "", (unsigned long)sam, (long)st);
    if (st == ERROR_SUCCESS && out != NULL)
        remember_key(*out, parent, sub);
    return st;
}

static LSTATUS WINAPI trace_create(HKEY key, LPCSTR sub, DWORD reserved, LPSTR cls, DWORD options, REGSAM sam,
                                   const LPSECURITY_ATTRIBUTES sec, PHKEY out, LPDWORD disposition)
{
    char scratch[32];
    const char *parent = key_name(key, scratch);
    LSTATUS st = RegCreateKeyExA(key, sub, reserved, cls, options, sam, sec, out, disposition);
    trace("create %s\\%s sam=%lx -> %ld\r\n", parent, sub ? sub : "", (unsigned long)sam, (long)st);
    if (st == ERROR_SUCCESS && out != NULL)
        remember_key(*out, parent, sub);
    return st;
}

static void trace_value(const char *verb, HKEY key, LPCSTR name, LSTATUS st, DWORD type, const BYTE *data, DWORD size)
{
    char scratch[32];
    const char *where = key_name(key, scratch);
    if (st != ERROR_SUCCESS || data == NULL)
        trace("%s %s [%s] -> %ld\r\n", verb, where, name ? name : "", (long)st);
    else if (type == REG_SZ)
        trace("%s %s [%s] = \"%.200s\"\r\n", verb, where, name ? name : "", (const char *)data);
    else if (type == REG_DWORD && size >= 4)
        trace("%s %s [%s] = %lu\r\n", verb, where, name ? name : "", (unsigned long)*(const DWORD *)data);
    else
        trace("%s %s [%s] type %lu size %lu\r\n", verb, where, name ? name : "", (unsigned long)type, (unsigned long)size);
}

static LSTATUS WINAPI trace_query(HKEY key, LPCSTR name, LPDWORD reserved, LPDWORD type, LPBYTE data, LPDWORD size)
{
    DWORD got = 0;
    LSTATUS st = RegQueryValueExA(key, name, reserved, &got, data, size);
    if (type != NULL)
        *type = got;
    trace_value("query ", key, name, st, got, data, size ? *size : 0);
    return st;
}

static LSTATUS WINAPI trace_set(HKEY key, LPCSTR name, DWORD reserved, DWORD type, const BYTE *data, DWORD size)
{
    LSTATUS st = RegSetValueExA(key, name, reserved, type, data, size);
    trace_value("set   ", key, name, st, type, data, size);
    return st;
}

static void patch_import(HMODULE module, const char *dll, const char *name, void *replacement);

static void trace_start(void)
{
    static const char *const vars[] = {"SteamAppId", "SteamGameId", "SteamClientLaunch", "SteamEnv", "__COMPAT_LAYER",
                                       "SRHOOK_CURSOR"};
    char path[MAX_PATH], text[MAX_PATH];
    HMODULE exe = GetModuleHandleW(NULL);
    int i;
    InitializeCriticalSection(&g_log_lock);
    GetTempPathA(sizeof(path) - 40, path);
    wsprintfA(path + lstrlenA(path), "srhook-trace-%lu.log", (unsigned long)GetCurrentProcessId());
    g_log = CreateFileA(path, GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    trace("cmdline %.400s\r\n", GetCommandLineA());
    GetCurrentDirectoryA(sizeof(text), text);
    trace("cwd     %s\r\n", text);
    for (i = 0; i < (int)(sizeof(vars) / sizeof(vars[0])); i++)
        if (GetEnvironmentVariableA(vars[i], text, sizeof(text)) > 0)
            trace("env     %s=%.100s\r\n", vars[i], text);
    patch_import(exe, "ADVAPI32.dll", "RegOpenKeyExA", (void *)trace_open);
    patch_import(exe, "ADVAPI32.dll", "RegCreateKeyExA", (void *)trace_create);
    patch_import(exe, "ADVAPI32.dll", "RegQueryValueExA", (void *)trace_query);
    patch_import(exe, "ADVAPI32.dll", "RegSetValueExA", (void *)trace_set);
}
#endif /* SRHOOK_TRACE */

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
#ifdef SRHOOK_TRACE
        trace_start();
#endif
    }
    return TRUE;
}
