#!/bin/bash
set -e

generator="datamodel-code-generator"

# Check for datamodel-codegen and install if missing
if ! pip show $generator > /dev/null 2>&1; then
    echo "$generator not found. Installing..."
    pip install $generator
else
    echo "$generator is already installed."
fi

# Check for yapf and install if missing
if ! pip show yapf > /dev/null 2>&1; then
    echo "yapf not found. Installing..."
    pip install yapf
else
    echo "yapf is already installed."
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="db"
DST_DIR="../runtime/shared"

mkdir -p "$DST_DIR"

for schema in $SRC_DIR/*.schema.json; do
    base=$(basename "$schema" .schema.json)
    out="$DST_DIR/models_${base}.py"
    echo "Generating $out from $schema..."
    datamodel-codegen \
        --input "$schema" \
        --input-file-type jsonschema \
        --output "$out" \
        --strict-types int float bool str \
        --field-constraints \

    # Remove any line containing 'timestamp' in the first 3 lines only
awk 'NR<=3 {if (tolower($0) !~ /timestamp:/) print; next} 1' "$out" > "${out}.tmp" && mv "${out}.tmp" "$out"

    # Format with yapf
    yapf -i "$out"
done

echo "All Pydantic models generated, timestamps removed, and formatted!"
