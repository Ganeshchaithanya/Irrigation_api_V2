import os
import re

def check_imports(directory):
    errors = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for i, line in enumerate(lines):
                    # Check for "from backend.xxx import yyy" or "import backend.xxx"
                    match = re.search(r'from (backend\.\w+(\.\w+)*) import|import (backend\.\w+(\.\w+)*)', line)
                    if match:
                        module = match.group(1) or match.group(3)
                        # Convert backend.xxx.yyy to backend/xxx/yyy.py
                        parts = module.split('.')
                        module_path = os.path.join(*parts) + '.py'
                        if not os.path.exists(module_path) and not os.path.exists(os.path.join(*parts, '__init__.py')):
                            print(f"Broken import in {path}:{i+1}: {module}")
                            errors += 1
    print(f"Total broken imports: {errors}")

if __name__ == "__main__":
    check_imports('backend')
