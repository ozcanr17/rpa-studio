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
    echo "  sudo dnf install -y python3-gobject at-spi2-core   # Element Spy support"
    echo "  python3 -m venv --system-site-packages build && . build/bin/activate"
    echo "  pip install -r rpa_framework/requirements-linux.txt nuitka"
    echo "  pip install -r rpa_framework/requirements-gui.txt   # GUI build only"
    exit 1
fi

if ! "$python" -c "import gi" 2>/dev/null; then
    echo "NOTE: gi (PyGObject) is not importable in the build venv, so Element Spy"
    echo "and findElement will be missing from this build. To include them:"
    echo "  sudo dnf install -y python3-gobject at-spi2-core"
    echo "  recreate the venv with: python3 -m venv --system-site-packages build"
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

# run.sh: launch with the bundled shared libraries visible to the loader, so
# dlopen'ed libs (Qt >= 6.5 needs libxcb-cursor.so.0 at runtime) resolve from
# the folder even on a machine that has none of them installed.
cat > "$stage/run.sh" << EOF
#!/bin/sh
dir="\$(cd "\$(dirname "\$0")" && pwd)"
qtlib="\$(find "\$dir" -name 'libQt6XcbQpa.so*' -print 2>/dev/null | head -n 1)"
[ -n "\$qtlib" ] && qtlib="\$(dirname "\$qtlib")"
LD_LIBRARY_PATH="\$dir\${qtlib:+:\$qtlib}\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH
if [ -z "\$DISPLAY" ] && [ -n "\$WAYLAND_DISPLAY" ] && [ -z "\$QT_QPA_PLATFORM" ]; then
    QT_QPA_PLATFORM=wayland
    export QT_QPA_PLATFORM
fi
exec "\$dir/$launcher" "\$@"
EOF

# diagnose.sh: ships with the app; run it on the target machine to list any
# shared library that still fails to resolve, plus display/session info.
cat > "$stage/diagnose.sh" << EOF
#!/bin/sh
dir="\$(cd "\$(dirname "\$0")" && pwd)"
echo "== session =="
echo "DISPLAY=\$DISPLAY WAYLAND_DISPLAY=\$WAYLAND_DISPLAY XDG_SESSION_TYPE=\$XDG_SESSION_TYPE"
ldd --version 2>/dev/null | head -n 1
echo "== unresolved shared libraries (empty list = all good) =="
qtlib="\$(find "\$dir" -name 'libQt6XcbQpa.so*' -print 2>/dev/null | head -n 1)"
[ -n "\$qtlib" ] && qtlib="\$(dirname "\$qtlib")"
export LD_LIBRARY_PATH="\$dir\${qtlib:+:\$qtlib}\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
find "\$dir" \( -name '*.so*' -o -name '*.bin' \) 2>/dev/null | while read -r f; do
    ldd "\$f" 2>/dev/null | grep "not found" | sed "s|^[[:space:]]*|\${f#\$dir/}: |"
done | sort -u
echo "== done =="
EOF
chmod +x "$stage/run.sh" "$stage/diagnose.sh" "$stage/$launcher" 2>/dev/null || true

# Informational check on the build machine; the authoritative run is
# `sh diagnose.sh` on the deployment target.
echo "== bundle check (unresolved libraries on THIS machine) =="
sh "$stage/diagnose.sh" | sed -n '/unresolved/,$p'

tar czf "$stage.tar.gz" -C "$root/dist" "$(basename "$stage")"
echo "Portable folder: $stage"
echo "Artifact: $stage.tar.gz"
