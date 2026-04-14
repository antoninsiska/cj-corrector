#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON=$(which python3)

echo "╔══════════════════════════════════════════╗"
echo "║     CJ Correcter – Setup                 ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Python: $PYTHON"
echo "Dir:    $SCRIPT_DIR"
echo ""

# ── install Python packages ──
echo "▸ Installing Python packages…"
$PYTHON -m pip install --quiet --upgrade rumps requests matplotlib torch transformers

# ── download HuggingFace model ──
echo "▸ Downloading grammar model (ufal/byt5-small-geccc-mate)…"
echo "  (first run only, ~300 MB)"
$PYTHON "$SCRIPT_DIR/ollama_client.py"

echo "✅  Packages installed"
echo ""

# ── create config directory ──
mkdir -p "$HOME/.cj_correcter"

# ── create Automator service ──
echo "▸ Creating Automator Quick Action (right-click service)…"
$PYTHON "$SCRIPT_DIR/create_service.py"

# ── refresh macOS services cache ──
echo ""
echo "▸ Refreshing macOS services cache…"
/System/Library/CoreServices/pbs -update 2>/dev/null || true

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║     Setup complete! 🎉                   ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "▸ Start the status bar app (keep it running):"
echo "    python3 $SCRIPT_DIR/app.py &"
echo ""
echo "▸ To test grammar correction directly:"
echo "    echo 'Já jdem do školy.' | python3 $SCRIPT_DIR/grammar_correct.py"
echo ""
echo "▸ To add the status bar app to Login Items:"
echo "    System Settings → General → Login Items → click +"
echo "    then select app.py  (or create the .command wrapper below)"
echo ""

# Create a double-clickable launcher
LAUNCHER="$SCRIPT_DIR/Start CJ Correcter.command"
cat > "$LAUNCHER" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
python3 "$SCRIPT_DIR/app.py"
EOF
chmod +x "$LAUNCHER"
echo "▸ A launcher was created:"
echo "    $LAUNCHER"
echo "   Double-click it to start the status bar app."
echo ""
