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
std::string region_label(int number);        // "독일". 표에 없으면 "#1499"

// 창의 나라 목록.
struct RegionView {
    int picked;               // 고른 나라. 이번 게임에 없거나 플레이어 자신이면 0
    std::vector<int> rows;    // 목록에 보일 지역 번호, 이름순(이름표에 없는 것은 "#번호"로 친다)
};

// numbers: 이번 게임에 있는 지역. 플레이어 자신은 뺀다. filter(이름이나 번호의 일부. 영문은 대소문자를 가리지 않는다)로 거른다 —
// 거르는 것은 목록뿐이고, 고른 나라는 목록에서 가려져도 그대로다.
RegionView region_view(const std::vector<int> &numbers, int player, int picked, const char *filter);
