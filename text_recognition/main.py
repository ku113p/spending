import asyncio
import shutil
import tempfile
import os
import logging
from contextlib import asynccontextmanager
from concurrent.futures import ProcessPoolExecutor

from fastapi import FastAPI, File, UploadFile, HTTPException, responses
from paddleocr import PaddleOCR

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NUM_WORKERS = 2
APP_TEMP_DIR = tempfile.gettempdir()
EXAMPLE_IMAGE = os.path.join(os.path.dirname(__file__), "example.png")

class ExecutorWrapper:
    _executor: ProcessPoolExecutor | None = None

    @classmethod
    def set_executor(cls, executor: ProcessPoolExecutor):
        cls._executor = executor

    @classmethod
    def get_executor(cls) -> ProcessPoolExecutor:
        if cls._executor is None:
            raise RuntimeError("Executor not initialized")
        return cls._executor


def create_model() -> PaddleOCR:
    return PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


class WorkerWrapper:
    _model: PaddleOCR | None = None

    @classmethod
    def init(cls):
        cls._model = create_model()

    @classmethod
    def extract_text_worker(cls, src: str) -> str:
        if cls._model is None:
            raise RuntimeError("Model not initialized")

        result = cls._model.predict(src)
        return "\n".join([line for block in result for line in block["rec_texts"]])

    @classmethod
    def warmup(cls):
        if os.path.exists(EXAMPLE_IMAGE):
            try:
                _ = cls.extract_text_worker(EXAMPLE_IMAGE)
                logger.info("Worker warmed up with example image.")
            except Exception as e:
                logger.warning(f"Warmup failed on example image: {e}")
        else:
            logger.warning("Warmup skipped: example image not found.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up app...")

    executor = ProcessPoolExecutor(
        max_workers=NUM_WORKERS,
        initializer=WorkerWrapper.init
    )
    ExecutorWrapper.set_executor(executor)

    # Warm up workers
    logger.info("Warming up workers...")
    loop = asyncio.get_event_loop()
    await asyncio.gather(*[
        loop.run_in_executor(executor, WorkerWrapper.warmup)
        for _ in range(NUM_WORKERS)
    ])

    yield

    logger.info("Shutting down executor...")
    executor.shutdown(wait=True)

app = FastAPI(lifespan=lifespan)


@app.post("/text")
async def recognize_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a filename")

    loop = asyncio.get_running_loop()
    suffix = f".{file.filename.split('.')[-1]}" if '.' in file.filename else ''

    with tempfile.NamedTemporaryFile(dir=APP_TEMP_DIR, suffix=suffix) as t_file:
        shutil.copyfileobj(file.file, t_file)

        result = await loop.run_in_executor(
            ExecutorWrapper.get_executor(),
            WorkerWrapper.extract_text_worker,
            t_file.name
        )

        if not result:
            return responses.JSONResponse(status_code=500, content={"error": "Failed to extract text from image"})

        logger.info(f"OCR output text length: {len(result)} characters")

        return {"text": result}
