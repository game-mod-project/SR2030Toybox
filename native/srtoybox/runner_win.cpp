#include "runner_win.h"

#include <mutex>

#include "log.h"

namespace {

std::mutex g_lock;      // 단추(그리는 스레드)와 틱(창 스레드)이 함께 만진다
std::string g_notice;   // 오류 가드가 걸린 까닭
bool g_faulted;         // 게임의 함수 안에서 예외가 났다
bool g_calling;         // 지금 게임의 함수 안이다(그 함수가 메시지를 돌리면 틱이 그 안에서 다시 온다)

}  // namespace

std::string runner_notice()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_notice;
}

bool runner_faulted()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_faulted;
}

bool runner_calling()
{
    std::lock_guard<std::mutex> lock(g_lock);
    return g_calling;
}

bool runner_enter_call()
{
    std::lock_guard<std::mutex> lock(g_lock);
    if (g_faulted || g_calling)
        return false;
    g_calling = true;
    return true;
}

void runner_leave_call(const char *what, unsigned long code)
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_calling = false;
    if (what == nullptr)
        return;
    // 게임의 상태가 어긋났을 수 있다. 더 부르지도 쓰지도 않는다
    g_faulted = true;
    g_notice = std::string(what) + " 중 오류가 났습니다. 저장하지 말고 게임을 다시 시작하십시오.";
    log_line("%s 중 예외 0x%08lX — ToyBox 를 멈춥니다", what, code);
}

void runner_reset_for_test()
{
    std::lock_guard<std::mutex> lock(g_lock);
    g_notice.clear();
    g_faulted = false;
    g_calling = false;
}
