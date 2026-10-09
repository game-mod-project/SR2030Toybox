#include "sigs.h"

#include <cstring>
#include <vector>

namespace {

int hex(char c)
{
    if (c >= '0' && c <= '9')
        return c - '0';
    c = static_cast<char>(c | 0x20);
    return c >= 'a' && c <= 'f' ? c - 'a' + 10 : -1;
}

// 읽어 낼 자리의 낱말들. 긴 것이 먼저다("[rip+1]" 이 "[rip]" 보다).
const struct Word {
    const char *text;
    uint32_t size;
    bool rip;
    uint32_t tail;
} WORDS[] = {{"[rip+1]", 4, true, 1}, {"[rip+4]", 4, true, 4}, {"[rip]", 4, true, 0}, {"[u32]", 4, false, 0}, {"[u8]", 1, false, 0}};

uint64_t read(const uint8_t *image, uint64_t rva, const Sig::Capture &c)
{
    if (c.size == 1)
        return image[rva + c.at];
    uint32_t raw = 0;
    memcpy(&raw, image + rva + c.at, sizeof(raw));
    if (!c.rip)
        return raw;
    return static_cast<uint64_t>(static_cast<int64_t>(rva) + c.at + 4 + c.tail + static_cast<int32_t>(raw));
}

}  // namespace

bool sig_parse(const char *text, Sig *out)
{
    Sig s = {};
    if (text == nullptr || out == nullptr)
        return false;
    for (const char *c = text; *c != '\0'; ) {
        if (*c == ' ') {
            c++;
            continue;
        }
        const Word *word = nullptr;
        for (const Word &w : WORDS)
            if (strncmp(c, w.text, strlen(w.text)) == 0) {
                word = &w;
                break;
            }
        if (word != nullptr) {
            if (s.captures >= SIG_CAPTURES || s.length + word->size > SIG_MAX)
                return false;
            Sig::Capture &capture = s.capture[s.captures++];
            capture.at = s.length;
            capture.size = word->size;
            capture.rip = word->rip;
            capture.tail = word->tail;
            for (uint32_t i = 0; i < word->size; i++)
                s.any[s.length++] = true;
            c += strlen(word->text);
        } else if (*c == '?') {
            if (s.length >= SIG_MAX)
                return false;
            s.any[s.length++] = true;
            c++;
        } else {
            const int high = hex(c[0]), low = high < 0 ? -1 : hex(c[1]);
            if (low < 0 || s.length >= SIG_MAX)
                return false;
            s.bytes[s.length++] = static_cast<uint8_t>(high * 16 + low);
            c += 2;
        }
    }
    if (s.length == 0 || s.any[0] || s.captures == 0)
        return false;       // 첫 바이트로 후보를 거르므로 첫 낱말은 정해진 바이트여야 한다
    *out = s;
    return true;
}

void sig_scan(const uint8_t *image, size_t size, const SigRange *ranges, int range_count, const Sig *sigs, int n, SigHit *hits)
{
    if (n <= 0)
        return;
    // 첫 바이트가 같은 서명끼리 줄을 세운다 — 구역을 서명의 수만큼이 아니라 한 번만 훑는다
    int head[256];
    for (int &h : head)
        h = -1;
    std::vector<int> next(static_cast<size_t>(n), -1);
    for (int i = n - 1; i >= 0; i--) {
        hits[i] = SigHit();
        next[static_cast<size_t>(i)] = head[sigs[i].bytes[0]];
        head[sigs[i].bytes[0]] = i;
    }
    for (int r = 0; r < range_count; r++) {
        const uint64_t end = ranges[r].end < size ? ranges[r].end : size;
        for (uint64_t rva = ranges[r].begin; rva < end; rva++) {
            for (int i = head[image[rva]]; i >= 0; i = next[static_cast<size_t>(i)]) {
                const Sig &s = sigs[i];
                if (hits[i].count >= 2 || rva + s.length > end)
                    continue;
                uint32_t k = 1;
                while (k < s.length && (s.any[k] || image[rva + k] == s.bytes[k]))
                    k++;
                if (k < s.length)
                    continue;
                if (hits[i].count++ == 0) {
                    hits[i].at = static_cast<uint32_t>(rva);
                    for (int c = 0; c < s.captures; c++)
                        hits[i].value[c] = read(image, rva, s.capture[c]);
                }
            }
        }
    }
}

bool sig_vote(const Sig *sigs, const SigHit *hits, int n, int need, uint64_t *value, int *matched)
{
    int once = 0, first = -1;
    bool same = true;
    for (int i = 0; i < n; i++) {
        if (hits[i].count != 1)
            continue;
        once++;
        if (first < 0)
            first = i;
        else if (sigs[i].captures != sigs[first].captures
                 || memcmp(hits[i].value, hits[first].value, sizeof(uint64_t) * static_cast<size_t>(sigs[first].captures)) != 0)
            same = false;
    }
    if (matched != nullptr)
        *matched = once;
    if (first < 0 || once < need || !same)
        return false;       // 맞은 서명이 하나도 없으면 need 가 0 이하여도 찾은 것이 없다(없는 서명의 값을 읽지 않는다)
    for (int c = 0; c < sigs[first].captures; c++)
        value[c] = hits[first].value[c];
    return true;
}
