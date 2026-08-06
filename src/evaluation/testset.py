from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

_MIN_DOCUMENTS = 3
_MAX_SAMPLE_PAPERS = 8


def _make_question(
    question_id: str, question_type: str, question: str, ground_truth: str, paper_id: str
) -> dict[str, Any]:
    return {
        "id": question_id,
        "question_type": question_type,
        "question": question,
        "ground_truth": ground_truth,
        "ground_truth_doc_ids": [paper_id],
    }


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao bo evaluation set tu cleaned dataframe."""
    if len(df) < _MIN_DOCUMENTS:
        raise ValueError(f"Need at least {_MIN_DOCUMENTS} cleaned documents to build a test set, got {len(df)}.")

    sample = df.head(min(_MAX_SAMPLE_PAPERS, len(df)))

    test_set: list[dict[str, Any]] = []
    counter = 0

    for _, row in sample.iterrows():
        title = row["title"]
        paper_id = row["paper_id"]

        # Cau hoi ve noi dung: khong co trigger phrase rieng -> qa.answer_question se
        # tra ve first_sentence(summary) cua doc duoc lookup/retrieve.
        counter += 1
        test_set.append(
            _make_question(
                f"q-{counter:03d}",
                "summary",
                f"What is the paper titled '{title}' about?",
                first_sentence(row["summary"]),
                paper_id,
            )
        )

        if row["authors_joined"]:
            counter += 1
            test_set.append(
                _make_question(
                    f"q-{counter:03d}",
                    "authors",
                    f"Who authored the paper titled '{title}'?",
                    row["authors_joined"],
                    paper_id,
                )
            )

        counter += 1
        test_set.append(
            _make_question(
                f"q-{counter:03d}",
                "date",
                f"When was the paper titled '{title}' published?",
                row["published"],
                paper_id,
            )
        )

        if row["categories_joined"]:
            counter += 1
            test_set.append(
                _make_question(
                    f"q-{counter:03d}",
                    "categories",
                    f"What categories does the paper titled '{title}' belong to?",
                    row["categories_joined"],
                    paper_id,
                )
            )

    write_json(output_path, test_set)
    return test_set