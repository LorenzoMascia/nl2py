"""
NLP Interpreter for NL2Py

This module provides natural language interpretation capabilities to match
user text commands with appropriate module methods and generate executable Python code.

Uses TF-IDF vectorization and cosine similarity to find the best matching method
based on examples provided in get_methods_info().
"""

import re
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter


@dataclass
class MatchResult:
    """Result of matching a text command to a method."""
    module_name: str
    method_name: str
    similarity_score: float
    matched_example: str
    extracted_params: Dict[str, str]
    generated_code: str
    original_text: str


@dataclass
class MethodEntry:
    """Internal representation of a method with its examples."""
    module_name: str
    method_name: str
    description: str
    parameters: Dict[str, str]
    example_text: str
    example_code: str


class TFIDFVectorizer:
    """Simple TF-IDF vectorizer without external dependencies."""

    def __init__(self):
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.documents: List[List[str]] = []

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase words."""
        # Remove template markers and special characters
        text = re.sub(r'\{\{[^}]+\}\}', ' PARAM ', text)
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = text.split()
        # Remove very short tokens
        return [t for t in tokens if len(t) > 1]

    def fit(self, documents: List[str]) -> 'TFIDFVectorizer':
        """Fit the vectorizer on a list of documents."""
        self.documents = [self._tokenize(doc) for doc in documents]

        # Build vocabulary
        all_tokens = set()
        for doc_tokens in self.documents:
            all_tokens.update(doc_tokens)
        self.vocabulary = {token: idx for idx, token in enumerate(sorted(all_tokens))}

        # Calculate IDF
        num_docs = len(self.documents)
        doc_freq = Counter()
        for doc_tokens in self.documents:
            doc_freq.update(set(doc_tokens))

        self.idf = {
            token: math.log((num_docs + 1) / (freq + 1)) + 1
            for token, freq in doc_freq.items()
        }

        return self

    def transform(self, text: str) -> Dict[str, float]:
        """Transform text into TF-IDF vector."""
        tokens = self._tokenize(text)
        if not tokens:
            return {}

        # Calculate TF
        tf = Counter(tokens)
        max_tf = max(tf.values()) if tf else 1

        # Calculate TF-IDF
        vector = {}
        for token, count in tf.items():
            if token in self.vocabulary:
                tf_norm = 0.5 + 0.5 * (count / max_tf)
                vector[token] = tf_norm * self.idf.get(token, 1.0)

        return vector

    def transform_all(self) -> List[Dict[str, float]]:
        """Transform all fitted documents."""
        vectors = []
        for doc_tokens in self.documents:
            if not doc_tokens:
                vectors.append({})
                continue

            tf = Counter(doc_tokens)
            max_tf = max(tf.values()) if tf else 1

            vector = {}
            for token, count in tf.items():
                if token in self.vocabulary:
                    tf_norm = 0.5 + 0.5 * (count / max_tf)
                    vector[token] = tf_norm * self.idf.get(token, 1.0)
            vectors.append(vector)

        return vectors


def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    """Calculate cosine similarity between two sparse vectors."""
    if not vec1 or not vec2:
        return 0.0

    # Get common keys
    common_keys = set(vec1.keys()) & set(vec2.keys())
    if not common_keys:
        return 0.0

    # Calculate dot product
    dot_product = sum(vec1[k] * vec2[k] for k in common_keys)

    # Calculate magnitudes
    mag1 = math.sqrt(sum(v * v for v in vec1.values()))
    mag2 = math.sqrt(sum(v * v for v in vec2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot_product / (mag1 * mag2)


class NLPInterpreter:
    """
    Natural Language Processing interpreter for NL2Py modules.

    Matches natural language commands to module methods using TF-IDF
    similarity and generates executable Python code.
    """

    def __init__(self):
        self.method_entries: List[MethodEntry] = []
        self.vectorizer: Optional[TFIDFVectorizer] = None
        self.document_vectors: List[Dict[str, float]] = []
        self._initialized = False

    def load_modules(self, module_classes: Optional[List[Any]] = None) -> int:
        """
        Load method information from all available modules.

        Args:
            module_classes: Optional list of module classes to load.
                          If None, loads all modules from nl2py.modules.

        Returns:
            Number of methods loaded.
        """
        self.method_entries = []

        if module_classes is None:
            # Import all modules
            try:
                from nl2py import modules
                module_classes = []
                for name in dir(modules):
                    if name.endswith('Module') and not name.startswith('_'):
                        try:
                            module_class = getattr(modules, name)
                            module_classes.append(module_class)
                        except Exception:
                            continue
            except ImportError:
                return 0

        # Extract method info from each module
        for module_class in module_classes:
            if not hasattr(module_class, 'get_methods_info'):
                continue

            try:
                methods_info = module_class.get_methods_info()
                module_name = module_class.__name__

                for method_info in methods_info:
                    # Each method can have multiple examples
                    examples = method_info.examples if hasattr(method_info, 'examples') else []
                    if not examples:
                        examples = getattr(method_info, 'examples', [])

                    # Handle both MethodInfo objects and dicts
                    if hasattr(method_info, 'name'):
                        method_name = method_info.name
                        description = method_info.description
                        parameters = method_info.parameters
                    else:
                        method_name = method_info.get('name', '')
                        description = method_info.get('description', '')
                        parameters = method_info.get('parameters', {})

                    for example in examples:
                        if isinstance(example, dict):
                            example_text = example.get('text', '')
                            example_code = example.get('code', '')
                        else:
                            example_text = getattr(example, 'text', '')
                            example_code = getattr(example, 'code', '')

                        if example_text and example_code:
                            self.method_entries.append(MethodEntry(
                                module_name=module_name,
                                method_name=method_name,
                                description=description,
                                parameters=parameters,
                                example_text=example_text,
                                example_code=example_code
                            ))

                    # Also add description as a matchable entry
                    if description:
                        # Create a generic example from description
                        self.method_entries.append(MethodEntry(
                            module_name=module_name,
                            method_name=method_name,
                            description=description,
                            parameters=parameters,
                            example_text=description,
                            example_code=f"{method_name}()"
                        ))
            except Exception:
                continue

        # Build TF-IDF index
        if self.method_entries:
            documents = [entry.example_text for entry in self.method_entries]
            self.vectorizer = TFIDFVectorizer().fit(documents)
            self.document_vectors = self.vectorizer.transform_all()
            self._initialized = True

        return len(self.method_entries)

    def _extract_params_from_text(self, text: str, example_text: str, example_code: str) -> Dict[str, str]:
        """
        Extract parameter values from user text by matching against example patterns.

        Uses the {{param}} markers in example_text to identify parameter positions
        and extracts corresponding values from the user's text.
        """
        params = {}

        # Find all parameter placeholders in example
        param_pattern = r'\{\{([^}]+)\}\}'
        placeholders = re.findall(param_pattern, example_text)

        if not placeholders:
            return params

        # Create a regex pattern from the example text
        # Replace {{param}} with capture groups
        pattern_text = re.escape(example_text)
        for placeholder in placeholders:
            escaped_placeholder = re.escape('{{' + placeholder + '}}')
            # Match word characters, numbers, hyphens, underscores, dots, paths
            pattern_text = pattern_text.replace(escaped_placeholder, r'([^\s,]+|"[^"]*"|\'[^\']*\')')

        # Try to match the pattern against user text
        try:
            match = re.search(pattern_text, text, re.IGNORECASE)
            if match:
                for i, placeholder in enumerate(placeholders):
                    if i < len(match.groups()):
                        value = match.group(i + 1)
                        # Clean up quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        params[placeholder] = value
        except re.error:
            pass

        # If pattern matching failed, try keyword extraction
        if not params:
            params = self._extract_params_by_keywords(text, placeholders)

        return params

    def _extract_params_by_keywords(self, text: str, placeholders: List[str]) -> Dict[str, str]:
        """
        Extract parameters using keyword matching when pattern matching fails.

        Looks for common parameter keywords like 'named', 'called', 'to', 'from', etc.
        """
        params = {}
        text_lower = text.lower()

        # Common patterns for parameter extraction
        keyword_patterns = [
            # "named X", "called X", "name X"
            (r'(?:named?|called?)\s+["\']?([^\s,"\'\)]+)["\']?', ['name', 'instance', 'bucket', 'topic', 'queue']),
            # "to X", "into X" (for destinations)
            (r'(?:to|into)\s+["\']?([^\s,"\'\)]+)["\']?', ['destination', 'target', 'bucket', 'topic']),
            # "from X" (for sources)
            (r'(?:from)\s+["\']?([^\s,"\'\)]+)["\']?', ['source', 'bucket', 'file']),
            # "in zone X", "zone X"
            (r'(?:in\s+)?zone\s+["\']?([^\s,"\'\)]+)["\']?', ['zone']),
            # "in region X", "region X"
            (r'(?:in\s+)?region\s+["\']?([^\s,"\'\)]+)["\']?', ['region']),
            # "with X Y" patterns
            (r'with\s+(\w+)\s+["\']?([^\s,"\'\)]+)["\']?', None),  # Special handling
            # Quoted values
            (r'["\']([^"\']+)["\']', None),  # Quoted strings
        ]

        for pattern, applicable_params in keyword_patterns:
            if applicable_params is None:
                continue
            try:
                match = re.search(pattern, text_lower)
                if match:
                    value = match.group(1)
                    # Find which placeholder this might belong to
                    for placeholder in placeholders:
                        placeholder_lower = placeholder.lower()
                        if any(p in placeholder_lower for p in applicable_params):
                            if placeholder not in params:
                                params[placeholder] = value
                                break
            except re.error:
                continue

        # Try to find quoted strings for remaining placeholders
        quoted_values = re.findall(r'["\']([^"\']+)["\']', text)
        unfilled_placeholders = [p for p in placeholders if p not in params]
        for i, placeholder in enumerate(unfilled_placeholders):
            if i < len(quoted_values):
                params[placeholder] = quoted_values[i]

        # Try to find standalone alphanumeric values for remaining placeholders
        words = re.findall(r'\b([a-zA-Z][\w\-\.]+)\b', text)
        # Filter out common words
        stopwords = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'from', 'with', 'and', 'or', 'for',
                     'create', 'delete', 'start', 'stop', 'list', 'get', 'set', 'update', 'send',
                     'upload', 'download', 'connect', 'instance', 'compute', 'storage', 'bucket'}
        words = [w for w in words if w.lower() not in stopwords]

        unfilled_placeholders = [p for p in placeholders if p not in params]
        for i, placeholder in enumerate(unfilled_placeholders):
            if i < len(words):
                params[placeholder] = words[i]

        return params

    def _generate_code(self, method_entry: MethodEntry, params: Dict[str, str]) -> str:
        """
        Generate Python code by substituting parameters into the example code.
        """
        code = method_entry.example_code

        # Replace {{param}} with actual values
        for param_name, param_value in params.items():
            placeholder = '{{' + param_name + '}}'

            # Determine if value should be quoted
            # Numbers and booleans don't need quotes
            if param_value.isdigit() or param_value.lower() in ('true', 'false', 'none'):
                code = code.replace(placeholder, param_value)
                code = code.replace(f"'{placeholder}'", param_value)
                code = code.replace(f'"{placeholder}"', param_value)
            else:
                code = code.replace(placeholder, param_value)

        # Remove any remaining unfilled placeholders with empty strings
        code = re.sub(r'\{\{[^}]+\}\}', "''", code)

        return code

    def match(self, text: str, threshold: float = 0.1, top_k: int = 1) -> List[MatchResult]:
        """
        Match input text to the most similar method(s).

        Args:
            text: Natural language command to interpret.
            threshold: Minimum similarity score (0-1) to consider a match.
            top_k: Number of top matches to return.

        Returns:
            List of MatchResult objects sorted by similarity score.
        """
        if not self._initialized or not self.vectorizer:
            return []

        # Transform input text
        input_vector = self.vectorizer.transform(text)

        # Calculate similarities
        similarities = []
        for i, doc_vector in enumerate(self.document_vectors):
            score = cosine_similarity(input_vector, doc_vector)
            if score >= threshold:
                similarities.append((i, score))

        # Sort by score descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Build results
        results = []
        seen_methods = set()

        for idx, score in similarities[:top_k * 2]:  # Get extra to handle deduplication
            entry = self.method_entries[idx]

            # Skip if we already have this method (keep highest scoring example)
            method_key = (entry.module_name, entry.method_name)
            if method_key in seen_methods:
                continue
            seen_methods.add(method_key)

            # Extract parameters
            params = self._extract_params_from_text(text, entry.example_text, entry.example_code)

            # Generate code
            code = self._generate_code(entry, params)

            results.append(MatchResult(
                module_name=entry.module_name,
                method_name=entry.method_name,
                similarity_score=score,
                matched_example=entry.example_text,
                extracted_params=params,
                generated_code=code,
                original_text=text
            ))

            if len(results) >= top_k:
                break

        return results

    def interpret(self, text: str) -> Optional[MatchResult]:
        """
        Interpret a single text command and return the best match.

        Args:
            text: Natural language command to interpret.

        Returns:
            Best MatchResult or None if no suitable match found.
        """
        results = self.match(text, threshold=0.1, top_k=1)
        return results[0] if results else None


class FileInterpreter:
    """
    Process a text file line by line and generate Python code.
    """

    def __init__(self, interpreter: Optional[NLPInterpreter] = None):
        """
        Initialize the file interpreter.

        Args:
            interpreter: NLPInterpreter instance. If None, creates a new one
                        and loads all available modules.
        """
        self.interpreter = interpreter or NLPInterpreter()
        if not self.interpreter._initialized:
            self.interpreter.load_modules()

    def process_file(self, file_path: str, output_path: Optional[str] = None,
                     threshold: float = 0.1, include_comments: bool = True) -> str:
        """
        Process a text file and generate Python code.

        Args:
            file_path: Path to input text file.
            output_path: Optional path to write generated code. If None, returns code.
            threshold: Minimum similarity threshold for matching.
            include_comments: Whether to include original text as comments.

        Returns:
            Generated Python code as string.
        """
        generated_lines = []
        imports_needed = set()

        # Add header
        generated_lines.append('"""')
        generated_lines.append(f'Generated Python code from: {file_path}')
        generated_lines.append('Auto-generated by NL2Py NLP Interpreter')
        generated_lines.append('"""')
        generated_lines.append('')

        # Process file
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    if line.startswith('#'):
                        generated_lines.append(line)
                    else:
                        generated_lines.append('')
                    continue

                # Try to interpret the line
                result = self.interpreter.interpret(line)

                if result and result.similarity_score >= threshold:
                    # Track imports
                    module_name = result.module_name
                    imports_needed.add(module_name)

                    # Add comment with original text
                    if include_comments:
                        generated_lines.append(f'# Line {line_num}: {line}')
                        generated_lines.append(f'# Matched: {result.matched_example} (score: {result.similarity_score:.2f})')

                    # Add generated code
                    generated_lines.append(result.generated_code)
                    generated_lines.append('')
                else:
                    # No match found
                    generated_lines.append(f'# Line {line_num}: {line}')
                    generated_lines.append(f'# WARNING: No matching method found')
                    generated_lines.append(f'# pass  # TODO: Implement manually')
                    generated_lines.append('')

        # Build final code with imports
        import_lines = ['from nl2py import modules']
        for module in sorted(imports_needed):
            import_lines.append(f'# Uses: {module}')
        import_lines.append('')

        final_code = '\n'.join(import_lines + generated_lines)

        # Write to file if output path specified
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_code)

        return final_code

    def process_lines(self, lines: List[str], threshold: float = 0.1) -> List[MatchResult]:
        """
        Process a list of text lines and return match results.

        Args:
            lines: List of natural language commands.
            threshold: Minimum similarity threshold.

        Returns:
            List of MatchResult objects (one per line, None for unmatched).
        """
        results = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                results.append(None)
                continue

            result = self.interpreter.interpret(line)
            if result and result.similarity_score >= threshold:
                results.append(result)
            else:
                results.append(None)

        return results


