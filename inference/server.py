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
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model instance
llm_engine = None


class CompletionRequest(BaseModel):
    """Request model for code completion"""
    prompt: str = Field(..., description="Code prompt/prefix")
    max_tokens: int = Field(default=150, ge=1, le=1024, description="Maximum tokens to generate")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: float = Field(default=0.95, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    top_k: int = Field(default=50, ge=1, le=100, description="Top-k sampling parameter")
    stop: Optional[List[str]] = Field(default=None, description="Stop sequences")
    stream: bool = Field(default=False, description="Stream response")


class ExplanationRequest(BaseModel):
    """Request model for code explanation"""
    code: str = Field(..., description="Code to explain")
    language: str = Field(default="c", description="Programming language (c/cpp)")


class BugDetectionRequest(BaseModel):
    """Request model for bug detection"""
    code: str = Field(..., description="Code to analyze")
    check_iso26262: bool = Field(default=True, description="Check ISO 26262 violations")


class TestGenerationRequest(BaseModel):
    """Request model for unit test generation"""
    function_code: str = Field(..., description="Function code to test")
    test_framework: str = Field(default="unity", description="Test framework (unity/gtest)")


class CompletionResponse(BaseModel):
    """Response model for completions"""
    completion: str
    tokens_generated: int
    finish_reason: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for model loading"""
    global llm_engine
    
    # Load model on startup
    model_path = os.getenv("MODEL_PATH", "../model/codepilot-13b")
    logger.info(f"Loading model from {model_path}...")
    
    llm_engine = LLM(
        model=model_path,
        tensor_parallel_size=1,
        dtype="float16",
        max_model_len=4096,
        gpu_memory_utilization=0.9,
        trust_remote_code=True,
    )
    
    logger.info("Model loaded successfully!")
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="CodePilot API",
    description="Automotive Embedded Code Assistant",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_completion_prompt(prompt: str) -> str:
    """Format prompt for code completion"""
    return f"### Instruction:\nComplete the following automotive embedded C/C++ code:\n\n### Code:\n{prompt}"


def create_explanation_prompt(code: str, language: str) -> str:
    """Format prompt for code explanation"""
    return f"""### Instruction:
Explain the following {language.upper()} code in the context of automotive embedded systems. 
Include information about:
- What the code does
- Automotive protocols/standards used (AUTOSAR, CAN, etc.)
- Safety considerations (ISO 26262)
- Potential issues or improvements

### Code:
{code}

### Explanation:"""


def create_bug_detection_prompt(code: str, check_iso26262: bool) -> str:
    """Format prompt for bug detection"""
    iso_instruction = "Check for ISO 26262 safety violations including null pointer checks, uninitialized variables, and buffer overflows." if check_iso26262 else ""
    
    return f"""### Instruction:
Analyze the following automotive embedded code for potential bugs and issues.
{iso_instruction}

### Code:
{code}

### Analysis:"""


def create_test_generation_prompt(function_code: str, framework: str) -> str:
    """Format prompt for test generation"""
    return f"""### Instruction:
Generate comprehensive unit tests for the following function using {framework.upper()} test framework.
Include:
- Normal case tests
- Edge case tests
- Error condition tests
- Mock automotive interfaces (CAN, etc.) if needed

### Function:
{function_code}

### Tests:"""


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CodePilot API",
        "version": "1.0.0",
        "model_loaded": llm_engine is not None
    }


@app.post("/complete", response_model=CompletionResponse)
async def complete_code(request: CompletionRequest):
    """Generate code completion"""
    if llm_engine is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Format prompt
        formatted_prompt = create_completion_prompt(request.prompt)
        
        # Configure sampling
        sampling_params = SamplingParams(
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k,
            max_tokens=request.max_tokens,
            stop=request.stop or ["###", "\n\n\n"],
        )
        
        # Generate completion
        outputs = llm_engine.generate([formatted_prompt], sampling_params)
        generated_text = outputs[0].outputs[0].text
        
        return CompletionResponse(
            completion=generated_text.strip(),
            tokens_generated=len(outputs[0].outputs[0].token_ids),
            finish_reason=outputs[0].outputs[0].finish_reason,
        )
        
    except Exception as e:
        logger.error(f"Error in completion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/explain")
async def explain_code(request: ExplanationRequest):
    """Generate code explanation"""
    if llm_engine is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        formatted_prompt = create_explanation_prompt(request.code, request.language)
        
        sampling_params = SamplingParams(
            temperature=0.3,
            top_p=0.9,
            max_tokens=500,
            stop=["###"],
        )
        
        outputs = llm_engine.generate([formatted_prompt], sampling_params)
        explanation = outputs[0].outputs[0].text.strip()
        
        return {"explanation": explanation}
        
    except Exception as e:
        logger.error(f"Error in explanation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect-bugs")
async def detect_bugs(request: BugDetectionRequest):
    """Detect potential bugs in code"""
    if llm_engine is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        formatted_prompt = create_bug_detection_prompt(request.code, request.check_iso26262)
        
        sampling_params = SamplingParams(
            temperature=0.1,  # Low temperature for deterministic analysis
            top_p=0.95,
            max_tokens=800,
            stop=["###"],
        )
        
        outputs = llm_engine.generate([formatted_prompt], sampling_params)
        analysis = outputs[0].outputs[0].text.strip()
        
        return {"analysis": analysis}
        
    except Exception as e:
        logger.error(f"Error in bug detection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-tests")
async def generate_tests(request: TestGenerationRequest):
    """Generate unit tests for function"""
    if llm_engine is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        formatted_prompt = create_test_generation_prompt(
            request.function_code,
            request.test_framework
        )
        
        sampling_params = SamplingParams(
            temperature=0.4,
            top_p=0.95,
            max_tokens=1000,
            stop=["###"],
        )
        
        outputs = llm_engine.generate([formatted_prompt], sampling_params)
        tests = outputs[0].outputs[0].text.strip()
        
        return {"tests": tests}
        
    except Exception as e:
        logger.error(f"Error in test generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy" if llm_engine is not None else "unhealthy",
        "model_loaded": llm_engine is not None,
        "gpu_available": os.system("nvidia-smi > /dev/null 2>&1") == 0,
    }


if __name__ == "__main__":
    # Run server
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        log_level="info",
    )
