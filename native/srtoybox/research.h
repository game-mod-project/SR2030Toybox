// 연구의 규칙: 표의 스냅숏에서 "완료 · 미완료가 바꿀 항목"을 셈한다. 게임도 창도 메모리도 모르는 순수 함수다.
// 게임이 스스로 쓰는 규칙 그대로다(docs/11-game-internals.md): 기술을 주면 선행 기술도 주고, 빼면 그 기술에 기대는 기술 · 부대 설계도 뺀다.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

struct TechRow {
    int id = 0;                 // 번호(표의 자리)
    int kind = 0;               // 분류(1 … 6)
    int level = 0;              // 기술 수준
    int needs[2] = {};          // 선행 기술의 번호(0 이면 없다)
    bool mine = false;          // 플레이어가 보유했다
    bool picked = false;        // 고른 나라가 보유했다(고른 나라가 없으면 false)
    int others = 0;             // 보유한 다른 나라의 수(플레이어는 세지 않는다)
    int owners[2] = {};         // 그 가운데 앞의 둘(지역 인덱스, 낮은 것부터. 없으면 0) — 목록이 이름으로 적는다
    bool queued = false;        // 플레이어의 연구 대기열에 있다
    bool housed = false;        // 보유 비트 묶음이 있다(없으면 아무도 보유한 적이 없다)
    uint64_t mask = 0;          // 지역 마스크(0 이면 모든 지역) — 읽기만
};

struct DesignRow {
    int id = 0;
    int cls = 0;                // 병과 번호
    int year = 0;               // 등장 연도 - 1900
    int needs[4] = {};          // 선행 기술의 번호
    std::string name;           // 이름(UTF-8). 게임 메모리에서 읽는다 — 읽지 못했으면 빈 글
    bool open = false;          // 연구 대상이다
    bool held = false;          // 게임이 "기술을 뺄 때" 건드리지 않는 설계(깃발)
    bool mine = false, picked = false;
    int others = 0;
    int owners[2] = {};
    bool queued = false, housed = false;
    uint64_t mask = 0;          // 지역 마스크(0 이면 모든 지역)
    bool special = false;       // 게임이 연구 목록에서 빼는 설계(+0xEC 의 비트 1 또는 +0xF0 의 0x1000000)
    int upgrade_to = 0;         // 개량되어 되는 설계의 번호(0 이면 없다) — 그 설계의 "앞 설계"가 이 설계다
    int upgrade_to_2 = 0;       // 개량되어 되는 둘째 설계(앞 설계를 셀 때는 보지 않는다 — 게임도 첫째만 본다)
    int retired = 0;            // 단종 연도 − 1900(0 이면 없다)
    bool kept = false;          // 단종돼도 연구 목록에 남는다
};

const int QUEUE_TECH = 1, QUEUE_DESIGN = 2;   // 노드의 종류

struct QueueRow {
    int kind = 0;
    int id = 0;
    uint32_t flags[2] = {};     // 쪽마다의 깃발
};

struct ResearchTables {
    int tech_slots = 0, design_slots = 0;   // 표의 자리 수(번호는 이것보다 작다)
    std::vector<TechRow> techs;             // 쓰는 기술, 번호순
    std::vector<DesignRow> designs;         // 쓰는 부대 설계, 번호순
    std::vector<QueueRow> queue;            // 플레이어의 연구 목록의 노드, 목록의 순서
    std::vector<int> regions;               // 지역 인덱스 → 지역 번호(없는 지역은 0). 목록이 보유국의 이름을 적을 때 쓴다
    uint64_t region_mask = 0;               // 플레이어 지역의 지역 마스크(읽지 못했으면 0 — 마스크가 있는 항목이 모두 막힌다)
    float year = 0;                         // 플레이어 지역의 지금 해 − 1900(읽지 못했으면 0 — 단종으로 막히는 것이 없다)
};

// 그 노드가 대기열에 있는가(게임의 기준): 깃발 둘 가운데 하나라도 아래 두 비트가 0 이 아니고 "뺐다"(NODE_GONE)가 꺼져 있다.
bool queue_live(const QueueRow &node);
// 행마다의 queued 를 노드에서 채운다(스냅숏을 뜬 쪽이 부른다).
void research_mark_queued(ResearchTables *tables);

enum class Research { Complete, Revoke, Unlock };

// 연구 가능으로(Unlock)가 열 수 없는 까닭 — 선행을 채워도 게임이 "가능한 연구"에 보이지 않는다(docs/superpowers/specs/2026-10-15-toybox-research-unlock-design.md)
const int BLOCK_NONE = 0, BLOCK_REGION = 1, BLOCK_CLOSED = 2, BLOCK_SPECIAL = 3, BLOCK_SUPERSEDED = 4, BLOCK_RETIRED = 5, BLOCKS = 6;
int tech_block(const TechRow &row, uint64_t region_mask);     // BLOCK_NONE · BLOCK_REGION
int design_block(const DesignRow &row, uint64_t region_mask); // 연구 대상 아님 → 특수 → 지역 의 순서로 첫째
std::string block_label(int block);                           // "다른 지역 전용" · "연구 대상 아님" · "특수 설계" · "이미 개량됨" · "단종" · 빈 글
// 설계마다(tables.designs 의 칸) design_block 에 표 전체를 보는 둘을 더한 까닭: 다음 설계(upgrade_to · upgrade_to_2)를 보유했고(그 선행도) 또는 대기열에 걸었으면
// BLOCK_SUPERSEDED(0x7ac3f4), 단종 연도가 있고 지금 해의 정수가 그보다 크고 kept 가 아니면 BLOCK_RETIRED(0x7ac380). 게임의 설정 비트에 따라 갈리는 갈래는 흔한 쪽으로 근사한다.
std::vector<int> design_blocks(const ResearchTables &t);
// 같은 것을 플레이어의 지역 마스크 대신 region_mask 로(~0 이면 지역을 뺀 까닭).
std::vector<int> design_blocks(const ResearchTables &t, uint64_t region_mask);
// 설계마다(tables.designs 의 칸) 연구 목록에 나오려면 등록해야 할 앞 설계의 번호. 0 이면 필요 없다 — 앞 설계(upgrade_to 가 그 설계이고 연구 대상이며
// held 가 아닌 설계)가 없거나 그 가운데 하나를 보유했다. 아니면 앞 설계 가운데 번호가 가장 낮은 것(게임은 앞 설계 하나만 보유하면 된다 — 0x7ac0ce).
std::vector<int> upgrade_heads(const ResearchTables &t);

