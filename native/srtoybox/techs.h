// 연구 목록의 이름과 줄. 게임도 창도 메모리도 모르는 순수 함수다.
// 기술의 이름표는 빌드할 때 저장소의 번역 테이블(mods/korean/translation/localtext-ttr.csv 의 TTRTEXT|<번호>|0)에서 만든다
// (src/srkit/toybox.py 의 tech_rows → build/toybox-obj/techs_table.inc). 부대 설계의 이름은 게임 메모리에서 읽는다(DesignRow.name).
#pragma once

#include <string>
#include <vector>

#include "research.h"

std::string tech_label(int id);              // "비생식 복제". 한글 이름이 비었으면 영문, 표에 없으면 "#49"
std::string tech_kind_label(int kind);       // 기술의 분류(1 … 6): "전쟁". 표에 없으면 번호
std::string design_class_label(int cls);     // 부대 설계의 병과(0 … 21): "보병". 표에 없으면 번호
const int TECH_KINDS = 6;                    // 분류는 1 … 6
const int DESIGN_CLASSES = 22;               // 병과는 0 … 21

// 게임 메모리의 글을 UTF-8 로. size 는 바이트 수(0 을 만나면 거기서 끝난다).
// 한글화가 옮긴 이름은 SR-UTF8(src/srkit/srutf8.py · native/srhook/srdecode.c 와 같은 규칙)이고, 원본의 이름은 CP1252 다 —
// SR-UTF8 의 유효한 시퀀스가 아닌 바이트는 CP1252 글자로 읽는다. 칸에 맞춰 잘린 한글의 꼬리(끝의 반쪽 글자)는 버린다.
std::string game_text_to_utf8(const char *text, size_t size);

// 목록의 보기.
enum class Show {
    All,          // 전체
    Mine,         // 자국 보유
    NotMine,      // 자국 미보유
    OthersOnly,   // 타국만 보유: 타국이 하나라도 보유했고 자국은 미보유
    Picked,       // 고른 나라의 보유
    FromPicked,   // 고른 나라에서 가져올 것: 그 나라가 보유했고 자국은 미보유
};

struct ListFilter {
    bool designs = false;         // 부대 설계의 목록인가(아니면 기술)
    Show show = Show::NotMine;
    int kind = -1;                // 분류(기술) · 병과(부대 설계). -1 이면 전체
    std::string find;             // 이름이나 번호의 일부(영문은 대소문자를 가리지 않는다). 비었으면 전부
    bool by_picked = false;       // 보유국으로 거른다: 고른 나라가 보유한 것만(보기와 함께 건다)
};

const int STATE_NONE = 0, STATE_QUEUED = 1, STATE_MINE = 2;   // 미보유 · 연구 중 · 보유

struct ListRow {
    int id = 0;
    std::string name;
    int kind = 0;                 // 분류 · 병과
    int level = 0;                // 기술 수준 · 등장 연도
    int state = STATE_NONE;
    int others = 0;               // 보유한 다른 나라의 수
    int owners[2] = {};           // 그 가운데 앞의 둘(지역 인덱스. 없으면 0)
    bool picked = false;          // 고른 나라가 보유했다
};

std::string state_label(int state);   // "미보유" · "연구 중" · "보유"

// 거르개를 지난 줄. 순서는 수준(연도) · 번호의 오름차순이다.
std::vector<ListRow> research_rows(const ResearchTables &tables, const ListFilter &filter);
