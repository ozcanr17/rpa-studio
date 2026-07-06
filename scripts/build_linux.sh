#!/bin/sh
# One-command Linux build. Produces portable standalone folders:
#   dist/rpa-studio-linux/ + dist/rpa-studio-linux.tar.gz     GUI build (default)
#   dist/rpa-run-linux/ + dist/rpa-run-linux.tar.gz           headless runner
# Usage:
#   scripts/build_linux.sh            GUI folder build + tar.gz package
#   scripts/build_linux.sh headless   headless runner folder + tar.gz
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
    built="$root/dist/runner_app.dist"
    stage="$root/dist/rpa-run-linux"
    launcher="rpa-run.bin"
else
    "$python" -m rpa_framework.packaging.build
    built="$root/dist/app.dist"
    stage="$root/dist/rpa-studio-linux"
    launcher="RPAStudio.bin"
fi

rm -rf "$stage"
mv "$built" "$stage"
cp "$root/rpa_framework/LINUX.md" "$stage/LINUX.md"
cat > "$stage/run.sh" << EOF
#!/bin/sh
cd "\$(dirname "\$0")"
exec ./$launcher "\$@"
EOF
chmod +x "$stage/run.sh" "$stage/$launcher" 2>/dev/null || true

tar czf "$stage.tar.gz" -C "$root/dist" "$(basename "$stage")"
echo "Portable folder: $stage"
echo "Artifact: $stage.tar.gz"
