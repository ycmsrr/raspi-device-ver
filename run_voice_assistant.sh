#!/usr/bin/env bash
# run_voice_assistant.sh

# 1. 指定要跑在哪个 X Display
export DISPLAY=:0
export XAUTHORITY=/home/student/.Xauthority

# 2. 激活虚拟环境（如果有）
source /home/student/gpt4all-env/bin/activate

# 3. 运行你的 GUI 程序
exec python3 /home/student/gpt4all-cli/gui_voice_llm.py
