#!/bin/bash

set -e
# Trap any error and print FAILED
trap 'echo""; echo "ERROR! CHECK ABOVE FOR DETAILS"; exit 1' ERR

echo "Building React frontend..."
cd ui
npm ci
CI=true npm run build

echo "Copying static files to package..."
cd ..
rm -rf sourcetext/server/static
cp -r ui/dist sourcetext/server/static

echo "Building Python package..."
rm -rf dist/
python -m build

echo "Verifying Python package..."
twine check dist/*
echo "Checking frontend in package..."
python -m zipfile -l dist/*.whl | grep -q "server/static/index.html"

echo ""
echo "SUCCESS! All done!"