// 올라와 있는 게임 실행 파일에서 ToyBox 가 쓰는 주소를 찾는다. 주소를 코드에 적어 두지 않는다.
// 창도 게임의 상태도 모르는 순수 함수다. 읽다가 예외가 나면(읽을 수 없는 쪽) "못 찾았다"로 친다.
//
// 찾는 길이 둘이다(docs/11-game-internals.md):
//   새 찾기 locate_state   게임 상태를 읽는 전역 일곱. 내장 치트와 무관한 코드의 서명으로(sigs.h) — 게임이 치트를 없애도 된다.
//           locate_values  값을 읽고 쓰는 자리(국고 칸, 재고 칸 …). 같은 규칙의 서명으로.
//           locate_more    더 쓰는 값의 자리(기술 수준, 세계 시장 여론, 관계). 기능마다 한 묶음 — 따로 찾고 따로 실패한다.
//           locate_research 연구: 기술 · 부대 설계의 표, 지역별 연구 목록, 지역의 효과를 다시 셈하는 게임의 함수.
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
// 읽어 낸 값이 말이 되는지도 본다: 포인터는 쓸 수 있는 자료 구역 안의 8 의 배수 자리, 자리는 0 보다 크고 0x100000 보다 작다,
// 국고 칸은 8 의 배수 · 표의 첫 칸과 간격은 4 의 배수, 국고 칸(8바이트)과 재고 칸들(4바이트 × STOCK_SLOTS)이 겹치지 않는다.
// rows: VALUE_WANTED * STATE_SIGS 칸(서명마다의 결과)이거나 nullptr.
bool locate_values(const uint8_t *image, size_t size, ValueLayout *out, SigRow *rows, char *why, size_t why_size);

// 두 묶음을 함께 본다(둘 다 찾은 뒤에): 세계 자료 포인터가 상태 전역 일곱 가운데 어느 것과도 겹치지 않아야 한다.
// 겹치면 false 와 why(UTF-8) — 값 묶음을 못 찾은 것으로 친다(상태 묶음은 그대로 쓴다).
bool locate_fits(const GameAddresses &state, const ValueLayout &values, char *why, size_t why_size);

// 더 쓰는 값(3단계 2 · 4): 모두 지역 객체 안의 자리(float)다. 필드는 서명 표의 순서대로 uint32_t 열이다.
struct MoreLayout {
    uint32_t tech;             // [지식] 기술 수준
    uint32_t opinion[3];       // [여론] 세계 시장 여론과 그 둘레의 세 칸
    uint32_t relation[2];      // [관계] 지역 인덱스로 찾는 표 둘의 첫 칸: 그 지역과의 관계(-1 … 1)
    uint32_t casus;            // [관계] 같은 꼴의 표: 그 지역에 대한 전쟁 명분(0 … 1)
    uint32_t people[2];        // [인구] 인구 칸(게임이 자정마다 다시 쓴다)과, 그 셈에 그대로 더해지는 풀(다시 쌓이지 않는 칸)
    uint32_t approval;         // [지지율] 국내 지지율(0 … 1)
};

const int MORE_TECH = 1, MORE_OPINION = 2, MORE_RELATIONS = 4, MORE_PEOPLE = 8, MORE_APPROVAL = 16;   // 묶음의 비트
const int MORE_GROUPS = 5;      // 묶음의 수(지식 · 여론 · 관계 · 인구 · 지지율 순)
const int MORE_WANTED = 10;     // 찾을 것의 수: 기술 수준 칸, 여론 칸 셋, 관계 표 둘, 전쟁 명분 표, 인구 칸 둘, 지지율 칸
const int REGION_SLOTS = 1024;  // 지역 표의 칸 수 = 관계 표 하나의 칸 수
const size_t MORE_WHY = 160;    // 까닭 한 줄의 크기

// 부르는 게임의 함수(3단계 4): 게임이 스스로도 부르는 함수를, 그것을 부르는 자리(치트 함수 밖)의 서명으로 찾는다. 필드는 함수의 RVA.
struct ActLayout {
    uint32_t colonize;         // void f(void *지역 객체, int 다른 지역의 인덱스, bool): 그 지역이 다른 지역을 식민지로 삼는다
    uint32_t fight;            // void f(void *지역 객체, bool, int 다른 지역의 인덱스, bool, bool): 그 지역이 다른 지역과 전쟁에 들어간다
    uint32_t become;           // void f(void *지역 객체, int 0): 플레이하는 나라를 바꾼 뒤 게임이 그 지역으로 화면을 맞춘다
    uint32_t map_pick;         // qword(자료). 그 포인터가 가리키는 word 가 "지도에서 고른 지역"의 인덱스다 — 읽기만 한다
    uint32_t player_index2;    // dword(자료). 플레이어의 인덱스의 둘째 사본 — "이 나라로 플레이"가 첫째(GameAddresses.player_index)와 함께 쓴다
    uint32_t player_pointer2;  // qword(자료). 플레이어의 지역 객체 포인터의 둘째 사본 — 〃 (첫째는 GameAddresses.player_pointer)
};

