// 서명: 게임의 코드에서 주소나 상수를 읽어 내는 짧은 바이트 꼴. 창도 게임도 PE 형식도 모르는 순수 함수다.
//
// 서명 글은 낱말을 빈칸으로 나눠 적는다:
//   48        정해진 바이트(16진수 두 자리)
//   ?         아무 바이트
//   [rip]     읽어 낼 주소: 4바이트 rip 상대 거리. 명령이 그 4바이트에서 끝난다
//   [rip+1]   〃 그 뒤에 상수 1바이트가 더 있고 명령이 끝난다 (cmp byte ptr [rip+d],0 같은 것)
//   [rip+4]   〃 상수 4바이트가 더 있다 (mov dword ptr [rip+d],2 같은 것)
//   [u32]     읽어 낼 상수 4바이트 (구조체 안의 자리, 간격)
//   [u8]      읽어 낼 상수 1바이트
// 첫 낱말은 정해진 바이트여야 하고, 읽어 낼 자리가 하나 이상 있어야 한다.
#pragma once

#include <cstddef>
#include <cstdint>

const int SIG_MAX = 64;         // 서명 하나의 최대 길이(바이트)
const int SIG_CAPTURES = 2;     // 서명 하나가 읽어 내는 값의 최대 개수

struct Sig {
    uint8_t bytes[SIG_MAX];
    bool any[SIG_MAX];          // 아무 바이트나 되는 자리(읽어 낼 자리도 여기에 든다)
    uint32_t length;
    int captures;
    struct Capture {
        uint32_t at;            // 서명 안에서의 자리
        uint32_t size;          // 1 또는 4
        bool rip;               // 4바이트 rip 상대 거리다 — 주소(RVA)로 푼다
        uint32_t tail;          // rip: 그 4바이트 뒤로 명령이 끝날 때까지의 바이트 수
    } capture[SIG_CAPTURES];
};

// 서명 글을 읽는다. 글이 틀리면 false.
bool sig_parse(const char *text, Sig *out);

struct SigRange {
    uint32_t begin, end;        // 훑을 곳 [begin, end) — image 안의 자리(RVA)
};

struct SigHit {
    int count;                          // 맞은 횟수. 2 에서 멈춘다 — 알고 싶은 것은 "정확히 한 번인가"뿐이다
    uint32_t at;                        // 처음 맞은 자리
    uint64_t value[SIG_CAPTURES];       // 그 자리에서 읽어 낸 값: 주소는 RVA, 상수는 그 값
};

// ranges 를 한 번 훑어 서명 n 개가 각각 몇 번 맞는지 센다. hits 는 n 칸.
void sig_scan(const uint8_t *image, size_t size, const SigRange *ranges, int range_count, const Sig *sigs, int n, SigHit *hits);

// 투표: 정확히 한 번 맞은 서명이 need 개 이상이고 그것들이 읽어 낸 값이 모두 같으면 true 와 value(SIG_CAPTURES 칸).
// matched 에 정확히 한 번 맞은 서명의 수. 값이 갈리면 false 다 — 틀린 주소를 내느니 못 찾은 것으로 친다.
bool sig_vote(const Sig *sigs, const SigHit *hits, int n, int need, uint64_t *value, int *matched);
