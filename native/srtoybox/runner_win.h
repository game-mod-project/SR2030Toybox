// 게임의 함수를 부를 때의 겹침 방지와 오류 가드(keeper.cpp 가 쓴다). 내장 치트를 넣던 실행기는 없어졌다 — 이름만 남았다.
#pragma once

#include <string>

std::string runner_notice();                       // 오류 가드가 걸린 까닭(창에 빨갛게 보인다). 없으면 빈 글
bool runner_faulted();                             // 게임의 함수 안에서 예외가 났다 — 게임을 다시 띄울 때까지 아무것도 부르지도 쓰지도 않는다
bool runner_calling();                             // 지금 게임의 함수 안이다 — 그동안 ToyBox 는 게임의 메모리에 쓰지 않는다

// ToyBox 가 게임의 함수를 부를 때: 들어갈 수 없으면 false(오류 가드가 걸렸다 · 이미 게임의 함수 안이다 — 게임의 함수가 메시지를 돌리면
// 틱이 그 안에서 다시 온다). true 를 받았으면 반드시 runner_leave_call 로 나온다.
bool runner_enter_call();
// what 이 nullptr 이면 탈 없이 나왔다. 아니면 그 일을 하다 예외(code)가 났다 — 오류 가드를 건다.
// what 은 "효과를 다시 셈하는" 처럼 "… 중 오류가 났습니다" 의 앞에 놓일 말이다.
void runner_leave_call(const char *what, unsigned long code);

void runner_reset_for_test();                      // 테스트: 알림 · 오류 가드 · 깃발을 지운다
