import statistics as st
from pydantic import BaseModel
from dataset import RubricItem, Query

from config import logger, settings
from openai import OpenAI


class PerformanceItem(BaseModel):
    """
    Base model for performance metrics
    """

    expert_time: float = 0.0
    model_time: float = 0.0

    correctness: list[float] = []
    contradictions: list[float] = []
    answer_overlap: float = 0.0


class Judge:
    """
    Makes the assessment for a given rubric
    """

    def __init__(
        self,
        question: Query,
        model_time: float,
        model: str = "moonshotai/Kimi-K2-Instruct",
        temperature: int = 0,
    ):
        # Question
        self.question = question

        # LLM settings
        self.model = model
        self.temperature = temperature
        self.conversation_history: list[dict] = []
        self.client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/", api_key=settings.NEBIUS_API_KEY
        )

        # Assessment
        self.performance = PerformanceItem(
            expert_time=question.expert_time_mins, model_time=model_time
        )

    def judge(self, response: str):
        """
        Fills the performance data according to the provided information
        """
        for r in self.question.rubrics:
            messages = self._get_rubric_messages(r.operator, response, r.criteria)

            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=messages,
            )

            logger.debug(f"[JUDGE EVAL] {response}")
            if r.operator == "contradiction":
                self.performance.contradictions.append(float(response.choices[0].message.content))
            elif r.operator == "correctness":
                self.performance.correctness.append(float(response.choices[0].message.content))

        # Final evaluation looking for overlap between two answers
        messages = self._get_rubric_messages("overlap", response)

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=messages,
        )
        self.performance.answer_overlap = response.choices[0].message.content

    def return_eval(self) -> dict:
        """
        Returns metrics according to assessment
        """
        logger.debug(self.performance)

        return {
            "time_taken": self.performance.model_time / self.performance.expert_time,
            "overlap": self.performance.answer_overlap,
            "correctness": st.mean(self.performance.correctness) if len(self.performance.correctness) > 0 else 0.0,
            "contradictions": st.mean(self.performance.contradictions) if len(self.performance.contradictions) > 0 else 0.0,
        }

    def _get_rubric_messages(self, eval_type: str, received: str, criteria: str = None):
        """
        Considering the types of the rubric returns a message to be used as evaluator

        Args:
            eval_type (str): Between 'correctness' or 'contradiction'
            question (str): Question to be answered
            received (str): Received answer or statement
            expected (str): Expected answer
            criteria (str): Criteria to be assessed

        Returns:
            list[str]: Returns the prompt to be used
        """
        messages = [
            {
                "role": "system",
                "content": """
                    Play the role of a judge evaluating an assignment.
                    Your task is to assess the rightfulness of the provided answer against the expected one.
                    The answer should be a score from 0.0 to 1.0, where:
                    - 0.0 means the criteria is completely not met
                    - 0.5 means the criteria is partially met
                    - 1.0 means the criteria is fully met
                    Use fractional values (e.g., 0.2, 0.7, 0.85) to express degrees of fulfillment.
                    You MUST only respond with a numeric value between 0.0 and 1.0.
                """,
            }
        ]

        if eval_type == "correctness":
            messages.append(
                {
                    "role": "user",
                    "content": f"""
                        Your duty is to assess the correctness of the provided answer according to the criteria we are looking for.

                        Question to be answered was: {self.question.question}
                        Provided answer: {received}

                        To what degree (0.0 to 1.0) is the statement "{criteria}" correct according to the provided answer?
                        Use fractional values to express partial correctness. For example:
                        - 0.0 = completely incorrect or not addressed
                        - 0.3-0.5 = partially correct or partially addressed
                        - 0.7-0.9 = mostly correct with minor gaps
                        - 1.0 = completely correct
                    """,
                }
            )
        elif eval_type == "contradiction":
            messages.append(
                {
                    "role": "user",
                    "content": f"""
                        Question to be answered was: {self.question.question}
                        Provided answer: {received}
                        Evidence: {criteria}

                        To what degree (0.0 to 1.0) is the evidence in contradiction with the provided answer?
                        Use fractional values to express degrees of contradiction. For example:
                        - 0.0 = no contradiction (evidence fully supports the answer)
                        - 0.3-0.5 = minor contradiction or partial inconsistency
                        - 0.7-0.9 = significant contradiction
                        - 1.0 = complete contradiction
                    """,
                }
            )
        else:
            messages.append(
                {
                    "role": "user",
                    "content": f"""
                        Question to be answered was: {self.question.question}
                        Provided answer: {received}
                        Expected: {self.question.expert_answer}

                        To what degree (0.0 to 1.0) do the expected and provided answers overlap?
                        Use fractional values to express similarity. For example:
                        - 0.0 = completely different, no overlap
                        - 0.2-0.4 = minimal overlap, different meaning
                        - 0.5-0.7 = moderate overlap, similar concepts but different wording
                        - 0.8-0.9 = high overlap, very similar meaning
                        - 1.0 = word-by-word coincidence or practically identical meaning
                    """,
                }
            )

        return messages
