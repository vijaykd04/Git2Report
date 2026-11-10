"""Interactive Terminal-Style Web GUI for Git2Report.

Provides an authentic CLI / Hacker terminal experience in the browser to configure,
execute, stream live logs, preview, and download engineering progress reports.
"""
from __future__ import annotations

import json
import logging
import mimetypes
import os
import subprocess
import threading
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from git2report.cache import default_cache
from git2report.models import GitReportError
from git2report.pipeline import Options, run_pipeline
from git2report.report import render_html, render_markdown, render_pdf
from git2report.summarizer import get_summarizer
from git2report.timeutil import parse_since

logger = logging.getLogger("git2report.web")


def discover_local_repos() -> list[dict[str, str]]:
    """Scan current folder and cloned_repos/ for existing Git repositories."""
    repos = []
    seen = set()

    def check(p: Path, label: str):
        resolved = str(p.resolve())
        if resolved not in seen and (p / ".git").exists():
            seen.add(resolved)
            repos.append({"path": str(p).replace("\\", "/"), "name": label})

    # Current directory
    check(Path("."), "Current Repo (.)")

    # Cloned repos
    cloned_dir = Path("cloned_repos")
    if cloned_dir.exists():
        for sub in cloned_dir.iterdir():
            if sub.is_dir():
                check(sub, f"cloned_repos/{sub.name}")

    # Parent directory check
    parent = Path("..")
    if parent.exists():
        for sub in parent.iterdir():
            if sub.is_dir() and sub.name != "git2report":
                check(sub, f"../{sub.name}")

    return repos


TERMINAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>git2report@terminal: ~</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&display=swap" rel="stylesheet">
  <style>
    :root {
      --term-bg: #0B0E14;
      --term-card: #0F131D;
      --term-border: #1E2638;
      --term-border-glow: #00ff8833;
      --text-main: #E2E8F0;
      --text-muted: #64748B;
      --prompt-user: #00FF88;
      --prompt-host: #38BDF8;
      --prompt-path: #FACC15;
      --prompt-symbol: #EC4899;
      --accent-green: #00FF88;
      --accent-cyan: #38BDF8;
      --accent-yellow: #FACC15;
      --accent-red: #EF4444;
      --accent-purple: #A855F7;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    
    body {
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      background-color: #05070A;
      background-image: 
        radial-gradient(ellipse at 50% 0%, rgba(14, 165, 233, 0.08) 0%, transparent 60%),
        linear-gradient(rgba(255, 255, 255, 0.015) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.015) 1px, transparent 1px);
      background-size: 100% 100%, 32px 32px, 32px 32px;
      color: var(--text-main);
      min-height: 100vh;
      padding: 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .term-window {
      width: 100%;
      max-width: 1360px;
      background: var(--term-bg);
      border: 1px solid var(--term-border);
      border-radius: 12px;
      box-shadow: 0 12px 48px rgba(0, 0, 0, 0.8), 0 0 1px 1px var(--term-border);
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    /* Top Title Bar */
    .title-bar {
      background: #090C12;
      border-bottom: 1px solid var(--term-border);
      padding: 10px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      user-select: none;
    }

    .window-controls {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .win-dot {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      display: inline-block;
    }

    .dot-close { background: #FF5F56; border: 1px solid #E0443E; }
    .dot-min { background: #FFBD2E; border: 1px solid #DEA123; }
    .dot-max { background: #27C93F; border: 1px solid #1AAB29; }

    .window-title {
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
      letter-spacing: 0.05em;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .session-badge {
      font-size: 0.7rem;
      background: rgba(0, 255, 136, 0.1);
      border: 1px solid rgba(0, 255, 136, 0.3);
      color: var(--accent-green);
      padding: 2px 8px;
      border-radius: 4px;
      font-weight: 600;
    }

    /* Terminal Body Content */
    .term-content {
      padding: 20px 24px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    /* ASCII Banner */
    .ascii-banner {
      color: var(--accent-green);
      font-size: 0.7rem;
      line-height: 1.15;
      white-space: pre;
      user-select: none;
      overflow-x: auto;
      text-shadow: 0 0 10px rgba(0, 255, 136, 0.3);
    }

    /* Prompt line */
    .cli-bar {
      background: var(--term-card);
      border: 1px solid var(--term-border);
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 0.88rem;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }

    .prompt-label {
      display: flex;
      align-items: center;
      gap: 2px;
      font-weight: 700;
    }
    .p-user { color: var(--prompt-user); }
    .p-at { color: var(--text-muted); }
    .p-host { color: var(--prompt-host); }
    .p-colon { color: var(--text-muted); }
    .p-path { color: var(--prompt-path); }
    .p-dollar { color: var(--prompt-symbol); margin-left: 4px; }

    .command-display {
      color: #FFFFFF;
      font-weight: 600;
      flex: 1;
      min-width: 250px;
      word-break: break-all;
    }

    .cursor-blink {
      display: inline-block;
      width: 8px;
      height: 15px;
      background: var(--accent-green);
      animation: blink 1s step-start infinite;
      vertical-align: middle;
      margin-left: 2px;
    }

    @keyframes blink {
      50% { opacity: 0; }
    }

    /* Quick Action Shortcuts */
    .quick-actions {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      font-size: 0.78rem;
    }

    .qa-title {
      color: var(--text-muted);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .btn-qa {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--term-border);
      color: var(--accent-cyan);
      padding: 5px 10px;
      border-radius: 6px;
      font-family: inherit;
      font-size: 0.75rem;
      cursor: pointer;
      transition: all 0.15s;
    }

    .btn-qa:hover {
      background: rgba(56, 189, 248, 0.15);
      border-color: var(--accent-cyan);
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.2);
    }

    .btn-qa.danger {
      color: var(--accent-red);
    }
    .btn-qa.danger:hover {
      background: rgba(239, 68, 68, 0.15);
      border-color: var(--accent-red);
    }

    /* Split Workspace Grid */
    .workspace-grid {
      display: grid;
      grid-template-columns: 460px 1fr;
      gap: 20px;
    }

    @media (max-width: 1024px) {
      .workspace-grid { grid-template-columns: 1fr; }
    }

    .terminal-pane {
      background: var(--term-card);
      border: 1px solid var(--term-border);
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .pane-header {
      background: #090C12;
      padding: 10px 14px;
      border-bottom: 1px solid var(--term-border);
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--accent-cyan);
      display: flex;
      align-items: center;
      justify-content: space-between;
      letter-spacing: 0.05em;
    }

    .pane-body {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    /* Terminal Fields */
    .arg-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .arg-label {
      font-size: 0.78rem;
      color: var(--accent-yellow);
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .arg-desc {
      font-size: 0.7rem;
      color: var(--text-muted);
      margin-left: 4px;
    }

    .term-input, .term-select {
      background: #06090F;
      border: 1px solid var(--term-border);
      color: #FFFFFF;
      padding: 8px 12px;
      border-radius: 6px;
      font-family: inherit;
      font-size: 0.85rem;
      outline: none;
      transition: all 0.2s;
      width: 100%;
    }

    .term-input:focus, .term-select:focus {
      border-color: var(--accent-green);
      box-shadow: 0 0 0 1px var(--accent-green), 0 0 10px rgba(0, 255, 136, 0.15);
    }

    .preset-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 2px;
    }

    .p-pill {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--term-border);
      color: var(--text-muted);
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.72rem;
      cursor: pointer;
      transition: all 0.15s;
    }

    .p-pill:hover, .p-pill.active {
      background: rgba(0, 255, 136, 0.15);
      border-color: var(--accent-green);
      color: var(--accent-green);
    }

    .checkbox-row {
      display: flex;
      gap: 16px;
      background: #06090F;
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid var(--term-border);
      font-size: 0.8rem;
    }

    .checkbox-item {
      display: flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      color: var(--text-main);
    }

    .btn-exec {
      background: linear-gradient(135deg, #00FF88 0%, #10B981 100%);
      color: #05070A;
      border: none;
      padding: 12px;
      border-radius: 6px;
      font-family: inherit;
      font-size: 0.88rem;
      font-weight: 800;
      letter-spacing: 0.05em;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      box-shadow: 0 4px 16px rgba(0, 255, 136, 0.3);
      transition: all 0.2s;
    }

    .btn-exec:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 6px 24px rgba(0, 255, 136, 0.5);
    }

    .btn-exec:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    /* Output Stream Section */
    .stream-box {
      background: #06090F;
      border: 1px solid var(--term-border);
      border-radius: 6px;
      padding: 14px;
      font-size: 0.8rem;
      height: 220px;
      overflow-y: auto;
      white-space: pre-wrap;
      color: #94A3B8;
      line-height: 1.5;
    }

    .stream-line {
      display: block;
      margin-bottom: 2px;
    }

    .stream-line.info { color: var(--accent-cyan); }
    .stream-line.success { color: var(--accent-green); font-weight: 700; }
    .stream-line.error { color: var(--accent-red); font-weight: 700; }

    /* ASCII KPI Table */
    .ascii-kpi-card {
      background: #06090F;
      border: 1px solid var(--term-border);
      border-radius: 6px;
      padding: 12px 14px;
      font-size: 0.8rem;
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
    }

    @media (max-width: 768px) {
      .ascii-kpi-card { grid-template-columns: repeat(2, 1fr); }
    }

    .kpi-unit-title {
      font-size: 0.68rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    .kpi-unit-val {
      font-size: 1.2rem;
      font-weight: 700;
      color: #FFFFFF;
      margin-top: 2px;
    }

    /* Downloads Bar */
    .term-export-bar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      background: #06090F;
      border: 1px solid var(--term-border);
      border-radius: 6px;
      padding: 10px 14px;
    }

    .export-btns {
      display: flex;
      gap: 8px;
    }

    .btn-export {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--term-border);
      color: var(--accent-green);
      padding: 6px 12px;
      border-radius: 5px;
      font-family: inherit;
      font-size: 0.78rem;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
    }

    .btn-export:hover {
      background: rgba(0, 255, 136, 0.15);
      border-color: var(--accent-green);
      box-shadow: 0 0 10px rgba(0, 255, 136, 0.2);
    }

    .btn-export.secondary {
      color: var(--accent-cyan);
    }
    .btn-export.secondary:hover {
      background: rgba(56, 189, 248, 0.15);
      border-color: var(--accent-cyan);
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.2);
    }

    /* Preview Frame */
    .preview-container {
      width: 100%;
      height: 520px;
      background: white;
      border: 1px solid var(--term-border);
      border-radius: 6px;
      overflow: hidden;
    }

    .preview-frame {
      width: 100%;
      height: 100%;
      border: none;
    }

    .tab-bar {
      display: flex;
      gap: 6px;
      border-bottom: 1px solid var(--term-border);
      padding: 0 12px;
      background: #090C12;
    }

    .t-tab {
      background: transparent;
      border: none;
      border-bottom: 2px solid transparent;
      color: var(--text-muted);
      padding: 8px 12px;
      font-family: inherit;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
    }

    .t-tab.active {
      color: var(--accent-green);
      border-bottom-color: var(--accent-green);
    }
  </style>
</head>
<body>

  <div class="term-window">
    <!-- Top macOS / Linux Window Bar -->
    <div class="title-bar">
      <div class="window-controls">
        <span class="win-dot dot-close"></span>
        <span class="win-dot dot-min"></span>
        <span class="win-dot dot-max"></span>
      </div>
      <div class="window-title">
        <span>terminal@git2report: ~ (pts/0 - zsh)</span>
      </div>
      <div class="session-badge">
        <span>● DAEMON ACTIVE</span>
      </div>
    </div>

    <div class="term-content">
      <!-- ASCII Header Art -->
      <pre class="ascii-banner">
  ██████╗ ██╗████████╗██████╗ ██████╗ ███████╗██████╗  ██████╗ ██████╗ ████████╗
 ██╔════╝ ██║╚══██╔══╝╚════██╗██╔══██╗██╔════╝██╔══██╗██╔═══██╗██╔══██╗╚══██╔══╝
 ██║  ███╗██║   ██║    █████╔╝██████╔╝█████╗  ██████╔╝██║   ██║██████╔╝   ██║   
 ██║   ██║██║   ██║   ██╔═══╝ ██╔══██╗██╔══╝  ██╔═══╝ ██║   ██║██╔══██╗   ██║   
 ╚██████╔╝██║   ██║   ███████╗██║  ██║███████╗██║     ╚██████╔╝██║  ██║   ██║   
  ╚═════╝ ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝      ╚═════╝ ╚═╝  ╚═╝   ╚═╝   
       [ v0.1.0 :: AUTONOMOUS EVIDENCE-LINKED REPOSITORY REPORTING SYSTEM ]
      </pre>

      <!-- Dynamic CLI Command Line -->
      <div class="cli-bar">
        <div class="prompt-label">
          <span class="p-user">root</span><span class="p-at">@</span><span class="p-host">git2report</span><span class="p-colon">:</span><span class="p-path">~</span><span class="p-dollar">$</span>
        </div>
        <div class="command-display" id="commandPreview">
          git2report --repo cloned_repos/CampusThrift --since 2025-01-01 --audience guide --llm gemini --all
        </div>
        <span class="cursor-blink"></span>
      </div>

      <!-- Quick Command Shortcuts -->
      <div class="quick-actions">
        <span class="qa-title">Presets:</span>
        <button type="button" class="btn-qa" onclick="loadPreset('campusthrift')">[$ CAMPUS THRIFT (FULL)]</button>
        <button type="button" class="btn-qa" onclick="loadPreset('current')">[$ CURRENT REPO (.)]</button>
        <button type="button" class="btn-qa" onclick="loadPreset('offline')">[$ FAST OFFLINE MODE]</button>
        <button type="button" class="btn-qa danger" onclick="clearCache()">[$ CLEAR CACHE]</button>
      </div>

      <!-- Main Workspace Grid -->
      <div class="workspace-grid">
        <!-- LEFT PANE: CONFIGURATION & COMMAND PROMPT -->
        <div class="terminal-pane">
          <div class="pane-header">
            <span>[1] CLI FLAGS &amp; PARAMETERS</span>
            <span style="color: var(--text-muted);">STDIN</span>
          </div>

          <form id="termForm" class="pane-body" onsubmit="executeRun(event)">
            <!-- Target Repo -->
            <div class="arg-group">
              <label class="arg-label" for="repoInput">
                <span>--repo, -r</span>
                <span class="arg-desc">&lt;path or github url&gt;</span>
              </label>
              <input type="text" id="repoInput" class="term-input" value="cloned_repos/CampusThrift" oninput="updateCliPreview()" required>
              <div class="preset-pills" id="discoveredReposPills">
                <!-- Dynamically populated -->
              </div>
            </div>

            <!-- Time Window -->
            <div class="arg-group">
              <label class="arg-label" for="sinceInput">
                <span>--since, -s</span>
                <span class="arg-desc">&lt;7d | 14d | 30d | YYYY-MM-DD&gt;</span>
              </label>
              <input type="text" id="sinceInput" class="term-input" value="2025-01-01" oninput="updateCliPreview()" required>
              <div class="preset-pills">
                <span class="p-pill" onclick="setSinceVal('7d')">7d</span>
                <span class="p-pill" onclick="setSinceVal('14d')">14d</span>
                <span class="p-pill" onclick="setSinceVal('30d')">30d</span>
                <span class="p-pill active" onclick="setSinceVal('2025-01-01')">2025-01-01 (All)</span>
              </div>
            </div>

            <!-- Audience Persona -->
            <div class="arg-group">
              <label class="arg-label" for="audienceSelect">
                <span>--audience, -a</span>
                <span class="arg-desc">&lt;guide | client | team&gt;</span>
              </label>
              <select id="audienceSelect" class="term-select" onchange="updateCliPreview()">
                <option value="guide" selected>guide (Academic &amp; Architecture)</option>
                <option value="client">client (Business &amp; User-Facing)</option>
                <option value="team">team (Release-Notes Technical)</option>
              </select>
            </div>

            <!-- AI Engine -->
            <div class="arg-group">
              <label class="arg-label" for="llmSelect">
                <span>--llm</span>
                <span class="arg-desc">&lt;gemini | ollama | offline&gt;</span>
              </label>
              <select id="llmSelect" class="term-select" onchange="onLlmChange()">
                <option value="gemini" selected>gemini (Google Gemini + Smart Cache)</option>
                <option value="ollama">ollama (Local Private AI / Offline Model)</option>
                <option value="offline">offline (Deterministic Heuristic / Zero AI)</option>
              </select>
            </div>

            <!-- Gemini API Key Input (Shows when gemini is selected) -->
            <div class="arg-group" id="apiKeyGroup">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <label class="arg-label" for="apiKeyInput">
                  <span>--api-key</span>
                  <span class="arg-desc">&lt;gemini key&gt;</span>
                </label>
                <span id="apiKeyStatusBadge" style="font-size: 0.68rem; color: var(--text-muted);"></span>
              </div>
              <input type="password" id="apiKeyInput" class="term-input" placeholder="Paste your GEMINI_API_KEY here..." oninput="updateCliPreview()">
            </div>

            <!-- Model Selection (Shows for Ollama & Gemini) -->
            <div class="arg-group" id="modelGroup" style="display: none;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <label class="arg-label" for="modelInput">
                  <span>--model</span>
                  <span class="arg-desc" id="modelLabelDesc">&lt;model name&gt;</span>
                </label>
                <span id="ollamaStatusBadge" style="font-size: 0.68rem; color: var(--text-muted);"></span>
              </div>
              <input type="text" id="modelInput" class="term-input" value="llama3:8b" placeholder="e.g. llama3:8b, mistral, deepseek-r1:8b" oninput="updateCliPreview()">
              <div class="preset-pills" id="modelPills">
                <span class="p-pill active" onclick="setModelVal('llama3:8b')">llama3:8b</span>
                <span class="p-pill" onclick="setModelVal('llama3.2')">llama3.2</span>
                <span class="p-pill" onclick="setModelVal('mistral')">mistral</span>
                <span class="p-pill" onclick="setModelVal('deepseek-r1:8b')">deepseek-r1:8b</span>
                <span class="p-pill" onclick="setModelVal('phi4')">phi4</span>
                <span class="p-pill" onclick="setModelVal('qwen2.5')">qwen2.5</span>
              </div>
            </div>

            <!-- Planned Goals -->
            <div class="arg-group">
              <label class="arg-label" for="nextGoalInput">
                <span>--next, -n</span>
                <span class="arg-desc">&lt;optional sprint goal&gt;</span>
              </label>
              <input type="text" id="nextGoalInput" class="term-input" placeholder="e.g. Implement realtime chat" oninput="updateCliPreview()">
            </div>

            <!-- Format Switches -->
            <div class="arg-group">
              <label class="arg-label">
                <span>--formats</span>
                <span class="arg-desc">&lt;emit outputs&gt;</span>
              </label>
              <div class="checkbox-row">
                <label class="checkbox-item"><input type="checkbox" id="fmtPdf" checked> .pdf</label>
                <label class="checkbox-item"><input type="checkbox" id="fmtHtml" checked> .html</label>
                <label class="checkbox-item"><input type="checkbox" id="fmtMd" checked> .md</label>
              </div>
            </div>

            <button type="submit" id="btnExecute" class="btn-exec">
              <span>▶ RUN PIPELINE (ENTER)</span>
            </button>
          </form>
        </div>

        <!-- RIGHT PANE: LIVE TERMINAL LOGS & RESULTS -->
        <div class="terminal-pane">
          <div class="pane-header">
            <span>[2] EXECUTION CONSOLE &amp; PREVIEW</span>
            <span id="execStatus" style="color: var(--accent-green);">STDOUT: IDLE</span>
          </div>

          <div class="tab-bar">
            <button class="t-tab active" id="tabStreamBtn" onclick="switchRightTab('stream')">💻 STDOUT STREAM</button>
            <button class="t-tab" id="tabPreviewBtn" onclick="switchRightTab('preview')">👁 SPLIT PREVIEW</button>
          </div>

          <div class="pane-body">
            <!-- Terminal Output Stream -->
            <div id="viewStream">
              <div class="stream-box" id="termStream">
<span class="stream-line info">[+] Git2Report System Initialized.</span>
<span class="stream-line">[*] Ready for execution. Press [▶ RUN PIPELINE] or hit ENTER.</span>
              </div>
            </div>

            <!-- Live HTML Report Preview -->
            <div id="viewPreview" style="display: none;">
              <div class="preview-container">
                <iframe id="reportPreviewFrame" class="preview-frame"></iframe>
              </div>
            </div>

            <!-- ASCII KPI Box -->
            <div class="ascii-kpi-card" id="kpiBox" style="display: none;">
              <div>
                <div class="kpi-unit-title">Commits</div>
                <div class="kpi-unit-val" id="kpiCommits" style="color: var(--accent-cyan);">0</div>
              </div>
              <div>
                <div class="kpi-unit-title">Code Churn</div>
                <div class="kpi-unit-val" id="kpiChurn" style="color: var(--accent-green);">0</div>
              </div>
              <div>
                <div class="kpi-unit-title">Top Focus</div>
                <div class="kpi-unit-val" id="kpiTop" style="color: var(--accent-yellow); font-size: 1rem;">-</div>
              </div>
              <div>
                <div class="kpi-unit-title">Test Ratio</div>
                <div class="kpi-unit-val" id="kpiTest" style="color: var(--accent-purple);">0.0</div>
              </div>
            </div>

            <!-- Terminal Downloads Toolbar -->
            <div class="term-export-bar" id="exportBar" style="display: none;">
              <div style="font-size: 0.78rem; color: var(--accent-green); font-weight: 700;">
                [✓] PIPELINE COMPLETE :: ARTIFACTS READY
              </div>
              <div class="export-btns">
                <a id="btnPdf" href="#" class="btn-export" download>⤓ report.pdf</a>
                <a id="btnHtml" href="#" class="btn-export secondary" download>⤓ report.html</a>
                <a id="btnMd" href="#" class="btn-export secondary" download>⤓ report.md</a>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    // Discover local repositories
    window.addEventListener('DOMContentLoaded', async () => {
      try {
        const res = await fetch('/api/repos');
        const data = await res.json();
        const container = document.getElementById('discoveredReposPills');
        data.repos.forEach(r => {
          const pill = document.createElement('span');
          pill.className = 'p-pill';
          pill.innerText = r.name;
          pill.onclick = () => {
            document.getElementById('repoInput').value = r.path;
            updateCliPreview();
          };
          container.appendChild(pill);
        });
      } catch (e) {
        console.error(e);
      }
      updateCliPreview();
      checkOllamaStatus();
      try {
        const cfgRes = await fetch('/api/config');
        const cfg = await cfgRes.json();
        if (cfg.has_gemini_key) {
          document.getElementById('apiKeyInput').placeholder = '●●●●●●●● (API key detected on system)';
          document.getElementById('apiKeyStatusBadge').innerHTML = '<span style="color: var(--accent-green);">● KEY ACTIVE</span>';
        }
      } catch (e) {}
    });

    async function checkOllamaStatus() {
      const badge = document.getElementById('ollamaStatusBadge');
      try {
        const res = await fetch('/api/ollama/status');
        const data = await res.json();
        if (data.online) {
          badge.innerHTML = `<span style="color: var(--accent-green);">● OLLAMA ONLINE</span>`;
          if (data.models && data.models.length > 0) {
            const container = document.getElementById('modelPills');
            container.innerHTML = '';
            data.models.forEach((m, idx) => {
              const pill = document.createElement('span');
              pill.className = 'p-pill' + (idx === 0 ? ' active' : '');
              pill.innerText = m;
              pill.onclick = () => setModelVal(m);
              container.appendChild(pill);
            });
            document.getElementById('modelInput').value = data.models[0];
            updateCliPreview();
          }
        } else {
          badge.innerHTML = `<span style="color: var(--text-muted);">○ OLLAMA OFFLINE (run 'ollama serve')</span>`;
        }
      } catch (e) {
        badge.innerHTML = `<span style="color: var(--text-muted);">○ OFFLINE</span>`;
      }
    }

    function onLlmChange() {
      const llm = document.getElementById('llmSelect').value;
      const modelGroup = document.getElementById('modelGroup');
      const apiKeyGroup = document.getElementById('apiKeyGroup');
      if (llm === 'ollama') {
        modelGroup.style.display = 'flex';
        apiKeyGroup.style.display = 'none';
        document.getElementById('modelLabelDesc').innerText = '<ollama model, e.g. llama3:8b>';
        checkOllamaStatus();
      } else if (llm === 'gemini') {
        modelGroup.style.display = 'none';
        apiKeyGroup.style.display = 'flex';
      } else {
        modelGroup.style.display = 'none';
        apiKeyGroup.style.display = 'none';
      }
      updateCliPreview();
    }

    function setModelVal(val) {
      document.getElementById('modelInput').value = val;
      document.querySelectorAll('#modelPills .p-pill').forEach(p => p.classList.remove('active'));
      event.target.classList.add('active');
      updateCliPreview();
    }

    function setSinceVal(val) {
      document.getElementById('sinceInput').value = val;
      document.querySelectorAll('.preset-pills .p-pill').forEach(p => p.classList.remove('active'));
      event.target.classList.add('active');
      updateCliPreview();
    }

    function updateCliPreview() {
      const repo = document.getElementById('repoInput').value.trim() || '.';
      const since = document.getElementById('sinceInput').value.trim() || '7d';
      const audience = document.getElementById('audienceSelect').value;
      const llm = document.getElementById('llmSelect').value;
      const model = document.getElementById('modelInput').value.trim();
      const apiKey = document.getElementById('apiKeyInput').value.trim();
      const next = document.getElementById('nextGoalInput').value.trim();

      let cmd = `git2report --repo ${repo} --since ${since} --audience ${audience} --llm ${llm}`;
      if (llm === 'ollama' && model) {
        cmd += ` --model ${model}`;
      }
      if (llm === 'gemini' && apiKey) {
        cmd += ` --api-key "●●●●"`;
      }
      if (next) {
        cmd += ` --next "${next}"`;
      }
      cmd += ' --all';
      document.getElementById('commandPreview').innerText = cmd;
    }

    function loadPreset(type) {
      if (type === 'campusthrift') {
        document.getElementById('repoInput').value = 'cloned_repos/CampusThrift';
        document.getElementById('sinceInput').value = '2025-01-01';
        document.getElementById('audienceSelect').value = 'guide';
        document.getElementById('llmSelect').value = 'gemini';
      } else if (type === 'current') {
        document.getElementById('repoInput').value = '.';
        document.getElementById('sinceInput').value = '7d';
        document.getElementById('audienceSelect').value = 'team';
        document.getElementById('llmSelect').value = 'gemini';
      } else if (type === 'offline') {
        document.getElementById('llmSelect').value = 'offline';
      }
      onLlmChange();
    }

    async function clearCache() {
      if (!confirm('Clear smart summary cache (.git2report_cache.json)?')) return;
      try {
        const res = await fetch('/api/cache/clear', { method: 'POST' });
        const data = await res.json();
        appendStreamLine(`[✓] Cache cleared: ${data.cleared || 0} entries removed.`, 'success');
      } catch (e) {
        appendStreamLine(`[!] Failed to clear cache: ${e.message}`, 'error');
      }
    }

    function switchRightTab(name) {
      document.getElementById('tabStreamBtn').classList.toggle('active', name === 'stream');
      document.getElementById('tabPreviewBtn').classList.toggle('active', name === 'preview');
      document.getElementById('viewStream').style.display = (name === 'stream') ? 'block' : 'none';
      document.getElementById('viewPreview').style.display = (name === 'preview') ? 'block' : 'none';
    }

    function appendStreamLine(text, type = '') {
      const box = document.getElementById('termStream');
      const line = document.createElement('span');
      line.className = 'stream-line ' + type;
      line.innerText = text;
      box.appendChild(line);
      box.scrollTop = box.scrollHeight;
    }

    async function executeRun(e) {
      e.preventDefault();
      const btn = document.getElementById('btnExecute');
      btn.disabled = true;
      btn.innerHTML = '<span>⚡ EXECUTING PIPELINE...</span>';
      document.getElementById('execStatus').innerText = 'STDOUT: RUNNING';
      document.getElementById('execStatus').style.color = 'var(--accent-yellow)';

      switchRightTab('stream');
      const stream = document.getElementById('termStream');
      stream.innerHTML = '';
      appendStreamLine(`$ ${document.getElementById('commandPreview').innerText}`, 'info');

      const repo = document.getElementById('repoInput').value.trim();
      const since = document.getElementById('sinceInput').value.trim();
      const audience = document.getElementById('audienceSelect').value;
      const llm = document.getElementById('llmSelect').value;
      const model = document.getElementById('modelInput').value.trim();
      const apiKey = document.getElementById('apiKeyInput').value.trim();
      const nextGoal = document.getElementById('nextGoalInput').value.trim();

      const payload = {
        repo,
        since,
        audience,
        llm,
        model: (llm === 'ollama') ? model : '',
        api_key: (llm === 'gemini') ? apiKey : '',
        next_goals: nextGoal ? [nextGoal] : [],
        formats: {
          pdf: document.getElementById('fmtPdf').checked,
          html: document.getElementById('fmtHtml').checked,
          md: document.getElementById('fmtMd').checked,
        }
      };

      try {
        const res = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const result = await res.json();

        if (result.error) {
          appendStreamLine(`[ERROR] ${result.error}`, 'error');
          document.getElementById('execStatus').innerText = 'STDOUT: FAILED';
          document.getElementById('execStatus').style.color = 'var(--accent-red)';
          return;
        }

        (result.logs || []).forEach(l => appendStreamLine(`[+] ${l}`, 'info'));
        appendStreamLine(`[✓] SUCCESS: Generated PDF, HTML & MD in reports/`, 'success');

        // Update KPI
        document.getElementById('kpiBox').style.display = 'grid';
        document.getElementById('kpiCommits').innerText = result.metrics.commits || '0';
        document.getElementById('kpiChurn').innerText = `+${result.metrics.lines_added || 0} / -${result.metrics.lines_deleted || 0}`;
        document.getElementById('kpiTop').innerText = result.metrics.top_module || '-';
        document.getElementById('kpiTest').innerText = result.metrics.test_to_code_ratio || '0.0';

        // Update Downloads
        document.getElementById('exportBar').style.display = 'flex';
        document.getElementById('btnPdf').href = '/api/download?type=pdf&token=' + Date.now();
        document.getElementById('btnHtml').href = '/api/download?type=html&token=' + Date.now();
        document.getElementById('btnMd').href = '/api/download?type=md&token=' + Date.now();

        // Update Live Frame
        document.getElementById('reportPreviewFrame').src = '/api/preview?token=' + Date.now();

        document.getElementById('execStatus').innerText = 'STDOUT: COMPLETED';
        document.getElementById('execStatus').style.color = 'var(--accent-green)';
      } catch (err) {
        appendStreamLine(`[CRITICAL] Server connection failed: ${err.message}`, 'error');
        document.getElementById('execStatus').innerText = 'STDOUT: ERROR';
        document.getElementById('execStatus').style.color = 'var(--accent-red)';
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>▶ RUN PIPELINE (ENTER)</span>';
      }
    }
  </script>
</body>
</html>
"""


class WebStudioHandler(BaseHTTPRequestHandler):
    last_generated_files: dict[str, Path] = {}

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress standard access logs to keep terminal output clean."""
        pass

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(TERMINAL_HTML.encode("utf-8"))
            return

        if path == "/api/repos":
            repos = discover_local_repos()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"repos": repos}).encode("utf-8"))
            return

        if path == "/api/ollama/status":
            from git2report.summarizer import list_local_ollama_models
            models = list_local_ollama_models()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"online": len(models) > 0, "models": models}).encode("utf-8"))
            return

        if path == "/api/config":
            from git2report.summarizer import _load_env_file
            _load_env_file()
            has_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"has_gemini_key": has_key}).encode("utf-8"))
            return

        if path == "/api/preview":
            html_path = self.last_generated_files.get("html")
            if html_path and html_path.exists():
                content = html_path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content)
                return
            self.send_error(HTTPStatus.NOT_FOUND, "No HTML report generated yet.")
            return

        if path == "/api/download":
            ftype = query.get("type", ["pdf"])[0].lower()
            target_path = self.last_generated_files.get(ftype)
            if target_path and target_path.exists():
                mime, _ = mimetypes.guess_type(str(target_path))
                mime = mime or "application/octet-stream"
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Disposition", f'attachment; filename="{target_path.name}"')
                self.send_header("Content-Length", str(target_path.stat().st_size))
                self.end_headers()
                self.wfile.write(target_path.read_bytes())
                return
            self.send_error(HTTPStatus.NOT_FOUND, f"File for {ftype} not found.")
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/cache/clear":
            cleared = default_cache.clear()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"cleared": cleared}).encode("utf-8"))
            return

        if parsed.path == "/api/generate":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            try:
                data = json.loads(body)
                repo_str = data.get("repo", ".")
                since_str = data.get("since", "7d")
                audience = data.get("audience", "guide")
                llm = data.get("llm", "gemini")
                model = data.get("model", "")
                user_api_key = data.get("api_key", "").strip()
                planned = data.get("next_goals", [])

                if user_api_key:
                    os.environ["GEMINI_API_KEY"] = user_api_key
                    try:
                        env_file = Path.home() / ".git2report_env"
                        env_file.write_text(f"GEMINI_API_KEY={user_api_key}\n", encoding="utf-8")
                    except Exception:
                        pass

                repo_path = Path(repo_str)
                if repo_str.startswith(("http://", "https://", "git@")):
                    repo_name = repo_str.rstrip("/").split("/")[-1]
                    if repo_name.endswith(".git"):
                        repo_name = repo_name[:-4]
                    local_dir = Path("cloned_repos") / repo_name
                    local_dir.parent.mkdir(parents=True, exist_ok=True)
                    if not (local_dir / ".git").exists():
                        subprocess.run(["git", "clone", repo_str, str(local_dir)], check=True)
                    repo_path = local_dir

                logs: list[str] = []
                log_fn = lambda m: logs.append(str(m))

                opts = Options(
                    repo=repo_path,
                    since=parse_since(since_str),
                    audience=audience,
                    planned=planned,
                    include_branches=True
                )

                chosen_model = model or ("gemini-2.5-flash" if llm == "gemini" else ("llama3:8b" if llm == "ollama" else ""))
                summarizer = get_summarizer(llm, chosen_model, api_key=user_api_key or None)
                report_data = run_pipeline(opts, summarizer, log=log_fn)

                reports_dir = Path("reports")
                reports_dir.mkdir(parents=True, exist_ok=True)
                clean_name = repo_path.resolve().name.lower()
                base_out = reports_dir / f"{clean_name}_report"

                # Write files
                html_p = base_out.with_suffix(".html")
                html_p.write_text(render_html(report_data), encoding="utf-8")
                self.last_generated_files["html"] = html_p

                pdf_p = base_out.with_suffix(".pdf")
                render_pdf(report_data, pdf_p)
                self.last_generated_files["pdf"] = pdf_p

                md_p = base_out.with_suffix(".md")
                md_p.write_text(render_markdown(report_data), encoding="utf-8")
                self.last_generated_files["md"] = md_p

                resp_payload = {
                    "status": "success",
                    "metrics": report_data.metrics,
                    "logs": logs,
                    "files": {
                        "html": str(html_p),
                        "pdf": str(pdf_p),
                        "md": str(md_p)
                    }
                }
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(resp_payload).encode("utf-8"))
            except Exception as exc:
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")


def launch_web_server(port: int = 5000, open_browser: bool = True) -> None:
    """Launch the Web Terminal server and open the browser."""
    for p in range(port, port + 20):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", p), WebStudioHandler)
            url = f"http://localhost:{p}"
            print(f"\n=======================================================")
            print(f" 📟 GIT2REPORT TERMINAL STUDIO RUNNING AT: {url}")
            print(f"=======================================================")
            print(" Press Ctrl+C in this terminal to stop the server.\n")
            if open_browser:
                threading.Timer(0.8, lambda: webbrowser.open(url)).start()
            httpd.serve_forever()
            return
        except OSError:
            continue
    raise RuntimeError("Could not find an available port to start the web server.")


def main():
    launch_web_server()


if __name__ == "__main__":
    main()
