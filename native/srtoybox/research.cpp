#include "research.h"

#include <algorithm>

#include "locate.h"

namespace {

// 번호 → 행의 칸(없으면 -1).
template <class Row>
std::vector<int> index_of(const std::vector<Row> &rows, int slots)
{
    std::vector<int> at(static_cast<size_t>(std::max(slots, 0)), -1);
    for (size_t i = 0; i < rows.size(); i++)
        if (rows[i].id > 0 && rows[i].id < slots)
            at[static_cast<size_t>(rows[i].id)] = static_cast<int>(i);
    return at;
}

int find(const std::vector<int> &at, int id)
{
    return id > 0 && id < static_cast<int>(at.size()) ? at[static_cast<size_t>(id)] : -1;
}

ResearchPlan complete(const ResearchTables &t, const ResearchWhat &what, bool can_house)
{
    const std::vector<int> tech_at = index_of(t.techs, t.tech_slots), design_at = index_of(t.designs, t.design_slots);
    std::vector<char> tech_seen(t.techs.size()), tech_asked(t.techs.size()), design_seen(t.designs.size());
    std::vector<char> tech_left(t.techs.size()), design_left(t.designs.size());   // 묶음이 없어 건너뛴 것
    std::vector<int> stack;                     // 볼 기술의 칸
    ResearchPlan plan;
    const auto pull_tech = [&](int id) {        // 딸려 오는 선행
        const int i = find(tech_at, id);
        if (i >= 0 && !tech_seen[static_cast<size_t>(i)]) {
            tech_seen[static_cast<size_t>(i)] = 1;
            stack.push_back(i);
        }
    };
    const auto ask_tech = [&](int id) {         // 고른 것
        const int i = find(tech_at, id);
        if (i >= 0)
            tech_asked[static_cast<size_t>(i)] = 1;
        pull_tech(id);
    };
    const auto ask_design = [&](int id) {
        const int i = find(design_at, id);
        if (i < 0 || design_seen[static_cast<size_t>(i)])
            return;
        design_seen[static_cast<size_t>(i)] = 1;
        const DesignRow &d = t.designs[static_cast<size_t>(i)];
        if (d.mine)
            return;
        if (!d.housed && !can_house) {
            design_left[static_cast<size_t>(i)] = 1;
            plan.skipped++;
            return;
        }
        plan.designs.push_back(d.id);
        plan.asked_designs++;
        if (d.open && !d.held)                  // 게임이 "보유한 설계의 선행 기술을 준다"에서 건너뛰는 설계는 설계의 비트만
            for (int need : d.needs)
                pull_tech(need);
    };
    switch (what.kind) {
    case ResearchWhat::Items:
        for (int id : what.techs)
            ask_tech(id);
        for (int id : what.designs)
            ask_design(id);
        break;
    case ResearchWhat::Level:
        for (const TechRow &row : t.techs)
            if (row.level <= what.level)
                ask_tech(row.id);
        break;
    case ResearchWhat::Queue:
        for (const QueueRow &node : t.queue)
            if (queue_live(node)) {
                if (node.kind == QUEUE_TECH)
                    ask_tech(node.id);
                else if (node.kind == QUEUE_DESIGN)
                    ask_design(node.id);
            }
        break;
    }
    while (!stack.empty()) {
        const size_t i = static_cast<size_t>(stack.back());
        stack.pop_back();
        const TechRow &row = t.techs[i];
        if (row.mine)
            continue;                           // 이미 보유했다 — 그 선행은 보지 않는다(게임과 같다)
        if (!row.housed && !can_house) {
            tech_left[i] = 1;
            plan.skipped++;
            continue;
        }
        plan.techs.push_back(row.id);
        plan.asked_techs += tech_asked[i];
        for (int need : row.needs)
            pull_tech(need);
    }
    for (size_t n = 0; n < t.queue.size(); n++) {
        const QueueRow &node = t.queue[n];
        if (!queue_live(node))
            continue;
        const int i = node.kind == QUEUE_TECH ? find(tech_at, node.id) : node.kind == QUEUE_DESIGN ? find(design_at, node.id) : -1;
        if (i >= 0 && (node.kind == QUEUE_TECH ? tech_seen : design_seen)[static_cast<size_t>(i)]
            && !(node.kind == QUEUE_TECH ? tech_left : design_left)[static_cast<size_t>(i)])
            plan.nodes.push_back(static_cast<int>(n));
    }
    return plan;
}

ResearchPlan revoke(const ResearchTables &t, const ResearchWhat &what)
{
    ResearchPlan plan;
    if (what.kind != ResearchWhat::Items)
        return plan;
    const std::vector<int> tech_at = index_of(t.techs, t.tech_slots), design_at = index_of(t.designs, t.design_slots);
    std::vector<char> tech_gone(t.techs.size()), design_gone(t.designs.size());
    std::vector<std::vector<int>> needed_by(t.techs.size());   // 기술의 칸 → 그것을 선행으로 갖는 기술의 칸들
    for (size_t i = 0; i < t.techs.size(); i++)
        for (int need : t.techs[i].needs) {
            const int j = find(tech_at, need);
            if (j >= 0 && static_cast<size_t>(j) != i)
                needed_by[static_cast<size_t>(j)].push_back(static_cast<int>(i));
        }
    std::vector<int> stack;
    for (int id : what.techs) {
        const int i = find(tech_at, id);
        if (i >= 0 && t.techs[static_cast<size_t>(i)].mine && !tech_gone[static_cast<size_t>(i)]) {
            tech_gone[static_cast<size_t>(i)] = 1;
            plan.asked_techs++;
            stack.push_back(i);
        }
    }
    while (!stack.empty()) {
        const size_t i = static_cast<size_t>(stack.back());
        stack.pop_back();
        plan.techs.push_back(t.techs[i].id);
        for (int j : needed_by[i])
            if (t.techs[static_cast<size_t>(j)].mine && !tech_gone[static_cast<size_t>(j)]) {
                tech_gone[static_cast<size_t>(j)] = 1;
                stack.push_back(j);
            }
    }
    for (int id : what.designs) {
        const int i = find(design_at, id);
        if (i >= 0 && t.designs[static_cast<size_t>(i)].mine && !design_gone[static_cast<size_t>(i)]) {
            design_gone[static_cast<size_t>(i)] = 1;
            plan.asked_designs++;
            plan.designs.push_back(id);
        }
    }
    for (size_t i = 0; i < t.designs.size(); i++) {
        const DesignRow &d = t.designs[i];
        if (!d.mine || design_gone[i] || d.held || !d.open)
            continue;
        for (int need : d.needs) {
            const int j = find(tech_at, need);
            if (j >= 0 && tech_gone[static_cast<size_t>(j)]) {
                design_gone[i] = 1;
                plan.designs.push_back(d.id);
                break;
            }
        }
    }
    return plan;
}

void add(std::string *text, const std::string &part)
{
    if (!text->empty())
        *text += " · ";
    *text += part;
}

}  // namespace

