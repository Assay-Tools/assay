#!/bin/bash
# run-session.sh — Launch a Claude Code session with a prompt file
# Usage: run-session.sh <prompt-file> [model]
#
# Designed to be called by launchd for unattended overnight work.

set -euo pipefail

# Ensure we're not blocked by nested session detection
unset CLAUDECODE 2>/dev/null || true

PROMPT_FILE="$1"
MODEL="${2:-sonnet}"  # Default to sonnet for cost efficiency
LOG_DIR="$HOME/git/assay/logs"
WORK_DIR="$HOME/git/assay"
TIMESTAMP=$(date +"%Y-%m-%d_%H%M")

mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/session-${TIMESTAMP}.log"

echo "=== Assay Overnight Session ===" > "$LOG_FILE"
echo "Started: $(date)" >> "$LOG_FILE"
echo "Prompt: $PROMPT_FILE" >> "$LOG_FILE"
echo "Model: $MODEL" >> "$LOG_FILE"
echo "===" >> "$LOG_FILE"

# Read prompt from file
PROMPT=$(cat "$PROMPT_FILE")

# Run claude in print mode (non-interactive), bypass permissions for autonomous work
cd "$WORK_DIR"
/Users/aj/.local/bin/claude \
  -p "$PROMPT" \
  --model "$MODEL" \
  --dangerously-skip-permissions \
  --verbose \
  2>&1 | tee -a "$LOG_FILE"

echo "" >> "$LOG_FILE"
echo "=== Session Complete ===" >> "$LOG_FILE"
echo "Ended: $(date)" >> "$LOG_FILE"
