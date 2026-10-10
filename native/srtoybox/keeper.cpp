#include "keeper.h"

#include <windows.h>

#include <cmath>
#include <cstdio>
#include <cstring>
#include <deque>
#include <mutex>

#include "game.h"
#include "log.h"
#include "products.h"
#include "regions.h"
#include "runner_win.h"

namespace {

const size_t MAX_QUEUE = 32;
const char *const LEFT_GAME = "게임이 진행 중이 아니어서 쓰지 않았습니다.";

std::mutex g_lock;          // 단추(그리는 스레드)와 틱(창 스레드)이 함께 만진다
std::deque<Request> g_queue;
std::deque<ResearchRequest> g_research;     // 연구 요청은 따로 줄을 선다 — 틱마다 값 요청을 비운 뒤 하나
std::deque<int> g_acts;                     // 게임의 함수를 부르는 요청(식민지로 삼을 나라의 번호) — 연구 요청보다 먼저, 틱마다 하나

// 이번 틱에 잠금을 놓고 할 일 하나: 게임의 함수를 부르는 요청이거나 연구 요청.
struct Job {
    bool act = false;
    int region = 0;
    ResearchRequest research;
};
std::string g_last, g_notice;
Keep g_keep;                        // 최소 유지의 설정(창이 넘긴 것)
bool g_keep_due;                    // 설정이 바뀌었다 — 0.5초를 기다리지 않고 다음 틱에 본다
unsigned long long g_keep_at;       // 마지막으로 유지를 본 때
bool g_kept[1 + STOCK_SLOTS];
std::shared_ptr<const ResearchShot> g_shot; // 연구 목록의 스냅숏(창에 넘긴다)
bool g_watch_seen, g_watch_dirty;           // 지난 스냅숏 뒤에 연구 탭이 그려졌다 / 연구를 썼다 — 기다리지 않고 다시 뜬다
int g_watch_picked;                         // 창이 고른 나라
unsigned long long g_shot_at, g_shot_serial;
bool g_shot_timed;                          // 스냅숏에 걸린 시간을 이번 실행의 로그에 적었다
       // 그 항목을 올린 것을 이번 실행의 로그에 적었다([0] 국고, [1 + 칸] 물자)

std::string target_name(int slot)
{
    return slot == TREASURY ? std::string("국고") : product_label(slot);
}

// 국고는 재무 패널의 표기로, 물자는 위쪽 자원 표시줄의 표기로 적는다.
std::string shown(int slot, double value)
{
    return slot == TREASURY ? short_number(value) : short_amount(value);
}

// 그 요청이 쓰는 값을 쓸 수 없는 까닭. 쓸 수 있으면 빈 글. 묶음마다 따로다.
std::string request_off(const Request &r)
{
    return r.slot == TECH ? game_more_off(MORE_TECH) : r.slot == OPINION ? game_more_off(MORE_OPINION)
        : r.slot == RELATION ? game_more_off(MORE_RELATIONS) : r.slot == PEOPLE ? game_more_off(MORE_PEOPLE)
        : r.slot == APPROVAL ? game_more_off(MORE_APPROVAL) : game_values_off();
}

// 수를 있는 그대로 적는다: 130, 130.5
std::string plain(double value)
{
    char text[32];
    snprintf(text, sizeof(text), "%.6g", value);
    return text;
}

// 더 쓰는 값의 요청 하나(기술 수준 · 여론 · 관계). 국고 · 재고는 읽지 않는다 — 그 묶음을 못 찾은 게임에서도 된다.
// 값 쓰기가 꺼졌으면(실패) false — 남은 요청을 버린다. g_lock 을 쥔 채로 부른다.
bool apply_more(const Request &r)
{
    Wrote wrote = Wrote::Off;
    std::string what;
    if (r.slot == TECH) {
        const GameMore now = game_more();
        if (!now.ok || !std::isfinite(now.tech) || now.tech < 0.0f) {
            g_notice = "기술 수준을 읽을 수 없어 쓰지 않았습니다.";
            return true;
        }
        if (now.tech + 1.0f > TECH_LIMIT) {
            g_notice = "기술 수준이 한도(999)라 쓰지 않았습니다.";
            return true;
        }
        what = "기술 수준 " + plain(now.tech) + " -> " + plain(now.tech + 1.0f);
        wrote = game_write_tech(now.tech + 1.0f);
    } else if (r.slot == OPINION) {
        what = "세계 시장 여론 최고";
        wrote = game_write_opinion();
    } else if (r.slot == PEOPLE) {
        const GameMore now = game_more();
        if (!now.ok || !std::isfinite(now.people[0]) || now.people[0] < 0.0f) {
            g_notice = "인구를 읽을 수 없어 쓰지 않았습니다.";
            return true;
        }
        what = "인구 " + short_amount(now.people[0]) + " -> " + short_amount(static_cast<double>(now.people[0]) + r.amount);
        wrote = game_write_people(static_cast<float>(r.amount));
        if (wrote == Wrote::BadValue) {
            g_notice = "인구의 칸이 수가 아니어서 쓰지 않았습니다.";
            return true;
        }
    } else if (r.slot == APPROVAL) {
        what = "지지율 100%";
        wrote = game_write_approval();
    } else {
        what = std::string(r.amount > 0.5 ? "관계 최고" : "관계 중립") + " — " + region_label(r.region) + " (" + std::to_string(r.region) + ")";
        wrote = game_write_relation(r.region, static_cast<float>(r.amount));
    }
    if (wrote == Wrote::Done) {
        g_last = what;
        log_line("값 쓰기: %s", what.c_str());
        return true;
    }
    if (wrote == Wrote::Failed || wrote == Wrote::Off)
        return false;                          // 까닭은 그 단추의 자리에 보인다(game_more_off)
    g_notice = wrote == Wrote::NoTarget ? "그 나라는 이번 판에 없어 쓰지 않았습니다." : LEFT_GAME;
    return true;
}

// 한 칸(국고나 물자 하나)에 대한 셈: 지금 값(*from)과 쓸 값(*to).
Verdict decide(int slot, Change change, double amount, const GameValues &now, double *from, double *to)
{
    if (slot == TREASURY) {
        *from = now.treasury;
        return treasury_value(now.treasury, change, amount, to);
    }
    float next = 0;
    *from = now.stock[slot];
    const Verdict verdict = stock_value(now.stock[slot], change, amount, &next);
    *to = next;
    return verdict;
}

Wrote write_slot(int slot, double value)
{
    return slot == TREASURY ? game_write_treasury(value) : game_write_stock(slot, static_cast<float>(value));
}

// 요청 하나(국고나 물자 한 칸)를 지금 값(now)에 대어 쓴다. 값 쓰기가 꺼졌으면(실패) false — 남은 요청을 버린다.
// 썼으면 *wrote_it 이 true. g_lock 을 쥔 채로 부른다.
bool apply(const Request &r, const GameValues &now, bool *wrote_it)
{
    *wrote_it = false;
    if (r.slot != TREASURY && (r.slot < 0 || r.slot >= STOCK_SLOTS || !now.used[r.slot])) {
        g_notice = "이번 판에서 쓰지 않는 물자입니다.";
        return true;
    }
    double from = 0, to = 0;
    const Verdict verdict = decide(r.slot, r.change, r.amount, now, &from, &to);
    if (verdict == Verdict::Refuse)
        g_notice = "지금 값이 수가 아니어서 쓰지 않았습니다.";
    if (verdict != Verdict::Write)
        return true;
    const Wrote wrote = write_slot(r.slot, to);
    if (wrote == Wrote::Done) {
        *wrote_it = true;
        g_last = target_name(r.slot) + " " + shown(r.slot, from) + " -> " + shown(r.slot, to);
        log_line("값 쓰기: %s", g_last.c_str());
        return true;
    }
    if (wrote == Wrote::Failed || wrote == Wrote::Off)
        return false;                          // 까닭은 탭이 보인다(game_values_off)
    g_notice = LEFT_GAME;                      // 읽은 뒤 쓰기 전에 게임이 바뀌었다
    return true;
}

// "모든 물자": 이번 판에서 쓰는 물자마다 같은 일을 한다. 한 칸에 쓰는 것은 다른 칸의 값을 바꾸지 않으므로 now 를 다시 읽지 않는다.
bool apply_all(const Request &r, const GameValues &now)
{
    int count = 0;
    for (int slot = 0; slot < STOCK_SLOTS; slot++) {
        if (!now.used[slot])
            continue;
        bool wrote_it = false;
        if (!apply({slot, r.change, r.amount}, now, &wrote_it))
            return false;
        count += wrote_it ? 1 : 0;
    }
    if (count > 0)
        g_last = "모든 물자 " + std::to_string(count) + "개";
    return true;
}

// 대기열을 비운다. 값 쓰기가 꺼졌거나 값을 읽지 못하면 false(남은 요청은 버렸다). g_lock 을 쥔 채로 부른다.
bool drain()
{
    g_notice.clear();
    while (!g_queue.empty()) {
        const Request r = g_queue.front();
        g_queue.pop_front();
        if (r.slot <= TECH) {                  // 더 쓰는 값: 국고 · 재고와 따로다
            if (!apply_more(r)) {
                g_queue.clear();
                return false;
            }
            continue;
        }
        const GameValues now = game_values();  // 요청마다 다시 읽는다 — 앞의 요청이 값을 바꿨다
        if (!now.ok) {
            g_queue.clear();
            g_notice = "게임의 값을 읽을 수 없어 쓰지 않았습니다.";
            return false;
        }
        bool wrote_it = false;
        if (!(r.slot == ALL_STOCK ? apply_all(r, now) : apply(r, now, &wrote_it))) {
            g_queue.clear();
            return false;
        }
    }
    return true;
}

// 유지의 한 항목: 지금 값이 바닥보다 작으면 바닥으로 올린다. 값 쓰기가 꺼졌으면(실패) false.
// 창에 알리지 않는다(0.5초마다 온다). 로그에는 항목마다 이번 실행의 첫 번째만 적는다.
bool hold(int slot, double floor, const GameValues &now)
{
    double from = 0, to = 0;
    if (decide(slot, Change::Floor, floor, now, &from, &to) != Verdict::Write)
        return true;                           // 바닥 위다. 지금 값이 수가 아니면 건드리지 않는다
    const Wrote wrote = write_slot(slot, to);
    if (wrote == Wrote::Done && !g_kept[1 + slot]) {
        g_kept[1 + slot] = true;
        log_line("유지: %s %s -> %s", target_name(slot).c_str(), shown(slot, from).c_str(), shown(slot, to).c_str());
    }
    return wrote != Wrote::Failed && wrote != Wrote::Off;
}

// 유지 검사: 켜진 항목마다 바닥을 댄다. 물자는 이번 판에서 쓰는 것만. g_lock 을 쥔 채로 부른다.
void keep_check()
{
    const GameValues now = game_values();
    if (!now.ok)
        return;
    if (g_keep.treasury && !hold(TREASURY, g_keep.treasury_floor, now))
        return;
    for (int slot = 0; slot < STOCK_SLOTS; slot++)
        if (g_keep.stock[slot] && now.used[slot] && !hold(slot, g_keep.stock_floor[slot], now))
            return;
}

// 틱의 앞쪽: 값 요청을 비우고, 때가 됐으면 유지를 본다. 이번 틱에 처리할 연구 요청이 있으면 *next 에 꺼내고 true —
// 그때는 "게임의 함수 안" 깃발을 세워 둔다(부른 쪽이 runner_leave_call 로 내린다). g_lock 을 쥔 채로 부른다.
bool tick_locked(unsigned long long now_ms, Job *next)
{
    if (runner_calling())
        return false;                          // 게임의 함수 안에서 다시 온 틱이면 기다린다 — 그 함수가 읽고 있는 값을 바꾸지 않는다
    const bool due = keep_count(g_keep) > 0 && (g_keep_due || now_ms - g_keep_at >= KEEP_EVERY_MS);
    if (g_queue.empty() && g_research.empty() && g_acts.empty() && !due)
        return false;
    if (due) {                                 // 쓰든 쉬든, 다음에 보는 것은 지금부터 0.5초 뒤다
        g_keep_due = false;
        g_keep_at = now_ms;
    }
    const GameState game = game_state();
    if (runner_faulted() || !game_writes()) {
        g_queue.clear();                       // 까닭은 창이 보인다(빨간 경고, 탭의 한 줄). 유지도 쉰다
        g_research.clear();
        g_acts.clear();
        return false;
    }
    if (!game.known || !game.in_game || game.multiplayer) {
        if (!g_queue.empty() || !g_research.empty() || !g_acts.empty()) {
            g_queue.clear();                   // 누른 뒤 게임에서 나갔다 — 돌아온 뒤에 쓰이지 않게 버린다
            g_research.clear();
            g_acts.clear();
            g_notice = LEFT_GAME;
        }
        return false;                          // 유지는 게임 밖 · 멀티플레이에서 쉰다
    }
    const bool values = !g_queue.empty();
    if (values && !drain()) {
        g_research.clear();                    // 값 쓰기가 꺼졌다 — 연구도 쓰지 않는다
        g_acts.clear();
        return false;
    }
    if (due && game_values_off().empty())      // 유지는 국고와 물자다 — 그 자리를 못 찾은 게임에서는 쉰다
        keep_check();                          // 단추의 요청을 쓴 뒤에 본다 — 방금 내린 값도 바닥 아래면 올린다
    if ((g_research.empty() && g_acts.empty()) || !runner_enter_call())
        return false;
    if (!values)
        g_notice.clear();                      // 이번 틱에 쓴 값 요청의 알림은 남긴다 — 연구의 알림이 생기면 그것이 덮는다
    if (!g_acts.empty()) {
        next->act = true;
        next->region = g_acts.front();
        g_acts.pop_front();
        return true;
    }
    next->research = g_research.front();
    g_research.pop_front();
    return true;
}

// 연구 요청 하나를 쓴다. g_lock 을 쥐지 않은 채로 부른다 — 끝에 게임의 "효과를 다시 셈"이 불리고, 그 함수가 안에서
// ToyBox 로 되돌아오면(타이머 · 단추) 그것들이 g_lock 을 잡는다. "게임의 함수 안" 깃발은 tick_locked 가 세워 뒀다.
void run_research(const ResearchRequest &r)
{
    ResearchDone done;
    const Wrote wrote = game_write_research(r.action, r.what, &done);
    runner_leave_call(wrote == Wrote::Crashed ? "효과를 다시 셈하는" : nullptr, done.code);

    std::lock_guard<std::mutex> lock(g_lock);
    const char *const verb = r.action == Research::Complete ? "완료" : "미완료";
    if (wrote == Wrote::NotInGame) {           // 읽은 뒤 쓰기 전에 게임이 바뀌었다
        g_notice = LEFT_GAME;
        return;
    }
    if (wrote == Wrote::Unreadable) {
        g_notice = "연구의 표를 읽을 수 없습니다 (" + done.why + ")";
        log_line("%s", g_notice.c_str());
        return;
    }
    if (wrote != Wrote::Done) {                // 실패 · 꺼짐 · 예외: 까닭은 그 단추의 자리와 빨간 경고에 보인다. 남은 요청을 버린다
        g_queue.clear();
        g_research.clear();
        g_acts.clear();
        return;
    }
    const std::string skipped = done.skipped == 0 ? std::string()
        : "묶음을 만들 수 없는 게임 판입니다 — 보유한 나라가 없는 항목 " + std::to_string(done.skipped) + "개를 건너뜁니다";
    if (!skipped.empty()) {
        g_notice = skipped;
        log_line("%s", skipped.c_str());
    }
    const std::string summary = research_summary(done.plan, r.action);
    if (summary.empty()) {
        if (skipped.empty()) {
            g_notice = "바꿀 것이 없습니다 — " + r.label;
            log_line("연구 %s (%s): 바꿀 것이 없습니다", verb, r.label.c_str());
        }
        return;
    }
    ResearchPlan bits = done.plan;             // 창의 한 줄에는 바뀐 기술 · 부대 설계만 적는다
    bits.nodes.clear();
    const std::string changed = research_summary(bits, r.action);
    g_last = (changed.empty() ? "대기열에서 " + std::to_string(done.plan.nodes.size()) + "개를 뺌" : changed + "를 " + verb + "로")
        + " — " + r.label;
    log_line("연구 %s (%s): %s%s", verb, r.label.c_str(), summary.c_str(),
             done.housed > 0 ? (" · 새 묶음 " + std::to_string(done.housed) + "개").c_str() : "");
}

}  // namespace

