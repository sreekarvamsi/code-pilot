"""
HumanEval-Automotive Benchmark
Custom evaluation benchmark for automotive embedded code
"""

import json
import subprocess
import tempfile
from typing import List, Dict
from dataclasses import dataclass
import re
from pathlib import Path


@dataclass
class TestCase:
    """Single test case"""
    task_id: str
    prompt: str
    canonical_solution: str
    test_cases: List[str]
    category: str  # CAN, AUTOSAR, Diagnostics, Safety, etc.
    difficulty: str  # easy, medium, hard


# Example automotive test cases
AUTOMOTIVE_TEST_CASES = [
    TestCase(
        task_id="AUTO/1",
        prompt="""// Implement a function to parse a CAN message
// Extract signal value from CAN data based on start bit and length
uint32_t extract_can_signal(uint8_t* data, uint8_t start_bit, uint8_t length)
{""",
        canonical_solution="""    uint32_t value = 0;
    uint8_t start_byte = start_bit / 8;
    uint8_t start_bit_in_byte = start_bit % 8;
    
    // Extract bits across bytes
    for (uint8_t i = 0; i < length; i++) {
        uint8_t bit_index = start_bit + i;
        uint8_t byte_index = bit_index / 8;
        uint8_t bit_in_byte = bit_index % 8;
        
        if ((data[byte_index] >> bit_in_byte) & 0x01) {
            value |= (1U << i);
        }
    }
    
    return value;
}""",
        test_cases=[
            "assert(extract_can_signal((uint8_t[]){0xFF, 0x00}, 0, 8) == 0xFF);",
            "assert(extract_can_signal((uint8_t[]){0x0F, 0xF0}, 4, 8) == 0xFF);",
            "assert(extract_can_signal((uint8_t[]){0xAA, 0x55}, 0, 16) == 0x55AA);"
        ],
        category="CAN",
        difficulty="medium"
    ),
    
    TestCase(
        task_id="AUTO/2",
        prompt="""// Implement safe memory copy with bounds checking (ISO 26262)
// Return 0 on success, -1 on error
int safe_memcpy(void* dest, const void* src, size_t dest_size, size_t n)
{""",
        canonical_solution="""    // Null pointer checks
    if (dest == NULL || src == NULL) {
        return -1;
    }
    
    // Bounds check
    if (n > dest_size) {
        return -1;
    }
    
    // Overlap check
    if (((uintptr_t)dest < (uintptr_t)src + n) && 
        ((uintptr_t)src < (uintptr_t)dest + n)) {
        return -1;
    }
    
    // Perform copy
    uint8_t* d = (uint8_t*)dest;
    const uint8_t* s = (const uint8_t*)src;
    for (size_t i = 0; i < n; i++) {
        d[i] = s[i];
    }
    
    return 0;
}""",
        test_cases=[
            "uint8_t src[10] = {1,2,3,4,5,6,7,8,9,10};",
            "uint8_t dest[10];",
            "assert(safe_memcpy(dest, src, 10, 10) == 0);",
            "assert(safe_memcpy(dest, src, 5, 10) == -1);  // overflow",
            "assert(safe_memcpy(NULL, src, 10, 5) == -1);  // null check"
        ],
        category="Safety",
        difficulty="medium"
    ),
    
    TestCase(
        task_id="AUTO/3",
        prompt="""// Implement UDS diagnostic service 0x22 (ReadDataByIdentifier)
// Returns 0 on success, error code otherwise
uint8_t uds_read_data_by_id(uint16_t data_id, uint8_t* response, uint16_t* length)
{""",
        canonical_solution="""    // Check for null pointers
    if (response == NULL || length == NULL) {
        return 0x13;  // NRC: incorrectRequestSequence
    }
    
    // Example data identifiers
    switch (data_id) {
        case 0xF190:  // VIN
            response[0] = 0x62;  // Positive response
            response[1] = 0xF1;
            response[2] = 0x90;
            // Mock VIN data
            memcpy(&response[3], "WAUZZZ4F0XN000001", 17);
            *length = 20;
            return 0x00;
            
        case 0xF186:  // Active diagnostic session
            response[0] = 0x62;
            response[1] = 0xF1;
            response[2] = 0x86;
            response[3] = 0x01;  // Default session
            *length = 4;
            return 0x00;
            
        default:
            return 0x31;  // NRC: requestOutOfRange
    }
}""",
        test_cases=[
            "uint8_t response[256];",
            "uint16_t length;",
            "assert(uds_read_data_by_id(0xF190, response, &length) == 0x00);",
            "assert(length == 20);",
            "assert(response[0] == 0x62);"
        ],
        category="Diagnostics",
        difficulty="hard"
    ),
    
    TestCase(
        task_id="AUTO/4",
        prompt="""// Implement AUTOSAR RTE write operation with error handling
// Write signal to RTE buffer
Std_ReturnType Rte_Write_Signal_Speed(uint16_t speed_value)
{""",
        canonical_solution="""    Std_ReturnType ret = E_OK;
    
    // Validate input range (0-300 km/h)
    if (speed_value > 300) {
        return E_NOT_OK;
    }
    
    // Critical section for thread safety
    SchM_Enter_RTE_EXCLUSIVE_AREA_0();
    
    // Write to shared buffer
    Rte_Buffer.Speed = speed_value;
    Rte_Buffer.SpeedValid = TRUE;
    
    // Update timestamp
    Rte_Buffer.SpeedTimestamp = GetCurrentTimestamp();
    
    SchM_Exit_RTE_EXCLUSIVE_AREA_0();
    
    return ret;
}""",
        test_cases=[
            "assert(Rte_Write_Signal_Speed(100) == E_OK);",
            "assert(Rte_Write_Signal_Speed(350) == E_NOT_OK);",
            "assert(Rte_Buffer.Speed == 100);",
            "assert(Rte_Buffer.SpeedValid == TRUE);"
        ],
        category="AUTOSAR",
        difficulty="medium"
    ),
]


