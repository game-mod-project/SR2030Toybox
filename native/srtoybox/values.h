// 값 계산: 지금 값 + 요청 → 쓸 값. 창도 게임도 모르는 순수 함수다.
#pragma once

#include <string>

enum class Change {
    Add,      // 더한다(음수면 뺀다)
    Set,      // 이 값으로
    Floor,    // 바닥: 지금 값이 이보다 작으면 이 값으로, 아니면 그대로(최소 유지)
};

enum class Verdict {
    Write,    // *out 을 쓴다
    Nothing,  // 바꿀 것이 없다(이미 그 값이다, 바닥 위다)
    Refuse,   // 쓰지 않는다: 지금 값이나 요청이 유한한 수가 아니다 — 구조가 바뀐 것일 수 있다
};

// 한도는 "여기까지만 민다"는 뜻이다. "이 값으로"는 한도 안으로 자르고, 더하기 · 바닥은 한도를 넘겨 밀지 않을 뿐
// 이미 한도 밖에 있는 값(게임이 그렇게 만든 값)을 한도 쪽으로 끌어오지 않는다.
const double TREASURY_LIMIT = 1e15;   // 국고: ±$1,000 T. 음수는 된다(게임이 허용한다)
const double STOCK_LIMIT = 1e9;       // 재고: 0 이상 10억 이하

Verdict treasury_value(double now, Change change, double amount, double *out);
// 셈은 double 로 하고 결과를 float 로 바꾼다(재고 칸이 float 다 — 약 1,677만부터 낱개 단위가 반올림된다).
Verdict stock_value(float now, Change change, double amount, float *out);

// 게임의 재무 패널과 같은 줄임 표기: 999 · 50.00 K · 1.10 M · 14.43 B · -1.00 T. 유한한 수가 아니면 "?".
std::string short_number(double value);
// 게임의 위쪽 자원 표시줄과 같은 줄임 표기(물자의 수량): 999 · 1.8 M · 23.7 M · 129 K · 779 M — 100 아래는 소수 첫째 자리까지.
std::string short_amount(double value);
