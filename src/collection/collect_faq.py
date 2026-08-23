from __future__ import annotations

import argparse
import asyncio
import csv
import json
import re
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Page


URL = "https://www.car.go.kr/rs/faq/list.do"

CSV_COLUMNS = [
    "faq_no",
    "page_no",
    "question",
    "answer",
    "source_url",
    "collected_at",
]


def clean(text: str | None) -> str:
    """줄바꿈/탭/연속 공백을 한 칸으로 정리"""
    return re.sub(r"\s+", " ", text or "").strip()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


async def get_page_info(page: Page) -> tuple[int, int, int]:
    """
    페이지에 표시되는:
        전체 12 건 (페이지 1/2)
    를 읽어서 (12, 1, 2) 반환
    """
    # 중요: inner_text가 아니라 text_content 사용
    body = await page.locator("body").text_content()
    body = body or ""

    m = re.search(
        r"전체\s*([\d,]+)\s*건\s*\(페이지\s*(\d+)\s*/\s*(\d+)\)",
        body,
    )

    if not m:
        raise RuntimeError(
            "페이지에서 '전체 N 건 (페이지 N/N)' 정보를 찾지 못했습니다."
        )

    total = int(m.group(1).replace(",", ""))
    current = int(m.group(2))
    total_pages = int(m.group(3))

    return total, current, total_pages


async def extract_faqs_from_dom(page: Page, page_no: int) -> list[dict]:
    """
    FAQ 답변이 접혀(display:none 등) 있어도
    textContent를 이용해 질문/답변을 전부 가져옵니다.

    1차: li 단위
    2차: dt/dd 구조
    3차: 질문 요소의 최소 부모 블록 탐색
    """

    rows = await page.evaluate(
        r"""
        () => {
            const norm = (s) =>
                (s || '').replace(/\s+/g, ' ').trim();

            const isQuestion = (s) => {
                s = norm(s);

                if (s.length < 5 || s.length > 500) return false;

                return s.includes('?') || s.includes('？');
            };

            const results = [];
            const seen = new Set();

            const add = (question, answer) => {
                question = norm(question);
                answer = norm(answer);

                // 질문 문구가 답변 앞에 다시 섞여 있으면 제거
                if (answer.startsWith(question)) {
                    answer = norm(answer.slice(question.length));
                }

                if (!isQuestion(question)) return;
                if (!answer) return;
                if (seen.has(question)) return;

                // FAQ 한 건 답변이라고 보기 어려울 정도로 지나치게 큰 블록은 제외
                if (answer.length > 12000) return;

                seen.add(question);
                results.push({question, answer});
            };

            // =====================================================
            // 1차: <li> 하나가 FAQ 한 건인 구조
            // =====================================================
            const lis = Array.from(document.querySelectorAll('li'));

            for (const li of lis) {
                // 화면에 숨겨져 있어도 textContent는 읽을 수 있음
                const blockText = norm(li.textContent);

                if (!blockText || blockText.length > 12000) continue;

                const candidates = Array.from(
                    li.querySelectorAll(
                        'a, button, dt, summary, strong, h3, h4, p, span'
                    )
                );

                const questions = [];

                for (const el of candidates) {
                    const t = norm(el.textContent);

                    if (isQuestion(t) && !questions.includes(t)) {
                        questions.push(t);
                    }
                }

                // 한 li 안에 질문이 정확히 하나일 때만 FAQ 한 건으로 인정
                if (questions.length !== 1) continue;

                const q = questions[0];
                const idx = blockText.indexOf(q);

                if (idx < 0) continue;

                const answer = norm(
                    blockText.slice(idx + q.length)
                );

                add(q, answer);
            }

            // =====================================================
            // 2차: <dt> 질문 + <dd> 답변 구조 fallback
            // =====================================================
            const dts = Array.from(document.querySelectorAll('dt'));

            for (const dt of dts) {
                const q = norm(dt.textContent);

                if (!isQuestion(q)) continue;

                let dd = dt.nextElementSibling;

                while (dd && dd.tagName !== 'DD') {
                    dd = dd.nextElementSibling;
                }

                if (!dd) continue;

                const answer = norm(dd.textContent);

                add(q, answer);
            }

            // =====================================================
            // 3차: 질문 요소 기준으로 '가장 작은 부모 블록' 탐색
            // =====================================================
            const all = Array.from(
                document.querySelectorAll(
                    'a, button, dt, summary, strong, h3, h4'
                )
            );

            for (const el of all) {
                const q = norm(el.textContent);

                if (!isQuestion(q)) continue;
                if (seen.has(q)) continue;

                let cur = el.parentElement;

                for (let depth = 0; depth < 8 && cur; depth++) {
                    const blockText = norm(cur.textContent);

                    if (
                        blockText.length > q.length + 5 &&
                        blockText.length <= 12000
                    ) {
                        // 이 부모 안에 질문이 여러 개 들어 있으면
                        // FAQ 목록 전체를 잡은 것이므로 제외
                        const qEls = Array.from(
                            cur.querySelectorAll(
                                'a, button, dt, summary, strong, h3, h4'
                            )
                        );

                        const uniqueQs = new Set();

                        for (const x of qEls) {
                            const t = norm(x.textContent);
                            if (isQuestion(t)) uniqueQs.add(t);
                        }

                        if (uniqueQs.size === 1) {
                            const idx = blockText.indexOf(q);

                            if (idx >= 0) {
                                const answer = norm(
                                    blockText.slice(idx + q.length)
                                );

                                add(q, answer);
                                break;
                            }
                        }
                    }

                    cur = cur.parentElement;
                }
            }

            return results;
        }
        """
    )

    return [
        {
            "page_no": page_no,
            "question": clean(row["question"]),
            "answer": clean(row["answer"]),
        }
        for row in rows
        if clean(row.get("question")) and clean(row.get("answer"))
    ]


