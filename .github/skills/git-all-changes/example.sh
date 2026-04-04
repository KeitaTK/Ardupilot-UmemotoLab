#!/bin/bash
# git-all-changes スキルの自動化例
# 全ての変更をadd/commit/push

COMMIT_MSG=${1:-"replay: add all changes (auto skill)"}

git add .
git commit -m "$COMMIT_MSG"
git push