class AutomotiveEvaluator:
    """Evaluate model on automotive coding tasks"""
    
    def __init__(self, model_inference_fn):
        """
        Args:
            model_inference_fn: Function that takes prompt and returns generated code
        """
        self.model_inference_fn = model_inference_fn
        self.results = []
    
    def compile_and_test(self, code: str, test_cases: List[str]) -> bool:
        """Compile and run test cases"""
        # Create temporary C file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            # Add necessary headers
            test_program = """
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>

// Mock definitions for automotive types
typedef uint8_t Std_ReturnType;
#define E_OK 0x00
#define E_NOT_OK 0x01
#define TRUE 1
#define FALSE 0

// Mock AUTOSAR functions
void SchM_Enter_RTE_EXCLUSIVE_AREA_0(void) {}
void SchM_Exit_RTE_EXCLUSIVE_AREA_0(void) {}
uint32_t GetCurrentTimestamp(void) { return 12345; }

// Mock RTE buffer
struct {
    uint16_t Speed;
    uint8_t SpeedValid;
    uint32_t SpeedTimestamp;
} Rte_Buffer;

"""
            test_program += code + "\n\n"
            test_program += "int main() {\n"
            for test in test_cases:
                test_program += f"    {test}\n"
            test_program += '    printf("All tests passed!\\n");\n'
            test_program += "    return 0;\n"
            test_program += "}\n"
            
            f.write(test_program)
            c_file = f.name
        
        try:
            # Compile
            exe_file = c_file.replace('.c', '')
            compile_result = subprocess.run(
                ['gcc', c_file, '-o', exe_file, '-std=c99'],
                capture_output=True,
                timeout=10
            )
            
            if compile_result.returncode != 0:
                return False
            
            # Run tests
            run_result = subprocess.run(
                [exe_file],
                capture_output=True,
                timeout=5
            )
            
            return run_result.returncode == 0
            
        except Exception as e:
            print(f"Error in compilation/testing: {e}")
            return False
        finally:
            # Cleanup
            Path(c_file).unlink(missing_ok=True)
            Path(exe_file).unlink(missing_ok=True)
    
    def evaluate_task(self, task: TestCase) -> Dict:
        """Evaluate model on single task"""
        print(f"Evaluating {task.task_id} ({task.category})...")
        
        # Generate code
        generated = self.model_inference_fn(task.prompt)
        
        # Extract function body
        full_code = task.prompt + "\n" + generated
        
        # Test
        passed = self.compile_and_test(full_code, task.test_cases)
        
        result = {
            'task_id': task.task_id,
            'category': task.category,
            'difficulty': task.difficulty,
            'passed': passed,
            'generated_code': generated
        }
        
        self.results.append(result)
        return result
    
    def evaluate_all(self, test_cases: List[TestCase]) -> Dict:
        """Evaluate on all test cases"""
        for task in test_cases:
            self.evaluate_task(task)
        
        # Compute metrics
        total = len(self.results)
        passed = sum(1 for r in self.results if r['passed'])
        pass_at_1 = (passed / total) * 100 if total > 0 else 0
        
        # Category breakdown
        category_stats = {}
        for result in self.results:
            cat = result['category']
            if cat not in category_stats:
                category_stats[cat] = {'total': 0, 'passed': 0}
            category_stats[cat]['total'] += 1
            if result['passed']:
                category_stats[cat]['passed'] += 1
        
        return {
            'pass@1': pass_at_1,
            'total_tasks': total,
            'passed_tasks': passed,
            'category_stats': category_stats,
            'detailed_results': self.results
        }
    
    def save_results(self, output_file: str):
        """Save evaluation results"""
        metrics = self.evaluate_all(AUTOMOTIVE_TEST_CASES)
        
        with open(output_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"\n{'='*50}")
        print(f"Evaluation Results")
        print(f"{'='*50}")
        print(f"Pass@1: {metrics['pass@1']:.2f}%")
        print(f"Tasks Passed: {metrics['passed_tasks']}/{metrics['total_tasks']}")
        print(f"\nCategory Breakdown:")
        for cat, stats in metrics['category_stats'].items():
            pass_rate = (stats['passed'] / stats['total']) * 100
            print(f"  {cat}: {stats['passed']}/{stats['total']} ({pass_rate:.1f}%)")
        print(f"\nResults saved to {output_file}")


def example_model_inference(prompt: str) -> str:
    """
    Example inference function - replace with actual model call
    This is a placeholder that returns the canonical solution
    """
    # In real usage, call your model here:
    # return model.generate(prompt)
    
    # For demonstration, return a mock response
    return "    return 0;\n}"


if __name__ == "__main__":
    # Example usage
    evaluator = AutomotiveEvaluator(example_model_inference)
    evaluator.save_results("evaluation_results.json")
