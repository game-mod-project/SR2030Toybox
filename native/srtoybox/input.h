// 게임 창의 창 프로시저를 감싼다: 실행기의 타이머, 여닫는 단축키, 설정 창으로 가는 입력.
#pragma once

#include <windows.h>

void input_install(HWND game_window);

// 코드 페이지의 앞 · 뒤 바이트를 한 글자(UTF-16)로. 2바이트 글자가 아니면 0.
unsigned dbcs_combine(unsigned char lead, unsigned char trail, unsigned codepage);
