<#
一键环境检查与自动修复脚本

用于跨设备部署 AI 运营分身项目时检查常见环境问题：
- Python 版本是否满足 3.10+
- Visual C++ 运行时是否存在
- Python 依赖包是否安装，缺失时自动安装
- 项目关键文件与本地索引目录是否存在
- sentence-transformers 嵌入模型是否可加载

运行方式：
    powershell -ExecutionPolicy Bypass -File .\check_env.ps1
#>

$ErrorActionPreference = "Continue"

$PassedCount = 0
$WarningCount = 0
$FailedCount = 0
$ManualFixes = New-Object System.Collections.Generic.List[string]

function Write-Info {
    param([string]$Message)
    Write-Host $Message -ForegroundColor DarkGray
}

function Write-Pass {
    param([string]$Message)
    $script:PassedCount += 1
    Write-Host "[PASS] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    $script:WarningCount += 1
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param(
        [string]$Message,
        [string]$Fix = ""
    )
    $script:FailedCount += 1
    Write-Host "[FAIL] $Message" -ForegroundColor Red
    if ($Fix) {
        $script:ManualFixes.Add($Fix) | Out-Null
        Write-Host "       手动修复：$Fix" -ForegroundColor DarkGray
    }
}

function Write-Fixed {
    param([string]$Message)
    $script:PassedCount += 1
    Write-Host "[FIXED] $Message" -ForegroundColor Green
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "== $Title ==" -ForegroundColor Cyan
}

function Get-PythonVersion {
    try {
        $versionText = (& python --version 2>&1).ToString().Trim()
        if ($versionText -match "Python\s+(\d+)\.(\d+)\.(\d+)") {
            return [pscustomobject]@{
                Found = $true
                Text = $versionText
                Major = [int]$Matches[1]
                Minor = [int]$Matches[2]
                Patch = [int]$Matches[3]
            }
        }
        return [pscustomobject]@{ Found = $false; Text = $versionText }
    }
    catch {
        return [pscustomobject]@{ Found = $false; Text = $_.Exception.Message }
    }
}

function Test-PipPackage {
    param([string]$PackageName)
    $output = & python -m pip show $PackageName 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $output) {
        return [pscustomobject]@{ Installed = $false; Version = "" }
    }

    $versionLine = $output | Where-Object { $_ -like "Version:*" } | Select-Object -First 1
    $version = ""
    if ($versionLine) {
        $version = ($versionLine -replace "^Version:\s*", "").Trim()
    }
    return [pscustomobject]@{ Installed = $true; Version = $version }
}

