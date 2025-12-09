<#
Save Vibe session helper

Purpose:
  Save the current VibeCoding chat contents to a local file under `.vibe/sessions`.
  The script supports interactive editing or reading from clipboard/stdin and can
  optionally `git add` + `git commit` the saved file when `-commit` is provided.

Usage examples:
  # Interactive (opens Notepad or $env:EDITOR). Use ExecutionPolicy bypass if needed:
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\save-vibe.ps1

  # Save text from clipboard (non-interactive):
  Get-Clipboard | .\tools\save-vibe.ps1

  # Save from clipboard and commit to the current branch:
  Get-Clipboard | .\tools\save-vibe.ps1 -commit

Notes:
  - On Windows the script prefers `Get-Clipboard` to avoid encoding issues.
  - If script execution is restricted, run the script with `-ExecutionPolicy Bypass`
    or set CurrentUser ExecutionPolicy to `RemoteSigned`.
  - Files are written as UTF-8 with BOM so Notepad shows them correctly.
  - `.vibe/` is added to `.gitignore` by default. Use `-commit` only if you intend
    to record the session in the branch (be cautious with secrets).
  - To enable pre-push checking, copy `tools/git-hooks/pre-push` to `.git/hooks/pre-push`.

  Vibe セッション保存スクリプト (日本語説明)
  
  目的:
    VibeCoding のチャット内容をローカルの `.vibe/sessions` 配下に保存します。
    インタラクティブ編集（エディタで貼り付け）またはクリップボード/stdin からの
    取り込みをサポートし、`-commit` を付けると自動で `git add`+`git commit` します。
  
  使い方例:
    # インタラクティブ（Notepad または $env:EDITOR を起動）:
    # Copilot Chat windowでCopy Allしてから実行するとcurrent branch名で.vive/sessionsにmdファイルが保存される
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\save-vibe.ps1
  
    # クリップボードから保存（非対話）:
    Get-Clipboard | .\tools\save-vibe.ps1
  
    # クリップボードから保存して現在のブランチにコミット:
    Get-Clipboard | .\tools\save-vibe.ps1 -commit
  
  注意事項:
    - Windows ではパイプ経由の文字コード不一致を避けるため `Get-Clipboard` を優先します。
    - スクリプト実行が制限されている場合は、一時的に `-ExecutionPolicy Bypass` を使うか、
      `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` を検討してください。
    - ファイルは UTF-8 (BOM付き) で書き出すため、Windows のメモ帳でも文字化けしにくくしています。
    - デフォルトで `.vibe/` は `.gitignore` に追加されています。ブランチに履歴を残す場合のみ
      `-commit` を使ってください（シークレットに注意）。
    - pre-push フックを有効にするには `tools/git-hooks/pre-push` を `.git/hooks/pre-push` にコピーしてください。
#>

param(
  [string]$message,
  [switch]$commit,
  [string]$prefix = ''
)

# Try to resolve repo root; fall back to current dir
$root = ""
try { $root = (git rev-parse --show-toplevel 2>$null) } catch { }
if (-not $root) { $root = (Get-Location).Path }
Set-Location $root

if (-not $message) {
  # If input is redirected (piped), read stdin. Otherwise open editor interactively.
  # Determine whether input is redirected (piped). If so, read stdin;
  # otherwise open a temporary file in the user's editor for interactive paste.
  $isRedirected = [Console]::IsInputRedirected
  if ($isRedirected) {
    $message = [Console]::In.ReadToEnd()
  } else {
    # If no piped input, try the clipboard (Windows PowerShell provides Get-Clipboard).
    # This makes running as a VS Code task (without explicit piping) work with clipboard workflow.
    $clipboardText = $null
    try {
      $clipboardText = Get-Clipboard -Raw
    } catch {
      # Get-Clipboard may not exist in some environments; ignore error and fall back to editor
      $clipboardText = $null
    }

    if ($clipboardText -and $clipboardText.Trim().Length -gt 0) {
      $message = $clipboardText
    } else {
      # No clipboard content — open a temp file in the editor for interactive paste
      $tmp = [System.IO.Path]::GetTempFileName()
      if ($env:EDITOR) {
        & $env:EDITOR $tmp
      } elseif ($env:OS -eq 'Windows_NT') {
        # Windows fallback
        notepad $tmp
      } else {
        # Unix-like fallback
        vi $tmp
      }
      $message = Get-Content $tmp -Raw
      Remove-Item $tmp -ErrorAction SilentlyContinue
    }
  }
}

if (-not $message) {
  Write-Error "No message provided. Use -message or pipe input."
  exit 1
}


# Compute target path early so interactive editor opens the real target file (avoids temp-file race)
$branch = (git rev-parse --abbrev-ref HEAD) -replace '/', '-'
$ts = (Get-Date).ToString('yyyyMMdd-HHmmss')
$dir = Join-Path $root '.vibe\sessions'
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

$filename = '{0}{1}-{2}.md' -f $prefix, $branch, $ts
$path = Join-Path $dir $filename

# If still no message and input is not redirected, open the target file in an editor for interactive paste/save
if (-not $message) {
  $header = @()
  $header += "# Vibe session - write your notes and save/close the editor"
  $header += ""
  $header += "Branch: $branch"
  $header += ""
  $header -join "`n" | Out-File -FilePath $path -Encoding UTF8

  # Launch editor and WAIT for it to exit so the script doesn't continue early.
  if ($env:EDITOR) {
    try {
      Start-Process -FilePath $env:EDITOR -ArgumentList $path -Wait -ErrorAction Stop
    } catch {
      # Fallback to invoking directly (works for terminal editors)
      & $env:EDITOR $path
    }
  } elseif ($env:OS -eq 'Windows_NT') {
    # Use Start-Process -Wait so PowerShell waits for Notepad to close
    Start-Process -FilePath 'notepad.exe' -ArgumentList $path -Wait
  } else {
    vi $path
  }

  # After editor closes, read the file content
  $message = Get-Content $path -Raw

  # If the user saved nothing (only header remained), offer to re-open the editor up to 3 times
  $minLength = 20
  $attempt = 0
  while (($message.Trim().Length -lt $minLength) -and ($attempt -lt 3)) {
    $attempt++
    Write-Host "The saved file looks empty or too short. Did you paste and save correctly?"
    $resp = Read-Host "Re-open editor to try again? (Y/n)"
    if ($resp -eq 'n' -or $resp -eq 'N') { break }

    # Re-open editor and wait
    if ($env:EDITOR) {
      try {
        Start-Process -FilePath $env:EDITOR -ArgumentList $path -Wait -ErrorAction Stop
      } catch {
        & $env:EDITOR $path
      }
    } elseif ($env:OS -eq 'Windows_NT') {
      Start-Process -FilePath 'notepad.exe' -ArgumentList $path -Wait
    } else {
      vi $path
    }

    $message = Get-Content $path -Raw
  }
}


$content = @()
$content += "# Vibe session saved on $((Get-Date).ToString())"
$content += ""
$content += "Branch: $branch"
$content += ""
$content += $message


$contentString = $content -join "`n"
# Write with BOM-enabled UTF8 so Notepad detects encoding correctly on Windows
[System.IO.File]::WriteAllText($path, $contentString, [System.Text.Encoding]::UTF8)

Write-Output "Saved to $path"

if ($commit) {
  git add $path
  $commitMsg = "vibe: save session $branch $ts"
  # Use PowerShell-compatible error handling for external git command
  & git commit -m $commitMsg 2>$null
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "Commit failed or nothing to commit"
  } else {
    Write-Output "Committed session file"
  }
}
