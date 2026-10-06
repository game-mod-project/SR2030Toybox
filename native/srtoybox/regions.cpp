#include "regions.h"

#include <algorithm>

namespace {

const RegionName NAMES[] = {   // 번호 오름차순
#include "regions_table.inc"
};
const int NAME_COUNT = static_cast<int>(sizeof(NAMES) / sizeof(NAMES[0]));

char lower(char c)
{
    return c >= 'A' && c <= 'Z' ? static_cast<char>(c + ('a' - 'A')) : c;
}

// part 가 text 안에 있는가. ASCII 는 대소문자를 가리지 않는다.
bool contains(const std::string &text, const std::string &part)
{
    if (part.size() > text.size())
        return false;
    for (size_t i = 0; i + part.size() <= text.size(); i++) {
        size_t j = 0;
        while (j < part.size() && lower(text[i + j]) == lower(part[j]))
            j++;
        if (j == part.size())
            return true;
    }
    return false;
}

bool matches(int number, const std::string &filter)
{
    const RegionName *name = find_region(number);
    return contains(std::to_string(number), filter)
        || (name != nullptr && (contains(name->ko, filter) || contains(name->en, filter)));
}

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

RegionView region_view(const std::vector<int> &numbers, int player, int picked, const char *filter)
{
    RegionView view;
    view.picked = 0;
    const std::string wanted = filter == nullptr ? "" : filter;
    for (int number : numbers) {
        if (number == player)
            continue;
        if (number == picked)
            view.picked = picked;
        if (matches(number, wanted))
            view.rows.push_back(number);
    }
    std::sort(view.rows.begin(), view.rows.end(), [](int a, int b) {
        const std::string la = region_label(a), lb = region_label(b);
        return la != lb ? la < lb : a < b;   // UTF-8 의 바이트순 = 한글의 가나다순
    });
    return view;
}
