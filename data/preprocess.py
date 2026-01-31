"""
Data Preprocessing for CodePilot
Clean and format automotive code samples for training
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
import tree_sitter
from datasets import Dataset, DatasetDict
from tqdm import tqdm
import hashlib


@dataclass
class CodeSample:
    """Data class for code samples"""
    code: str
    instruction: str
    language: str
    source: str
    tags: List[str]


class AutomotiveCodePreprocessor:
    """Preprocess automotive code for training"""
    
    def __init__(self, raw_data_dir: str, output_dir: str):
        self.raw_data_dir = Path(raw_data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Automotive-specific keywords for filtering
        self.automotive_keywords = [
            'CAN', 'LIN', 'FlexRay', 'AUTOSAR', 'MISRA',
            'ISO26262', 'ASIL', 'ECU', 'UDS', 'OBD',
            'DiagnosticMonitor', 'Rte_', 'Com_', 'CanIf_',
            'PduR_', 'DEM_', 'FIM_', 'NvM_', 'E2E_',
        ]
        
        # File deduplication
        self.seen_hashes = set()
    
    def is_automotive_code(self, code: str) -> bool:
        """Check if code contains automotive-specific patterns"""
        return any(keyword.lower() in code.lower() for keyword in self.automotive_keywords)
    
    def extract_function(self, code: str) -> Dict[str, str]:
        """Extract function signature and body"""
        # Simple regex-based extraction (tree-sitter would be better)
        function_pattern = r'(\w+\s+\w+\s*\([^)]*\)\s*\{[^}]*\})'
        matches = re.findall(function_pattern, code, re.DOTALL)
        
        if matches:
            return {
                'code': matches[0],
                'has_function': True
            }
        return {'code': code, 'has_function': False}
    
    def generate_instruction(self, code: str, source: str) -> str:
        """Generate instruction based on code content"""
        code_lower = code.lower()
        
        # Detect code type and generate appropriate instruction
        if 'can' in code_lower and 'transmit' in code_lower:
            return "Implement a CAN message transmission function for automotive ECU"
        elif 'can' in code_lower and 'receive' in code_lower:
            return "Implement a CAN message reception handler for automotive ECU"
        elif 'rte_' in code_lower:
            return "Implement an AUTOSAR RTE callback function"
        elif 'diagnostic' in code_lower or 'uds' in code_lower:
            return "Implement a UDS diagnostic service handler"
        elif 'null' in code_lower and 'check' in code_lower:
            return "Implement safe pointer handling with null checks (ISO 26262)"
        elif 'memcpy' in code_lower or 'buffer' in code_lower:
            return "Implement safe buffer operations with bounds checking"
        else:
            return f"Complete the following automotive embedded C/C++ code from {source}"
    
    def clean_code(self, code: str) -> str:
        """Clean and normalize code"""
        # Remove excessive whitespace
        code = re.sub(r'\n\s*\n\s*\n+', '\n\n', code)
        
        # Remove comments (keep important ones)
        # This is simplified - you'd want more sophisticated comment handling
        code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        
        # Normalize indentation
        lines = code.split('\n')
        cleaned_lines = [line.rstrip() for line in lines]
        code = '\n'.join(cleaned_lines)
        
        return code.strip()
    
    def deduplicate(self, code: str) -> bool:
        """Check if code is duplicate based on hash"""
        code_hash = hashlib.md5(code.encode()).hexdigest()
        if code_hash in self.seen_hashes:
            return True
        self.seen_hashes.add(code_hash)
        return False
    
    def process_file(self, file_path: Path) -> List[CodeSample]:
        """Process a single source file"""
        samples = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Only process if contains automotive code
            if not self.is_automotive_code(content):
                return samples
            
            # Clean code
            cleaned_code = self.clean_code(content)
            
            # Skip if duplicate
            if self.deduplicate(cleaned_code):
                return samples
            
            # Extract functions or use whole file
            if len(cleaned_code) < 5000:  # Reasonable size
                instruction = self.generate_instruction(cleaned_code, file_path.stem)
                
                sample = CodeSample(
                    code=cleaned_code,
                    instruction=instruction,
                    language='c' if file_path.suffix == '.c' else 'cpp',
                    source=str(file_path),
                    tags=self._extract_tags(cleaned_code)
                )
                samples.append(sample)
        
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
        
        return samples
    
    def _extract_tags(self, code: str) -> List[str]:
        """Extract automotive-specific tags from code"""
        tags = []
        code_lower = code.lower()
        
        tag_mapping = {
            'can': 'CAN',
            'lin': 'LIN',
            'flexray': 'FlexRay',
            'autosar': 'AUTOSAR',
            'uds': 'UDS',
            'obd': 'OBD',
            'diagnostic': 'Diagnostics',
            'iso26262': 'ISO26262',
            'asil': 'Safety',
        }
        
        for keyword, tag in tag_mapping.items():
            if keyword in code_lower:
                tags.append(tag)
        
        return list(set(tags))
    
    def process_directory(self, source_dir: str) -> List[CodeSample]:
        """Process all files in directory"""
        all_samples = []
        source_path = Path(source_dir)
        
        # Find all C/C++ files
        c_files = list(source_path.rglob('*.c'))
        cpp_files = list(source_path.rglob('*.cpp'))
        h_files = list(source_path.rglob('*.h'))
        hpp_files = list(source_path.rglob('*.hpp'))
        
        all_files = c_files + cpp_files + h_files + hpp_files
        
        print(f"Processing {len(all_files)} files from {source_dir}...")
        
        for file_path in tqdm(all_files):
            samples = self.process_file(file_path)
            all_samples.extend(samples)
        
        return all_samples
    
    def create_dataset(self, samples: List[CodeSample]) -> DatasetDict:
        """Create HuggingFace dataset from samples"""
        # Convert to dictionary format
        data = {
            'instruction': [s.instruction for s in samples],
            'code': [s.code for s in samples],
            'language': [s.language for s in samples],
            'source': [s.source for s in samples],
            'tags': [s.tags for s in samples],
        }
        
        # Create dataset
        dataset = Dataset.from_dict(data)
        
        # Split into train/validation (90/10)
        split_dataset = dataset.train_test_split(test_size=0.1, seed=42)
        
        return DatasetDict({
            'train': split_dataset['train'],
            'validation': split_dataset['test']
        })
    
    def save_dataset(self, dataset: DatasetDict):
        """Save dataset to disk"""
        dataset.save_to_disk(str(self.output_dir))
        print(f"Dataset saved to {self.output_dir}")
        
        # Also save statistics
        stats = {
            'total_samples': len(dataset['train']) + len(dataset['validation']),
            'train_samples': len(dataset['train']),
            'validation_samples': len(dataset['validation']),
            'languages': {},
            'tags': {}
        }
        
        # Count languages
        for lang in dataset['train']['language']:
            stats['languages'][lang] = stats['languages'].get(lang, 0) + 1
        
        # Count tags
        for tag_list in dataset['train']['tags']:
            for tag in tag_list:
                stats['tags'][tag] = stats['tags'].get(tag, 0) + 1
        
        with open(self.output_dir / 'statistics.json', 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"Statistics saved to {self.output_dir / 'statistics.json'}")
        print(f"\nDataset Statistics:")
        print(f"Total samples: {stats['total_samples']}")
        print(f"Train samples: {stats['train_samples']}")
        print(f"Validation samples: {stats['validation_samples']}")
        print(f"Languages: {stats['languages']}")
        print(f"Top tags: {dict(sorted(stats['tags'].items(), key=lambda x: x[1], reverse=True)[:10])}")


def main():
    """Main preprocessing pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Preprocess automotive code data")
    parser.add_argument("--input", type=str, required=True, help="Input directory with raw data")
    parser.add_argument("--output", type=str, default="../data/processed", help="Output directory")
    args = parser.parse_args()
    
    # Initialize preprocessor
    preprocessor = AutomotiveCodePreprocessor(args.input, args.output)
    
    # Process all code
    print("Starting preprocessing...")
    samples = preprocessor.process_directory(args.input)
    
    print(f"\nProcessed {len(samples)} code samples")
    
    if len(samples) == 0:
        print("No automotive code samples found!")
        return
    
    # Create and save dataset
    print("\nCreating dataset...")
    dataset = preprocessor.create_dataset(samples)
    preprocessor.save_dataset(dataset)
    
    print("\nPreprocessing complete!")


if __name__ == "__main__":
    main()
