"""
Load the data from public.csv considering the query type and the rubric to be used for the assessment.
"""
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class RubricItem:
    """Rubric item schema"""
    operator: str  # 'correctness' or 'contradiction'
    criteria: str


@dataclass
class Query:
    """A single financial research query."""
    id: str
    question: str
    expert_answer: str
    question_type: str
    expert_time_mins: float
    rubrics: list[RubricItem]

    @property
    def correctness_rubrics(self) -> list[RubricItem]:
        """Get only correctness rubrics."""
        return [r for r in self.rubrics if r.operator == "correctness"]

    @property
    def contradiction_rubric(self) -> Optional[RubricItem]:
        """Get the contradiction rubric if exists."""
        for r in self.rubrics:
            if r.operator == "contradiction":
                return r
        return None

class DatasetLoader:
    """Dataset loader for the public size of the benchmark"""

    QUESTION_TYPES = [
        "Quantitative Retrieval",
        "Qualitative Retrieval",
        "Numerical Reasoning",
        "Complex Retrieval",
        "Adjustments",
        "Beat or Miss",
        "Trends",
        "Financial Modeling",
        "Market Analysis",
    ]

    def __init__(self, data_path: str = "data/public.csv"):
        self.data_path = Path(data_path)
        self._queries: list[Query] = []
        self._load_data()

    def _load_data(self) -> None:
        """Load queries from CSV file."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.data_path}")

        with open(self.data_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                # Parse rubrics from JSON string
                rubrics_str = row.get("Rubric", "[]")
                try:
                    # Handle single quotes in JSON
                    rubrics_str = rubrics_str.replace("'", '"')
                    rubrics_data = json.loads(rubrics_str)
                except json.JSONDecodeError:
                    rubrics_data = []

                rubrics = [
                    RubricItem(
                        operator=r.get("operator", ""),
                        criteria=r.get("criteria", "")
                    )
                    for r in rubrics_data
                ]

                # Parse expert time
                try:
                    expert_time = float(row.get("Expert time (mins)", 0))
                except (ValueError, TypeError):
                    expert_time = 0.0

                task = Query(
                    id=f"q_{idx:03d}",
                    question=row.get("Question", ""),
                    expert_answer=row.get("Answer", ""),
                    question_type=row.get("Question Type", "Unknown"),
                    expert_time_mins=expert_time,
                    rubrics=rubrics,
                )
                self._queries.append(task)

    def get_queries(
        self,
        question_type: Optional[list[str]] = None,
    ) -> list[Query]:
        """
        Get queries with type filtering.
        """
        tasks = self._queries

        # Filter by categories
        if question_type in self.QUESTION_TYPES:
            tasks = [t for t in tasks if t.category in self.QUESTION_TYPES]

        return tasks

    def get_task_by_id(self, task_id: str) -> Optional[Query]:
        """Get a specific task by ID."""
        for task in self._queries:
            if task.id == task_id:
                return task
        return None

    def __len__(self) -> int:
        return len(self._queries)

    def __iter__(self):
        return iter(self._queries)
