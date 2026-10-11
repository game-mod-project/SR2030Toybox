// 지역 번호 → 이름. 표는 빌드할 때 저장소의 번역 테이블(mods/korean/translation/localtext-regions.csv)에서 만든다
// (src/srkit/toybox.py 의 regions_inc → build/toybox-obj/regions_table.inc).
#pragma once

#include <string>
#include <vector>

struct RegionName {
    int number;
    const char *ko;   // UTF-8
    const char *en;
};

const RegionName *find_region(int number);   // 표에 없으면 nullptr
// 창에 적는 이름. 게임이 지금 판에서 쓰는 이름을 받아 두었으면(regions_set_game_names) 그것을 따른다:
//   이름표의 그 번호가 같은 나라면(영문이나 한글 이름이 게임의 이름과 같다) 이름표의 한글 이름,
//   아니면(역사 시나리오 — 같은 번호가 다른 나라다) 게임의 이름을 영문 이름 → 한글 이름의 표에서 찾고, 없으면 게임의 이름 그대로.
// 받아 둔 것이 없으면 이름표의 이름, 이름표에도 없으면 "#1499".
std::string region_label(int number);
// 게임이 지금 판에서 쓰는 이름(지역 번호, UTF-8)을 넘긴다 — 창이 1초마다. 빈 목록이면 이름표만 쓴다(게임 밖).
void regions_set_game_names(std::vector<std::pair<int, std::string>> names);
const char *find_region_alias(const char *en);   // 영문 이름 → 한글 이름(역사 시나리오의 이름까지 든 표). 없으면 nullptr

// 창의 나라 목록.
struct RegionView {
    int picked;               // 고른 나라. 이번 게임에 없거나 플레이어 자신이면 0
    std::vector<int> rows;    // 목록에 보일 지역 번호, 이름순(이름표에 없는 것은 "#번호"로 친다)
};

// numbers: 이번 게임에 있는 지역. 플레이어 자신은 뺀다. filter(이름이나 번호의 일부. 영문은 대소문자를 가리지 않는다)로 거른다 —
// 거르는 것은 목록뿐이고, 고른 나라는 목록에서 가려져도 그대로다.
RegionView region_view(const std::vector<int> &numbers, int player, int picked, const char *filter);
