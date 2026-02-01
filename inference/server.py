"""
CodePilot Inference Server
High-performance inference using vLLM with PagedAttention
"""

import os
import logging
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# ---------------------------------------------------------------------------
# vLLM is only available when the GPU image is present.  CI imports are
# guarded so that linting / type-checking can still run on a plain runner.
# ---------------------------------------------------------------------------
try:
    from vllm import LLM, SamplingParams
except ImportError:  # pragma: no cover
    LLM = None  # type: ignore[assignment,misc]
    SamplingParams = None  # type: ignore[assignment,misc]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

llm_engine = None


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class CompletionRequest(BaseModel):
    """Request model for code completion"""

    prompt: str = Field(..., description="Code prompt/prefix")
    max_tokens: int = Field(
        default=150, ge=1, le=1024, description="Maximum tokens to generate"
    )
    temperature: float = Field(
        default=0.2, ge=0.0, le=2.0, description="Sampling temperature"
    )
    top_p: float = Field(
        default=0.95, ge=0.0, le=1.0, description="Nucleus sampling parameter"
    )
    top_k: int = Field(
        default=50, ge=1, le=100, description="Top-k sampling parameter"
    )
    stop: Optional[List[str]] = Field(default=None, description="Stop sequences")
    stream: bool = Field(default=False, description="Stream response")


class ExplanationRequest(BaseModel):
    """Request model for code explanation"""

    code: str = Field(..., description="Code to explain")
    language: str = Field(default="c", description="Programming language (c/cpp)")


class BugDetectionRequest(BaseModel):
    """Request model for bug detection"""

    code: str = Field(..., description="Code to analyze")
    check_iso26262: bool = Field(
        default=True, description="Check ISO 26262 violations"
    )


class TestGenerationRequest(BaseModel):
    """Request model for unit test generation"""

    function_code: str = Field(..., description="Function code to test")
    test_framework: str = Field(
        default="unity", description="Test framework (unity/gtest)"
    )


class CompletionResponse(BaseModel):
    """Response model for completions"""

    completion: str
    tokens_generated: int
    finish_reason: str


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------


def create_completion_prompt(prompt: str) -> str:
    return (
        "### Instruction:\n"
        "Complete the following automotive embedded C/C++ code:\n\n"
        f"### Code:\n{prompt}"
    )


def create_explanation_prompt(code: str, language: str) -> str:
    return (
        "### Instruction:\n"
        f"Explain the following {language.upper()} code in the context of automotive "
        "embedded systems.\nInclude information about:\n"
        "- What the code does\n"
        "- Automotive protocols/standards used (AUTOSAR, CAN, etc.)\n"
        "- Safety considerations (ISO 26262)\n"
        "- Potential issues or improvements\n\n"
        f"### Code:\n{code}\n\n"
        "### Explanation:"
    )


def create_bug_detection_prompt(code: str, check_iso26262: bool) -> str:
    iso_note = (
        "Check for ISO 26262 safety violations including null pointer checks, "
        "uninitialized variables, and buffer overflows. "
        if check_iso26262
        else ""
    )
    return (
        "### Instruction:\n"
        "Analyze the following automotive embedded code for potential bugs and issues.\n"
        f"{iso_note}\n\n"
        f"### Code:\n{code}\n\n"
        "### Analysis:"
    )


def create_test_generation_prompt(function_code: str, framework: str) -> str:
    return (
        "### Instruction:\n"
        f"Generate comprehensive unit tests for the following function using "
        f"{framework.upper()} test framework.\n"
        "Include:\n"
        "- Normal case tests\n"
        "- Edge case tests\n"
        "- Error condition tests\n"
        "- Mock automotive interfaces (CAN, etc.) if needed\n\n"
        f"### Function:\n{function_code}\n\n"
        "### Tests:"
    )


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm_engine

    model_path = os.getenv("MODEL_PATH", "../model/codepilot-13b")
    logger.info("Loading model from %s ...", model_path)

    if LLM is None:
        logger.warning("vLLM not installed – running in stub mode (no completions).")
    else:
        llm_engine = LLM(
            model=model_path,
            tensor_parallel_size=1,
            dtype="float16",
            max_model_len=4096,
            gpu_memory_utilization=0.9,
            trust_remote_code=True,
        )
        logger.info("Model loaded successfully.")

    yield

    logger.info("Shutting down.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CodePilot API",
    description="Automotive Embedded Code Assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "CodePilot API",
        "version": "1.0.0",
        "model_loaded": llm_engine is not None,
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy" if llm_engine is not None else "unhealthy",
        "model_loaded": llm_engine is not None,
    }


@app.post("/complete", response_model=CompletionResponse)
async def complete_code(request: CompletionRequest):
    if llm_engine is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        formatted_prompt = create_completion_prompt(request.prompt)

        sampling_params = SamplingParams(
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k,
            max_tokens=request.max_tokens,
            stop=request.stop or ["###", "\n\n\n"],
        )

        outputs = llm_engine.generate([formatted_prompt], sampling_params)
        generated_text = outputs[0].outputs[0].text

        return CompletionResponse(
            completion=generated_text.strip(),
            tokens_generated=len(outputs[0].outputs[0].token_ids),
            finish_reason=outputs[0].outputs[0].finish_reason,
        )
    except Exception as exc:
        logger.error("Error in completion: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/explain")
async def explain_code(request: ExplanationRequest):
    if llm_engine is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        formatted_prompt = create_explanation_prompt(request.code, request.language)

        sampling_params = SamplingParams(
            temperature=0.3, top_p=0.9, max_tokens=500, stop=["###"]
        )

        outputs = llm_engine.generate([formatted_prompt], sampling_params)
        return {"explanation": outputs[0].outputs[0].text.strip()}
    except Exception as exc:
        logger.error("Error in explanation: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/detect-bugs")
async def detect_bugs(request: BugDetectionRequest):
    if llm_engine is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        formatted_prompt = create_bug_detection_prompt(
            request.code, request.check_iso26262
        )

        sampling_params = SamplingParams(
            temperature=0.1, top_p=0.95, max_tokens=800, stop=["###"]
        )

        outputs = llm_engine.generate([formatted_prompt], sampling_params)
        return {"analysis": outputs[0].outputs[0].text.strip()}
    except Exception as exc:
        logger.error("Error in bug detection: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/generate-tests")
async def generate_tests(request: TestGenerationRequest):
    if llm_engine is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        formatted_prompt = create_test_generation_prompt(
            request.function_code, request.test_framework
        )

        sampling_params = SamplingParams(
            temperature=0.4, top_p=0.95, max_tokens=1000, stop=["###"]
        )

        outputs = llm_engine.generate([formatted_prompt], sampling_params)
        return {"tests": outputs[0].outputs[0].text.strip()}
    except Exception as exc:
        logger.error("Error in test generation: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        log_level="info",
    )
