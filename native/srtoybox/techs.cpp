#include "techs.h"

#include <algorithm>

namespace {

struct TechName {
    int id;
    const char *ko;   // UTF-8. 한글 이름이 빈 행은 빌드 때 영문으로 채운다
    const char *en;
};

const TechName NAMES[] = {   // 번호 오름차순
#include "techs_table.inc"
};
const int NAME_COUNT = static_cast<int>(sizeof(NAMES) / sizeof(NAMES[0]));

// 번역 표의 LOCALIZE|techcategory|1 … 6
const char *const KINDS[TECH_KINDS + 1] = {nullptr, "전쟁", "수송", "과학", "기술", "의료", "사회"};
// 번역 표의 LOCALIZE|milclass|0 … 21. 6 · 14 · 20 은 표에서 셋 다 "수송"이다 — 여기서는 가른다
const char *const CLASSES[DESIGN_CLASSES] = {
    "보병", "정찰", "전차", "대전차", "포병", "방공", "수송", "헬리콥터", "미사일", "요격기", "전술 폭격기",
    "다목적기", "전략 폭격기", "초계", "공중 수송", "잠수함", "항공모함", "주력함", "호위함", "경비함", "해상 수송", "시설",
};

// 0x80 … 0x9F 의 CP1252 글자(나머지는 Latin-1 과 같다). 0 은 정해지지 않은 자리다
const unsigned short HIGH[32] = {
    0x20AC, 0, 0x201A, 0x0192, 0x201E, 0x2026, 0x2020, 0x2021, 0x02C6, 0x2030, 0x0160, 0x2039, 0x0152, 0, 0x017D, 0,
    0, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2013, 0x2014, 0x02DC, 0x2122, 0x0161, 0x203A, 0x0153, 0, 0x017E, 0x0178,
};

const TechName *find_tech(int id)
{
    int lo = 0, hi = NAME_COUNT;
    while (lo < hi) {
        const int mid = lo + (hi - lo) / 2;
        if (NAMES[mid].id == id)
            return &NAMES[mid];
        if (NAMES[mid].id < id)
            lo = mid + 1;
        else
            hi = mid;
    }
    return nullptr;
}

char lower(char c)
{
    return c >= 'A' && c <= 'Z' ? static_cast<char>(c + ('a' - 'A')) : c;
}

// part 가 text 안에 있는가. ASCII 는 대소문자를 가리지 않는다(나라 목록의 찾기와 같다).
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

bool shown(Show show, bool mine, bool picked, int others)
{
    switch (show) {
    case Show::Mine: return mine;
    case Show::NotMine: return !mine;
    case Show::OthersOnly: return !mine && others > 0;
    case Show::Picked: return picked;
    case Show::FromPicked: return picked && !mine;
    default: return true;
    }
}

template <class Row>
void fill(ListRow *out, const Row &row)
{
    out->id = row.id;
    out->state = row.mine ? STATE_MINE : row.queued ? STATE_QUEUED : STATE_NONE;
    out->others = row.others;
    out->picked = row.picked;
}

}  // namespace

std::string tech_label(int id)
{
    const TechName *name = find_tech(id);
    return name != nullptr ? std::string(name->ko) : "#" + std::to_string(id);
}

std::string tech_kind_label(int kind)
{
    return kind >= 1 && kind <= TECH_KINDS ? std::string(KINDS[kind]) : std::to_string(kind);
}

std::string design_class_label(int cls)
{
    return cls >= 0 && cls < DESIGN_CLASSES ? std::string(CLASSES[cls]) : std::to_string(cls);
}

std::string cp1252_to_utf8(const char *text, size_t size)
{
    std::string out;
    for (size_t i = 0; i < size && text[i] != '\0'; i++) {
        const unsigned char c = static_cast<unsigned char>(text[i]);
        unsigned code = c >= 0x80 && c < 0xA0 ? HIGH[c - 0x80] : c;
        if (code == 0)
            code = '?';
        if (code < 0x80) {
            out += static_cast<char>(code);
        } else if (code < 0x800) {
            out += static_cast<char>(0xC0 | (code >> 6));
            out += static_cast<char>(0x80 | (code & 0x3F));
        } else {
            out += static_cast<char>(0xE0 | (code >> 12));
            out += static_cast<char>(0x80 | ((code >> 6) & 0x3F));
            out += static_cast<char>(0x80 | (code & 0x3F));
        }
    }
    return out;
}

std::string state_label(int state)
{
    return state == STATE_MINE ? "보유" : state == STATE_QUEUED ? "연구 중" : "미보유";
}

std::vector<ListRow> research_rows(const ResearchTables &tables, const ListFilter &filter)
{
    std::vector<ListRow> rows;
    if (filter.designs) {
        for (const DesignRow &d : tables.designs) {
            if ((filter.kind >= 0 && d.cls != filter.kind) || !shown(filter.show, d.mine, d.picked, d.others))
                continue;
            ListRow row;
            fill(&row, d);
            row.name = d.name.empty() ? "#" + std::to_string(d.id) : d.name;
            if (!filter.find.empty() && !contains(row.name, filter.find) && !contains(std::to_string(d.id), filter.find))
                continue;
            row.kind = d.cls;
            row.level = 1900 + d.year;
            rows.push_back(row);
        }
    } else {
        for (const TechRow &t : tables.techs) {
            if ((filter.kind >= 0 && t.kind != filter.kind) || !shown(filter.show, t.mine, t.picked, t.others))
                continue;
            const TechName *name = find_tech(t.id);
            if (!filter.find.empty() && !contains(std::to_string(t.id), filter.find)
                && !(name != nullptr && (contains(name->ko, filter.find) || contains(name->en, filter.find))))
                continue;
            ListRow row;
            fill(&row, t);
            row.name = tech_label(t.id);
            row.kind = t.kind;
            row.level = t.level;
            rows.push_back(row);
        }
    }
    std::stable_sort(rows.begin(), rows.end(), [](const ListRow &a, const ListRow &b) {
        return a.level != b.level ? a.level < b.level : a.id < b.id;
    });
    return rows;
}
