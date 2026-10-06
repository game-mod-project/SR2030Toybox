// 기능 → 게임에 넣을 글, 그리고 그 글을 게임의 설정 창에 넣는 동작의 순서. 창도 게임도 모르는 순수 함수다.
#pragma once

#include <string>
#include <vector>

#include "features.h"

// 값은 기능의 범위로 잘라 맞춘다. 값이 없는 기능은 값을 무시한다.
std::string build_command(const Feature &f, long long value);

enum class Act { Mods, Down, Up, Char, Wait };

struct Action {
    Act act;
    int value;   // Mods: 1 누름 / 0 되돌림, Down·Up: 가상 키 코드, Char: 글자, Wait: 밀리초
};

// 명령 한 개를 넣는 동작의 순서: 설정 창 열기(Ctrl+Shift+S) → cheat allowcheats → 명령 → ESC.
// scripts/gamedrive.py 가 밖에서 넣는(게임에서 확인된) 순서와 간격을 그대로 따른다.
// 게임의 입력란이 받을 수 없는 글(빈 글, ASCII 밖, 64자 초과)이면 빈 목록을 준다.
std::vector<Action> plan_command(const std::string &command);

std::string describe(const std::vector<Action> &plan);   // 한 줄에 동작 하나: "DOWN 83"
