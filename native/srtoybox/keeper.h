// 값 쓰기 요청의 대기열. 창의 단추(그리는 스레드)가 넣고, 게임 창의 타이머(창 스레드)가 비운다.
// 내장 치트를 거치지 않는다 — 지금 값을 읽고(game.h) 쓸 값을 셈해(values.h) 그 칸에 쓴다.
#pragma once

#include <string>

#include "values.h"

const int TREASURY = -1;                       // Request.slot: 국고. 0 … STOCK_SLOTS - 1 은 그 칸의 물자 재고
const int ALL_STOCK = -2;                      // Request.slot: 이번 판에서 쓰는 물자 모두 — 쓸 때 칸마다의 요청으로 풀린다

struct Request {
    int slot;
    Change change;
    double amount;                             // 국고는 달러, 재고는 수량
};

bool keeper_enqueue(const Request &request);   // 받지 못하면 false: 가득 찼다(32개), 값 쓰기가 꺼져 있다
// 대기열을 비운다. 게임 창을 가진 스레드에서 부른다. 게임 밖 · 멀티플레이 · 오류 가드 뒤에는 남은 요청을 버리고,
// 게임의 명령 처리 함수(옮기지 않은 기능의 직접 실행) 안에서 다시 온 틱이면 아무것도 하지 않는다.
void keeper_tick();
std::string keeper_last();                     // 마지막으로 쓴 것: "국고 14.43 B -> 24.43 B" · "석유 2.5 M -> 3.5 M" · "모든 물자 11개". 없으면 빈 글
std::string keeper_notice();                   // 쓰지 못한 까닭(창에 보인다). 없으면 빈 글
void keeper_reset_for_test();
