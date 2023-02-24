#!/bin/bash
cd "$(dirname "$0")"
cd ../..
cd ui.apps
mvn clean install -T 8C -DskipTests -Dmaven.test.skip -Dmaven.javadoc.skip=true -P autoInstallPackage -Daem.port=4503
