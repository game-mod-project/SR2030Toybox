// 명령의 대기열과 시간 맞추기. 동작을 실제로 보내는 일은 Sink 가 한다
// (게임 안에서는 창 메시지와 키 상태표 — runner_win.cpp, 테스트에서는 기록만).
#pragma once

#include <deque>
#include <string>
#include <vector>

#include "command.h"

struct Sink {
    virtual void mods(bool on) = 0;             // 수정키(Ctrl·Shift)를 눌린 것으로 적는다 / 되돌린다
    virtual void key(Act act, int value) = 0;   // Down · Up · Char
    virtual unsigned long long now_ms() = 0;
    virtual ~Sink() {}
};

class Runner {
public:
    static const size_t MAX_QUEUE = 8;          // 넣는 중인 것까지 합쳐서

    bool enqueue(const std::string &command);   // 가득 찼거나 넣을 수 없는 글이면 받지 않는다
    void tick(Sink &sink);                      // 한 번에 동작 하나. WAIT 가 다 지나기 전에는 아무것도 하지 않는다
    bool starting() const { return plan_.empty() && !queue_.empty(); }   // 다음 틱에 새 명령을 시작한다
    void clear();                               // 대기열을 비운다(넣던 것이 있으면 그것도)
    bool busy() const { return !plan_.empty() || !queue_.empty(); }
    size_t pending() const { return queue_.size() + (plan_.empty() ? 0 : 1); }
    const std::string &last() const { return last_; }

private:
    std::deque<std::string> queue_;
    std::vector<Action> plan_;
    size_t at_ = 0;
    unsigned long long wait_until_ = 0;         // 명령이 끝나도 지우지 않는다 — 마지막 WAIT 가 다음 명령 앞의 간격이 된다
    std::string last_;
};
