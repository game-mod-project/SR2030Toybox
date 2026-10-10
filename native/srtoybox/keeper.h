// 값 쓰기 요청의 대기열과 최소 유지. 창의 단추(그리는 스레드)가 넣고, 게임 창의 타이머(창 스레드)가 비운다.
// 내장 치트를 거치지 않는다 — 지금 값을 읽고(game.h) 쓸 값을 셈해(values.h) 그 칸에 쓴다.
// 요청은 다섯 가지다: 국고, 물자 한 칸, 쓰는 물자 모두(3단계 1), 기술 수준 +1, 세계 시장 여론 최고, 한 나라와의 관계(3단계 2).
#pragma once

#include <string>

#include "locate.h"
#include "values.h"

const int TREASURY = -1;                       // Request.slot: 국고. 0 … STOCK_SLOTS - 1 은 그 칸의 물자 재고
const int ALL_STOCK = -2;                      // Request.slot: 이번 판에서 쓰는 물자 모두 — 쓸 때 칸마다의 요청으로 풀린다
const int TECH = -3;                           // Request.slot: 기술 수준에 1 을 더한다(change · amount 는 보지 않는다)
const int OPINION = -4;                        // Request.slot: 세계 시장 여론의 세 칸을 최고(1.0)로(〃)
const int RELATION = -5;                       // Request.slot: region 의 나라와의 관계를 amount 로, 전쟁 명분을 0 으로(change 는 보지 않는다)

struct Request {
    int slot;
    Change change;
    double amount;                             // 국고는 달러, 재고는 수량, 관계는 수준(1 최고, 0 중립)
    int region = 0;                            // RELATION: 대상 나라의 지역 번호
};

const float TECH_LIMIT = 999.0f;               // 기술 수준의 한도 — 이것을 넘게 되면 올리지 않는다

// 최소 유지: 켜진 항목이 바닥보다 작아지면 바닥으로 올린다. KEEP_EVERY_MS 마다 보고, 설정 창이 닫혀 있어도 돈다.
// 플레이하는 나라가 바뀌면 그 뒤로는 새 나라의 값을 본다. 물자는 이번 판에서 쓰는 것만 올린다.
struct Keep {
    bool treasury = false;
    double treasury_floor = 0;                 // 달러
    bool stock[STOCK_SLOTS] = {};
    double stock_floor[STOCK_SLOTS] = {};      // 수량
};

const unsigned long long KEEP_EVERY_MS = 500;

// 받지 못하면 false: 가득 찼다(32개), 그 요청이 쓰는 값을 쓸 수 없다(국고 · 재고는 game_values_off, 나머지는 그 묶음의 game_more_off)
bool keeper_enqueue(const Request &request);
// 대기열을 비우고, 때가 됐으면 유지를 본다. 게임 창을 가진 스레드에서 부른다(now_ms: 흐르는 시계, 밀리초).
// 게임 밖 · 멀티플레이 · 오류 가드 뒤에는 남은 요청을 버리고 유지는 쉰다.
// 게임의 명령 처리 함수(옮기지 않은 기능의 직접 실행) 안에서 다시 온 틱이면 아무것도 하지 않는다.
void keeper_tick(unsigned long long now_ms);
// 마지막으로 쓴 것: "국고 14.43 B -> 24.43 B" · "석유 2.5 M -> 3.5 M" · "모든 물자 11개" · "기술 수준 130 -> 131" ·
// "세계 시장 여론 최고" · "관계 최고 — 폴란드 (1106)". 없으면 빈 글
std::string keeper_last();
std::string keeper_notice();                   // 쓰지 못한 까닭(창에 보인다). 없으면 빈 글

void keeper_set_keep(const Keep &keep);        // 창이 설정을 읽었거나 고쳤다. 다음 틱에 바로 본다
Keep keeper_keep();
int keep_count(const Keep &keep);              // 켜진 항목의 수
// 상태 줄의 뒤에 붙는 글. used: 이번 판에서 쓰는 물자(STOCK_SLOTS 칸).
// " · 유지 중: 국고, 석유, 전력" — 넷을 넘으면 " · 유지 중: 국고 외 5개". 지금 유지되는 것이 없으면 빈 글.
std::string keep_active_text(const Keep &keep, const bool *used);
// 쉬는 동안의 글: " · 유지 3개 켜짐(<까닭>)". 켜진 것이 없으면 빈 글.
std::string keep_resting_text(const Keep &keep, const char *why);

void keeper_reset_for_test();
