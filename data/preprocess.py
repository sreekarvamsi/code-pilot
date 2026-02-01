"""
Data Preprocessing for CodePilot
Clean and format automotive code samples for training
"""

import json
import re
import hashlib
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
from datasets import Dataset, DatasetDict
from tqdm import tqdm


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

        self.automotive_keywords = [
            "CAN",
            "LIN",
            "FlexRay",
            "AUTOSAR",
            "MISRA",
            "ISO26262",
            "ASIL",
            "ECU",
            "UDS",
            "OBD",
            "DiagnosticMonitor",
            "Rte_",
            "Com_",
            "CanIf_",
            "PduR_",
            "DEM_",
            "FIM_",
            "NvM_",
            "E2E_",
        ]

        self.seen_hashes: set = set()

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def is_automotive_code(self, code: str) -> bool:
        """Check if code contains automotive-specific patterns"""
        return any(kw.lower() in code.lower() for kw in self.automotive_keywords)

    # ------------------------------------------------------------------
    # Instruction generation
    # ------------------------------------------------------------------

    def generate_instruction(self, code: str, source: str) -> str:
        """Generate instruction based on code content"""
        code_lower = code.lower()

        if "can" in code_lower and "transmit" in code_lower:
            return "Implement a CAN message transmission function for automotive ECU"
        if "can" in code_lower and "receive" in code_lower:
            return "Implement a CAN message reception handler for automotive ECU"
        if "rte_" in code_lower:
            return "Implement an AUTOSAR RTE callback function"
        if "diagnostic" in code_lower or "uds" in code_lower:
            return "Implement a UDS diagnostic service handler"
        if "null" in code_lower and "check" in code_lower:
            return "Implement safe pointer handling with null checks (ISO 26262)"
        if "memcpy" in code_lower or "buffer" in code_lower:
            return "Implement safe buffer operations with bounds checking"

        return f"Complete the following automotive embedded C/C++ code from {source}"

    # ------------------------------------------------------------------
    # Cleaning
    # ------------------------------------------------------------------

    def clean_code(self, code: str) -> str:
        """Clean and normalize code"""
        # Collapse three+ blank lines into two
        code = re.sub(r"\n\s*\n\s*\n+", "\n\n", code)
        # Strip trailing whitespace per line
        code = "\n".join(line.rstrip() for line in code.split("\n"))
        return code.strip()

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def deduplicate(self, code: str) -> bool:
        """Return True if we have already seen this code (by MD5 hash)"""
        code_hash = hashlib.md5(code.encode()).hexdigest()
        if code_hash in self.seen_hashes:
            return True
        self.seen_hashes.add(code_hash)
        return False

    # ------------------------------------------------------------------
    # Tag extraction
    # ------------------------------------------------------------------

    def _extract_tags(self, code: str) -> List[str]:
        """Extract automotive-specific tags from code"""
        tag_mapping: Dict[str, str] = {
            "can": "CAN",
            "lin": "LIN",
            "flexray": "FlexRay",
            "autosar": "AUTOSAR",
            "uds": "UDS",
            "obd": "OBD",
            "diagnostic": "Diagnostics",
            "iso26262": "ISO26262",
            "asil": "Safety",
        }
        code_lower = code.lower()
        return list({tag for kw, tag in tag_mapping.items() if kw in code_lower})

    # ------------------------------------------------------------------
    # File / directory processing
    # ------------------------------------------------------------------

    def process_file(self, file_path: Path) -> List[CodeSample]:
        """Process a single source file"""
        samples: List[CodeSample] = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            print(f"Error reading {file_path}: {exc}")
            return samples

        if not self.is_automotive_code(content):
            return samples

        cleaned_code = self.clean_code(content)

        if self.deduplicate(cleaned_code):
            return samples

        if len(cleaned_code) < 5000:
            instruction = self.generate_instruction(cleaned_code, file_path.stem)
            samples.append(
                CodeSample(
                    code=cleaned_code,
                    instruction=instruction,
                    language="c" if file_path.suffix == ".c" else "cpp",
                    source=str(file_path),
                    tags=self._extract_tags(cleaned_code),
                )
            )

        return samples

    def process_directory(self, source_dir: str) -> List[CodeSample]:
        """Process all C/C++ files in directory"""
        all_samples: List[CodeSample] = []
        source_path = Path(source_dir)

        extensions = ("*.c", "*.cpp", "*.h", "*.hpp")
        all_files = [f for ext in extensions for f in source_path.rglob(ext)]

        print(f"Processing {len(all_files)} files from {source_dir}...")

        for file_path in tqdm(all_files):
            all_samples.extend(self.process_file(file_path))

        return all_samples

    # ------------------------------------------------------------------
    # Dataset creation & saving
    # ------------------------------------------------------------------

    def create_dataset(self, samples: List[CodeSample]) -> DatasetDict:
        """Create HuggingFace dataset from samples"""
        data = {
            "instruction": [s.instruction for s in samples],
            "code": [s.code for s in samples],
            "language": [s.language for s in samples],
            "source": [s.source for s in samples],
            "tags": [s.tags for s in samples],
        }

        dataset = Dataset.from_dict(data)
        split = dataset.train_test_split(test_size=0.1, seed=42)

        return DatasetDict({"train": split["train"], "validation": split["test"]})

    def save_dataset(self, dataset: DatasetDict):
        """Save dataset to disk and print statistics"""
        dataset.save_to_disk(str(self.output_dir))
        print(f"Dataset saved to {self.output_dir}")

        stats: Dict = {
            "total_samples": len(dataset["train"]) + len(dataset["validation"]),
            "train_samples": len(dataset["train"]),
            "validation_samples": len(dataset["validation"]),
            "languages": {},
            "tags": {},
        }

        for lang in dataset["train"]["language"]:
            stats["languages"][lang] = stats["languages"].get(lang, 0) + 1

        for tag_list in dataset["train"]["tags"]:
            for tag in tag_list:
                stats["tags"][tag] = stats["tags"].get(tag, 0) + 1

        with open(self.output_dir / "statistics.json", "w") as fh:
            json.dump(stats, fh, indent=2)

        print(f"Statistics saved to {self.output_dir / 'statistics.json'}")
        print(f"\nDataset Statistics:")
        print(f"  Total samples      : {stats['total_samples']}")
        print(f"  Train samples      : {stats['train_samples']}")
        print(f"  Validation samples : {stats['validation_samples']}")
        print(f"  Languages          : {stats['languages']}")

        top_tags = dict(
            sorted(stats["tags"].items(), key=lambda x: x[1], reverse=True)[:10]
        )
        print(f"  Top tags           : {top_tags}")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Preprocess automotive code data")
    parser.add_argument(
        "--input", type=str, required=True, help="Input directory with raw data"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="../data/processed",
        help="Output directory",
    )
    args = parser.parse_args()

    preprocessor = AutomotiveCodePreprocessor(args.input, args.output)

    print("Starting preprocessing...")
    samples = preprocessor.process_directory(args.input)
    print(f"\nProcessed {len(samples)} code samples")

    if len(samples) == 0:
        print("No automotive code samples found!")
        return

    print("\nCreating dataset...")
    dataset = preprocessor.create_dataset(samples)
    preprocessor.save_dataset(dataset)

    print("\nPreprocessing complete!")


if __name__ == "__main__":
    main()
