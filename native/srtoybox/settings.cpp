#include "settings.h"

#include <windows.h>

#include <cstdio>
#include <cstdlib>

#include "features.h"

namespace {

std::string trim(const std::string &s)
{
    size_t a = 0, b = s.size();
    while (a < b && (s[a] == ' ' || s[a] == '\t' || s[a] == '\r'))
        a++;
    while (b > a && (s[b - 1] == ' ' || s[b - 1] == '\t' || s[b - 1] == '\r'))
        b--;
    return s.substr(a, b - a);
}

bool parse_int(const std::string &s, long long &out)
{
    if (s.empty() || s.size() > 18)
        return false;
    char *end = nullptr;
    const long long v = strtoll(s.c_str(), &end, 10);
    if (end == s.c_str() || *end != '\0')
        return false;
    out = v;
    return true;
}

// "keep.stock.<칸>" 과 "keep.stock.<칸>.value" 의 줄. rest 는 "keep.stock." 뒤의 글이다. 칸이나 값이 틀리면 버린다.
void parse_keep_stock(const std::string &rest, long long n, Settings &s)
{
    const size_t dot = rest.find('.');
    const std::string digits = rest.substr(0, dot);
    if (digits.empty() || digits.size() > 2 || digits.find_first_not_of("0123456789") != std::string::npos)
        return;
    const int slot = atoi(digits.c_str());
    if (slot >= STOCK_SLOTS)
        return;
    if (dot == std::string::npos) {
        if (n == 0 || n == 1)
            s.keep_stock[slot] = n == 1;
    } else if (rest.compare(dot, std::string::npos, ".value") == 0 && n >= 0 && n <= KEEP_STOCK_MAX) {
        s.keep_stock_value[slot] = n;
    }
}

std::wstring env(const wchar_t *name)
{
    wchar_t buf[MAX_PATH];
    const DWORD n = GetEnvironmentVariableW(name, buf, MAX_PATH);
    return n > 0 && n < MAX_PATH ? std::wstring(buf, n) : std::wstring();
}

std::wstring settings_path()
{
    const std::wstring dir = settings_dir();
    return dir.empty() ? dir : dir + L"\\toybox.ini";
}

}  // namespace

bool valid_hotkey(int vk, int mods)
{
    if (mods < 0 || mods > 7 || vk < 0x08 || vk > 0xFE)
        return false;
    if (vk == 0x10 || vk == 0x11 || vk == 0x12 || vk == 0x5B || vk == 0x5C || (vk >= 0xA0 && vk <= 0xA5))
        return false;   // Shift · Ctrl · Alt · Win 과 그 좌우
    return !(vk == 0x1B && mods == 0);
}

std::string hotkey_name(int vk, int mods)
{
    std::string out;
    if (mods & HOTKEY_CTRL)
        out += "Ctrl+";
    if (mods & HOTKEY_SHIFT)
        out += "Shift+";
    if (mods & HOTKEY_ALT)
        out += "Alt+";
    if ((vk >= '0' && vk <= '9') || (vk >= 'A' && vk <= 'Z')) {
        out += static_cast<char>(vk);
    } else if (vk >= 0x70 && vk <= 0x87) {
        out += "F" + std::to_string(vk - 0x6F);
    } else {
        char hex[8];
        snprintf(hex, sizeof(hex), "0x%02X", vk & 0xFF);
        out += hex;
    }
    return out;
}

Settings default_settings()
{
    Settings s;
    for (int i = 0; i < FEATURE_COUNT; i++)
        if (FEATURES[i].has_value)
            s.values[FEATURES[i].id] = FEATURES[i].def;
    return s;
}

