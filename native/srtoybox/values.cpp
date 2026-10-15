#include "values.h"

#include <algorithm>
#include <cmath>
#include <cstdio>

namespace {

// 자르기 전의 바라는 값. 쓸 것이 없거나 쓰면 안 되면 그 판정을, 셈했으면 Verdict::Write 와 *out.
Verdict wanted(double now, Change change, double amount, double *out)
{
    if (!std::isfinite(now) || !std::isfinite(amount))
        return Verdict::Refuse;
    if (change == Change::Floor && now >= amount)
        return Verdict::Nothing;     // 바닥은 값을 내리지 않는다 — 한도 밖의 값이어도 자르지 않는다
    *out = change == Change::Add ? now + amount : amount;
    return Verdict::Write;
}

}  // namespace

Verdict treasury_value(double now, Change change, double amount, double *out)
{
    double value = 0;
    const Verdict verdict = wanted(now, change, amount, &value);
    if (verdict != Verdict::Write)
        return verdict;
    const bool set = change == Change::Set;      // 더하기 · 바닥은 한도 밖에 있던 값을 한도 쪽으로 끌어오지 않는다
    const double high = set ? TREASURY_LIMIT : std::max(TREASURY_LIMIT, now);
    const double low = set ? -TREASURY_LIMIT : std::min(-TREASURY_LIMIT, now);
    value = std::min(high, std::max(low, value));
    if (value == now)
        return Verdict::Nothing;
    *out = value;
    return Verdict::Write;
}

Verdict stock_value(float now, Change change, double amount, float *out)
{
    double value = 0;
    const Verdict verdict = wanted(now, change, amount, &value);
    if (verdict != Verdict::Write)
        return verdict;
    const double high = change == Change::Set ? STOCK_LIMIT : std::max(STOCK_LIMIT, static_cast<double>(now));
    const float next = static_cast<float>(std::min(high, std::max(0.0, value)));
    if (next == now)
        return Verdict::Nothing;
    *out = next;
    return Verdict::Write;
}

std::string short_number(double value)
{
    if (!std::isfinite(value))
        return "?";
    const double size = std::fabs(value);
    if (size < 0.5)
        return "0";                  // "-0" 이 되지 않게
    char text[40];
    if (size < 999.5)
        snprintf(text, sizeof(text), "%.0f", value);
    else if (size < 999.995e3)
        snprintf(text, sizeof(text), "%.2f K", value / 1e3);
    else if (size < 999.995e6)
        snprintf(text, sizeof(text), "%.2f M", value / 1e6);
    else if (size < 999.995e9)
        snprintf(text, sizeof(text), "%.2f B", value / 1e9);
    else
        snprintf(text, sizeof(text), "%.2f T", value / 1e12);
    return text;
}

std::string short_amount(double value)
{
    static const struct {
        double unit;
        char letter;
    } UNITS[] = {{1e3, 'K'}, {1e6, 'M'}, {1e9, 'B'}, {1e12, 'T'}};
    const int last = static_cast<int>(sizeof(UNITS) / sizeof(UNITS[0])) - 1;
    if (!std::isfinite(value))
        return "?";
    const double size = std::fabs(value);
    if (size < 0.5)
        return "0";                  // "-0" 이 되지 않게
    char text[40] = "";
    if (size < 999.5) {
        snprintf(text, sizeof(text), "%.0f", value);
        return text;
    }
    int u = 0;
    while (u < last && size / UNITS[u].unit >= 999.5)
        u++;                         // 999.5 K 부터는 1.0 M 이다
    snprintf(text, sizeof(text), size / UNITS[u].unit < 99.95 ? "%.1f %c" : "%.0f %c", value / UNITS[u].unit, UNITS[u].letter);
    return text;
}
