// 창에서 바꾸는 설정: 여닫는 단축키와 기능마다 마지막에 넣은 값.
// 글 형식은 한 줄에 "키=값". 모르는 줄은 버리고 틀린 값은 기본값으로 돌린다.
#pragma once

#include <map>
#include <string>

const int HOTKEY_CTRL = 1, HOTKEY_SHIFT = 2, HOTKEY_ALT = 4;

struct Settings {
    int hotkey_vk = 0x54;                            // T
    int hotkey_mods = HOTKEY_CTRL | HOTKEY_SHIFT;
    std::map<std::string, long long> values;         // 값이 있는 기능의 id → 값
};

Settings default_settings();
Settings parse_settings(const std::string &ini);
std::string format_settings(const Settings &s);
bool valid_hotkey(int vk, int mods);                 // 수정키만으로는 안 되고, ESC 만 누른 것은 취소다
std::string hotkey_name(int vk, int mods);           // "Ctrl+Shift+T"

// 파일: %APPDATA%\SR2030ToyBox\ (환경 변수 SRTOYBOX_HOME 이 있으면 그 폴더). 게임 폴더와 문서 폴더에는 쓰지 않는다.
std::wstring settings_dir();                         // 없으면 만든다. 구하지 못하면 빈 글
Settings load_settings();                            // 파일이 없거나 깨져 있으면 기본값
bool save_settings(const Settings &s);
