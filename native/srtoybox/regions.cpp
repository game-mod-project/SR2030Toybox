#include "regions.h"

namespace {

const RegionName NAMES[] = {   // 번호 오름차순
#include "regions_table.inc"
};
const int NAME_COUNT = static_cast<int>(sizeof(NAMES) / sizeof(NAMES[0]));

}  // namespace

const RegionName *find_region(int number)
{
    int lo = 0, hi = NAME_COUNT;
    while (lo < hi) {
        const int mid = lo + (hi - lo) / 2;
        if (NAMES[mid].number == number)
            return &NAMES[mid];
        if (NAMES[mid].number < number)
            lo = mid + 1;
        else
            hi = mid;
    }
    return nullptr;
}

std::string region_label(int number)
{
    const RegionName *name = find_region(number);
    return name != nullptr ? std::string(name->ko) : "#" + std::to_string(number);
}