def create_interpreter() -> NLPInterpreter:
    """
    Create and initialize an NLP interpreter with all available modules.

    Returns:
        Initialized NLPInterpreter instance.
    """
    interpreter = NLPInterpreter()
    count = interpreter.load_modules()
    print(f"Loaded {count} method examples from modules")
    return interpreter


# CLI interface
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python nlp_interpreter.py <input_file> [output_file]")
        print("       python nlp_interpreter.py --interactive")
        sys.exit(1)

    if sys.argv[1] == '--interactive':
        # Interactive mode
        print("NL2Py NLP Interpreter - Interactive Mode")
        print("Enter natural language commands (Ctrl+C to exit)")
        print("-" * 50)

        interpreter = create_interpreter()

        while True:
            try:
                text = input("\n> ").strip()
                if not text:
                    continue

                results = interpreter.match(text, threshold=0.05, top_k=3)

                if not results:
                    print("No matching methods found")
                    continue

                print(f"\nTop {len(results)} matches:")
                for i, result in enumerate(results, 1):
                    print(f"\n{i}. {result.module_name}.{result.method_name}")
                    print(f"   Score: {result.similarity_score:.2f}")
                    print(f"   Example: {result.matched_example}")
                    print(f"   Params: {result.extracted_params}")
                    print(f"   Code: {result.generated_code}")

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")

    else:
        # File processing mode
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None

        print(f"Processing: {input_file}")

        file_interpreter = FileInterpreter()
        code = file_interpreter.process_file(input_file, output_file)

        if output_file:
            print(f"Generated code written to: {output_file}")
        else:
            print("\nGenerated code:")
            print("-" * 50)
            print(code)
