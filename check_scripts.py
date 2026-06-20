import re
import sys

def check_html_scripts(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
    for i, script in enumerate(scripts):
        # Very simple check for 'await' outside 'async' is hard with regex, 
        # but we can try to find 'await ' that is NOT preceded by 'async' somewhere in the same scope.
        # However, a better way is to just print the lines around 'await'.
        lines = script.split('\n')
        for j, line in enumerate(lines):
            if 'await ' in line:
                # Check if it's inside a function that is NOT async
                # This is hard.
                pass
    print(f"Found {len(scripts)} script blocks.")

if __name__ == "__main__":
    check_html_scripts(sys.argv[1])
