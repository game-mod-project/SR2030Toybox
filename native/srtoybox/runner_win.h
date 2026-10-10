// 게임 안의 실행기: Runner(runner.h)에 게임 창으로 실제로 보내는 Sink 를 물린 것.
#pragma once

#include <windows.h>

#include <string>

bool runner_enqueue(const std::string &command);   // 받지 못하면 false (가득 참)
void runner_tick(HWND hwnd);                       // 게임 창을 가진 스레드에서만 부른다(키 상태표가 그 스레드의 것이다)
bool runner_injecting();                           // 넣는 중인가 — 그동안의 키 메시지는 입력 끼어들기가 게임에 그대로 넘긴다
int runner_pending();
std::string runner_last();
std::string runner_notice();                       // 실행하지 못한 까닭(창에 보인다). 없으면 빈 글
bool runner_faulted();                             // 게임의 함수 안에서 예외가 났다 — 게임을 다시 띄울 때까지 아무것도 실행하지도 쓰지도 않는다
bool runner_calling();                             // 지금 게임의 함수 안이다 — 그동안 ToyBox 는 게임의 메모리에 쓰지 않는다
bool runner_direct();                              // 명령을 게임의 함수에 바로 넘기는가(아니면 글쇠 방식)

// ToyBox 가 게임의 함수를 스스로 부를 때(연구의 "효과를 다시 셈" — keeper.cpp)의 겹침 방지와 오류 가드.
// 직접 실행과 한 쌍의 깃발을 쓴다: 한쪽이 게임의 함수 안이면 다른 쪽은 시작하지 않고, 한쪽에서 예외가 나면 둘 다 멈춘다.
// 들어갈 수 없으면 false(오류 가드가 걸렸다 · 이미 게임의 함수 안이다). true 를 받았으면 반드시 runner_leave_call 로 나온다.
bool runner_enter_call();
// what 이 nullptr 이면 탈 없이 나왔다. 아니면 그 일을 하다 예외(code)가 났다 — 오류 가드를 건다.
// what 은 "효과를 다시 셈하는" 처럼 "… 중 오류가 났습니다" 의 앞에 놓일 말이다.
void runner_leave_call(const char *what, unsigned long code);
void runner_reset_for_test();                      // 테스트: 대기열 · 알림 · 오류 가드 · 깃발을 지운다
