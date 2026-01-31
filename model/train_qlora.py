"""
CodePilot QLoRA Fine-Tuning Script
Fine-tune CodeLlama-13B on automotive embedded C/C++ code
"""

import os
import torch
from dataclasses import dataclass, field
from typing import Optional
import transformers
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    HfArgumentParser,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset, load_from_disk
import wandb


@dataclass
class ModelArguments:
    """Arguments for model configuration"""
    model_name_or_path: str = field(
        default="codellama/CodeLlama-13b-Instruct-hf",
        metadata={"help": "Path to pretrained model or model identifier from huggingface.co/models"}
    )
    use_4bit: bool = field(
        default=True,
        metadata={"help": "Use 4-bit quantization"}
    )
    bnb_4bit_compute_dtype: str = field(
        default="float16",
        metadata={"help": "Compute dtype for 4-bit base models"}
    )
    bnb_4bit_quant_type: str = field(
        default="nf4",
        metadata={"help": "Quantization type (fp4 or nf4)"}
    )
    use_nested_quant: bool = field(
        default=False,
        metadata={"help": "Use nested quantization for 4-bit base models"}
    )


@dataclass
class DataArguments:
    """Arguments for data loading"""
    dataset_path: str = field(
        default="../data/processed",
        metadata={"help": "Path to preprocessed dataset"}
    )
    max_seq_length: int = field(
        default=2048,
        metadata={"help": "Maximum sequence length"}
    )


@dataclass
class LoraArguments:
    """Arguments for LoRA configuration"""
    lora_r: int = field(
        default=16,
        metadata={"help": "LoRA rank"}
    )
    lora_alpha: int = field(
        default=32,
        metadata={"help": "LoRA alpha"}
    )
    lora_dropout: float = field(
        default=0.05,
        metadata={"help": "LoRA dropout"}
    )
    target_modules: Optional[str] = field(
        default="q_proj,v_proj,k_proj,o_proj,gate_proj,up_proj,down_proj",
        metadata={"help": "Comma-separated list of target modules"}
    )


def create_bnb_config(args: ModelArguments):
    """Create BitsAndBytes configuration for quantization"""
    compute_dtype = getattr(torch, args.bnb_4bit_compute_dtype)
    
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=args.use_4bit,
        bnb_4bit_quant_type=args.bnb_4bit_quant_type,
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=args.use_nested_quant,
    )
    return bnb_config


def create_peft_config(lora_args: LoraArguments):
    """Create PEFT (LoRA) configuration"""
    target_modules = lora_args.target_modules.split(",")
    
    peft_config = LoraConfig(
        r=lora_args.lora_r,
        lora_alpha=lora_args.lora_alpha,
        lora_dropout=lora_args.lora_dropout,
        target_modules=target_modules,
        bias="none",
        task_type="CAUSAL_LM",
    )
    return peft_config


def load_model_and_tokenizer(model_args: ModelArguments):
    """Load model and tokenizer with quantization"""
    bnb_config = create_bnb_config(model_args)
    
    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        model_args.model_name_or_path,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    
    # Disable cache for training
    model.config.use_cache = False
    model.config.pretraining_tp = 1
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_args.model_name_or_path,
        trust_remote_code=True,
    )
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    
    return model, tokenizer


def prepare_dataset(data_args: DataArguments, tokenizer):
    """Load and prepare the automotive dataset"""
    # Load from disk or HuggingFace
    if os.path.exists(data_args.dataset_path):
        dataset = load_from_disk(data_args.dataset_path)
    else:
        dataset = load_dataset(data_args.dataset_path)
    
    # Tokenization function
    def tokenize_function(examples):
        # Format: instruction + code
        texts = []
        for instruction, code in zip(examples["instruction"], examples["code"]):
            text = f"### Instruction:\n{instruction}\n\n### Code:\n{code}"
            texts.append(text)
        
        return tokenizer(
            texts,
            truncation=True,
            max_length=data_args.max_seq_length,
            padding="max_length",
        )
    
    # Tokenize dataset
    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=dataset["train"].column_names,
        desc="Tokenizing dataset",
    )
    
    return tokenized_dataset


def main():
    # Parse arguments
    parser = HfArgumentParser((ModelArguments, DataArguments, LoraArguments, TrainingArguments))
    model_args, data_args, lora_args, training_args = parser.parse_args_into_dataclasses()
    
    # Initialize wandb
    wandb.init(
        project="codepilot-automotive",
        name=training_args.run_name or "qlora-codellama-13b",
        config={
            "model": model_args.model_name_or_path,
            "lora_r": lora_args.lora_r,
            "lora_alpha": lora_args.lora_alpha,
            "max_seq_length": data_args.max_seq_length,
        }
    )
    
    # Load model and tokenizer
    print("Loading model and tokenizer...")
    model, tokenizer = load_model_and_tokenizer(model_args)
    
    # Prepare model for k-bit training
    model = prepare_model_for_kbit_training(model)
    
    # Create and apply LoRA configuration
    print("Applying LoRA configuration...")
    peft_config = create_peft_config(lora_args)
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    
    # Prepare dataset
    print("Loading and preparing dataset...")
    tokenized_dataset = prepare_dataset(data_args, tokenizer)
    
    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,  # Causal LM, not masked LM
    )
    
    # Training
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset.get("validation"),
        data_collator=data_collator,
    )
    
    print("Starting training...")
    trainer.train()
    
    # Save final model
    print("Saving model...")
    trainer.save_model(training_args.output_dir)
    tokenizer.save_pretrained(training_args.output_dir)
    
    print("Training complete!")
    wandb.finish()


if __name__ == "__main__":
    main()
