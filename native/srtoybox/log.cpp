#include "log.h"

#include <windows.h>

#include <cstdarg>
#include <cstdio>
#include <string>

#include "settings.h"

void log_line(const char *fmt, ...)
{
    char text[400], line[480];
    va_list args;
    va_start(args, fmt);
    vsnprintf(text, sizeof(text), fmt, args);
    va_end(args);

    SYSTEMTIME t;
    GetLocalTime(&t);
    int n = snprintf(line, sizeof(line), "%04d-%02d-%02d %02d:%02d:%02d %s\r\n", t.wYear, t.wMonth, t.wDay, t.wHour, t.wMinute,
                     t.wSecond, text);
    if (n <= 0)
        return;
    if (n >= static_cast<int>(sizeof(line)))
        n = static_cast<int>(sizeof(line)) - 1;

    const std::wstring dir = settings_dir();
    if (dir.empty())
        return;
    const HANDLE f = CreateFileW((dir + L"\\toybox.log").c_str(), FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                                 OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (f == INVALID_HANDLE_VALUE)
        return;
    DWORD written = 0;
    WriteFile(f, line, static_cast<DWORD>(n), &written, nullptr);
    CloseHandle(f);
}
