"""The tools themselves: every function the `if __name__ == "__main__"` block of a tool calls is defined before
it (build_extra.py called one defined after it: NameError), and build_extra.py no longer has a way to overwrite
the app's fonts.
  python3 tools/tools_test.py"""
import ast
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
FONTS = os.path.join(ROOT, "ports", "mothership", "assets", "fonts")

for path in sorted(glob.glob(os.path.join(TOOLS, "*.py"))):
    tree = ast.parse(open(path, encoding="utf-8").read())
    defined = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
              and getattr(node.test.left, "id", "") == "__name__"):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id.startswith("build"):
                    assert sub.func.id in defined, "%s: %s() is called before it is defined" % (
                        os.path.basename(path), sub.func.id)
print("every build function a tool's main block calls is defined before it")

before = dict((f, os.path.getmtime(f)) for f in glob.glob(os.path.join(FONTS, "*")))
r = subprocess.run([sys.executable, os.path.join(TOOLS, "build_extra.py"), "font"], stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT)
assert r.returncode != 0 and b"build_font.py" in r.stdout, r.stdout
assert before == dict((f, os.path.getmtime(f)) for f in glob.glob(os.path.join(FONTS, "*"))), "fonts touched"
assert "def build_kid_font" not in open(os.path.join(TOOLS, "build_extra.py"), encoding="utf-8").read()
print("build_extra.py points to build_font.py for the fonts and leaves them alone")
print("ok")
