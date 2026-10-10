// 찾은 주소(locate.h)로 게임의 상태와 값을 읽고 고친다. 내장 치트를 거치지 않는다.
// 게임의 메모리에 쓰는 곳은 이것뿐이다:
//   플레이어 지역 객체의 국고 1칸 · 재고 STOCK_SLOTS 칸 · 기술 수준 1칸 · 세계 시장 여론 3칸 · 관계 표 셋에서 고른 나라의 칸,
//   그리고 고른 나라의 지역 객체의 관계 표 셋에서 플레이어의 칸.
//   연구(3단계 3): 기술 · 부대 설계의 보유 비트 묶음에서 플레이어의 비트, 묶음이 없는 항목의 포인터 칸(새 묶음을 걸 때),
//   플레이어의 연구 목록 노드의 깃발 두 칸.
// 그 밖의 지역 · 다른 칸 · 전역 · 치트 허용 비트에는 쓰지 않는다. 기술 표와 부대 설계 표는 모든 나라가 함께 쓰는 표다 — 거기에 쓰는 것은
// 플레이어의 비트와, 플레이어의 비트 하나만 켜질 빈 묶음을 거는 것뿐이다(다른 나라의 비트 · 연구 기간 · 비용은 건드리지 않는다).
// 게임의 함수는 하나만 부른다: "지역의 효과를 다시 셈"(치트가 아니다 — 게임이 연구가 끝날 때 스스로 부르는 함수), 플레이어 지역에 대해서만.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "locate.h"
#include "research.h"

struct GameState {
    bool known = false;         // 주소를 찾았고(새 찾기 — 서명), 읽은 값이 서로 맞는다. 거짓이면 내장 치트로 도는 기능은 글쇠 방식으로 동작한다
    bool in_game = false;       // 게임을 진행 중이다
    bool multiplayer = false;
    bool cheats_on = false;     // 치트 허용 비트. 옛 찾기가 옵션 묶음을 찾았을 때만 읽는다(못 찾았으면 늘 false)
    int player = 0;             // 플레이어 지역의 번호(in_game 일 때만)
    int index = 0;              // 플레이어 지역의 인덱스(in_game 일 때만) — 지역 표의 그 칸이 플레이어 객체임을 확인한 값이다
    int regions = 0;            // 지역 수(in_game 일 때만)
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
    Unreadable,  // (연구) 표나 연구 목록을 읽을 수 없다 — 꼴이 다른 게임일 수 있다. 쓰지 않았다
    Crashed,     // (연구) 비트는 썼는데 효과를 다시 셈하는 게임의 함수에서 예외가 났다 — 게임의 상태를 믿을 수 없다
};

// 연구를 쓴 결과(write_research).
struct ResearchDone {
    ResearchPlan plan;           // 바꾼 것(묶음을 만들 수 없어 건너뛴 항목은 빠져 있다)
    int housed = 0;              // 새로 만들어 건 보유 비트 묶음의 수
    int skipped = 0;             // 묶음을 만들 수 없어 건너뛴 항목의 수(아무도 보유하지 않은 항목)
    int cells = 0, written = 0;  // 쓰려던 칸의 수 · 쓴 칸의 수(비트 하나, 포인터 하나, 노드의 깃발 하나가 저마다 한 칸)
    bool recomputed = false;     // 플레이어 지역의 효과를 다시 셈했다
    unsigned long code = 0;      // 다시 셈에서 난 예외의 코드(Wrote::Crashed)
    std::string why;             // 읽지 못한 까닭(Wrote::Unreadable) · 쓰지 못한 곳(Wrote::Failed)
};

// 게임의 "지역의 효과를 다시 셈": 그 지역이 보유한 기술의 효과를 처음부터 다시 쌓는다. 다른 함수를 부르지 않는다(docs/11).
typedef void (*Recompute)(void *world, int index);

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

// 연구의 표 둘과 플레이어의 연구 목록을 읽는다(행의 queued 까지 채운다). picked: 고른 나라의 번호 — 이번 판에 없거나 0 이면 행의
// picked 는 모두 false 다. 읽을 수 없으면 false 와 why: 게임을 진행 중이 아니다(일관성 포함) / 멀티플레이다 / 표의 자리 수가 2 … 65536 이
// 아니다 / 표 · 보유 묶음 · 연구 목록의 노드 가운데 읽을 수 없는 것이 있다 / 연구 목록이 4096 노드 안에 끝나지 않는다.
bool read_research(const uint8_t *base, const GameAddresses &at, const ResearchLayout &research, int picked, ResearchTables *out,
                   std::string *why);
