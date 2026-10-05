/* SR-UTF8 디코더. 규칙 설명은 src/srkit/srutf8.py 참고(두 구현은 같은 결과를 내야 한다). */
#ifndef SRDECODE_H
#define SRDECODE_H

#include <stddef.h>

#define SR_PH_CELL 0xE000 /* 폭 측정용: 한글 한 칸 */
#define SR_PH_ZERO 0xE001 /* 폭 측정용: 폭 0 */

/* src[0..n) 을 UTF-16 으로 풀어 필요한 코드 유닛 수를 돌려준다.
 * dst 가 NULL 이 아니면 최대 cap 개까지만 쓴다(넘쳐도 개수는 끝까지 센다).
 * measure != 0 은 폭 측정 경로(한 바이트만 넘어오는 경우의 자리표시 처리). */
size_t sr_decode(const unsigned char *src, size_t n, int measure, wchar_t *dst, size_t cap);

#endif
