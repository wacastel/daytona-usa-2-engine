#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d 'build/Daytona USA 2.app' ]]; then
    scripts/build.sh
fi
open 'build/Daytona USA 2.app'
