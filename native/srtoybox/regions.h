// 지역 번호 → 이름. 표는 빌드할 때 저장소의 번역 테이블(mods/korean/translation/localtext-regions.csv)에서 만든다
// (src/srkit/toybox.py 의 regions_inc → build/toybox-obj/regions_table.inc).
#pragma once

#include <string>

struct RegionName {
    int number;
    const char *ko;   // UTF-8
    const char *en;
};

const RegionName *find_region(int number);   // 표에 없으면 nullptr
std::string region_label(int number);        // "독일". 표에 없으면 "#1499"
