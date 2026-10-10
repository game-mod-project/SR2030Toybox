// ToyBox 가 창에서 내놓는 기능 표.
// 넣는 기준: docs/07 에서 검증이 [확인: 효과]인 치트 가운데 불리해지지 않는 것 — 대상이 "플레이어" · "고른 부대"이거나,
// 사용자가 창이나 지도에서 고른 나라 하나에만 닿는 것("외교·영토" 탭. 2026-10-07 에 사용자가 범위를 정했다).
// tests/test_toybox.py 가 이 표를 docs/07 과 대조한다.
// 줄은 두 가지다: 아직 내장 치트로 도는 줄(command 를 게임에 넣는다)과, ToyBox 가 값을 직접 쓰는 줄(direct — 3단계 2 부터).
// 직접 쓰는 줄은 자리와 이름만 표에 두고, 하는 일은 keeper 의 요청이다 — 내장 치트를 거치지 않는다.
// 연구의 두 줄(technology · e=mc2)은 3단계 3 에서 직접 쓰는 줄이 됐다 — 기술 · 부대 설계의 보유 비트를 쓴다(research.h).
#pragma once

// 명령 뒤에 붙는 지역 번호. 한 기능의 인자는 하나다 — 값(has_value)이 있는 기능에는 대상이 없다.
enum class Target {
    None,
    Player,   // 플레이어의 지역(ToyBox 가 게임에서 읽는다)
    Picked,   // 창의 목록에서 고른 나라
};

// 내장 치트를 거치지 않고 ToyBox 가 직접 쓰는 일의 종류. None 이면 아직 내장 치트로 도는 줄이다.
enum class Direct {
    None,
    TechUp,            // 플레이어의 기술 수준 +1
    OpinionBest,       // 플레이어의 세계 시장 여론 세 칸을 최고로
    RelationBest,      // 고른 나라와의 관계 최고, 전쟁 명분 0(양쪽 객체에)
    RelationNeutral,   // 고른 나라와의 관계 중립, 전쟁 명분 0(〃)
    TechLevel,         // 입력한 수준 이하의 기술을 모두 플레이어의 보유로(선행 기술 포함)
    QueueDone,         // 플레이어의 대기열에 있는 기술 · 부대 설계를 모두 보유로 만들고 대기열에서 뺀다
    PeopleAdd,         // 플레이어의 인구 +100만(3단계 4)
    ApprovalBest,      // 플레이어의 국내 지지율 100%(3단계 4)
};

struct Feature {
    const char *id;       // 치트 이름(직접 쓰는 줄은 그 일을 하던 치트의 이름). 설정 파일의 키로도 쓴다
    const char *tab;      // 창의 탭 (UTF-8)
    const char *label;    // 단추의 이름 (UTF-8)
    const char *help;     // 한 줄 설명 (UTF-8)
    const char *command;  // 게임에 넣는 글. 값이 있으면 뒤에 " <값>" 이 붙는다. 직접 쓰는 줄은 빈 글이다
    bool has_value;       // 단추 앞에 수를 받는다(내장 치트: 명령 뒤에 붙는다, TechLevel: 기술 수준)
    long long def, min, max;
    bool confirm;         // 실행 전에 한 번 더 누르게 한다
    Target target;        // 명령 뒤에 붙일 지역(직접 쓰는 줄: Picked 면 고른 나라가 대상이다)
    Direct direct;        // 직접 쓰는 일
};

extern const Feature FEATURES[];
extern const int FEATURE_COUNT;
int cheat_feature_count();   // 아직 내장 치트로 도는 줄의 수

const Feature *find_feature(const char *id);
