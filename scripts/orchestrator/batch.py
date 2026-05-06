"""
Batch Strategy Module

Provides different strategies for batching items before worker execution.
"""

import json
from abc import ABC, abstractmethod
from typing import Any


class BatchStrategy(ABC):
    """Abstract base class for batch creation strategies."""
    
    @abstractmethod
    def create_batches(self, items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        """Create batches from a list of items."""
        pass


class TokenBasedBatch(BatchStrategy):
    """
    Create batches based on estimated token count.
    
    This strategy ensures that each batch fits within the context window
    by estimating the token count of serialized items.
    """
    
    def __init__(
        self,
        max_tokens: int = 190_000,
        base_tokens: int = 5_000,
    ):
        self.max_tokens = max_tokens
        self.base_tokens = base_tokens
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text length."""
        return len(text) // 4
    
    def create_batches(self, items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        """Create batches that fit within token limits."""
        batches: list[list[dict[str, Any]]] = []
        current_batch: list[dict[str, Any]] = []
        current_tokens = self.base_tokens
        
        for item in items:
            item_json = json.dumps(item)
            item_tokens = self.estimate_tokens(item_json)
            
            # Check if adding this item would exceed the limit
            if current_batch and (current_tokens + item_tokens > self.max_tokens):
                batches.append(current_batch)
                current_batch = []
                current_tokens = self.base_tokens
            
            current_batch.append(item)
            current_tokens += item_tokens
        
        # Don't forget the last batch
        if current_batch:
            batches.append(current_batch)
        
        return batches


class CountBasedBatch(BatchStrategy):
    """
    Create batches based on item count.
    
    This strategy simply groups items into fixed-size batches.
    """
    
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
    
    def create_batches(self, items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        """Create batches of fixed size."""
        batches = []
        
        for i in range(0, len(items), self.max_size):
            batches.append(items[i:i + self.max_size])
        
        return batches


class ByteBasedBatch(BatchStrategy):
    """
    Create batches based on file size in bytes.
    
    This strategy is useful when items reference external files
    and we want to limit the total file size per batch.
    """
    
    def __init__(
        self,
        max_bytes: int = 160 * 1024,
        size_keys: list[str] | None = None,
    ):
        self.max_bytes = max_bytes
        self.size_keys = size_keys or ["source_file"]
    
    def create_batches(self, items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        """Create batches that fit within byte limits."""
        import os
        
        batches: list[list[dict[str, Any]]] = []
        current_batch: list[dict[str, Any]] = []
        current_bytes = 0
        seen_files: set[str] = set()
        
        for item in items:
            # Calculate size of files referenced by this item
            item_bytes = 0
            item_files: set[str] = set()
            
            for key in self.size_keys:
                file_path = item.get(key)
                if file_path and os.path.exists(file_path):
                    item_files.add(file_path)
                    if file_path not in seen_files:
                        item_bytes += os.path.getsize(file_path)
            
            # Check if adding this item would exceed the limit
            if current_batch and (current_bytes + item_bytes > self.max_bytes):
                batches.append(current_batch)
                current_batch = []
                current_bytes = 0
                seen_files.clear()
            
            current_batch.append(item)
            current_bytes += item_bytes
            seen_files.update(item_files)
        
        # Don't forget the last batch
        if current_batch:
            batches.append(current_batch)
        
        return batches


class HybridBatch(BatchStrategy):
    """
    Create batches using multiple strategies.
    
    This strategy applies multiple constraints (tokens, count, bytes)
    and uses the most restrictive result.
    """
    
    def __init__(
        self,
        max_tokens: int = 190_000,
        base_tokens: int = 5_000,
        max_count: int = 50,
        max_bytes: int | None = None,
    ):
        self.token_strategy = TokenBasedBatch(max_tokens, base_tokens)
        self.count_strategy = CountBasedBatch(max_count)
        self.byte_strategy = ByteBasedBatch(max_bytes) if max_bytes else None
    
    def create_batches(self, items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        """Create batches using the most restrictive strategy."""
        # Get batches from each strategy
        token_batches = self.token_strategy.create_batches(items)
        count_batches = self.count_strategy.create_batches(items)
        
        # Use the strategy that produces more (smaller) batches
        if len(token_batches) >= len(count_batches):
            result = token_batches
        else:
            result = count_batches
        
        # Apply byte-based splitting if configured
        if self.byte_strategy:
            final_batches = []
            for batch in result:
                sub_batches = self.byte_strategy.create_batches(batch)
                final_batches.extend(sub_batches)
            return final_batches
        
        return result
