#!/bin/bash
set -e

REPO="antoninsiska/cj-corrector"
FORMULA="Formula/cj-corrector.rb"

# ── 1. Zeptej se na verzi ─────────────────────────────────────────────────────
read -rp "Verze (např. 1.0.1): " VERSION
VERSION="${VERSION#v}"   # odstraň případné 'v' na začátku

TAG="v${VERSION}"
TARBALL_URL="https://github.com/${REPO}/archive/refs/tags/${TAG}.tar.gz"

echo ""
echo "Budu vytvářet release ${TAG} na ${REPO}"
read -rp "Pokračovat? [y/N] " CONFIRM
[[ "$CONFIRM" =~ ^[Yy]$ ]] || { echo "Zrušeno."; exit 0; }

# ── 2. Vytvoř git tag a pushni ────────────────────────────────────────────────
echo ""
echo "▶ Vytvářím git tag ${TAG}..."
git tag "${TAG}"
git push origin "${TAG}"

# ── 3. Vytvoř GitHub release ──────────────────────────────────────────────────
echo "▶ Vytvářím GitHub release..."
gh release create "${TAG}" \
  --title "${TAG}" \
  --notes "Release ${TAG}" \
  --repo "${REPO}"

# ── 4. Stáhni tar.gz a spočítej SHA256 ───────────────────────────────────────
echo "▶ Stahuji tarball..."
TMP_TAR=$(mktemp /tmp/cj-release-XXXXXX.tar.gz)
curl -fsSL "${TARBALL_URL}" -o "${TMP_TAR}"

SHA256=$(shasum -a 256 "${TMP_TAR}" | awk '{print $1}')
rm "${TMP_TAR}"

echo "   SHA256: ${SHA256}"

# ── 5. Uprav Formuli ──────────────────────────────────────────────────────────
echo "▶ Aktualizuji ${FORMULA}..."

# Nahraď url řádek
sed -i '' "s|url \"https://github.com/${REPO}/archive/refs/tags/v[^\"]*\.tar\.gz\"|url \"${TARBALL_URL}\"|" "${FORMULA}"

# Nahraď sha256 řádek
sed -i '' "s|sha256 \"[a-f0-9]*\"|sha256 \"${SHA256}\"|" "${FORMULA}"

echo "   Nová URL:    ${TARBALL_URL}"
echo "   Nový SHA256: ${SHA256}"

# ── 6. Commitni a pushni ──────────────────────────────────────────────────────
echo "▶ Commituju a pushuju formuli..."
git add "${FORMULA}"
git commit -m "Release ${TAG}: update Homebrew formula"
git push origin main

echo ""
echo "✓ Hotovo! Release ${TAG} je na GitHubu."
echo "  https://github.com/${REPO}/releases/tag/${TAG}"