Settings parse_settings(const std::string &ini)
{
    Settings s = default_settings();
    long long vk = s.hotkey_vk, mods = s.hotkey_mods;
    size_t pos = 0;
    while (pos <= ini.size()) {
        size_t end = ini.find('\n', pos);
        if (end == std::string::npos)
            end = ini.size();
        const std::string line = ini.substr(pos, end - pos);
        pos = end + 1;
        const size_t eq = line.find('=');
        long long n = 0;
        if (eq == std::string::npos || !parse_int(trim(line.substr(eq + 1)), n))
            continue;
        const std::string key = trim(line.substr(0, eq));
        if (key == "hotkey_vk") {
            vk = n;
        } else if (key == "hotkey_mods") {
            mods = n;
        } else if (key == "money.amount") {
            if (n >= MONEY_AMOUNT_MIN && n <= MONEY_AMOUNT_MAX)
                s.money_amount = n;
        } else if (key == "keep.treasury") {
            if (n == 0 || n == 1)
                s.keep_treasury = n == 1;
        } else if (key == "keep.treasury.value") {
            if (n >= 0 && n <= KEEP_TREASURY_MAX)
                s.keep_treasury_value = n;
        } else if (key.compare(0, 11, "keep.stock.") == 0) {
            parse_keep_stock(key.substr(11), n, s);
        } else {
            const Feature *f = find_feature(key.c_str());
            if (f != nullptr && f->has_value && n >= f->min && n <= f->max)
                s.values[f->id] = n;
        }
    }
    if (vk >= 0 && vk <= 0xFE && mods >= 0 && mods <= 7 && valid_hotkey(static_cast<int>(vk), static_cast<int>(mods))) {
        s.hotkey_vk = static_cast<int>(vk);
        s.hotkey_mods = static_cast<int>(mods);
    }
    return s;
}

std::string format_settings(const Settings &s)
{
    std::string out = "hotkey_vk=" + std::to_string(s.hotkey_vk) + "\nhotkey_mods=" + std::to_string(s.hotkey_mods)
        + "\nmoney.amount=" + std::to_string(s.money_amount) + "\n";
    out += "keep.treasury=" + std::to_string(s.keep_treasury ? 1 : 0) + "\nkeep.treasury.value=" + std::to_string(s.keep_treasury_value)
        + "\n";
    for (int slot = 0; slot < STOCK_SLOTS; slot++) {
        const std::string key = "keep.stock." + std::to_string(slot);
        out += key + "=" + std::to_string(s.keep_stock[slot] ? 1 : 0) + "\n" + key + ".value=" + std::to_string(s.keep_stock_value[slot])
            + "\n";
    }
    for (int i = 0; i < FEATURE_COUNT; i++) {
        if (!FEATURES[i].has_value)
            continue;
        const auto found = s.values.find(FEATURES[i].id);
        out += std::string(FEATURES[i].id) + "=" + std::to_string(found == s.values.end() ? FEATURES[i].def : found->second) + "\n";
    }
    return out;
}

std::wstring settings_dir()
{
    std::wstring dir = env(L"SRTOYBOX_HOME");
    if (dir.empty()) {
        dir = env(L"APPDATA");
        if (dir.empty())
            return dir;
        dir += L"\\SR2030ToyBox";
    }
    CreateDirectoryW(dir.c_str(), nullptr);   // 이미 있으면 실패하지만 그대로 쓴다
    return dir;
}

Settings load_settings()
{
    const std::wstring path = settings_path();
    std::string ini;
    if (!path.empty()) {
        const HANDLE f = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (f != INVALID_HANDLE_VALUE) {
            char buf[4096];
            DWORD n = 0;
            if (ReadFile(f, buf, sizeof(buf), &n, nullptr))   // 설정 파일은 1 KB 를 넘지 않는다. 4096 을 넘는 부분은 읽지 않는다
                ini.assign(buf, n);
            CloseHandle(f);
        }
    }
    return parse_settings(ini);
}

bool save_settings(const Settings &s)
{
    const std::wstring path = settings_path();
    if (path.empty())
        return false;
    const std::string ini = format_settings(s);
    const HANDLE f = CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (f == INVALID_HANDLE_VALUE)
        return false;
    DWORD n = 0;
    const BOOL ok = WriteFile(f, ini.data(), static_cast<DWORD>(ini.size()), &n, nullptr);
    CloseHandle(f);
    return ok && n == ini.size();
}
