# Fixed source ground truth: docx-novel-001

Source SHA-256: `c2c13eaf5110ea7e68a41893b91c762151bab5e926e6cc316087b3dc99aa9a26`

Characters are Unicode code points excluding `str.isspace()` whitespace. Punctuation, numbers, and Latin letters count. Markdown/XML markup does not.

There are **19 numbered chapters**, **1 epilogue**, **1 appendix**, and **1 afterword**: **22 body sections**. With the combined cover/TOC front-matter unit, the case expects **23 Markdown files**.

| Scope | Non-whitespace characters | Nonempty paragraphs |
| --- | ---: | ---: |
| whole_document | 114,063 | 1,926 |
| cover | 21 | 3 |
| table_of_contents | 153 | 23 |
| body_including_headings | 113,889 | 1,900 |
| narrative_including_headings | 109,694 | 1,820 |
| narrative_excluding_headings | 109,607 | 1,800 |

| Unit | Section | Characters incl. heading | Characters excl. heading | Nonempty paragraphs |
| --- | --- | ---: | ---: | ---: |
| front-matter | Cover and TOC | 174 | 174 | 26 |
| body-unit-01 | 一、新年 | 8,612 | 8,608 | 162 |
| body-unit-02 | 二、异梦 | 4,670 | 4,666 | 66 |
| body-unit-03 | 三、指环 | 5,157 | 5,153 | 101 |
| body-unit-04 | 四、往事 | 7,899 | 7,895 | 113 |
| body-unit-05 | 五、访客 | 6,139 | 6,135 | 84 |
| body-unit-06 | 六、梦婆 | 5,489 | 5,485 | 74 |
| body-unit-07 | 七、谜团 | 7,030 | 7,026 | 97 |
| body-unit-08 | 八、真相 | 6,204 | 6,200 | 114 |
| body-unit-09 | 九、追忆 | 4,365 | 4,361 | 59 |
| body-unit-10 | 十、故乡 | 4,849 | 4,845 | 55 |
| body-unit-11 | 十一、重逢 | 5,215 | 5,210 | 88 |
| body-unit-12 | 十二、浮城 | 4,226 | 4,221 | 63 |
| body-unit-13 | 十三、祭司 | 4,926 | 4,921 | 64 |
| body-unit-14 | 十四、米娅 | 4,072 | 4,067 | 63 |
| body-unit-15 | 十五、陷阱 | 5,980 | 5,975 | 100 |
| body-unit-16 | 十六、高塔 | 4,358 | 4,353 | 78 |
| body-unit-17 | 十七、博士 | 4,527 | 4,522 | 68 |
| body-unit-18 | 十八、基地 | 4,719 | 4,714 | 89 |
| body-unit-19 | 十九、末日 | 4,176 | 4,171 | 67 |
| body-unit-20 | 尾声 | 7,081 | 7,079 | 215 |
| body-unit-21 | 附录：遗落的传说 | 3,610 | 3,602 | 73 |
| body-unit-22 | 后记 | 585 | 583 | 7 |

The baseline was calculated directly from the DOCX and cross-checked with a second XML parser using the alternative Word representation. Both traversals agree on every logical paragraph's text, style, and order; the TOC and body headings also agree.

Word's cached application statistics are retained in the JSON for audit but are not the counting authority. The two footer parts contain a cached page-number value and are excluded.

Run `python evals/check_preparation.py --case docx-novel-001 --check-reference` to verify the source hash, frozen ground-truth binding, and reference consistency. Ground truth is retained as fixed data; the one-time establishment script is not part of the repository.

This freezes source text and structure. It does not assert that a human has approved the reference Markdown's visual formatting.
