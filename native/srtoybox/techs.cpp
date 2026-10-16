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
    case Show::NotMine:
    case Show::Open:
    case Show::Lacking: return !mine;
    case Show::OthersOnly: return !mine && others > 0;
    case Show::Picked: return picked;
    case Show::FromPicked: return picked && !mine;
    default: return true;
    }
}

// 기술 번호 → 플레이어가 보유했는가(표에 없으면 -1).
std::vector<signed char> tech_owned(const ResearchTables &tables)
{
    std::vector<signed char> owned(static_cast<size_t>(tables.tech_slots > 0 ? tables.tech_slots : 0), -1);
    for (const TechRow &t : tables.techs)
        if (t.id >= 0 && static_cast<size_t>(t.id) < owned.size())
            owned[static_cast<size_t>(t.id)] = t.mine ? 1 : 0;
    return owned;
}

template <class Row, int N>
void fill_needs(ListRow *out, const Row &row, const int (&needs)[N], const std::vector<signed char> &owned)
{
    (void)row;
    for (int n = 0; n < N; n++) {
        const int id = needs[n];
        if (id <= 0 || static_cast<size_t>(id) >= owned.size() || owned[static_cast<size_t>(id)] < 0)
            continue;                            // 없는 자리 · 표에 없는 기술(게임도 건너뛴다)
        out->need_ids[out->needs++] = id;
        out->needs_mine += owned[static_cast<size_t>(id)];
    }
}

template <class Row>
void fill(ListRow *out, const Row &row)
{
    out->id = row.id;
    out->state = row.mine ? STATE_MINE : row.queued ? STATE_QUEUED : STATE_NONE;
    out->others = row.others;
    out->owners[0] = row.owners[0];
    out->owners[1] = row.owners[1];
    out->picked = row.picked;
}

