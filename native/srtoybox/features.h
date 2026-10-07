// ToyBox 가 창에서 내놓는 기능 표.
// 넣는 기준: docs/07 에서 검증이 [확인: 효과]인 치트 가운데 불리해지지 않는 것 — 대상이 "플레이어" · "고른 부대"이거나,
// 사용자가 창이나 지도에서 고른 나라 하나에만 닿는 것("외교·영토" 탭. 2026-10-07 에 사용자가 범위를 정했다).
// tests/test_toybox.py 가 이 표를 docs/07 과 대조한다.
#pragma once

// 명령 뒤에 붙는 지역 번호. 한 기능의 인자는 하나다 — 값(has_value)이 있는 기능에는 대상이 없다.
enum class Target {
    None,
    Player,   // 플레이어의 지역(ToyBox 가 게임에서 읽는다)
    Picked,   // 창의 목록에서 고른 나라
};

struct Feature {
    const char *id;       // 치트 이름. 설정 파일의 키로도 쓴다
    const char *tab;      // 창의 탭 (UTF-8)
    const char *label;    // 단추의 이름 (UTF-8)
    const char *help;     // 한 줄 설명 (UTF-8)
    const char *command;  // 게임에 넣는 글. 값이 있으면 뒤에 " <값>" 이 붙는다
    bool has_value;
    long long def, min, max;
    bool confirm;         // 실행 전에 한 번 더 누르게 한다
    Target target;        // 명령 뒤에 붙일 지역
};

extern const Feature FEATURES[];
extern const int FEATURE_COUNT;

const Feature *find_feature(const char *id);
