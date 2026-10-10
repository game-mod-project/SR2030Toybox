// 찾은 주소(locate.h)로 게임의 상태와 값을 읽고 고친다. 내장 치트를 거치지 않는다.
// 게임의 메모리에 쓰는 곳은 이것뿐이다:
//   플레이어 지역 객체의 국고 1칸 · 재고 STOCK_SLOTS 칸 · 기술 수준 1칸 · 세계 시장 여론 3칸 · 관계 표 셋에서 고른 나라의 칸,
//   그리고 고른 나라의 지역 객체의 관계 표 셋에서 플레이어의 칸.
// 그 밖의 지역 · 다른 칸 · 전역 · 치트 허용 비트에는 쓰지 않는다.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "locate.h"

struct GameState {
    bool known = false;         // 주소를 찾았고(새 찾기 — 서명), 읽은 값이 서로 맞는다. 거짓이면 내장 치트로 도는 기능은 글쇠 방식으로 동작한다
    bool in_game = false;       // 게임을 진행 중이다
    bool multiplayer = false;
    bool cheats_on = false;     // 치트 허용 비트. 옛 찾기가 옵션 묶음을 찾았을 때만 읽는다(못 찾았으면 늘 false)
    int player = 0;             // 플레이어 지역의 번호(in_game 일 때만)
};

// 플레이어의 값(locate_values 가 찾은 자리에서 읽는다).
struct GameValues {
    bool ok = false;                 // 읽었다: 게임을 진행 중이고 재고 열두 칸이 모두 유한한 수다
    double treasury = 0;             // 국고(달러). 유한한 수가 아닐 수 있다 — 쓰는 쪽(values.h)이 거른다
    bool used[STOCK_SLOTS] = {};     // 이번 판에서 쓰는 물자인가
    float stock[STOCK_SLOTS] = {};   // 재고
};

// 더 쓰는 값(locate_more 가 찾은 자리에서 읽는다): 플레이어의 기술 수준과 세계 시장 여론의 세 칸.
struct GameMore {
    bool ok = false;         // 읽었다: 게임을 진행 중이다. 못 찾은 묶음의 값은 0 으로 둔다
    float tech = 0;          // 기술 수준. 유한한 수가 아닐 수 있다 — 쓰는 쪽(keeper)이 거른다
    float opinion[3] = {};
};

// 한 나라와의 관계: [0] · [1] 은 관계 표 둘, [2] 는 전쟁 명분 표.
struct Relation {
    bool ok = false;         // 읽었다: 게임을 진행 중이고 그 나라가 이번 판에 있다(플레이어 자신이 아니다)
    float mine[3] = {};      // 플레이어 객체의 표에서 그 나라의 칸
    float theirs[3] = {};    // 그 나라 객체의 표에서 플레이어의 칸
};

enum class Wrote {
    Done,        // 썼고, 다시 읽어 그 값인 것을 봤다
    NotInGame,   // 게임을 진행 중이 아니다(멀티플레이, 읽은 값이 서로 맞지 않는 것 포함)
    NotUsed,     // 이번 판에서 쓰지 않는 물자의 칸이다
    BadValue,    // 쓸 값이 유한한 수가 아니다, 재고가 음수다, 없는 칸이다
    Failed,      // 쓸 수 없는 자리이거나 쓴 값이 남지 않았다
    Off,         // 값 쓰기가 꺼져 있다(game_values_off · game_more_off), 그 묶음의 자리를 모른다
    NoTarget,    // 그 번호의 나라가 이번 판에 없다(없는 번호, 사람도 AI 도 맡지 않은 지역, 플레이어 자신)
};

