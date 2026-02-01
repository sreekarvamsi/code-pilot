"""
HumanEval-Automotive Benchmark
Custom evaluation benchmark for automotive embedded code
"""

import json
import subprocess
import tempfile
from typing import List, Dict, Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestCase:
    """Single benchmark task"""

    task_id: str
    prompt: str
    canonical_solution: str
    test_cases: List[str]
    category: str  # CAN | AUTOSAR | Diagnostics | Safety
    difficulty: str  # easy | medium | hard


# ---------------------------------------------------------------------------
# Benchmark tasks
# ---------------------------------------------------------------------------

AUTOMOTIVE_TEST_CASES: List[TestCase] = [
    TestCase(
        task_id="AUTO/1",
        prompt=(
            "// Extract signal value from CAN data based on start bit and length\n"
            "uint32_t extract_can_signal(uint8_t* data, uint8_t start_bit, uint8_t length)\n"
            "{"
        ),
        canonical_solution=(
            "    uint32_t value = 0;\n"
            "    for (uint8_t i = 0; i < length; i++) {\n"
            "        uint8_t bit_index = start_bit + i;\n"
            "        uint8_t byte_index = bit_index / 8;\n"
            "        uint8_t bit_in_byte = bit_index % 8;\n"
            "        if ((data[byte_index] >> bit_in_byte) & 0x01) {\n"
            "            value |= (1U << i);\n"
            "        }\n"
            "    }\n"
            "    return value;\n"
            "}"
        ),
        test_cases=[
            "uint8_t d1[] = {0xFF, 0x00};\n"
            "    assert(extract_can_signal(d1, 0, 8) == 0xFF);",
            "uint8_t d2[] = {0x0F, 0xF0};\n"
            "    assert(extract_can_signal(d2, 4, 8) == 0xFF);",
            "uint8_t d3[] = {0xAA, 0x55};\n"
            "    assert(extract_can_signal(d3, 0, 16) == 0x55AA);",
        ],
        category="CAN",
        difficulty="medium",
    ),
    TestCase(
        task_id="AUTO/2",
        prompt=(
            "// Safe memory copy with bounds checking (ISO 26262)\n"
            "// Return 0 on success, -1 on error\n"
            "int safe_memcpy(void* dest, const void* src, size_t dest_size, size_t n)\n"
            "{"
        ),
        canonical_solution=(
            "    if (dest == NULL || src == NULL) return -1;\n"
            "    if (n > dest_size) return -1;\n"
            "    uint8_t* d = (uint8_t*)dest;\n"
            "    const uint8_t* s = (const uint8_t*)src;\n"
            "    for (size_t i = 0; i < n; i++) d[i] = s[i];\n"
            "    return 0;\n"
            "}"
        ),
        test_cases=[
            "uint8_t src[10] = {1,2,3,4,5,6,7,8,9,10};\n"
            "    uint8_t dest[10];\n"
            "    assert(safe_memcpy(dest, src, 10, 10) == 0);",
            "uint8_t src2[10] = {0};\n"
            "    uint8_t dest2[5];\n"
            "    assert(safe_memcpy(dest2, src2, 5, 10) == -1);",
            "uint8_t src3[10] = {0};\n"
            "    uint8_t dest3[10];\n"
            "    assert(safe_memcpy(NULL, src3, 10, 5) == -1);",
        ],
        category="Safety",
        difficulty="medium",
    ),
    TestCase(
        task_id="AUTO/3",
        prompt=(
            "// UDS 0x22 ReadDataByIdentifier – VIN (0xF190)\n"
            "// Returns 0 on success, NRC otherwise\n"
            "uint8_t uds_read_vin(uint8_t* response, uint16_t* length)\n"
            "{"
        ),
        canonical_solution=(
            '    if (response == NULL || length == NULL) return 0x13;\n'
            "    response[0] = 0x62;\n"
            "    response[1] = 0xF1;\n"
            "    response[2] = 0x90;\n"
            '    memcpy(&response[3], "WAUZZZ4F0XN000001", 17);\n'
            "    *length = 20;\n"
            "    return 0x00;\n"
            "}"
        ),
        test_cases=[
            "uint8_t resp[256];\n"
            "    uint16_t len;\n"
            "    assert(uds_read_vin(resp, &len) == 0x00);",
            "uint8_t resp2[256];\n"
            "    uint16_t len2;\n"
            "    uds_read_vin(resp2, &len2);\n"
            "    assert(len2 == 20);",
            "uint8_t resp3[256];\n"
            "    uint16_t len3;\n"
            "    uds_read_vin(resp3, &len3);\n"
            "    assert(resp3[0] == 0x62);",
            "assert(uds_read_vin(NULL, NULL) == 0x13);",
        ],
        category="Diagnostics",
        difficulty="hard",
    ),
    TestCase(
        task_id="AUTO/4",
        prompt=(
            "// AUTOSAR RTE write – vehicle speed (0-300 km/h)\n"
            "// Returns E_OK (0) on success, E_NOT_OK (1) on bad input\n"
            "typedef uint8_t Std_ReturnType;\n"
            "#define E_OK     0x00\n"
            "#define E_NOT_OK 0x01\n"
            "uint16_t g_speed = 0;\n"
            "Std_ReturnType Rte_Write_Signal_Speed(uint16_t speed_value)\n"
            "{"
        ),
        canonical_solution=(
            "    if (speed_value > 300) return E_NOT_OK;\n"
            "    g_speed = speed_value;\n"
            "    return E_OK;\n"
            "}"
        ),
        test_cases=[
            "assert(Rte_Write_Signal_Speed(100) == E_OK);",
            "assert(Rte_Write_Signal_Speed(350) == E_NOT_OK);",
            "Rte_Write_Signal_Speed(200);\n    assert(g_speed == 200);",
        ],
        category="AUTOSAR",
        difficulty="medium",
    ),
]


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