const int ACT_COLONIZE = 1, ACT_FIGHT = 2, ACT_BECOME = 4, ACT_MAP_PICK = 8, ACT_INDEX2 = 16, ACT_POINTER2 = 32;   // 찾을 것의 비트
const int ACT_WANTED = 6;       // 찾을 것의 수(ActLayout 의 필드 순서와 같다)
const int ACT_FUNCTIONS = 3;    // 그 가운데 앞의 이만큼이 함수다(나머지는 자료의 주소)

// 새 찾기(부르는 함수): 함수마다 서명 셋이 모두 정확히 한 번 맞고 같은 주소를 내야 하며, 그 주소가 함수 표에 있는 함수의 시작이어야 한다.
// 자료의 주소는 쓸 수 있는 자료 구역에 있고 제 크기(4 · 8)의 배수여야 한다.
// 돌려주는 값은 찾은 함수의 비트. 못 찾은 것의 필드는 0, why 의 그 줄에 까닭(UTF-8).
// rows: ACT_WANTED * STATE_SIGS 칸이거나 nullptr.
int locate_acts(const uint8_t *image, size_t size, ActLayout *out, SigRow *rows, char (*why)[MORE_WHY]);

// 새 찾기(더 쓰는 값): 서명의 규칙은 locate_state 와 같다. 돌려주는 값은 찾은 묶음의 비트다 — 찾은 묶음의 필드만 채우고
// 못 찾은 묶음의 필드는 0 으로 둔다. 한 묶음은 그 안의 것을 모두 찾아야 찾은 것이다(반쪽 묶음은 없다).
// why 는 MORE_GROUPS 줄: 못 찾은 묶음의 까닭(UTF-8). 찾은 묶음은 빈 글.
// 읽어 낸 자리가 말이 되는지도 본다: 0 보다 크고 0x100000 보다 작은 4 의 배수, 칸(4바이트)과 표(4바이트 × REGION_SLOTS)가
// 서로 겹치지 않는다 — 겹치면 어느 쪽이 엉뚱한 것을 읽었는지 모르므로 두 묶음 다 버린다.
// values 를 주면(값 묶음을 찾았을 때) 국고 칸 · 재고 칸들과 겹치는 묶음도 버린다(값 묶음은 그대로 둔다).
// rows: MORE_WANTED * STATE_SIGS 칸(서명마다의 결과)이거나 nullptr.
int locate_more(const uint8_t *image, size_t size, const ValueLayout *values, MoreLayout *out, SigRow *rows, char (*why)[MORE_WHY]);
// 찾을 것(표의 wanted 째. rows 의 칸 번호 / STATE_SIGS)이 든 묶음: 0 지식, 1 여론, 2 관계.
int locate_more_group(int wanted);

// 연구(3단계 3). 앞의 넷은 전역의 RVA, world 는 전역 객체의 RVA, lists 는 그 객체 안의 자리, recompute 는 함수의 RVA 다.
struct ResearchLayout {
    uint32_t tech_table;       // qword. 기술 표(레코드 TECH_SIZE 바이트 × 자리 수)의 포인터
    uint32_t tech_count;       // dword. 기술 표의 자리 수
    uint32_t design_table;     // qword. 부대 설계 표(레코드 DESIGN_SIZE 바이트 × 자리 수)의 포인터
    uint32_t design_count;     // dword. 설계 표의 자리 수
    uint32_t world;            // 세계 객체(큰 전역 구조체)의 시작. 지역 표와 연구 목록이 그 안에 있다
    uint32_t lists;            // 세계 객체 안. 지역 인덱스마다 LIST_STEP 바이트 — 그 지역의 연구 목록(맨 앞이 머리 노드의 포인터)
    uint32_t recompute;        // void f(void *세계 객체, int 지역 인덱스): 그 지역의 효과를 다시 셈한다(-1 이면 모든 지역)
};

const int RESEARCH_WANTED = 7;  // 찾을 것의 수(ResearchLayout 의 필드 순서와 같다)
const int RESEARCH_NEED = 3;    // 찾을 것마다 서명 셋이 모두 정확히 한 번 맞아야 한다 — 한 서명에만 박힌 꼴의 상수도 지켜지게