bool keeper_enqueue(const Request &request)
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (g_queue.size() >= MAX_QUEUE || !request_off(request).empty())
        return false;
    g_queue.push_back(request);
    return true;
}

bool keeper_enqueue_research(const ResearchRequest &request)
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (g_research.size() >= RESEARCH_QUEUE || !game_research_off().empty())
        return false;
    g_research.push_back(request);
    return true;
}

namespace {

// 고른 나라를 식민지로 삼는다(게임의 함수를 부른다). g_lock 을 쥐지 않은 채로 부른다 — "게임의 함수 안" 깃발은 tick_locked 가 세워 뒀다.
void run_colonize(int region)
{
    unsigned long code = 0;
    const Wrote wrote = game_colonize(region, &code);
    runner_leave_call(wrote == Wrote::Crashed ? "식민지화하는" : nullptr, code);

    std::lock_guard<std::mutex> lock(g_lock);
    const std::string who = region_label(region) + " (" + std::to_string(region) + ")";
    if (wrote == Wrote::Done) {
        g_last = "식민지화 — " + who;
        log_line("게임의 함수: 식민지화 — %s", who.c_str());
    } else if (wrote == Wrote::NoTarget) {
        g_notice = "그 나라는 이번 판에 없어 하지 않았습니다.";
    } else if (wrote == Wrote::NotInGame) {
        g_notice = LEFT_GAME;
    } else {                                   // 꺼짐 · 예외: 까닭은 그 단추의 자리와 빨간 경고에 보인다. 남은 요청을 버린다
        g_queue.clear();
        g_research.clear();
        g_acts.clear();
    }
}

// 연구 탭이 보이는 동안의 스냅숏. g_lock 을 쥐지 않은 채로 부른다(읽는 동안 그리는 스레드를 세우지 않는다).
void watch_tick(unsigned long long now_ms)
{
    int picked = 0;
    {
        std::lock_guard<std::mutex> lock(g_lock);
        const bool due = g_watch_dirty || g_shot == nullptr || g_shot->picked != g_watch_picked || now_ms - g_shot_at >= RESEARCH_EVERY_MS;
        if (!g_watch_seen || !due || runner_calling())
            return;
        g_watch_seen = g_watch_dirty = false;
        g_shot_at = now_ms;
        picked = g_watch_picked;
    }
    std::shared_ptr<ResearchShot> shot = std::make_shared<ResearchShot>();
    const GameState game = game_state();
    const unsigned long long began = GetTickCount64();
    shot->picked = picked;
    shot->player = game.player;
    if (!game.known || !game.in_game)
        shot->why = "게임이 진행 중이 아닙니다";
    else if (game.multiplayer)
        shot->why = "멀티플레이에서는 연구를 읽지 않습니다";
    else
        shot->ok = game_research(picked, &shot->tables, &shot->why);
    std::lock_guard<std::mutex> lock(g_lock);
    if (shot->ok && !g_shot_timed) {           // 큰 판에서 얼마나 걸리는지 한 번 적어 둔다(첫 스냅숏은 부대 설계의 이름도 읽는다)
        g_shot_timed = true;
        log_line("연구 목록: 기술 %d개 · 부대 설계 %d개 · 노드 %d개를 %llu ms 에 읽음", static_cast<int>(shot->tables.techs.size()),
                 static_cast<int>(shot->tables.designs.size()), static_cast<int>(shot->tables.queue.size()), GetTickCount64() - began);
    }
    shot->serial = ++g_shot_serial;
    g_shot = shot;
}

}  // namespace

