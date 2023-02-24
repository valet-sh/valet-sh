#!/bin/bash
cd "$(dirname "$0")"
cd ../..
mvn clean install -T 8C -DskipTests -Dmaven.test.skip -Dmaven.javadoc.skip=true -pl -it.tests,-ui.tests -P autoInstallSinglePackage -Daem.port=4503
