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
bool runner_faulted();                             // 직접 실행 중 예외가 났다 — 게임을 다시 띄울 때까지 아무것도 실행하지 않는다
bool runner_direct();                              // 명령을 게임의 함수에 바로 넘기는가(아니면 글쇠 방식)
