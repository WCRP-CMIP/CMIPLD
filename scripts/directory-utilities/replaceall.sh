#!/bin/bash

perl -pi -e 's/MIP-universe/MIP-universe/g' $(find . -type f)

# no binary
# find . -type f -exec grep -Iq . {} \; -and -exec perl -pi -e 's/MIP-UNIVERSE/MIP-universe/g' {} +