async def save_debug(page: Page, page_no: int, debug_dir: Path) -> None:
    """
    문제가 발생할 때 실제 HTML과 textContent를 확인할 수 있도록 저장.
    """
    debug_dir.mkdir(parents=True, exist_ok=True)

    html = await page.content()
    body_text_content = await page.locator("body").text_content()

    (debug_dir / f"car_go_page_{page_no}.html").write_text(
        html,
        encoding="utf-8",
    )

    (debug_dir / f"car_go_page_{page_no}_text.txt").write_text(
        body_text_content or "",
        encoding="utf-8",
    )


async def go_to_page(page: Page, target_page: int) -> bool:
    """
    페이지 하단 페이지네이션의 숫자(예: 2)를 실제로 클릭.
    페이지 표시가 target_page로 바뀔 때까지 확인.
    """

    _, current, _ = await get_page_info(page)

    if current == target_page:
        return True

    print(f"→ {target_page}페이지 이동")

    # 정확히 숫자만 표시되는 a 태그를 뒤에서부터 확인
    anchors = page.locator("a")
    count = await anchors.count()

    candidates = []

    for i in range(count):
        a = anchors.nth(i)

        try:
            txt = clean(await a.text_content(timeout=500))
        except Exception:
            continue

        if txt == str(target_page):
            candidates.append(a)

    # pagination은 보통 페이지 하단이므로 뒤쪽부터 시도
    for a in reversed(candidates):
        try:
            href = await a.get_attribute("href")
            onclick = await a.get_attribute("onclick")

            print(
                f"  페이지 버튼 발견: "
                f"href={href!r}, onclick={onclick!r}"
            )

            try:
                await a.scroll_into_view_if_needed()
            except Exception:
                pass

            try:
                await a.click(force=True, timeout=3000)
            except Exception:
                try:
                    await a.evaluate("el => el.click()")
                except Exception:
                    continue

            # 페이지 번호 변경 대기
            for _ in range(30):
                await page.wait_for_timeout(200)

                try:
                    _, current, _ = await get_page_info(page)
                except Exception:
                    continue

                if current == target_page:
                    print(f"  {target_page}페이지 이동 성공")
                    return True

        except Exception:
            continue

    return False


def deduplicate(rows: list[dict]) -> list[dict]:
    result = []
    seen = set()

    for row in rows:
        key = clean(row["question"])

        if key in seen:
            continue

        seen.add(key)
        result.append(row)

    return result


