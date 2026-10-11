#include "regions.h"

#include <algorithm>
#include <cstring>
#include <mutex>

namespace {

struct RegionAlias {
    const char *en;
    const char *ko;
};
const RegionAlias ALIASES[] = {   // 영문 이름의 바이트순. 역사 시나리오의 표까지 모은 것(src/srkit/toybox.py 의 alias_rows)
#include "regions_alias.inc"
    {"", ""},                     // 표가 비어도 배열이 서게
};
const int ALIAS_COUNT = static_cast<int>(sizeof(ALIASES) / sizeof(ALIASES[0])) - 1;

std::mutex g_names_lock;          // 창(그리는 스레드)이 넘기고, 창과 keeper(창 스레드)가 읽는다
std::vector<std::pair<int, std::string>> g_game_names;   // 번호 오름차순

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

std::string game_name(int number)
{
    std::lock_guard<std::mutex> lock(g_names_lock);
    const auto it = std::lower_bound(g_game_names.begin(), g_game_names.end(), number,
                                     [](const std::pair<int, std::string> &row, int n) { return row.first < n; });
    return it != g_game_names.end() && it->first == number ? it->second : std::string();
}

bool matches(int number, const std::string &filter)
{
    const RegionName *name = find_region(number);
    return contains(std::to_string(number), filter) || contains(region_label(number), filter) || contains(game_name(number), filter)
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

const char *find_region_alias(const char *en)
{
    int lo = 0, hi = ALIAS_COUNT;
    while (lo < hi) {
        const int mid = lo + (hi - lo) / 2;
        const int order = strcmp(ALIASES[mid].en, en);
        if (order == 0)
            return ALIASES[mid].ko;
        if (order < 0)
            lo = mid + 1;
        else
            hi = mid;
    }
    return nullptr;
}

void regions_set_game_names(std::vector<std::pair<int, std::string>> names)
{
    std::sort(names.begin(), names.end());
    std::lock_guard<std::mutex> lock(g_names_lock);
    g_game_names = std::move(names);
}

std::string region_label(int number)
{
    const RegionName *name = find_region(number);
    const std::string game = game_name(number);
    if (game.empty())
        return name != nullptr ? std::string(name->ko) : "#" + std::to_string(number);
    if (name != nullptr && (game == name->en || game == name->ko))
        return name->ko;
    const char *alias = find_region_alias(game.c_str());   // 같은 번호가 다른 나라다(역사 시나리오) — 게임의 이름을 따른다
    return alias != nullptr ? std::string(alias) : game;
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