// 표와 목록의 꼴. 읽어 내지 않고 상수로 둔다 — 대신 이 상수가 박힌 명령을 서명에 넣었다(locate.cpp 의 표 RESEARCH,
// docs/11-game-internals.md). 꼴이 바뀐 빌드에서는 서명이 맞지 않아 묶음을 못 찾는다.
const uint32_t TECH_SIZE = 0x88;            // 기술 레코드. 번호가 곧 자리다
const uint32_t TECH_KIND = 0x00;            // byte. 분류(1 … 6). 0 이면 빈 자리
const uint32_t TECH_LEVEL = 0x01;           // byte. 기술 수준
const uint32_t TECH_NEEDS = 0x04;           // word × TECH_NEED_COUNT. 선행 기술의 번호(0 이면 없다)
const int TECH_NEED_COUNT = 2;
const uint32_t TECH_OWNERS = 0x50;          // qword. 보유 비트 묶음의 포인터(아무도 보유하지 않았으면 0)
const uint32_t DESIGN_SIZE = 0x168;         // 부대 설계 레코드. 번호가 곧 자리다
const uint32_t DESIGN_NAME = 0x00;          // qword. 이름 글의 포인터. 0 이면 빈 자리
const uint32_t DESIGN_CLASS = 0x08;         // byte. 병과 번호 — 표시에만 쓴다(서명에 박지 못했다)
const uint32_t DESIGN_YEAR = 0x0A;          // byte. 등장 연도 - 1900 — 〃
const uint32_t DESIGN_OPEN = 0x20;          // word. 0 이면 연구 대상이 아니다
const uint32_t DESIGN_NEEDS = 0x34;         // word × DESIGN_NEED_COUNT. 선행 기술의 번호
const int DESIGN_NEED_COUNT = 4;
const uint32_t DESIGN_HOLD_A = 0xEC;        // dword. DESIGN_HOLD_A_BIT 이 켜진 설계는 게임이 "기술을 뺄 때" 건드리지 않는다
const uint32_t DESIGN_HOLD_A_BIT = 0x1;
const uint32_t DESIGN_HOLD_B = 0xF0;        // dword. DESIGN_HOLD_B_BIT 〃
const uint32_t DESIGN_HOLD_B_BIT = 0x1000000;
const uint32_t DESIGN_OWNERS = 0xF8;        // qword. 보유 비트 묶음의 포인터
const uint32_t OWNERS_BYTES = 128;          // 보유 비트 묶음 하나 = 지역 인덱스로 찾는 1024비트
const uint32_t LIST_STEP = 24;              // 지역 하나의 연구 목록 칸
const uint32_t NODE_NEXT = 0x10;            // qword. 다음 노드
const uint32_t NODE_ID = 0x18;              // dword. 기술이나 설계의 번호
const uint32_t NODE_KIND = 0x1C;            // byte. 1 기술, 2 부대 설계
const uint32_t NODE_FLAGS = 0x20;           // dword × 2. 쪽마다의 깃발
const uint32_t NODE_GONE = 0x80000000;      // 그 쪽에서 뺐다
const uint32_t NODE_ENDED = 0x08000000;     // 내장 치트가 켜는 "끝냄"

// 새 찾기(연구): 서명의 규칙은 locate_state 와 같되 찾을 것마다 **셋이 모두** 정확히 한 번 맞고 같은 값을 내야 한다(RESEARCH_NEED).
// 일곱을 모두 찾아야 찾은 것이다(반쪽 묶음은 없다). state 는 이미 찾은 상태 묶음이다.
// 읽어 낸 값이 말이 되는지도 본다: 전역 넷은 쓸 수 있는 자료 구역 안의 제 크기의 배수 자리이고 서로 · 상태 전역과 겹치지 않는다 /
// 세계 객체 + (세계 객체의 서명이 함께 읽어 낸 거리) == 상태 묶음의 지역 표 / 연구 목록 전체가 쓸 수 있는 자료 구역 안이고 지역 표와
// 겹치지 않는다 / 다시 셈 함수는 함수 표에서 함수의 시작이다.
// 찾으면 true 와 out. 못 찾으면 false 와 why(UTF-8) — out 은 그대로다.
// rows: RESEARCH_WANTED * STATE_SIGS 칸(서명마다의 결과. 세계 객체의 둘째 값은 지역 표까지의 거리)이거나 nullptr.
bool locate_research(const uint8_t *image, size_t size, const GameAddresses &state, ResearchLayout *out, SigRow *rows, char *why,
                     size_t why_size);
// 꼴의 상수를 "이름\t값(16진수)" 줄로(테스트가 서명에 박힌 바이트와 댄다).
const char *locate_research_shape();
// 연구 묶음과 값 묶음을 함께 본다(둘 다 찾은 뒤에): 연구의 전역 넷이 세계 자료 포인터와 겹치지 않아야 한다.
// 겹치면 false 와 why(UTF-8) — 연구 묶음을 못 찾은 것으로 친다(값 묶음은 그대로 쓴다).
bool locate_research_fits(const ResearchLayout &research, const ValueLayout &values, char *why, size_t why_size);

// 옛 찾기(전환 기간에만): 찾으면 nullptr 과 out 의 handler · context · options(다른 필드는 건드리지 않는다).
// 못 찾으면 까닭(UTF-8, 정적 문자열)이고 out 은 그대로다.
const char *locate_legacy(const uint8_t *image, size_t size, GameAddresses *out);

// rva 가 든 함수의 시작(함수 표에서. chained unwind 를 뿌리까지). 없으면 0. 테스트와 srkit 이 쓴다.
uint32_t locate_function_root(const uint8_t *image, size_t size, uint32_t rva);
