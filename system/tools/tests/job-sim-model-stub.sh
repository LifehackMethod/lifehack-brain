#!/usr/bin/env bash
# job-sim-model-stub.sh — TEST-ONLY stand-in for `claude`, used via LIFEHACK_MODEL_STUB (model.lib.sh).
# Called as: <this> <model-id> <prompt-file> <out-file>. Mode file $JOB_SIM_DIR/model-mode: empty | ok.
set -u
case "$(cat "${JOB_SIM_DIR:?}/model-mode" 2>/dev/null || echo ok)" in
  empty) : > "$3" ;;
  *) printf 'reply from %s MARK\n' "$1" > "$3" ;;
esac
