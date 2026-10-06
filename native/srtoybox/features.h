// ToyBox 가 창에서 내놓는 기능 표.
// 넣는 기준: docs/07 에서 검증이 [확인: 효과]이고 대상이 "플레이어" 또는 "고른 부대"인 치트 가운데 불리해지지 않는 것.
// tests/test_toybox.py 가 이 표를 docs/07 과 대조한다.
#pragma once

struct Feature {
    const char *id;       // 치트 이름. 설정 파일의 키로도 쓴다
    const char *tab;      // 창의 탭 (UTF-8)
    const char *label;    // 단추의 이름 (UTF-8)
    const char *help;     // 한 줄 설명 (UTF-8)
    const char *command;  // 게임에 넣는 글. 값이 있으면 뒤에 " <값>" 이 붙는다
    bool has_value;
    long long def, min, max;
    bool confirm;         // 실행 전에 한 번 더 누르게 한다
};

extern const Feature FEATURES[];
extern const int FEATURE_COUNT;

const Feature *find_feature(const char *id);
