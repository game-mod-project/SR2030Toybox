// 올라와 있는 게임 실행 파일에서 ToyBox 가 쓰는 주소를 찾는다. 주소를 코드에 적어 두지 않는다 —
// "cheat allowcheats" 문자열을 닻으로 삼아 그것을 쓰는 함수와 그 안의 명령에서 얻는다(docs/11-game-internals.md).
// 창도 Windows 도 모르는 순수 함수다. 대조가 하나라도 어긋나면 "못 찾았다"로 친다.
#pragma once

#include <cstddef>
#include <cstdint>

// 모두 이미지의 시작으로부터의 거리(RVA).
struct GameAddresses {
    uint32_t handler;          // 명령 처리 함수: void f(void *context, const char *line)
    uint32_t context;          // 그 함수의 첫 인자로 넘기는 전역 객체(게임이 넘기는 것과 같은 주소)
    uint32_t multiplayer;      // byte. 0 이 아니면 함수가 아무것도 하지 않는다
    uint32_t options;          // dword. 비트 0x40 = 치트 허용
    uint32_t program_state;    // dword. 1 = 월드가 돌고 있다
    uint32_t mode_state;       // dword. 2 = 게임
    uint32_t player_index;     // dword. 플레이어 지역의 인덱스(지역 표의 칸)
    uint32_t player_pointer;   // qword. 플레이어 지역 객체
    uint32_t region_table;     // qword × 1024. 인덱스순 지역 객체 포인터
    uint32_t region_count;     // dword. 지역 표의 마지막 인덱스
};

// image: RVA 대로 펼쳐진 실행 파일(올라와 있는 모듈의 시작 주소), size: 그 크기.
// 찾으면 out 을 채우고 nullptr, 못 찾으면 까닭(UTF-8, 정적 문자열)을 돌려준다.
const char *locate_game(const uint8_t *image, size_t size, GameAddresses *out);
