#include "keeper.h"

#include <deque>
#include <mutex>

#include "game.h"
#include "log.h"
#include "runner_win.h"

namespace {

const size_t MAX_QUEUE = 32;
const char *const LEFT_GAME = "게임이 진행 중이 아니어서 쓰지 않았습니다.";

std::mutex g_lock;          // 단추(그리는 스레드)와 틱(창 스레드)이 함께 만진다
std::deque<Request> g_queue;
std::string g_last, g_notice;

std::string target_name(int slot)
{
    return slot == TREASURY ? std::string("국고") : "재고 칸 " + std::to_string(slot);
}

// 요청 하나를 지금 값(now)에 대어 쓴다. 값 쓰기가 꺼졌으면(실패) false — 남은 요청을 버린다. g_lock 을 쥔 채로 부른다.
bool apply(const Request &r, const GameValues &now)
{
    double from = 0, to = 0;
    Verdict verdict = Verdict::Refuse;
    if (r.slot == TREASURY) {
        from = now.treasury;
        verdict = treasury_value(now.treasury, r.change, r.amount, &to);
    } else {
        if (r.slot < 0 || r.slot >= STOCK_SLOTS || !now.used[r.slot]) {
            g_notice = "이번 판에서 쓰지 않는 물자입니다.";
            return true;
        }
        float next = 0;
        from = now.stock[r.slot];
        verdict = stock_value(now.stock[r.slot], r.change, r.amount, &next);
        to = next;
    }
    if (verdict == Verdict::Refuse)
        g_notice = "지금 값이 수가 아니어서 쓰지 않았습니다.";
    if (verdict != Verdict::Write)
        return true;
    const Wrote wrote = r.slot == TREASURY ? game_write_treasury(to) : game_write_stock(r.slot, static_cast<float>(to));
    if (wrote == Wrote::Done) {
        g_last = target_name(r.slot) + " " + short_number(from) + " -> " + short_number(to);
        log_line("값 쓰기: %s", g_last.c_str());
        return true;
    }
    if (wrote == Wrote::Failed || wrote == Wrote::Off)
        return false;                          // 까닭은 탭이 보인다(game_values_off)
    g_notice = LEFT_GAME;                      // 읽은 뒤 쓰기 전에 게임이 바뀌었다
    return true;
}

}  // namespace

bool keeper_enqueue(const Request &request)
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (g_queue.size() >= MAX_QUEUE || !game_values_off().empty())
        return false;
    g_queue.push_back(request);
    return true;
}

void keeper_tick()
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (g_queue.empty() || runner_calling())
        return;                                // 게임의 함수 안에서 다시 온 틱이면 기다린다 — 그 함수가 읽고 있는 값을 바꾸지 않는다
    const GameState game = game_state();
    if (runner_faulted() || !game_values_off().empty()) {
        g_queue.clear();                       // 까닭은 창이 보인다(빨간 경고, 탭의 한 줄)
        return;
    }
    if (!game.known || !game.in_game || game.multiplayer) {
        g_queue.clear();                       // 누른 뒤 게임에서 나갔다 — 돌아온 뒤에 쓰이지 않게 버린다
        g_notice = LEFT_GAME;
        return;
    }
    g_notice.clear();
    while (!g_queue.empty()) {
        const Request r = g_queue.front();
        g_queue.pop_front();
        const GameValues now = game_values();  // 요청마다 다시 읽는다 — 앞의 요청이 값을 바꿨다
        if (!now.ok) {
            g_queue.clear();
            g_notice = "게임의 값을 읽을 수 없어 쓰지 않았습니다.";
            return;
        }
        if (!apply(r, now)) {
            g_queue.clear();
            return;
        }
    }
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

void keeper_reset_for_test()
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_queue.clear();
    g_last.clear();
    g_notice.clear();
}
