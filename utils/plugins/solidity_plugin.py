"""
Solidity language plugin for AST analysis using multiple approaches.
"""

import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from .base_plugin import LanguagePlugin


class SolidityPlugin(LanguagePlugin):
    """Solidity analysis plugin with fallback parsing strategies."""
    
    def extensions(self) -> List[str]:
        return ['.sol']
    
    def get_excluded_dirs(self) -> List[str]:
        return ['node_modules', 'lib/openzeppelin', 'lib/forge-std', 'out', 'cache']
    
    def is_available(self) -> bool:
        """Check if Solidity analysis tools are available."""
        # Use regex parsing (always available)
        return True
    
    def build_ast(self, file_path: Path) -> Dict[str, Any]:
        """
        Build AST for Solidity file using regex-based parsing.
        
        Args:
            file_path: Path to Solidity file
            
        Returns:
            AST data dictionary
        """
        return self._build_ast_with_regex(file_path)
    
    
    def _build_ast_with_regex(self, file_path: Path) -> Dict[str, Any]:
        """Build AST using regex-based parsing."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self._parse_solidity_content(content, file_path)
            
        except Exception as e:
            return {
                "plugin": "SolidityPlugin",
                "method": "regex_fallback",
                "error": str(e),
                "contracts": {},
                "functions": {},
                "imports": []
            }
    
    
    def _parse_solidity_content(self, content: str, file_path: Path) -> Dict[str, Any]:
        """Parse Solidity content using regex patterns."""
        contracts = {}
        functions = {}
        imports = []
        
        # Extract pragma version
        pragma_match = re.search(r'pragma\s+solidity\s+([^;]+);', content)
        pragma_version = pragma_match.group(1) if pragma_match else "unknown"
        
        # Extract imports
        import_matches = re.findall(r'import\s+["\']([^"\']+)["\']', content)
        imports = import_matches
        
        # Extract contracts
        contract_pattern = r'(contract|interface|library)\s+(\w+)(?:\s+is\s+([^{]+))?\s*\{'
        contract_matches = re.finditer(contract_pattern, content)
        
        for match in contract_matches:
            contract_type = match.group(1)
            contract_name = match.group(2)
            inherits = match.group(3).strip() if match.group(3) else ""
            
            contracts[contract_name] = {
                "type": contract_type,
                "inherits": [x.strip() for x in inherits.split(',') if x.strip()],
                "line_number": content[:match.start()].count('\n') + 1
            }
        
        # Extract functions
        function_pattern = r'function\s+(\w+)\s*\([^)]*\)\s*([^{]*)\{'
        function_matches = re.finditer(function_pattern, content)
        
        for match in function_matches:
            func_name = match.group(1)
            func_modifiers = match.group(2).strip()
            
            # Determine contract for this function
            func_start = match.start()
            current_contract = self._find_containing_contract(content, func_start, contracts)
            
            func_sig = f"{current_contract}.{func_name}" if current_contract else func_name
            
            # Parse visibility and mutability
            visibility = self._extract_visibility(func_modifiers)
            mutability = self._extract_mutability(func_modifiers)
            modifiers = self._extract_modifiers(func_modifiers)
            
            # Analyze function body for external calls
            func_body = self._extract_function_body(content, match.end())
            external_calls = self._find_external_calls(func_body)
            state_change_after = self._has_state_changes_after_calls(func_body)
            
            functions[func_sig] = {
                "visibility": visibility,
                "mutability": mutability,
                "external_calls": external_calls,
                "state_change_after": state_change_after,
                "complexity_score": self._calculate_complexity_from_body(func_body),
                "parameters": [],  # Would need more complex parsing
                "return_type": "void",  # Would need more complex parsing
                "modifiers": modifiers,
                "line_number": content[:match.start()].count('\n') + 1
            }
        
        return {
            "plugin": "SolidityPlugin",
            "method": "regex",
            "pragma_version": pragma_version,
            "contracts": contracts,
            "functions": functions,
            "imports": imports
        }
    
    def _find_containing_contract(self, content: str, position: int, contracts: Dict[str, Any]) -> Optional[str]:
        """Find which contract contains a function at given position."""
        content_before = content[:position]
        
        # Find the last contract declaration before this position
        contract_pattern = r'(contract|interface|library)\s+(\w+)'
        matches = list(re.finditer(contract_pattern, content_before))
        
        if matches:
            return matches[-1].group(2)
        return None
    
    def _extract_visibility(self, modifiers: str) -> str:
        """Extract visibility from function modifiers."""
        if 'public' in modifiers:
            return 'public'
        elif 'external' in modifiers:
            return 'external'
        elif 'internal' in modifiers:
            return 'internal'
        else:
            return 'private'
    
    def _extract_mutability(self, modifiers: str) -> str:
        """Extract state mutability from function modifiers."""
        if 'pure' in modifiers:
            return 'pure'
        elif 'view' in modifiers:
            return 'view'
        elif 'payable' in modifiers:
            return 'payable'
        else:
            return 'nonpayable'
    
    def _extract_modifiers(self, modifiers: str) -> List[str]:
        """Extract custom modifiers from function declaration."""
        # Simple heuristic: words that are not keywords
        keywords = {'public', 'private', 'external', 'internal', 'view', 'pure', 'payable', 'override', 'virtual'}
        words = re.findall(r'\b\w+\b', modifiers)
        return [word for word in words if word not in keywords]
    
    def _extract_function_body(self, content: str, start_pos: int) -> str:
        """Extract function body starting from given position."""
        brace_count = 1
        pos = start_pos
        
        while pos < len(content) and brace_count > 0:
            char = content[pos]
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            pos += 1
        
        return content[start_pos:pos-1] if brace_count == 0 else ""
    
    def _find_external_calls(self, func_body: str) -> List[Dict[str, Any]]:
        """Find external calls in function body."""
        external_calls = []
        
        # Pattern for contract calls: contractVar.method()
        call_patterns = [
            r'(\w+)\.(\w+)\s*\(',
            r'(address|payable)\s*\([^)]+\)\.call\s*\(',
            r'(\w+)\.transfer\s*\(',
            r'(\w+)\.send\s*\('
        ]
        
        for pattern in call_patterns:
            matches = re.finditer(pattern, func_body)
            for match in matches:
                external_calls.append({
                    "target": match.group(1),
                    "method": match.group(2) if len(match.groups()) > 1 else "call",
                    "line_offset": func_body[:match.start()].count('\n')
                })
        
        return external_calls
    
    def _has_state_changes_after_calls(self, func_body: str) -> bool:
        """Check if there are state changes after external calls."""
        # Simple heuristic: look for assignment operations after call patterns
        lines = func_body.split('\n')
        
        for i, line in enumerate(lines):
            if any(pattern in line for pattern in ['.call(', '.transfer(', '.send(']):
                # Check subsequent lines for state changes
                for j in range(i + 1, len(lines)):
                    if re.search(r'\w+\s*[\+\-\*\/]?=', lines[j]):
                        return True
        
        return False
    
    def _calculate_complexity_from_body(self, func_body: str) -> int:
        """Calculate complexity score from function body."""
        complexity = 0
        
        # Count control flow statements
        complexity += len(re.findall(r'\b(if|for|while|do)\b', func_body))
        
        # Count external calls
        complexity += len(re.findall(r'\.\w+\s*\(', func_body))
        
        # Count state variable assignments
        complexity += len(re.findall(r'\w+\s*=', func_body))
        
        return complexity
    
    
    def summarize(self, ast_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary from Solidity AST data."""
        functions = ast_data.get("functions", {})
        contracts = ast_data.get("contracts", {})
        
        # Get top functions by importance
        top_functions = []
        for func_sig, func_data in functions.items():
            score = (
                len(func_data.get("external_calls", [])) * 3 +
                (2 if func_data.get("state_change_after") else 0) +
                func_data.get("complexity_score", 0)
            )
            
            if score >= 3:  # Threshold for inclusion
                top_functions.append({
                    "signature": func_sig,
                    "visibility": func_data.get("visibility"),
                    "score": score,
                    "risk_factors": self._identify_risk_factors(func_data)
                })
        
        # Sort by score
        top_functions.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "summary_type": "solidity_analysis",
            "contracts_count": len(contracts),
            "functions_count": len(functions),
            "external_functions": len([f for f in functions.values() if f.get("visibility") in ["public", "external"]]),
            "top_functions": top_functions[:10],  # Top 10 functions
            "pragma_version": ast_data.get("pragma_version", "unknown"),
            "imports": ast_data.get("imports", [])
        }
    
    def _identify_risk_factors(self, func_data: Dict[str, Any]) -> List[str]:
        """Identify risk factors for a function."""
        risks = []
        
        if func_data.get("external_calls"):
            risks.append("external_calls")
        
        if func_data.get("state_change_after"):
            risks.append("state_change_after_call")
        
        if func_data.get("visibility") in ["public", "external"]:
            risks.append("external_access")
        
        if func_data.get("mutability") == "payable":
            risks.append("payable")
        
        return risks