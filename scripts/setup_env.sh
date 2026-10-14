#!/usr/bin/env bash
# Reproducible Debian 13 cloud setup; never changes tracked repository files.
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_DIR="$PROJECT_DIR/.local"
mkdir -p "$LOCAL_DIR/bin" "$PROJECT_DIR/.cache/pip" "$PROJECT_DIR/.cache/matplotlib"

system_install() {
    if [[ "$(id -u)" == 0 ]]; then
        apt-get update
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$@"
    elif command -v sudo >/dev/null && sudo -n true 2>/dev/null; then
        sudo -n apt-get update
        sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$@"
    else
        printf 'Missing prerequisites (%s); install them with your system administrator.\n' "$*" >&2
        return 1
    fi
}

if ! command -v python3 >/dev/null; then
    system_install python3 python3-venv
fi
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11 or newer is required"'

# Debian packages are authenticated by APT's signed Release files and hashes.
# Download and extract locally: no root, sudo, or system modification required.
# Debian's stable release pins ngspice separately from the Python lockfile.
. /etc/os-release
if [[ "$ID" == debian && "${VERSION_CODENAME:-}" == trixie ]]; then
    APT_DIR="$PROJECT_DIR/.cache/apt"
    mkdir -p "$APT_DIR/lists/partial" "$APT_DIR/archives/partial" "$APT_DIR/configparts" "$LOCAL_DIR/ngspice"
    cat > "$APT_DIR/sources.list" <<'SOURCES'
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main
SOURCES
    # Set this before APT starts reading configuration, to avoid system hooks.
    printf 'Dir::Etc::main "/dev/null";\nDir::Etc::parts "%s";\n' \
        "$APT_DIR/configparts" > "$APT_DIR/apt.conf"
    apt_options=(
        -o "Dir::Etc::sourcelist=$APT_DIR/sources.list"
        -o Dir::Etc::sourceparts=-
        -o "Dir::State::lists=$APT_DIR/lists"
        -o "Dir::Cache::archives=$APT_DIR/archives"
        -o "APT::Sandbox::User=$(id -un)"
        -o Debug::NoLocking=1
        -o Acquire::Languages=none
        -o APT::Update::Error-Mode=any
    )
    # Use the real APT executable, keeping all state in this checkout.
    APT_CONFIG="$APT_DIR/apt.conf" /usr/bin/apt-get "${apt_options[@]}" update
    APT_CONFIG="$APT_DIR/apt.conf" /usr/bin/apt-get "${apt_options[@]}" \
        --download-only --no-install-recommends -y install 'ngspice=44.2+ds-1'
    shopt -s nullglob
    debs=("$APT_DIR"/archives/*.deb)
    # A system with this exact version already installed may need no download.
    if ((${#debs[@]})); then
        for deb in "${debs[@]}"; do
            dpkg-deb --extract "$deb" "$LOCAL_DIR/ngspice"
        done
    elif ! command -v ngspice >/dev/null; then
        printf 'APT did not provide an ngspice executable.\n' >&2
        exit 1
    fi
    if [[ -x "$LOCAL_DIR/ngspice/usr/bin/ngspice" ]]; then
        # APT's system spinit contains absolute /usr/lib paths. Rootless package
        # extraction does not relocate these; keep the authenticated package
        # file unchanged and use ngspice's documented SPICE_SCRIPTS override.
        multiarch="$(dpkg-architecture -qDEB_HOST_MULTIARCH)"
        python3 - "$LOCAL_DIR/ngspice" "$LOCAL_DIR/ngspice-runtime" "$multiarch" <<'RELOCATE'
import pathlib
import re
import sys

prefix, runtime = map(pathlib.Path, sys.argv[1:3])
multiarch = sys.argv[3]
source = prefix / "usr/share/ngspice/scripts/spinit"
model_dir = prefix / "usr/lib" / multiarch / "ngspice"
if any(char.isspace() for char in str(model_dir)):
    raise SystemExit("ngspice Code Model paths must not contain whitespace; use a workspace path without spaces")
required = ("spice2poly.cm", "analog.cm", "digital.cm", "xtradev.cm", "xtraevt.cm", "table.cm")
for name in required:
    if not (model_dir / name).is_file():
        raise SystemExit(f"Missing required ngspice Code Model library: {model_dir / name}")
text = source.read_text()
pattern = rf'(?m)^([ \t]*(?:codemodel|osdi))[ \t]+/usr/lib/{re.escape(multiarch)}/ngspice/(\S+)[ \t]*$'
# codemodel passes its filename straight to dlopen; quotes become filename bytes.
text, count = re.subn(pattern, lambda m: f'{m[1]} {model_dir / m[2]}', text)
if count < len(required):
    raise SystemExit("Unexpected packaged spinit: required model paths could not be relocated")
runtime.mkdir(parents=True, exist_ok=True)
(runtime / "spinit").write_text(text)
print(f"Relocated {count} model paths into {runtime / 'spinit'}")
RELOCATE
        cat > "$LOCAL_DIR/bin/ngspice" <<'WRAPPER'
#!/usr/bin/env bash
set -euo pipefail
local_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
prefix="$local_dir/ngspice"
multiarch="$(dpkg-architecture -qDEB_HOST_MULTIARCH)"
export LD_LIBRARY_PATH="$prefix/usr/lib/$multiarch${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export SPICE_SCRIPTS="$local_dir/ngspice-runtime"
exec "$prefix/usr/bin/ngspice" "$@"
WRAPPER
        chmod +x "$LOCAL_DIR/bin/ngspice"
    fi
elif ! command -v ngspice >/dev/null; then
    # Other Debian/Ubuntu releases use their native package, requiring root/sudo.
    system_install ngspice
fi

if [[ ! -x "$PROJECT_DIR/.venv/bin/python" ]]; then
    python3 -m venv "$PROJECT_DIR/.venv"
fi
export PIP_CACHE_DIR="$PROJECT_DIR/.cache/pip"
"$PROJECT_DIR/.venv/bin/python" -m pip install --disable-pip-version-check \
    --index-url https://pypi.org/simple --require-hashes --only-binary=:all: \
    -r "$PROJECT_DIR/requirements.lock"
"$PROJECT_DIR/.venv/bin/python" -m pip check

cat > "$LOCAL_DIR/env.sh" <<'ACTIVATE'
# Source this from Bash to activate the repository's Python and ngspice.
_spice_lab_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$_spice_lab_root/.venv/bin/activate"
export PATH="$_spice_lab_root/.local/bin:$PATH"
export MPLBACKEND=Agg
export MPLCONFIGDIR="$_spice_lab_root/.cache/matplotlib"
unset _spice_lab_root
ACTIVATE
source "$LOCAL_DIR/env.sh"
ngspice --version
python - <<'PY'
import sys
import numpy, scipy, matplotlib, pandas
print('Python', sys.version.split()[0])
for module in (numpy, scipy, matplotlib, pandas):
    print(module.__name__, module.__version__)
PY
python "$PROJECT_DIR/scripts/test_ngspice_models.py" \
    --output-dir "$LOCAL_DIR/code_model_validation"
printf '\nSetup complete. In Bash run: source "%s/.local/env.sh"\n' "$PROJECT_DIR"
