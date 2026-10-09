// 올라와 있는 게임 실행 파일에서 ToyBox 가 쓰는 주소를 찾는다. 주소를 코드에 적어 두지 않는다 —
// "cheat allowcheats" 문자열을 닻으로 삼아 그것을 쓰는 함수와 그 안의 명령에서 얻는다(docs/11-game-internals.md).
// 창도 게임의 상태도 모르는 순수 함수다. 대조가 하나라도 어긋나거나 읽다가 예외가 나면(읽을 수 없는 쪽) "못 찾았다"로 친다.
#pragma once

#include <cstddef>
#include <cstdint>

// 모두 이미지의 시작으로부터의 거리(RVA).
struct GameAddresses {
    uint32_t handler;          // 명령 처리 함수: void f(void *context, const char *line)
    uint32_t context;          // 그 함수의 첫 인자로 넘기는 전역 객체(게임이 넘기는 것과 같은 주소)
    uint32_t multiplayer;      // byte. 0 이 아니면 함수가 아무것도 하지 않는다
    uint32_t options;          // dword. 비트 0x40 = 치트 허용
    uint32_t program_state;    // dword. 1 = 월드가 돌고 있다
    uint32_t mode_state;       // dword. 2 = 게임
    uint32_t player_index;     // dword. 플레이어 지역의 인덱스(지역 표의 칸)
    uint32_t player_pointer;   // qword. 플레이어 지역 객체
    uint32_t region_table;     // qword × 1024. 인덱스순 지역 객체 포인터
    uint32_t region_count;     // dword. 지역 표의 마지막 인덱스
};

// image: RVA 대로 펼쳐진 실행 파일(올라와 있는 모듈의 시작 주소), size: 그 크기.
// 찾으면 out 을 채우고 nullptr, 못 찾으면 까닭(UTF-8, 정적 문자열)을 돌려준다.
const char *locate_game(const uint8_t *image, size_t size, GameAddresses *out);

const int STATE_WANTED = 7;     // 상태 묶음에서 찾을 것의 수
const int STATE_SIGS = 3;       // 찾을 것마다의 서명 수
const int STATE_NEED = 2;       // 그 가운데 정확히 한 번 맞아야 하는 수

// 서명 하나의 결과(로그와 srkit locate 가 쓴다).
struct SigRow {
    const char *name;           // 찾을 것(GameAddresses 의 필드 이름)
    const char *text;           // 서명 글
    int count;                  // 실행 구역에서 맞은 횟수(2 에서 멈춘다)
    uint32_t at;                // 처음 맞은 자리
    uint32_t value;             // 거기서 읽어 낸 주소
};

// 새 찾기: 게임 상태를 읽는 데 쓰는 전역 일곱을 서명으로 찾는다(sigs.h). 치트 문자열도 치트 명령 처리 함수의 코드도 쓰지 않는다 —
// 게임이 치트를 없애도 된다. 찾을 것마다 서명 STATE_SIGS 개 가운데 STATE_NEED 개 이상이 정확히 한 번 맞고 같은 주소를 내야 한다.
// 찾으면 true 와 out 의 일곱 필드(handler · context · options 는 건드리지 않는다). 못 찾으면 false 와 why(UTF-8).
// rows: STATE_WANTED * STATE_SIGS 칸(서명마다의 결과)이거나 nullptr. 읽을 수 없는 쪽을 만나도 죽지 않는다.
bool locate_state(const uint8_t *image, size_t size, GameAddresses *out, SigRow *rows, char *why, size_t why_size);

// rva 가 든 함수의 시작(함수 표에서. chained unwind 를 뿌리까지). 없으면 0. 테스트와 srkit 이 쓴다.
uint32_t locate_function_root(const uint8_t *image, size_t size, uint32_t rva);
