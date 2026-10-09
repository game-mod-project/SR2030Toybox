// 찾은 주소(locate.h)로 게임의 상태를 읽는다. 읽기만 한다 — 게임의 메모리에 쓰지 않는다.
#pragma once

#include <cstdint>
#include <vector>

#include "locate.h"

struct GameState {
    bool known = false;         // 주소를 찾았고(새 찾기 — 서명), 읽은 값이 서로 맞는다. 거짓이면 내장 치트로 도는 기능은 글쇠 방식으로 동작한다
    bool in_game = false;       // 게임을 진행 중이다
    bool multiplayer = false;
    bool cheats_on = false;     // 치트 허용 비트. 옛 찾기가 옵션 묶음을 찾았을 때만 읽는다(못 찾았으면 늘 false)
    int player = 0;             // 플레이어 지역의 번호(in_game 일 때만)
};

// base: 실행 파일이 올라온 주소(테스트에서는 가짜 메모리). 읽을 수 없는 주소를 만나도 죽지 않는다.
GameState read_game(const uint8_t *base, const GameAddresses &at);
// 이번 게임에 실제로 있는 나라(사람이나 AI 가 맡은 지역)의 번호들(오름차순). 진행 중이 아니면 빈 목록.
std::vector<int> read_regions(const uint8_t *base, const GameAddresses &at);

void game_init();                  // 올라와 있는 실행 파일에서 주소를 찾는다(시작할 때 한 번). 결과를 로그에 적는다
GameState game_state();            // 지금의 상태. 부를 때마다 읽는다 — 플레이어는 게임 중에 바뀔 수 있다(cheat becomeregion)
std::vector<int> game_regions();
bool game_can_call();              // 명령 처리 함수의 주소를 안다
// 명령 처리 함수에 한 줄을 넘긴다 — 게임이 설정 창의 입력줄에서 하는 것과 같은 호출이다.
// 창 스레드에서, 게임이 진행 중일 때만 부른다(함수는 그것을 검사하지 않고 플레이어 포인터를 그대로 따라간다).
// 함수 안에서 예외가 나면 잡고 false 를 돌려준다(code 에 예외 코드). 그 뒤로 게임의 상태는 믿을 수 없다.
bool game_call(const char *line, unsigned long *code);
// 테스트: 이 프로세스의 "게임"을 가짜 메모리로 바꾼다. handler 는 명령 처리 함수 자리에 둘 함수(없으면 nullptr).
void game_set_for_test(const uint8_t *base, const GameAddresses *at, void *handler);
