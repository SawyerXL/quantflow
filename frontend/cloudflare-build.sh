#!/bin/sh
set -e
echo "Building Next.js..."
next build
echo "Cleaning webpack cache..."
rm -rf .next/cache/webpack
echo "Build complete — cache cleaned"