def validate_rows(rows: list[dict], expected_total: int) -> None:
    """
    빈 질문/답변 또는 총건수 불일치 시
    성공한 척 CSV를 만들지 않고 오류를 발생시킴.
    """

    empty_question = [
        r for r in rows
        if not clean(r.get("question"))
    ]

    empty_answer = [
        r for r in rows
        if not clean(r.get("answer"))
    ]

    if empty_question:
        raise RuntimeError(
            f"질문이 비어 있는 FAQ가 {len(empty_question)}건 있습니다."
        )

    if empty_answer:
        raise RuntimeError(
            f"답변이 비어 있는 FAQ가 {len(empty_answer)}건 있습니다."
        )

    if len(rows) != expected_total:
        raise RuntimeError(
            f"사이트에는 {expected_total}건이라고 표시되는데 "
            f"실제 추출은 {len(rows)}건입니다. "
            f"불완전한 결과는 정상 완료로 저장하지 않습니다."
        )


def save_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    collected_at = now_iso()

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=CSV_COLUMNS,
        )

        writer.writeheader()

        for faq_no, row in enumerate(rows, start=1):
            writer.writerow(
                {
                    "faq_no": faq_no,
                    "page_no": row["page_no"],
                    "question": row["question"],
                    "answer": row["answer"],
                    "source_url": URL,
                    "collected_at": collected_at,
                }
            )


def save_json(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    output = []

    for faq_no, row in enumerate(rows, start=1):
        output.append(
            {
                "faq_no": faq_no,
                "page_no": row["page_no"],
                "question": row["question"],
                "answer": row["answer"],
                "source_url": URL,
            }
        )

    path.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


async def run(args) -> None:
    debug_dir = Path("data/debug/car_go_faq")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=not args.headed,
            slow_mo=100 if args.headed else 0,
        )

        page = await browser.new_page(
            locale="ko-KR",
            viewport={"width": 1440, "height": 1000},
        )

        print("=" * 65)
        print("자동차리콜센터 FAQ 전체 게시물 수집")
        print(URL)
        print("=" * 65)

        await page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        await page.wait_for_timeout(1200)

        total_count, current_page, total_pages = await get_page_info(page)

        print(f"사이트 전체 게시물 : {total_count}건")
        print(f"총 페이지 수       : {total_pages}페이지")
        print()

        all_rows = []

        for target_page in range(1, total_pages + 1):

            _, current_page, _ = await get_page_info(page)

            if current_page != target_page:
                moved = await go_to_page(page, target_page)

                if not moved:
                    await save_debug(
                        page,
                        current_page,
                        debug_dir,
                    )

                    raise RuntimeError(
                        f"{target_page}페이지 이동에 실패했습니다."
                    )

            # 페이지가 완전히 반영될 시간을 조금 줌
            await page.wait_for_timeout(500)

            _, current_page, _ = await get_page_info(page)

            # 실제 HTML / textContent 백업
            await save_debug(
                page,
                current_page,
                debug_dir,
            )

            rows = await extract_faqs_from_dom(
                page,
                current_page,
            )

            print(
                f"{current_page}페이지 추출: "
                f"{len(rows)}건"
            )

            for i, row in enumerate(rows, start=1):
                print(
                    f"  {i}. {row['question']}"
                )
                print(
                    f"     답변 글자수: {len(row['answer'])}"
                )

            all_rows.extend(rows)

        await browser.close()

    all_rows = deduplicate(all_rows)

    print()
    print("-" * 65)
    print(f"중복 제거 후 실제 FAQ: {len(all_rows)}건")
    print("-" * 65)

    # ★ 핵심 검증:
    # 12건이 아니거나 답변이 공백이면 여기서 에러 발생
    validate_rows(
        all_rows,
        total_count,
    )

    csv_path = Path(args.output)
    json_path = csv_path.with_suffix(".json")

    save_csv(
        csv_path,
        all_rows,
    )

    save_json(
        json_path,
        all_rows,
    )

    print()
    print("=" * 65)
    print("[성공] 모든 FAQ의 질문 + 답변 수집 완료")
    print(f"사이트 표시 건수 : {total_count}건")
    print(f"저장 건수        : {len(all_rows)}건")
    print("빈 질문          : 0건")
    print("빈 답변          : 0건")
    print("=" * 65)
    print(f"CSV  : {csv_path}")
    print(f"JSON : {json_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "자동차리콜센터 FAQ의 모든 페이지를 순회하여 "
            "모든 질문과 답변을 CSV/JSON으로 저장합니다."
        )
    )

    parser.add_argument(
        "--headed",
        action="store_true",
        help="브라우저를 화면에 띄워 실행",
    )

    parser.add_argument(
        "--output",
        default="data/output/car_go_all_faq_complete.csv",
        help="CSV 저장 경로",
    )

    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
