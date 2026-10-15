#include "products.h"

namespace {

const ProductName NAMES[] = {   // 칸 오름차순
#include "products_table.inc"
};
const int NAME_COUNT = static_cast<int>(sizeof(NAMES) / sizeof(NAMES[0]));

}  // namespace

const ProductName *find_product(int slot)
{
    for (int i = 0; i < NAME_COUNT; i++)
        if (NAMES[i].slot == slot)
            return &NAMES[i];
    return nullptr;
}

std::string product_label(int slot)
{
    const ProductName *name = find_product(slot);
    return name != nullptr ? std::string(name->ko) : "물자 #" + std::to_string(slot);
}