void keeper_watch_research(int picked)
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_watch_seen = true;
    g_watch_picked = picked;
}

std::shared_ptr<const ResearchShot> keeper_research_shot()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_shot;
}

bool keeper_enqueue_colonize(int region)
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (g_acts.size() >= RESEARCH_QUEUE || !game_act_off(ACT_COLONIZE).empty())
        return false;
    g_acts.push_back(region);
    return true;
}

void keeper_tick(unsigned long long now_ms)
{
    Job job;
    bool write = false;
    {
        std::lock_guard<std::mutex> lock(g_lock);
        write = tick_locked(now_ms, &job);
    }
    if (write && job.act) {
        run_colonize(job.region);
    } else if (write) {
        run_research(job.research);
        std::lock_guard<std::mutex> lock(g_lock);
        g_watch_dirty = true;                  // 쓴 것이 목록에 바로 보이게
    }
    watch_tick(now_ms);
}

std::string keeper_last()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_last;
}

std::string keeper_notice()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_notice;
}

void keeper_set_keep(const Keep &keep)
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (keep.treasury != g_keep.treasury || keep.treasury_floor != g_keep.treasury_floor)
        g_kept[0] = false;                     // 바뀐 항목은 다음에 올릴 때 다시 로그에 적는다
    for (int slot = 0; slot < STOCK_SLOTS; slot++)
        if (keep.stock[slot] != g_keep.stock[slot] || keep.stock_floor[slot] != g_keep.stock_floor[slot])
            g_kept[1 + slot] = false;
    g_keep = keep;
    g_keep_due = true;
}