// 연구를 완료 · 미완료로 바꾼다. 방금 읽은 표에 규칙(research_plan)을 돌려 바꿀 것을 정하고, 쓰기 전에 모든 칸이 읽기 · 쓰기 쪽인지 본다.
//   비트    보유 묶음의 (플레이어 인덱스 / 8)째 바이트에서 그 비트만, 원자적으로 — 같은 바이트의 다른 나라의 비트는 읽어서
//           되쓰지 않는다(그 순간 게임이 다른 나라의 연구를 끝내도 덮어쓰지 않는다).
//   묶음    완료로 바꿀 항목에 묶음이 없으면 프로세스 힙에서 OWNERS_BYTES 를 0 으로 받아 레코드의 포인터 칸에 건다(게임이 하는 그대로).
//           먼저 이미 있는 묶음 하나가 그 힙의 OWNERS_BYTES 짜리 블록인지 본다 — 아니면 만들지 않고 그 항목들을 건너뛴다(skipped).
//           거는 것은 칸이 아직 비어 있을 때만이다(hang_owners) — 표를 읽은 뒤에 게임이 제 묶음을 걸었으면 그 묶음을 쓴다.
//   노드    대기열에서 뺄 노드의 깃발 둘에 NODE_GONE 을 켠다(게임이 연구를 끝낼 때 하는 그대로). 그 비트만, 원자적으로.
//   다시 셈 기술의 비트를 하나라도 바꿨으면 끝에 recompute(세계 객체, 플레이어 인덱스)를 한 번 부른다. -1(모든 지역)로는 부르지 않는다.
// 순서는 칸의 확인 → 묶음 → 비트 → 노드 → 다시 셈. 도중에 쓰기가 실패하면 거기서 멈춘다(Wrote::Failed. 앞서 쓴 것은 되돌리지 않고
// 다시 셈도 부르지 않는다). 바꿀 것이 없어도 Wrote::Done 이다(done->plan 이 비어 있다).
Wrote write_research(const uint8_t *base, const GameAddresses &at, const ResearchLayout &research, Recompute recompute, Research action,
                     const ResearchWhat &what, ResearchDone *done);
// 비어 있는(0) 포인터 칸에 새 묶음(block)을 건다 — 한 번의 원자적 비교 · 교환으로. 그사이 게임이 그 칸에 제 묶음을 걸었으면(다른 나라가
// 그 항목을 처음 보유했다) 덮어쓰지 않는다 — 덮어쓰면 그 나라의 보유가 사라진다. *owners 는 그 칸에 걸려 있는 묶음이다.
// 0 걸었다 / 1 이미 걸려 있었다(block 은 쓰이지 않았다) / -1 쓸 수 없는 칸이다(*owners 는 그대로).
int hang_owners(uint64_t cell, uint64_t block, uint64_t *owners);

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

// 연구를 쓸 수 없는 까닭(창에 그대로 보인다). 쓸 수 있으면 빈 글. 다른 묶음과 따로다.
std::string game_research_off();
// 지금의 연구의 표(read_research). 연구 묶음을 못 찾았으면 false 와 그 까닭.
bool game_research(int picked, ResearchTables *out, std::string *why);
// 연구를 완료 · 미완료로 바꾼다(write_research). 쓰기가 실패하면(Wrote::Failed) 값 쓰기 전체를 끄고 로그에 적는다 — 그 뒤로는 Wrote::Off 다.
// Wrote::Crashed 는 부른 쪽이 처리한다(오류 가드를 건다 — runner_win.h).
Wrote game_write_research(Research action, const ResearchWhat &what, ResearchDone *done);

// 테스트: 이 프로세스의 "게임"을 가짜 메모리로 바꾼다. handler 는 명령 처리 함수 자리에 둘 함수(없으면 nullptr).
// 값의 자리는 비워 두고 값 쓰기의 실패 표시도 지운다 — 자리는 game_set_values_for_test 로 따로 준다.
void game_set_for_test(const uint8_t *base, const GameAddresses *at, void *handler);
void game_set_values_for_test(const ValueLayout *layout);
// 더 쓰는 값의 자리를 준다 — 자리가 0 이 아닌 묶음을 찾은 것으로 친다. nullptr 이면 모두 못 찾은 것으로.
void game_set_more_for_test(const MoreLayout *layout);
// 연구의 자리와 "다시 셈" 자리에 둘 함수를 준다(layout 의 recompute 는 보지 않는다). nullptr 이면 못 찾은 것으로.
void game_set_research_for_test(const ResearchLayout *layout, void *recompute);
