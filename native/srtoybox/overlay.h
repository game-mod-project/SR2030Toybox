// 게임이 화면을 내보내는 자리(swap chain 의 Present)에 끼어들어 ImGui 로 설정 창을 그린다.
// 실행 파일의 주소를 쓰지 않는다: 임시 swap chain 에서 가상 함수 표의 주소를 얻는다.
#pragma once

#include <mutex>

bool overlay_install();                 // 끼어든다. 실패하면 false — 게임은 그대로 돈다
bool overlay_ready();                   // ImGui 가 준비됐다(게임의 첫 Present 뒤)
std::recursive_mutex &ui_mutex();       // ImGui 와 창의 상태를 만지는 곳은 이 잠금 안에서 (그리기 · 입력 전달 · ui_*)
