// 올라와 있는 게임 실행 파일에서 ToyBox 가 쓰는 주소를 찾는다. 주소를 코드에 적어 두지 않는다.
// 창도 게임의 상태도 모르는 순수 함수다. 읽다가 예외가 나면(읽을 수 없는 쪽) "못 찾았다"로 친다.
//
// 찾는 길이 둘이다(docs/11-game-internals.md):
//   새 찾기 locate_state   게임 상태를 읽는 전역 일곱. 내장 치트와 무관한 코드의 서명으로(sigs.h) — 게임이 치트를 없애도 된다.
//           locate_values  값을 읽고 쓰는 자리(국고 칸, 재고 칸 …). 같은 규칙의 서명으로.
//   옛 찾기 locate_legacy  치트 명령 처리 함수와 그 둘레의 셋. "cheat allowcheats" 문자열을 닻으로. 아직 내장 치트로 도는
//                          기능이 쓴다 — 모든 기능을 옮긴 뒤(3단계의 마지막 묶음) 직접 실행 · 글쇠 방식과 함께 지운다.
#pragma once

#include <cstddef>
#include <cstdint>

// 모두 이미지의 시작으로부터의 거리(RVA). 0 이면 찾지 못한 것이다.
struct GameAddresses {
    uint32_t handler;          // [옛 찾기] 명령 처리 함수: void f(void *context, const char *line)
    uint32_t context;          // [옛 찾기] 그 함수의 첫 인자로 넘기는 전역 객체(게임이 넘기는 것과 같은 주소)
    uint32_t multiplayer;      // byte. 0 이 아니면 멀티플레이다
    uint32_t options;          // [옛 찾기] dword. 비트 0x40 = 치트 허용
    uint32_t program_state;    // dword. 1 = 월드가 돌고 있다
    uint32_t mode_state;       // dword. 2 = 게임
    uint32_t player_index;     // dword. 플레이어 지역의 인덱스(지역 표의 칸)
    uint32_t player_pointer;   // qword. 플레이어 지역 객체
    uint32_t region_table;     // qword × 1024. 인덱스순 지역 객체 포인터
    uint32_t region_count;     // dword. 지역 표의 마지막 인덱스
};

const int STATE_WANTED = 7;     // 상태 묶음에서 찾을 것의 수
const int STATE_SIGS = 3;       // 찾을 것마다의 서명 수
const int STATE_NEED = 2;       // 그 가운데 정확히 한 번 맞아야 하는 수

// 서명 하나의 결과(로그와 srkit locate 가 쓴다).
struct SigRow {
    const char *name;           // 찾을 것(GameAddresses 의 필드 이름)
    const char *text;           // 서명 글
    int count;                  // 실행 구역에서 맞은 횟수(2 에서 멈춘다)
    uint32_t at;                // 처음 맞은 자리
    uint32_t value;             // 거기서 읽어 낸 주소나 상수(둘을 읽는 서명이면 첫째 — 간격)
    uint32_t value2;            // 둘째로 읽어 낸 상수(첫 칸). 없으면 0
};

// image: RVA 대로 펼쳐진 실행 파일(올라와 있는 모듈의 시작 주소), size: 그 크기.

// 새 찾기: 찾을 것마다 서명 STATE_SIGS 개 가운데 STATE_NEED 개 이상이 정확히 한 번 맞고 같은 주소를 내야 한다.
// 찾은 주소는 쓸 수 있는 자료 구역 안이어야 하고 서로 겹치지 않아야 한다.
// 찾으면 true 와 out 의 일곱 필드(handler · context · options 는 건드리지 않는다). 못 찾으면 false 와 why(UTF-8).
// rows: STATE_WANTED * STATE_SIGS 칸(서명마다의 결과)이거나 nullptr.
bool locate_state(const uint8_t *image, size_t size, GameAddresses *out, SigRow *rows, char *why, size_t why_size);

// 값 묶음: 플레이어의 국고와 물자 재고를 읽고 쓰는 자리. world_pointer 만 RVA 이고 나머지는 객체 안의 자리다.
struct ValueLayout {
    uint32_t world_pointer;    // qword. 세계 자료 객체("이 물자를 쓰는가"의 표가 그 안에 있다)
    uint32_t treasury;         // 지역 객체 안. double, 달러
    uint32_t stock_first;      // 지역 객체 안. 첫 물자의 재고(float)
    uint32_t stock_step;       // 물자 사이의 간격
    uint32_t used_first;       // 세계 자료 객체 안. 첫 물자의 "쓰는가"(float. 0 보다 크면 이번 판에서 쓴다)
    uint32_t used_step;
};

const int VALUE_WANTED = 4;     // 값 묶음에서 찾을 것의 수: 세계 자료 포인터, 국고 칸, 재고 칸(간격 · 첫 칸), 쓰는 물자 표(간격 · 첫 칸)
const int STOCK_SLOTS = 12;     // 재고의 칸 수. 코드에서 한 가지 꼴로 읽어 낼 자리가 없어 상수로 둔다(docs/11-game-internals.md)

// 새 찾기(값 묶음): 규칙은 locate_state 와 같다. 찾으면 true 와 out. 못 찾으면 false 와 why(UTF-8) — out 은 그대로다.
// 읽어 낸 값이 말이 되는지도 본다: 포인터는 쓸 수 있는 자료 구역 안, 자리는 0 보다 크고 0x100000 보다 작다, 간격은 4 의 배수,
// 국고 칸(8바이트)과 재고 칸들(4바이트 × STOCK_SLOTS)이 겹치지 않는다.
// rows: VALUE_WANTED * STATE_SIGS 칸(서명마다의 결과)이거나 nullptr.
bool locate_values(const uint8_t *image, size_t size, ValueLayout *out, SigRow *rows, char *why, size_t why_size);

// 옛 찾기(전환 기간에만): 찾으면 nullptr 과 out 의 handler · context · options(다른 필드는 건드리지 않는다).
// 못 찾으면 까닭(UTF-8, 정적 문자열)이고 out 은 그대로다.
const char *locate_legacy(const uint8_t *image, size_t size, GameAddresses *out);

// rva 가 든 함수의 시작(함수 표에서. chained unwind 를 뿌리까지). 없으면 0. 테스트와 srkit 이 쓴다.
uint32_t locate_function_root(const uint8_t *image, size_t size, uint32_t rva);
