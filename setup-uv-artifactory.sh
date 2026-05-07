#!/bin/bash
# setup-uv-artifactory.sh
# Helper script to configure uv with Artifactory

set -e

echo "=== Coding Agent - uv + Artifactory Setup ==="
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "ERROR: uv is not installed."
    echo "Install it with:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "[1/4] Checking uv installation..."
uv --version

echo ""
echo "[2/4] Enter your Artifactory details:"
read -p "  Organization URL (e.g., myorg.jfrog.io): " ORG_URL
read -p "  Repository name (e.g., pypi-virtual): " REPO_NAME
read -p "  Username (leave empty for JWT token): " USERNAME

echo ""
if [ -z "$USERNAME" ]; then
    read -p "  JWT Token: " JWT_TOKEN
    echo ""
    echo "Setting up JWT authentication..."
    export UV_INDEX_ARTIFACTORY_USERNAME=""
    export UV_INDEX_ARTIFACTORY_PASSWORD="$JWT_TOKEN"
    AUTH_PART=""
else
    read -sp "  Password/API Key: " PASSWORD
    echo ""
    export UV_INDEX_ARTIFACTORY_USERNAME="$USERNAME"
    export UV_INDEX_ARTIFACTORY_PASSWORD="$PASSWORD"
    AUTH_PART="${USERNAME}:${PASSWORD}@"
fi

ARTIFACTORY_URL="https://${AUTH_PART}${ORG_URL}/artifactory/api/pypi/${REPO_NAME}/simple"

echo ""
echo "[3/4] Updating pyproject.toml with Artifactory index..."

# Add the index to pyproject.toml (commented, user needs to uncomment)
if ! grep -q "artifactory" pyproject.toml 2>/dev/null; then
    cat >> pyproject.toml <<EOF

# Uncomment to use Artifactory as the default index
# [[tool.uv.index]]
# name = "artifactory"
# url = "https://${ORG_URL}/artifactory/api/pypi/${REPO_NAME}/simple"
# default = true
EOF
    echo "  Added template to pyproject.toml (commented out)"
else
    echo "  pyproject.toml already has Artifactory configuration"
fi

echo ""
echo "[4/4] Creating uv.toml.example with your settings..."

cat > uv.toml.example <<EOF
[[index]]
name = "artifactory"
url = "https://${ORG_URL}/artifactory/api/pypi/${REPO_NAME}/simple"
default = true
EOF

echo "  Created uv.toml.example"

echo ""
echo "=== Next Steps ==="
echo "1. Add credentials to your shell config (~/.zshrc or ~/.bashrc):"
echo "     export UV_INDEX_ARTIFACTORY_USERNAME=\"$USERNAME\""
if [ -z "$USERNAME" ]; then
    echo "     export UV_INDEX_ARTIFACTORY_PASSWORD=\"\$JWT_TOKEN\""
else
    echo "     export UV_INDEX_ARTIFACTORY_PASSWORD=\"your-password\""
fi
echo ""
echo "2. Uncomment the [[tool.uv.index]] section in pyproject.toml"
echo ""
echo "3. Run: uv sync --group dev"
echo ""
echo "4. Verify with: uv run python -c \"import langchain; print('Success!')\""
echo ""
echo "=== Setup complete! ==="
