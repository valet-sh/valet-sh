#!/bin/bash
cd "$(dirname "$0")"
cd ../..
mvn clean install -T 8C -PautoInstallSinglePackage -Daem.port=4502