// 미보유 · 대기열에 없는 줄을 나눈다: 막혔으면 열 수 없음, 선행을 다 가졌으면 연구 가능, 아니면 선행 부족. 보기 Open · Lacking 에 맞지 않으면 거짓.
// waits: 앞 설계를 보유해야 나오는 설계(upgrade_heads) — 선행 기술을 다 가져도 선행 부족이다.
bool settle(ListRow *row, int block, Show show, bool waits = false)
{
    if (row->state == STATE_NONE) {
        row->block = block;
        row->state = block != BLOCK_NONE ? STATE_BLOCKED : row->needs_mine == row->needs && !waits ? STATE_OPEN : STATE_LACKING;
    }
    return show == Show::Open ? row->state == STATE_OPEN : show == Show::Lacking ? row->state == STATE_LACKING : true;
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

namespace {

void put_utf8(std::string *out, unsigned code)
{
    if (code < 0x80) {
        *out += static_cast<char>(code);
    } else if (code < 0x800) {
        *out += static_cast<char>(0xC0 | (code >> 6));
        *out += static_cast<char>(0x80 | (code & 0x3F));
    } else {
        *out += static_cast<char>(0xE0 | (code >> 12));
        *out += static_cast<char>(0x80 | ((code >> 6) & 0x3F));
        *out += static_cast<char>(0x80 | (code & 0x3F));
    }
}

// SR-UTF8 의 연속 바이트인가: 0x80 … 0xBF(줄바꿈 기호 0xB6 은 빼고)와, 바꿔 쓴 셋(0xFF · 0xF7 · 0xFE).
bool is_cont(unsigned char b)
{
    return (b >= 0x80 && b <= 0xBF && b != 0xB6) || b == 0xFF || b == 0xF7 || b == 0xFE;
}

unsigned cont(unsigned char b)
{
    return (b == 0xFF ? 0xB6u : b == 0xF7 ? 0x9Au : b == 0xFE ? 0x9Eu : b) & 0x3F;
}

// 바꿔 쓴 선두 바이트 → 실제 UTF-8 의 선두 바이트.
unsigned lead(unsigned char b)
{
    return b == 0xE5 ? 0xEAu : b == 0xE6 ? 0xEBu : b == 0xE8 ? 0xEDu : b == 0xE0 ? 0xE2u : b;
}

}  // namespace

std::string game_text_to_utf8(const char *text, size_t size)
{
    std::string out;
    size_t n = 0;
    while (n < size && text[n] != '\0')
        n++;
    const unsigned char *const s = reinterpret_cast<const unsigned char *>(text);
    bool multibyte = false;                      // 앞에서 여러 바이트 글자가 나왔다(= 한글이 섞인 글이다)
    for (size_t i = 0; i < n;) {
        const unsigned char b = s[i];
        if (b < 0x80 || b == 0xB6) {
            put_utf8(&out, b);
            i++;
            continue;
        }
        if (b >= 0xC2 && b <= 0xDF && i + 1 < n && is_cont(s[i + 1])) {
            put_utf8(&out, ((b & 0x1Fu) << 6) | cont(s[i + 1]));
            i += 2;
            multibyte = true;
            continue;
        }
        if (b >= 0xE0 && b <= 0xEF) {
            if (i + 2 < n && is_cont(s[i + 1]) && is_cont(s[i + 2])) {
                const unsigned code = ((lead(b) & 0x0F) << 12) | (cont(s[i + 1]) << 6) | cont(s[i + 2]);
                if (code >= 0x800 && !(code >= 0xD800 && code <= 0xDFFF)) {
                    put_utf8(&out, code);
                    i += 3;
                    multibyte = true;
                    continue;
                }
            } else if (i + 2 == n && is_cont(s[i + 1])) {
                break;                           // 글자의 중간에서 잘렸다 — 깨진 꼬리는 버린다
            } else if (i + 1 == n && multibyte) {
                break;                           // 한글이 든 글의 끝에 선두 바이트만 남았다(원본의 'Bogotá' 같은 끝 글자는 아래에서 살린다)
            }
        }
        unsigned code = b >= 0x80 && b < 0xA0 ? HIGH[b - 0x80] : b;   // 유효한 시퀀스가 아니다 — CP1252 의 글자다
        put_utf8(&out, code == 0 ? '?' : code);
        i++;
    }
    return out;
}

int design_domain(int cls)
{
    return cls < 0 || cls >= DESIGN_CLASSES ? -1 : cls <= 6 ? 0 : cls == 8 ? 3 : cls <= 14 ? 1 : cls <= 20 ? 2 : 4;
}

std::string domain_label(int domain)
{
    static const char *const DOMAIN_NAMES[DOMAINS] = {"육군", "공군", "해군", "미사일", "시설"};
    return domain >= 0 && domain < DOMAINS ? std::string(DOMAIN_NAMES[domain]) : std::to_string(domain);
}

std::string needs_label(const ListRow &row)
{
    return row.needs == 0 ? "-" : row.needs_mine == row.needs ? "보유" : std::to_string(row.needs_mine) + "/" + std::to_string(row.needs);
}

std::string needs_detail(const ListRow &row, const ResearchTables &tables)
{
    const std::vector<signed char> owned = tech_owned(tables);
    std::string out;
    for (int n = 0; n < row.needs; n++) {
        const int id = row.need_ids[n];
        const bool mine = static_cast<size_t>(id) < owned.size() && owned[static_cast<size_t>(id)] > 0;
        out += (out.empty() ? "" : "\n") + tech_label(id) + " — " + (mine ? "보유" : "미보유");
    }
    return out;
}

std::string state_label(const ListRow &row, bool units)
{
    switch (row.state) {
    case STATE_MINE: return units ? "등록" : "보유";
    case STATE_QUEUED: return "연구 중";
    case STATE_OPEN: return "연구 가능";
    case STATE_LACKING: return "선행 부족";
    case STATE_BLOCKED: return block_label(row.block);
    default: return units ? "미등록" : "미보유";
    }
}

std::vector<ListRow> research_rows(const ResearchTables &tables, const ListFilter &filter)
{
    std::vector<ListRow> rows;
    const std::vector<signed char> owned = tech_owned(tables);
    if (filter.designs) {
        const std::vector<int> heads = upgrade_heads(tables);
        for (const DesignRow &d : tables.designs) {
            if ((filter.domain >= 0 && design_domain(d.cls) != filter.domain) || (filter.kind >= 0 && d.cls != filter.kind) || !shown(filter.show, d.mine, d.picked, d.others) || (filter.by_picked && !d.picked))
                continue;
            ListRow row;
            fill(&row, d);
            row.name = d.name.empty() ? "#" + std::to_string(d.id) : d.name;
            if (!filter.find.empty() && !contains(row.name, filter.find) && !contains(std::to_string(d.id), filter.find))
                continue;
            row.kind = d.cls;
            row.level = 1900 + d.year;
            fill_needs(&row, d, d.needs, owned);
            if (!settle(&row, design_block(d, tables.region_mask), filter.show, heads[static_cast<size_t>(&d - tables.designs.data())] != 0))
                continue;
            rows.push_back(row);
        }
    } else {
        for (const TechRow &t : tables.techs) {
            if ((filter.kind >= 0 && t.kind != filter.kind) || !shown(filter.show, t.mine, t.picked, t.others) || (filter.by_picked && !t.picked))
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
            fill_needs(&row, t, t.needs, owned);
            if (!settle(&row, tech_block(t, tables.region_mask), filter.show))
                continue;
            rows.push_back(row);
        }
    }
    std::stable_sort(rows.begin(), rows.end(), [](const ListRow &a, const ListRow &b) {
        return a.level != b.level ? a.level < b.level : a.id < b.id;
    });
    return rows;
}
