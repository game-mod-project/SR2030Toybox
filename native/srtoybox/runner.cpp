#include "runner.h"

bool Runner::enqueue(const std::string &command)
{
    if (pending() >= MAX_QUEUE || plan_command(command).empty())
        return false;
    queue_.push_back(command);
    return true;
}

void Runner::tick(Sink &sink)
{
    if (plan_.empty()) {
        if (queue_.empty())
            return;
        last_ = queue_.front();
        queue_.pop_front();
        plan_ = plan_command(last_);
        at_ = 0;
    }
    if (sink.now_ms() < wait_until_)
        return;
    const Action a = plan_[at_++];
    switch (a.act) {
    case Act::Mods:
        sink.mods(a.value != 0);
        break;
    case Act::Wait:
        wait_until_ = sink.now_ms() + static_cast<unsigned long long>(a.value);
        break;
    default:
        sink.key(a.act, a.value);
        break;
    }
    if (at_ >= plan_.size())
        plan_.clear();
}
