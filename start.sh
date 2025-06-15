#!/bin/bash
export SESSION_SECRET="0b0cfe14f5349b3d9df3573b6e88dfa8d642674f770eeb16b30aae2a9d8a7bd3"
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app