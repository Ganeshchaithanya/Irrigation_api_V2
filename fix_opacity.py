import os
import re

def replace_with_opacity(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.dart'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace withOpacity(0.12) with withValues(alpha: 0.12)
                # This regex handles cases like .withOpacity(0.1), .withOpacity(value), etc.
                new_content = re.sub(r'\.withOpacity\((.*?)\)', r'.withValues(alpha: \1)', content)
                
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Fixed {path}")

if __name__ == "__main__":
    replace_with_opacity('aquasol_app/lib')
