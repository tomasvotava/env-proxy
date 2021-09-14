#!/bin/bash

rm -rf ./docs
pdoc3 --html -o ./docs/ env_proxy
mv ./docs/env_proxy.html ./docs/index.html