Keep keeper_keep()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_keep;
}

int keep_count(const Keep &keep)
{
    int count = keep.treasury ? 1 : 0;
    for (int slot = 0; slot < STOCK_SLOTS; slot++)
        count += keep.stock[slot] ? 1 : 0;
    return count;
}

std::string keep_active_text(const Keep &keep, const bool *used)
{
    std::string first, names;
    int count = 0;
    for (int slot = TREASURY; slot < STOCK_SLOTS; slot++) {
        if (slot == TREASURY ? !keep.treasury : !(keep.stock[slot] && used[slot]))
            continue;
        const std::string name = target_name(slot);
        if (count++ == 0)
            first = name;
        else
            names += ", ";
        names += name;
    }
    if (count == 0)
        return std::string();
    return " · 유지 중: " + (count > 4 ? first + " 외 " + std::to_string(count - 1) + "개" : names);
}

std::string keep_resting_text(const Keep &keep, const char *why)
{
    const int count = keep_count(keep);
    return count == 0 ? std::string() : " · 유지 " + std::to_string(count) + "개 켜짐(" + why + ")";
}

void keeper_reset_for_test()
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_queue.clear();
    g_research.clear();
    g_acts.clear();
    g_last.clear();
    g_notice.clear();
    g_keep = Keep();
    g_keep_due = false;
    g_keep_at = 0;
    memset(g_kept, 0, sizeof(g_kept));
    g_shot.reset();
    g_watch_seen = g_watch_dirty = g_shot_timed = false;
    g_watch_picked = 0;
    g_shot_at = 0;
}
