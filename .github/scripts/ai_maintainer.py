import os
import google.generativeai as genai
from pathlib import Path

# Supported file extensions
SUPPORTED_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.java', '.cpp', '.rs', '.md', '.txt', '.yml', '.yaml', '.json'}

def get_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not found.")
        exit(1)
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')

def analyze_and_fix(model, file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Could not read {file_path}: {e}")
        return None

    prompt = f"""
    You are an autonomous AI software maintainer. Your goal is to improve the following file.
    
    Focus areas:
    1. Bug Fixes: Identify and fix logic errors, potential crashes, or edge case failures.
    2. Dependency Updates: If this is a requirements or package file, suggest updates for known vulnerabilities or outdated versions.
    3. Refactoring & Docs: Improve code readability, add missing docstrings/comments, and simplify complex logic.
    4. Testing: If applicable, suggest or add missing test cases.

    File Path: {file_path}
    Content:
    ```
    {content}
    ```

    Instructions:
    - If no changes are needed, respond with "NO_CHANGES_NEEDED".
    - If changes are needed, provide the FULL, CORRECTED content of the file.
    - DO NOT include any markdown code block backticks (```) in your response unless they are part of the file content itself.
    - Provide ONLY the file content.
    """

    response = model.generate_content(prompt)
    new_content = response.text.strip()

    if "NO_CHANGES_NEEDED" in new_content:
        return None
    
    # Basic cleanup in case model includes backticks
    if new_content.startswith("```") and new_content.endswith("```"):
        lines = new_content.splitlines()
        if lines[0].startswith("```"):
            new_content = "\n".join(lines[1:-1])

    return new_content

def main():
    model = get_model()
    project_root = Path(".")
    
    for path in project_root.rglob("*"):
        if path.is_file() and path.suffix in SUPPORTED_EXTENSIONS:
            # Skip hidden files and common build/dependency directories
            if any(part.startswith('.') for part in path.parts) or \
               'node_modules' in path.parts or \
               'venv' in path.parts or \
               '__pycache__' in path.parts:
                continue

            print(f"Analyzing {path}...")
            new_content = analyze_and_fix(model, path)
            
            if new_content:
                print(f"Applying updates to {path}...")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
            else:
                print(f"No changes needed for {path}.")

if __name__ == "__main__":
    main()
