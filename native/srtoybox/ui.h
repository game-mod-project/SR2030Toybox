// 모드 설정 창의 상태와 내용. 그리기(ui_draw)는 ImGui 프레임 안에서, 나머지는 어느 스레드에서 불러도 된다.
#pragma once

void ui_init();                           // 설정을 읽는다
bool ui_visible();
void ui_toggle();
bool ui_is_hotkey(int vk, int mods);      // 창을 여닫는 단축키인가
bool ui_hit(int x, int y);                // 이 점(그리는 좌표 — overlay_to_drawn)이 열려 있는 설정 창 위인가
bool ui_capturing_hotkey();               // "단축키 바꾸기"를 누르고 새 조합을 기다리는 중인가
void ui_capture_key(int vk, int mods);    // 그때 눌린 키. 수정키만이면 더 기다리고, ESC 만이면 취소한다
void ui_draw();