bool queue_live(const QueueRow &node)
{
    for (uint32_t flags : node.flags)
        if ((flags & 3) != 0 && (flags & NODE_GONE) == 0)
            return true;
    return false;
}

void research_mark_queued(ResearchTables *tables)
{
    const std::vector<int> tech_at = index_of(tables->techs, tables->tech_slots);
    const std::vector<int> design_at = index_of(tables->designs, tables->design_slots);
    for (TechRow &row : tables->techs)
        row.queued = false;
    for (DesignRow &row : tables->designs)
        row.queued = false;
    for (const QueueRow &node : tables->queue) {
        if (!queue_live(node))
            continue;
        if (node.kind == QUEUE_TECH && find(tech_at, node.id) >= 0)
            tables->techs[static_cast<size_t>(find(tech_at, node.id))].queued = true;
        else if (node.kind == QUEUE_DESIGN && find(design_at, node.id) >= 0)
            tables->designs[static_cast<size_t>(find(design_at, node.id))].queued = true;
    }
}

ResearchPlan research_plan(const ResearchTables &tables, Research action, const ResearchWhat &what, bool can_house)
{
    ResearchPlan plan = action == Research::Complete ? complete(tables, what, can_house) : revoke(tables, what);
    std::sort(plan.techs.begin(), plan.techs.end());
    std::sort(plan.designs.begin(), plan.designs.end());
    return plan;
}

std::string research_summary(const ResearchPlan &plan, Research action)
{
    const int techs = static_cast<int>(plan.techs.size()), designs = static_cast<int>(plan.designs.size());
    const char *const extra = action == Research::Complete ? "선행" : "딸린 것";
    std::string text;
    if (techs > 0)
        add(&text, "기술 " + std::to_string(techs) + "개"
            + (techs > plan.asked_techs ? "(" + std::string(extra) + " " + std::to_string(techs - plan.asked_techs) + "개 포함)" : ""));
    if (designs > 0)
        add(&text, "부대 설계 " + std::to_string(designs) + "개"
            + (designs > plan.asked_designs ? "(" + std::string(extra) + " " + std::to_string(designs - plan.asked_designs) + "개 포함)" : ""));
    if (!plan.nodes.empty())
        add(&text, "대기열에서 " + std::to_string(plan.nodes.size()) + "개");
    return text;
}