struct ResearchWhat {
    enum Kind { Items, Level, Queue } kind = Items;
    std::vector<int> techs, designs;        // Items: 번호들
    int level = 0;                          // Level: 기술 수준이 이것 이하인 기술 모두
};

struct ResearchPlan {
    std::vector<int> techs, designs;        // 비트를 바꿀 항목의 번호(오름차순). 완료면 켜고 미완료면 끈다
    std::vector<int> nodes;                 // 대기열에서 뺄 노드(tables.queue 의 칸 번호, 오름차순). 완료 · 연구 가능으로에서만
    int asked_techs = 0, asked_designs = 0; // 그 가운데 고른 것. 나머지는 딸려 온 것(완료: 선행 기술, 미완료: 그것에 기대던 것)
    int skipped = 0;                        // 보유 비트 묶음이 없어 건너뛴 항목의 수(can_house 가 false 일 때만)
    int opened = 0, already = 0;            // 연구 가능으로: 연 항목 · 이미 열려 있던(보유 · 대기열 · 선행을 다 가진) 항목의 수
    int blocked[BLOCKS] = {};               // 연구 가능으로: 열 수 없는 항목의 수(까닭마다)
    uint64_t region_add = 0;                // 연구 가능으로: 플레이어 지역의 지역 마스크에 더할 비트들(0 이면 없다)
    int regions = 0;                        // 그 비트의 수
};

// 연구 가능으로(Unlock) — Items 만. 항목마다 보유 · 대기열이면 이미 열림, 열 수 없으면(tech_block · design_block) 세기만, 아니면 직접 선행 가운데
//   표에 있고 보유하지 않은 것을 모은다(없으면 이미 열림). 모은 선행에 완료 규칙을 쓴다(asked 는 0). 항목 자체의 비트는 바꾸지 않는다.
//   설계는 앞 설계가 필요하면(upgrade_heads) 그 앞 설계도 완료 규칙으로 등록한다(그 선행 기술도 함께) — plan.designs 가 그것이다.
//   지역만이 막는 항목(다른 까닭이 없고 지역 마스크가 플레이어의 것과 겹치지 않는다)은 그 마스크의 비트 하나를 region_add 에 더하고 연다 —
//   더했을 때 새로 열리는 항목(보유 · 대기열 · 다른 까닭이 없는 기술 · 설계)이 가장 적은 비트, 같으면 낮은 비트. 뒤 항목은 더한 비트를 본 마스크로 판정한다.
//   플레이어의 마스크가 0(읽지 못했다)이면 더하지 않고 다른 지역 전용으로 센다(docs/superpowers/specs/2026-10-17-toybox-region-unlock-design.md).
// 완료(Complete)
//   기술      그 기술 + 선행 둘 가운데 보유하지 않은 것(거슬러 올라가며 전부). 이미 보유한 선행의 선행은 보지 않는다.
//             선행의 번호가 0 이거나 자리 수 이상이거나 빈 자리면 건너뛴다.
//   부대 설계 그 설계 + 선행 기술 넷을 위 규칙으로. 게임이 건너뛰는 설계(held 이거나 open 이 아닌 것)는 설계의 비트만.
//   대기열    이 요청이 닿은 항목(고른 것과 딸려 온 선행 — 이미 보유한 것도) 가운데 대기열에 있는 것의 노드를 뺀다.
//   무엇을    Items: 그 번호들 / Level: 수준이 level 이하인 기술 모두 / Queue: 대기열에 있는 기술 · 부대 설계 모두.
// 미완료(Revoke) — Items 만
//   기술      그 기술(보유한 것만) + 그것을 선행으로 갖는 보유 기술(따라 내려가며 전부)
//             + 그 기술들 가운데 하나를 선행 넷에 갖는 보유 설계(held 이거나 open 이 아닌 것은 뺀다)
//   부대 설계 그 설계만(보유한 것만)
// 이미 그 상태인 항목은 넣지 않는다.
// can_house: 보유 비트 묶음이 없는 항목(아무도 보유한 적이 없다)에 새 묶음을 걸 수 있는가. 없으면 완료에서 그런 항목을 건너뛰고
// skipped 에 센다 — 그 선행은 따라가지 않고, 대기열에 있어도 빼지 않는다.
ResearchPlan research_plan(const ResearchTables &tables, Research action, const ResearchWhat &what, bool can_house = true);

// 알림과 로그의 글: "기술 12개(선행 5개 포함) · 부대 설계 1개 · 대기열에서 2개" /
// 미완료는 "기술 3개(딸린 것 2개 포함) · 부대 설계 7개(딸린 것 7개 포함)". 바꿀 것이 없으면 빈 글.
std::string research_summary(const ResearchPlan &plan, Research action);
