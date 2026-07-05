#!/bin/sh
# One-command Linux build. Produces:
#   dist/rpa-run.bin                 headless zero-install runner (--headless only)
#   dist/rpa-studio-linux.tar.gz     standalone GUI folder build (default)
# Usage:
#   scripts/build_linux.sh            GUI folder build + tar.gz package
#   scripts/build_linux.sh headless   headless onefile runner only
# Build on a machine as old as (or older than) the deployment target so glibc matches.

set -e
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

python="${PYTHON:-python3}"
if [ -x "$root/build/bin/python" ]; then
    python="$root/build/bin/python"
fi

if ! "$python" -c "import nuitka" 2>/dev/null; then
    echo "nuitka is not installed for $python"
    echo "Prepare a build venv first:"
    echo "  python3 -m venv build && . build/bin/activate"
    echo "  pip install -r rpa_framework/requirements-linux.txt nuitka"
    echo "  pip install -r rpa_framework/requirements-gui.txt   # GUI build only"
    exit 1
fi

if [ "$1" = "headless" ]; then
    "$python" -m rpa_framework.packaging.build --headless
    echo "Artifact: $root/dist/rpa-run.bin"
    exit 0
fi

"$python" -m rpa_framework.packaging.build --no-onefile

stage="$root/dist/rpa-studio-linux"
rm -rf "$stage"
cp -r "$root/dist/app.dist" "$stage"
cp "$root/rpa_framework/LINUX.md" "$stage/LINUX.md"
cat > "$stage/run.sh" << 'EOF'
#!/bin/sh
cd "$(dirname "$0")"
exec ./RPAStudio.bin "$@"
EOF
chmod +x "$stage/run.sh" "$stage/RPAStudio.bin" 2>/dev/null || true

tar czf "$root/dist/rpa-studio-linux.tar.gz" -C "$root/dist" rpa-studio-linux
echo "Artifact: $root/dist/rpa-studio-linux.tar.gz"
