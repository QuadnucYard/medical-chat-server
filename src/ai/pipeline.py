from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, overload

from .config import settings
from .logging import logger

logger.info("Start pipeline")

from .kgqa.answer import Answer

if TYPE_CHECKING:
    from .slu.detector import DetectResult


class MedQAPipeline:
    def __init__(self) -> None:
        logger.info("Init MedQAPipeline")
        logger.info("Loading model async.")
        self.load_model_task = asyncio.ensure_future(self._load_model())
        self.answerer = Answer()
        logger.info("OK.")

    async def _load_model(self):
        from .slu.detector import JointIntentSlotDetector

        self.detector = JointIntentSlotDetector.from_pretrained(
            model_path=settings.MODEL_PATH,
            tokenizer_path=settings.TOKENIZER_PATH,
            intent_label_path=settings.INTENT_LABEL_PATH,
            slot_label_path=settings.SLOT_LABEL_PATH,
        )
        logger.info("Model loading done")

    def identify_question_entity(self, q: DetectResult) -> tuple[str, str] | None:
        entity: str | None = None
        question_type: str | None = None
        if q.slots.__contains__("disease"):
            entity = q.slots["disease"][0]
        elif q.slots.__contains__("symptom"):
            entity = q.slots["symptom"][0]
        question_type = q.intent
        return None if not question_type or not entity else (question_type, entity)

    async def pipeline(self, question: str):
        # asyncio.get_event_loop().run_until_complete(self.load_model_task)
        await self.load_model_task
        res = self.detector.detect(question)
        logger.info(res)
        qe = self.identify_question_entity(res)
        if not qe or qe[0] == "[UNK]":
            return "您的问题并不明确，请换个问法再说一遍，谢谢。"
        return self.answerer.create_answer(*qe)

    @overload
    async def __call__(self, question: str) -> str:
        ...

    @overload
    async def __call__(self, question: list[str]) -> list[str]:
        ...

    async def __call__(self, question: str | list[str]):
        if isinstance(question, list):
            return await asyncio.gather(*list(map(self.pipeline, question)))
        return await self.pipeline(question)


async def main():
    pipeline = MedQAPipeline()
    while True:
        text = input("input: ")
        print(await pipeline(text))


if __name__ == "__main__":
    asyncio.run(main())