// base: 실행 파일이 올라온 주소(테스트에서는 가짜 메모리). 읽을 수 없는 주소를 만나도 죽지 않는다.
GameState read_game(const uint8_t *base, const GameAddresses &at);
// 이번 게임에 실제로 있는 나라(사람이나 AI 가 맡은 지역)의 번호들(오름차순). 진행 중이 아니면 빈 목록.
std::vector<int> read_regions(const uint8_t *base, const GameAddresses &at);
GameValues read_values(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout);
// 쓰기 직전에 다시 확인한다: 게임을 진행 중이다(일관성 포함) · 멀티플레이가 아니다 · (재고) 그 칸이 쓰는 물자다 ·
// 쓸 값이 유한한 수다 · 쓸 자리가 읽기 · 쓰기 쪽이다. 쓴 뒤 다시 읽어 그 값인지 본다(아니면 한 번 더).
Wrote write_treasury(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout, double value);
Wrote write_stock(const uint8_t *base, const GameAddresses &at, const ValueLayout &layout, int slot, float value);
GameMore read_more(const uint8_t *base, const GameAddresses &at, const MoreLayout &more);
Relation read_relation(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, int number);
// 쓰기 직전의 확인은 write_treasury 와 같다. 그 묶음의 자리를 모르면(0) Wrote::Off.
// 여러 칸을 쓰는 것은 쓰기 전에 모든 칸이 읽기 · 쓰기 쪽인지 먼저 본다(반쪽만 쓰고 멈추지 않게). done 에 쓴 칸의 수.
Wrote write_tech(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, float value);   // 0 이상의 유한한 수
Wrote write_opinion(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, int *done);  // 세 칸에 1.0
// 그 번호의 나라와의 관계를 level(-1 … 1)로, 전쟁 명분을 0 으로: 플레이어 객체의 그 나라 칸 셋, 그 나라 객체의 플레이어 칸 셋.
Wrote write_relation(const uint8_t *base, const GameAddresses &at, const MoreLayout &more, int number, float level, int *done);

void game_init();                  // 올라와 있는 실행 파일에서 주소와 자리를 찾는다(시작할 때 한 번). 결과를 로그에 적는다
void game_init_from(const uint8_t *base, size_t size);   // 그 일의 몸통(테스트는 가짜 이미지로 부른다)
GameState game_state();            // 지금의 상태. 부를 때마다 읽는다 — 플레이어는 게임 중에 바뀔 수 있다(cheat becomeregion)
std::vector<int> game_regions();
bool game_reads();                 // 상태 묶음을 찾았다(게임을 읽는다)
bool game_can_call();              // 명령 처리 함수의 주소를 안다
// 명령 처리 함수에 한 줄을 넘긴다 — 게임이 설정 창의 입력줄에서 하는 것과 같은 호출이다.
// 창 스레드에서, 게임이 진행 중일 때만 부른다(함수는 그것을 검사하지 않고 플레이어 포인터를 그대로 따라간다).
// 함수 안에서 예외가 나면 잡고 false 를 돌려준다(code 에 예외 코드). 그 뒤로 게임의 상태는 믿을 수 없다.
bool game_call(const char *line, unsigned long *code);

std::string game_values_off();     // 값을 쓸 수 없는 까닭(창에 그대로 보인다). 쓸 수 있으면 빈 글
GameValues game_values();          // 지금의 값. 부를 때마다 읽는다
// 쓰기가 실패하면(Wrote::Failed) 이번 실행에서는 값 쓰기를 끄고 로그에 적는다 — 그 뒤로는 Wrote::Off 다.
Wrote game_write_treasury(double value);
Wrote game_write_stock(int slot, float value);

// 값 쓰기가 켜져 있다: 게임을 읽고, SRTOYBOX_WRITE 가 0 이 아니고, 이번 실행에서 쓰기가 실패한 적이 없다.
// 어느 묶음의 자리를 찾았는지는 보지 않는다(game_values_off · game_more_off 가 본다).
bool game_writes();
// 더 쓰는 값의 묶음(MORE_TECH · MORE_OPINION · MORE_RELATIONS)을 쓸 수 없는 까닭(창에 그대로 보인다). 쓸 수 있으면 빈 글.
// 묶음마다 따로다 — 한 묶음을 못 찾아도 다른 묶음과 국고 · 재고는 그대로다.
std::string game_more_off(int group);
GameMore game_more();                  // 지금의 값. 부를 때마다 읽는다
Relation game_relation(int number);
Wrote game_write_tech(float value);    // 실패하면 game_write_treasury 처럼 값 쓰기 전체를 끈다
Wrote game_write_opinion();
Wrote game_write_relation(int number, float level);

// 테스트: 이 프로세스의 "게임"을 가짜 메모리로 바꾼다. handler 는 명령 처리 함수 자리에 둘 함수(없으면 nullptr).
// 값의 자리는 비워 두고 값 쓰기의 실패 표시도 지운다 — 자리는 game_set_values_for_test 로 따로 준다.
void game_set_for_test(const uint8_t *base, const GameAddresses *at, void *handler);
void game_set_values_for_test(const ValueLayout *layout);
// 더 쓰는 값의 자리를 준다 — 자리가 0 이 아닌 묶음을 찾은 것으로 친다. nullptr 이면 모두 못 찾은 것으로.
void game_set_more_for_test(const MoreLayout *layout);
