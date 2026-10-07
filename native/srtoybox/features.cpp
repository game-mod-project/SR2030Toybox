#include "features.h"

#include <cstring>

const Feature FEATURES[] = {
    {"treasury", "돈", "국고 추가", "입력한 금액(백만 달러)만큼 국고가 늘어난다", "cheat treasury", true, 10000, 1, 1000000, false},
    {"georgew", "돈", "국고 +$10 B", "국고가 100억 달러 늘어난다", "cheat georgew", false, 0, 0, 0, false},
    {"georgeww", "돈", "국고 +$100 B", "국고가 1000억 달러 늘어난다", "cheat georgeww", false, 0, 0, 0, false},
    {"products", "물자", "모든 물자 추가", "입력한 수량만큼 모든 물자의 재고가 늘어난다", "cheat products", true, 100000, 1, 100000000, false},
    {"branson", "물자", "모든 물자 +100만", "모든 물자의 재고가 100만씩 늘어난다", "cheat branson", false, 0, 0, 0, false},
    {"bezos", "물자", "모든 물자 +1억", "모든 물자의 재고가 약 1억씩 늘어난다", "cheat bezos", false, 0, 0, 0, false},
    {"technology", "연구", "기술 수준 N 이하 전부 보유", "입력한 기술 수준 이하의 기술을 모두 연구한 것으로 만든다", "cheat technology", true, 120, 1, 999, false},
    {"e=mc2", "연구", "대기열의 연구 즉시 완료", "대기열에 건 연구가 바로 끝난다. 대기열이 비어 있으면 아무 일도 없다", "cheat e=mc2", false, 0, 0, 0, false},
    {"finalexam", "연구", "지식 순위 올리기", "지식 지수 순위가 오른다", "cheat finalexam", false, 0, 0, 0, false},
    {"populate", "인구·여론", "인구 +100만", "인구가 100만 늘어난다", "cheat populate", false, 0, 0, 0, false},
    {"shelovesme", "인구·여론", "세계 시장 여론 최고", "세계 시장 여론과 보조금률이 최고가 된다", "cheat shelovesme", false, 0, 0, 0, false},
    {"approval", "인구·여론", "내 나라 지지율 100%", "국내 지지율이 100% 가 된다", "cheat approval", false, 0, 0, 0, false, Target::Player},
    {"love", "외교·영토", "관계 최고", "고른 나라와의 외교 · 민간 관계가 가득 차고 전쟁 명분이 0 이 된다", "cheat love", false, 0, 0, 0, false, Target::Picked},
    {"neutral", "외교·영토", "관계 중립", "고른 나라와의 관계가 절반이 되고 전쟁 명분이 0 이 된다", "cheat neutral", false, 0, 0, 0, false, Target::Picked},
    {"treaty", "외교·영토", "동맹 맺기", "지도에서 나라를 고른 뒤 누른다. 그 나라와 동맹이 된다(조약 13종). 위 목록과는 상관없다", "cheat treaty", false, 0, 0, 0, false, Target::None},
    {"annex", "외교·영토", "병합", "고른 나라의 땅이 내 영토가 된다", "cheat annex", false, 0, 0, 0, true, Target::Picked},
    {"colonize", "외교·영토", "식민지화", "고른 나라가 내 식민지이자 동맹국이 된다", "cheat colonize", false, 0, 0, 0, true, Target::Picked},
    {"novichok", "외교·영토", "지도자 제거", "고른 나라의 지도자가 죽는다", "cheat novichok", false, 0, 0, 0, true, Target::Picked},
    {"fight", "외교·영토", "전쟁 붙이기", "지도에서 한 나라를 고른 뒤 누른다. 그 나라와 목록에서 고른 나라가 싸운다", "cheat fight", false, 0, 0, 0, true, Target::Picked},
    {"becomeregion", "외교·영토", "이 나라로 플레이", "플레이하는 나라가 고른 나라로 바뀐다", "cheat becomeregion", false, 0, 0, 0, true, Target::Picked},
    {"spawnunit", "부대", "고른 칸에 부대 생성", "지도에서 칸을 고른 뒤 누른다. 입력한 장비 번호의 부대가 생긴다(보급은 빈 채)", "cheat spawnunit", true, 2413, 1, 99999, false},
    {"stranded", "부대", "고른 부대 보급 채우기/비우기", "부대를 고른 뒤 누른다. 연료·보급·탄약이 100% 가 되고, 다시 누르면 0% 가 된다", "cheat stranded", false, 0, 0, 0, false},
    {"darran", "부대", "최강 부대 묶음 받기", "병과마다 강한 부대를 한 묶음 받는다", "cheat darran", false, 0, 0, 0, false},
    {"fullmapshow", "화면·진행", "GUI 숨기기/보이기", "게임의 GUI 를 모두 숨긴다. 다시 누르면 돌아온다", "cheat fullmapshow", false, 0, 0, 0, false},
    {"instantwin", "화면·진행", "즉시 승리", "승리 창이 뜬다. 이어서 할 수 있다", "cheat instantwin", false, 0, 0, 0, true},
};

const int FEATURE_COUNT = static_cast<int>(sizeof(FEATURES) / sizeof(FEATURES[0]));

const Feature *find_feature(const char *id)
{
    for (int i = 0; i < FEATURE_COUNT; i++)
        if (strcmp(FEATURES[i].id, id) == 0)
            return &FEATURES[i];
    return nullptr;
}
