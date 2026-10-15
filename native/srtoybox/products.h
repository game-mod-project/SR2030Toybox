// 재고 칸 번호 → 물자 이름. 표는 빌드할 때 저장소의 번역 테이블(mods/korean/translation/variables.csv 의
// LOCALIZE|productsl|0 … 10)에서 만든다(src/srkit/toybox.py 의 products_inc → build/toybox-obj/products_table.inc).
#pragma once

#include <string>

struct ProductName {
    int slot;         // 재고 칸(0 … STOCK_SLOTS - 1)
    const char *ko;   // UTF-8
    const char *en;
};

const ProductName *find_product(int slot);   // 표에 없으면 nullptr
std::string product_label(int slot);         // "석유". 표에 없으면 "물자 #11"
