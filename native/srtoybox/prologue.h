// 함수의 머리(프롤로그)에서 통째로 옮겨도 되는 명령들의 길이를 센다.
// 다른 훅(Steam 오버레이 등)이 함수 머리에 심은 점프를 건너뛰는 진입로를 만들 때 쓴다(overlay.cpp).
#pragma once

// code 의 처음부터 명령을 하나씩 세어, want 바이트 이상을 덮는 가장 짧은 길이를 돌려준다.
// 아는 것은 함수 머리에 흔하고 다른 자리로 옮겨도 뜻이 같은 명령뿐이다: push, mov · lea 의 레지스터 · [레지스터+변위] 꼴, sub rsp.
// 모르는 명령(점프 · 호출 · RIP 상대 주소 등)을 만나거나 size 안에서 끝나지 않으면 0 — 그때는 옮기지 않는다.
int prologue_length(const unsigned char *code, int size, int want);
