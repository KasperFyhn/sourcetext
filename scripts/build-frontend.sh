#!/bin/bash
# Quick frontend rebuild for testing the production build locally

set -e

cd ui
npm run build
cd ..
rm -rf sourcetext/server/static
cp -r ui/dist sourcetext/server/static
echo "✓ Frontend rebuilt and copied to sourcetext/server/static/"