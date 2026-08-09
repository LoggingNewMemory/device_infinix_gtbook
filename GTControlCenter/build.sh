#!/bin/bash
cd "$(dirname "$0")"

VERSION="3.0.0"
DIST_NAME="gt-controlcenter-linux-installer-$VERSION"
DIST_DIR="dist/$DIST_NAME"

echo "Cleaning previous builds..."
rm -rf dist/
mkdir -p "$DIST_DIR"

echo "Copying files to distribution folder..."
cp -r assets controlcenter "$DIST_DIR/"
cp run_app.py 99-byd-keyboard.rules acpi-call-perms.service install.sh uninstall.sh "$DIST_DIR/"

echo "Creating tarball..."
cd dist
tar -czvf "$DIST_NAME.tar.gz" "$DIST_NAME"
cd ..

echo "----------------------------------------"
echo "Build complete!"
echo "Installer archive is at: dist/$DIST_NAME.tar.gz"
echo "Distribute this lightweight .tar.gz file to your users."
