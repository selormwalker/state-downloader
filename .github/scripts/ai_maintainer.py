import os
import google.generativeai as genai
from pathlib import Path

# Supported file extensions for deep analysis and modification
SUPPORTED_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.java', '.cpp', '.rs', '.md', '.txt', '.yml', '.yaml', '.json'}

def get_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not found.")
        exit(1)
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash-latest')

def analyze_and_fix(model, file_path, context_summary=""):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Could not read {file_path}: {e}")
        return None

    prompt = f"""
    ROLE: You are an ELITE Senior Software Engineer and Autonomous AI Architect.
    GOAL: Perform deep, substantive upgrades to the provided file. You have FULL AUTHORITY to rewrite logic, implement new features, fix architectural bugs, and optimize performance.

    PROJECT CONTEXT:
    This file is part of a larger project. 
    Current File: {file_path}

    TASKS:
    1.  **Bug Fixes & Security**: Identify and fix deep-seated logic errors, race conditions, memory leaks, and security vulnerabilities (XSS, SQLi, etc.).
    2.  **Feature Implementation**: Look for "TODOs" or logical gaps where new functionality would be beneficial. Implement them immediately.
    3.  **Architectural Refactoring**: Simplify complex patterns, improve type safety, and apply modern design patterns (SOLID, Clean Architecture).
    4.  **Performance**: Optimize hot loops, reduce memory footprint, and improve algorithmic complexity.
    5.  **Documentation**: Ensure every function has comprehensive docstrings and clear comments explaining the "why" behind complex logic.

    FILE CONTENT:
    ```
    {content}
    ```

    INSTRUCTIONS:
    - You MUST provide the ENTIRE updated file content.
    - If no *substantive* changes are possible (meaning the code is already perfect), respond with "NO_CHANGES_NEEDED".
    - DO NOT include markdown code block backticks (```) in your response.
    - BE BOLD. Do not just make minor style changes; make the code better, faster, and more robust.
    """

    try:
        response = model.generate_content(prompt)
        new_content = response.text.strip()
    except Exception as e:
        print(f"AI generation failed for {file_path}: {e}")
        return None

    if "NO_CHANGES_NEEDED" in new_content:
        return None
    
    # Advanced cleanup for common AI formatting errors
    if new_content.startswith("```"):
        lines = new_content.splitlines()
        if lines[0].startswith("```"):
            # Remove first and last line if they are backticks
            new_content = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])

    return new_content

def main():
    model = get_model()
    project_root = Path(".")
    
    # 1. Identify files to process
    files_to_process = []
    for path in project_root.rglob("*"):
        if path.is_file() and path.suffix in SUPPORTED_EXTENSIONS:
            if any(part.startswith('.') for part in path.parts) or \
               'node_modules' in path.parts or \
               'venv' in path.parts or \
               '__pycache__' in path.parts or \
               'dist' in path.parts or \
               'build' in path.parts:
                continue
            files_to_process.append(path)

    # 2. Process files
    for path in files_to_process:
        print(f"Deep analyzing {path}...")
        new_content = analyze_and_fix(model, path)
        
        if new_content and len(new_content) > 10: # Ensure we don't write empty/corrupt files
            print(f"Applying substantive upgrades to {path}...")
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
        else:
            print(f"No substantive changes needed for {path}.")

if __name__ == "__main__":
    main()
