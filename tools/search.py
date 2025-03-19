"""
Tool for searching files and file content on the system.
"""
import os
import re
from typing import Any, Dict, List, Optional

from tools.base import Tool


class SearchTool(Tool):
    """
    Tool for searching files and file content on the system.
    """
    
    def __init__(self):
        """
        Initialize the search tool.
        """
        super().__init__(
            name="search",
            description="Search for files or file content on the system",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["find_files", "grep"],
                        "description": "Action to perform (find_files, grep)",
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to search in",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Pattern to search for (filename pattern or content pattern)",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Whether to search recursively",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether the search should be case-sensitive",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                    },
                    "include_extensions": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                        "description": "File extensions to include in the search",
                    },
                    "exclude_extensions": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                        "description": "File extensions to exclude from the search",
                    },
                },
                "required": ["action", "path", "pattern"],
            },
        )
    
    def _find_files(
        self,
        path: str,
        pattern: str,
        recursive: bool = True,
        case_sensitive: bool = False,
        max_results: int = 100,
        include_extensions: Optional[List[str]] = None,
        exclude_extensions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Find files matching a pattern in a directory.
        
        Args:
            path: Path to search in
            pattern: Filename pattern to search for
            recursive: Whether to search recursively
            case_sensitive: Whether the search should be case-sensitive
            max_results: Maximum number of results to return
            include_extensions: File extensions to include
            exclude_extensions: File extensions to exclude
            
        Returns:
            Dictionary with the search results
        """
        try:
            # Validate path
            if not os.path.exists(path):
                return {
                    "success": False,
                    "message": f"Path not found: {path}",
                }
                
            # Compile pattern
            if not case_sensitive:
                pattern = pattern.lower()
                re_flags = re.IGNORECASE
            else:
                re_flags = 0
                
            try:
                regex = re.compile(pattern, re_flags)
            except re.error:
                # If not a valid regex, use simple string matching
                regex = None
                
            # Process extensions
            if include_extensions:
                include_extensions = [ext.lower() if not ext.startswith(".") else ext.lower()[1:] for ext in include_extensions]
            if exclude_extensions:
                exclude_extensions = [ext.lower() if not ext.startswith(".") else ext.lower()[1:] for ext in exclude_extensions]
                
            # Find files
            results = []
            
            if recursive:
                for root, _, files in os.walk(path):
                    for file in files:
                        if len(results) >= max_results:
                            break
                            
                        # Check extensions
                        ext = os.path.splitext(file)[1].lower()[1:] if os.path.splitext(file)[1] else ""
                        if include_extensions and ext not in include_extensions:
                            continue
                        if exclude_extensions and ext in exclude_extensions:
                            continue
                            
                        # Check pattern
                        match = False
                        if regex:
                            match = bool(regex.search(file))
                        else:
                            if not case_sensitive:
                                match = pattern in file.lower()
                            else:
                                match = pattern in file
                                
                        if match:
                            file_path = os.path.join(root, file)
                            results.append({
                                "path": file_path,
                                "name": file,
                                "size": os.path.getsize(file_path),
                                "modified": os.path.getmtime(file_path),
                            })
            else:
                for file in os.listdir(path):
                    if len(results) >= max_results:
                        break
                        
                    file_path = os.path.join(path, file)
                    if not os.path.isfile(file_path):
                        continue
                        
                    # Check extensions
                    ext = os.path.splitext(file)[1].lower()[1:] if os.path.splitext(file)[1] else ""
                    if include_extensions and ext not in include_extensions:
                        continue
                    if exclude_extensions and ext in exclude_extensions:
                        continue
                        
                    # Check pattern
                    match = False
                    if regex:
                        match = bool(regex.search(file))
                    else:
                        if not case_sensitive:
                            match = pattern in file.lower()
                        else:
                            match = pattern in file
                            
                    if match:
                        results.append({
                            "path": file_path,
                            "name": file,
                            "size": os.path.getsize(file_path),
                            "modified": os.path.getmtime(file_path),
                        })
                        
            return {
                "success": True,
                "files": results,
                "count": len(results),
                "truncated": len(results) >= max_results,
                "message": f"Found {len(results)} files matching pattern '{pattern}'",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to find files: {str(e)}",
            }
    
    def _grep(
        self,
        path: str,
        pattern: str,
        recursive: bool = True,
        case_sensitive: bool = False,
        max_results: int = 100,
        include_extensions: Optional[List[str]] = None,
        exclude_extensions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Search for content in files.
        
        Args:
            path: Path to search in
            pattern: Content pattern to search for
            recursive: Whether to search recursively
            case_sensitive: Whether the search should be case-sensitive
            max_results: Maximum number of results to return
            include_extensions: File extensions to include
            exclude_extensions: File extensions to exclude
            
        Returns:
            Dictionary with the search results
        """
        try:
            # Validate path
            if not os.path.exists(path):
                return {
                    "success": False,
                    "message": f"Path not found: {path}",
                }
                
            # Compile pattern
            if not case_sensitive:
                re_flags = re.IGNORECASE
            else:
                re_flags = 0
                
            try:
                regex = re.compile(pattern, re_flags)
            except re.error:
                return {
                    "success": False,
                    "message": f"Invalid regex pattern: {pattern}",
                }
                
            # Process extensions
            if include_extensions:
                include_extensions = [ext.lower() if not ext.startswith(".") else ext.lower()[1:] for ext in include_extensions]
            if exclude_extensions:
                exclude_extensions = [ext.lower() if not ext.startswith(".") else ext.lower()[1:] for ext in exclude_extensions]
                
            # Search files
            results = []
            total_matches = 0
            
            if recursive:
                for root, _, files in os.walk(path):
                    for file in files:
                        if total_matches >= max_results:
                            break
                            
                        # Check extensions
                        ext = os.path.splitext(file)[1].lower()[1:] if os.path.splitext(file)[1] else ""
                        if include_extensions and ext not in include_extensions:
                            continue
                        if exclude_extensions and ext in exclude_extensions:
                            continue
                            
                        # Search in file
                        file_path = os.path.join(root, file)
                        file_matches = self._search_in_file(file_path, regex, max_results - total_matches)
                        
                        if file_matches:
                            results.append({
                                "path": file_path,
                                "matches": file_matches,
                                "count": len(file_matches),
                            })
                            total_matches += len(file_matches)
            else:
                for file in os.listdir(path):
                    if total_matches >= max_results:
                        break
                        
                    file_path = os.path.join(path, file)
                    if not os.path.isfile(file_path):
                        continue
                        
                    # Check extensions
                    ext = os.path.splitext(file)[1].lower()[1:] if os.path.splitext(file)[1] else ""
                    if include_extensions and ext not in include_extensions:
                        continue
                    if exclude_extensions and ext in exclude_extensions:
                        continue
                        
                    # Search in file
                    file_matches = self._search_in_file(file_path, regex, max_results - total_matches)
                    
                    if file_matches:
                        results.append({
                            "path": file_path,
                            "matches": file_matches,
                            "count": len(file_matches),
                        })
                        total_matches += len(file_matches)
                        
            return {
                "success": True,
                "matches": results,
                "file_count": len(results),
                "match_count": total_matches,
                "truncated": total_matches >= max_results,
                "message": f"Found {total_matches} matches in {len(results)} files",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to search files: {str(e)}",
            }
    
    def _search_in_file(self, file_path: str, regex: re.Pattern, max_matches: int) -> List[Dict[str, Any]]:
        """
        Search for matches in a file.
        
        Args:
            file_path: Path to the file
            regex: Compiled regex pattern
            max_matches: Maximum number of matches to return
            
        Returns:
            List of matches
        """
        try:
            matches = []
            
            # Skip binary files
            if self._is_binary_file(file_path):
                return matches
                
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f):
                    if len(matches) >= max_matches:
                        break
                        
                    for match in regex.finditer(line):
                        if len(matches) >= max_matches:
                            break
                            
                        start = max(0, match.start() - 20)
                        end = min(len(line), match.end() + 20)
                        
                        matches.append({
                            "line": i + 1,
                            "column": match.start() + 1,
                            "text": line.strip(),
                            "context": line[start:end].strip(),
                            "match": match.group(0),
                        })
                        
            return matches
        except Exception:
            # Silently fail for inaccessible files
            return []
    
    def _is_binary_file(self, file_path: str) -> bool:
        """
        Check if a file is binary.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file is binary, False otherwise
        """
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                return b"\0" in chunk
        except Exception:
            # If we can't read the file, assume it's not binary
            return True
    
    def execute(
        self,
        action: str,
        path: str,
        pattern: str,
        recursive: bool = True,
        case_sensitive: bool = False,
        max_results: int = 100,
        include_extensions: Optional[List[str]] = None,
        exclude_extensions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the search tool with the given parameters.
        
        Args:
            action: Action to perform (find_files, grep)
            path: Path to search in
            pattern: Pattern to search for
            recursive: Whether to search recursively
            case_sensitive: Whether the search should be case-sensitive
            max_results: Maximum number of results to return
            include_extensions: File extensions to include
            exclude_extensions: File extensions to exclude
            
        Returns:
            Result of the tool execution
        """
        if action == "find_files":
            return self._find_files(
                path,
                pattern,
                recursive,
                case_sensitive,
                max_results,
                include_extensions,
                exclude_extensions,
            )
        elif action == "grep":
            return self._grep(
                path,
                pattern,
                recursive,
                case_sensitive,
                max_results,
                include_extensions,
                exclude_extensions,
            )
        else:
            return {
                "success": False,
                "message": f"Unknown action: {action}",
            }