function Install-PipPackage {
    param([string]$PackageName)
    Write-Info "正在安装：$PackageName"
    & python -m pip install $PackageName
    return ($LASTEXITCODE -eq 0)
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "AI 运营分身环境检查与自动修复" -ForegroundColor Cyan
Write-Info "项目目录：$ProjectRoot"

Write-Section "一、检查 Python 版本"
$pythonVersion = Get-PythonVersion
$PythonReady = $false
if (-not $pythonVersion.Found) {
    Write-Fail "未检测到可用 Python。输出：$($pythonVersion.Text)" "请从 https://www.python.org/downloads/ 下载并安装 Python 3.10 或以上版本，安装时勾选 Add python.exe to PATH。"
}
elseif ($pythonVersion.Major -gt 3 -or ($pythonVersion.Major -eq 3 -and $pythonVersion.Minor -ge 10)) {
    $PythonReady = $true
    Write-Pass "Python 版本符合要求：$($pythonVersion.Text)"
}
else {
    Write-Fail "Python 版本低于 3.10：$($pythonVersion.Text)" "请从 https://www.python.org/downloads/ 下载并安装 Python 3.10 或以上版本。"
}

Write-Section "二、检查 Visual C++ 运行时"
$vcRuntimeInstalled = $false
try {
    $vcRegPath = "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64"
    $vcRuntime = Get-ItemProperty -Path $vcRegPath -ErrorAction Stop
    if ($vcRuntime.Installed -eq 1) {
        $vcRuntimeInstalled = $true
        Write-Pass "Visual C++ 运行时已安装（注册表 Installed=1）。"
    }
}
catch {
    Write-Info "未在注册表中找到 Visual C++ 运行时标记，继续检查 vcruntime140.dll。"
}

if (-not $vcRuntimeInstalled) {
    $vcDll = "C:\Windows\System32\vcruntime140.dll"
    if (Test-Path $vcDll) {
        $vcRuntimeInstalled = $true
        Write-Pass "Visual C++ 运行时 DLL 存在：$vcDll"
    }
}

if (-not $vcRuntimeInstalled) {
    Write-Warn "未检测到 Visual C++ 运行时。缺失时可能导致 onnxruntime 和 chromadb 默认模型加载失败。"
    Write-Info "手动下载地址：https://aka.ms/vs/17/release/vc_redist.x64.exe"
}

Write-Section "三、检查并安装 Python 依赖包"
$RequiredPackages = @(
    "streamlit",
    "openai",
    "langgraph",
    "langchain",
    "langchain-community",
    "chromadb",
    "sentence-transformers",
    "matplotlib",
    "pyyaml",
    "python-dotenv"
)

if (-not $PythonReady) {
    Write-Fail "跳过依赖检查：Python 不可用或版本不符合要求。" "安装 Python 3.10+ 后重新运行 powershell -ExecutionPolicy Bypass -File .\check_env.ps1"
}
else {
    foreach ($package in $RequiredPackages) {
        $status = Test-PipPackage -PackageName $package
        if ($status.Installed) {
            Write-Pass "$package 已安装，版本：$($status.Version)"
            continue
        }

        Write-Warn "$package 未安装，尝试自动安装。"
        $installed = Install-PipPackage -PackageName $package
        if ($installed) {
            Write-Fixed "$package 安装成功。"
        }
        else {
            Write-Fail "$package 自动安装失败。" "请手动运行：python -m pip install $package"
        }
    }
}

Write-Section "四、检查项目关键文件"
if (Test-Path ".env") {
    Write-Pass ".env 文件存在。"
}
else {
    Write-Warn ".env 文件不存在。请复制 .env.example 为 .env，并填入 API Key。"
    Write-Info "推荐命令：Copy-Item .env.example .env"
}

if (Test-Path "config.yaml") {
    Write-Pass "config.yaml 文件存在。"
}
else {
    Write-Warn "config.yaml 文件不存在。当前项目可使用默认配置；如需启用知识同步路径，请按需创建。"
}

if (Test-Path "chroma_db") {
    Write-Pass "项目根目录 chroma_db/ 文件夹存在。"
}
else {
    Write-Warn "项目根目录 chroma_db/ 文件夹不存在。当前版本默认把索引写入用户数据目录；如需构建索引，请运行 python build_index.py。"
}

if (Test-Path "works") {
    Write-Pass "works/ 文件夹存在。"
}
else {
    Write-Fail "works/ 文件夹不存在。" "请确认项目文件完整，或从仓库重新拉取 works/ 文件夹。"
}

Write-Section "五、检查嵌入模型"
if (-not $PythonReady) {
    Write-Fail "跳过嵌入模型检查：Python 不可用或版本不符合要求。" "安装 Python 3.10+ 后重新运行脚本。"
}
else {
    $modelCheckScript = @'
from sentence_transformers import SentenceTransformer
SentenceTransformer("BAAI/bge-small-zh-v1.5")
print("MODEL_READY")
'@
    $modelOutput = $modelCheckScript | python - 2>&1
    if ($LASTEXITCODE -eq 0 -and ($modelOutput -join "`n") -match "MODEL_READY") {
        Write-Pass "嵌入模型 BAAI/bge-small-zh-v1.5 已就绪。"
    }
    else {
        Write-Warn "嵌入模型暂时无法加载。首次使用需下载模型（约 400MB），请确保网络通畅。"
        Write-Info "如果网络受限，可临时设置 HuggingFace 镜像："
        Write-Host '       $env:HF_ENDPOINT="https://hf-mirror.com"' -ForegroundColor DarkGray
        Write-Info "然后重新运行：python build_index.py"
    }
}

Write-Section "六、汇总报告"
Write-Host "通过项：$PassedCount" -ForegroundColor Green
Write-Host "警告项：$WarningCount" -ForegroundColor Yellow
Write-Host "失败项：$FailedCount" -ForegroundColor Red

if ($ManualFixes.Count -gt 0) {
    Write-Host ""
    Write-Host "需要手动处理的事项：" -ForegroundColor Red
    for ($i = 0; $i -lt $ManualFixes.Count; $i++) {
        Write-Host ("{0}. {1}" -f ($i + 1), $ManualFixes[$i]) -ForegroundColor DarkGray
    }
}

if ($FailedCount -eq 0) {
    Write-Host ""
    Write-Host "环境就绪，可以启动应用：streamlit run app.py" -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "环境仍有失败项，请按上方指引修复后重新运行本脚本。" -ForegroundColor Red
exit 1