class AutomotiveEvaluator:
    """Evaluate a model on the automotive coding benchmark"""

    def __init__(self, model_inference_fn: Callable[[str], str]):
        self.model_inference_fn = model_inference_fn
        self.results: List[Dict] = []

    # ------------------------------------------------------------------
    # Compile & run
    # ------------------------------------------------------------------

    @staticmethod
    def _compile_and_test(code: str, test_cases: List[str]) -> bool:
        """Write a small C program, compile with gcc, and run assertions."""
        preamble = (
            '#include <stdio.h>\n'
            '#include <stdint.h>\n'
            '#include <string.h>\n'
            '#include <assert.h>\n'
            '#include <stddef.h>\n\n'
        )

        test_body = "\n    ".join(test_cases)
        program = (
            f"{preamble}{code}\n\n"
            f'int main(void) {{\n    {test_body}\n'
            f'    printf("All tests passed!\\n");\n'
            f"    return 0;\n}}\n"
        )

        c_file = Path(tempfile.mktemp(suffix=".c"))
        exe_file = c_file.with_suffix("")

        try:
            c_file.write_text(program)

            compile_result = subprocess.run(
                ["gcc", str(c_file), "-o", str(exe_file), "-std=c99", "-Wall"],
                capture_output=True,
                timeout=10,
            )
            if compile_result.returncode != 0:
                return False

            run_result = subprocess.run(
                [str(exe_file)], capture_output=True, timeout=5
            )
            return run_result.returncode == 0

        except Exception:
            return False
        finally:
            c_file.unlink(missing_ok=True)
            exe_file.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Single-task evaluation
    # ------------------------------------------------------------------

    def evaluate_task(self, task: TestCase) -> Dict:
        print(f"Evaluating {task.task_id} ({task.category})...")

        generated = self.model_inference_fn(task.prompt)
        full_code = task.prompt + "\n" + generated

        passed = self._compile_and_test(full_code, task.test_cases)

        result: Dict = {
            "task_id": task.task_id,
            "category": task.category,
            "difficulty": task.difficulty,
            "passed": passed,
            "generated_code": generated,
        }
        self.results.append(result)
        return result

    # ------------------------------------------------------------------
    # Full benchmark
    # ------------------------------------------------------------------

    def evaluate_all(self, test_cases: List[TestCase]) -> Dict:
        for task in test_cases:
            self.evaluate_task(task)

        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        pass_at_1 = (passed / total * 100) if total else 0.0

        category_stats: Dict[str, Dict[str, int]] = {}
        for result in self.results:
            cat = result["category"]
            category_stats.setdefault(cat, {"total": 0, "passed": 0})
            category_stats[cat]["total"] += 1
            if result["passed"]:
                category_stats[cat]["passed"] += 1

        return {
            "pass@1": pass_at_1,
            "total_tasks": total,
            "passed_tasks": passed,
            "category_stats": category_stats,
            "detailed_results": self.results,
        }

    def save_results(self, output_file: str):
        metrics = self.evaluate_all(AUTOMOTIVE_TEST_CASES)

        with open(output_file, "w") as fh:
            json.dump(metrics, fh, indent=2)

        print("\n" + "=" * 50)
        print("Evaluation Results")
        print("=" * 50)
        print(f"Pass@1            : {metrics['pass@1']:.2f}%")
        print(f"Tasks Passed      : {metrics['passed_tasks']}/{metrics['total_tasks']}")
        print("\nCategory Breakdown:")
        for cat, stats in metrics["category_stats"].items():
            rate = stats["passed"] / stats["total"] * 100
            print(f"  {cat}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")
        print(f"\nResults saved to {output_file}")


# ---------------------------------------------------------------------------
# Default inference stub
# ---------------------------------------------------------------------------


def _stub_inference(prompt: str) -> str:  # noqa: ARG001
    """
    Placeholder – replace with your real model call:
        return model.generate(prompt)
    """
    return "    return 0;\n}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    evaluator = AutomotiveEvaluator(_stub_inference)
    evaluator.save_results("evaluation_results.json")
