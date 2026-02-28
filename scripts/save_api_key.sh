#!/usr/bin/env bash
# 安全保存并加载 LLM API Key 的本地脚本（不会将密钥提交到仓库）
# 用法示例：
#   ./scripts/save_api_key.sh --write-from-arg "sk-..."
#   ./scripts/save_api_key.sh --write  # 从交互式提示输入
#   ./scripts/save_api_key.sh --print  # 显示当前已存（仅用于确认，慎用）

set -euo pipefail
SECRETS_FILE="$HOME/.longtext_secrets"

usage() {
  cat <<-'USAGE'
Usage:
  save_api_key.sh --write-from-arg <API_KEY>  # 从参数写入密钥
  save_api_key.sh --write                     # 交互式提示输入并写入
  save_api_key.sh --print                     # 仅打印当前存储的非空变量名（不打印值）
  save_api_key.sh --help

This script stores the API key at $HOME/.longtext_secrets with mode 600.
It will not add the key to the repository. Keep this file private.
USAGE
}

write_key() {
  local key="$1"
  mkdir -p "$(dirname "$SECRETS_FILE")"
  # 使用临时文件写入，随后设置权限并原子移动
  local tmp
  tmp="$(mktemp)"
  printf "# Local secrets for long_text_agent\nLLM_API_KEY=%s\n" "$key" > "$tmp"
  chmod 600 "$tmp"
  mv "$tmp" "$SECRETS_FILE"
  echo "Saved secrets to $SECRETS_FILE (mode 600)."
}

interactive_write() {
  echo -n "Enter LLM API Key (will not be echoed): "
  # readline not used to avoid leaving in shell history
  read -rs key
  echo
  if [ -z "$key" ]; then
    echo "Empty key; aborting." >&2
    exit 2
  fi
  write_key "$key"
}

print_info() {
  if [ -f "$SECRETS_FILE" ]; then
    echo "$SECRETS_FILE exists. Contents not shown for safety. To use it, run:"
    echo "  export \\$(grep -v '^#' $SECRETS_FILE | xargs)"
  else
    echo "$SECRETS_FILE not found."
  fi
}

if [ "$#" -eq 0 ]; then
  usage
  exit 1
fi

case "$1" in
  --write-from-arg)
    if [ "$#" -ne 2 ]; then
      echo "Missing API key argument" >&2
      usage
      exit 2
    fi
    write_key "$2"
    ;;
  --write)
    interactive_write
    ;;
  --print)
    print_info
    ;;
  --help|-h)
    usage
    ;;
  *)
    usage
    exit 2
    ;;
esac
