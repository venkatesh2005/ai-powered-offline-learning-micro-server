# Campus Connect - GitHub Push Script
# ====================================
# Edit the variables below, then run this script in PowerShell

# ⚠️ EDIT THESE VARIABLES FIRST!
$YourName = "Venkatesh"                    # Change if needed
$YourEmail = "venkat42005@gmail.com"       # Change to your actual email
$GitHubUsername = "venkatesh2005"          # Your GitHub username
$RepoName = "ai-powered-offline-learning-micro-server"               # Your desired repository name

# ====================================
# DO NOT EDIT BELOW THIS LINE
# ====================================

Write-Host "🚀 AI-Powered Offline Learning Micro Server - GitHub Push Script" -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

# Navigate to project directory
$ProjectPath = "C:\Users\HP X360\Downloads\Final-Year-Project"
Set-Location $ProjectPath

# Configure Git
Write-Host "⚙️  Configuring Git user..." -ForegroundColor Yellow
git config --global user.name $YourName
git config --global user.email $YourEmail
Write-Host "✅ Git configured as: $YourName <$YourEmail>`n" -ForegroundColor Green

# Verify Git status
Write-Host "📋 Checking Git status..." -ForegroundColor Yellow
git status --short
Write-Host ""

# Commit
Write-Host "💾 Committing files..." -ForegroundColor Yellow
git commit -m "Initial commit: AI-Powered Offline Learning Micro Server with TinyLlama

- Complete Flask backend with offline AI chatbot
- React frontend with Vite and Tailwind CSS
- RAG implementation for document-based Q&A
- Resource management (PDF, PPT, videos)
- Quiz system with admin panel
- TinyLlama 1.1B model included (fast responses)
- Comprehensive setup and deployment guides
- Optimized for CPU-only inference (2-5s response time)"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Files committed successfully!`n" -ForegroundColor Green
} else {
    Write-Host "❌ Commit failed! Check error messages above.`n" -ForegroundColor Red
    exit 1
}

# Construct GitHub URL
$GitHubURL = "https://github.com/$GitHubUsername/$RepoName.git"

# Add remote
Write-Host "🔗 Adding remote repository..." -ForegroundColor Yellow
Write-Host "   URL: $GitHubURL" -ForegroundColor Cyan

# Check if remote already exists
$remoteExists = git remote | Select-String -Pattern "^origin$" -Quiet
if ($remoteExists) {
    Write-Host "⚠️  Remote 'origin' already exists. Removing it..." -ForegroundColor Yellow
    git remote remove origin
}

git remote add origin $GitHubURL

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Remote repository added!`n" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to add remote! Check the URL.`n" -ForegroundColor Red
    exit 1
}

# Verify remote
Write-Host "📡 Verifying remote..." -ForegroundColor Yellow
git remote -v
Write-Host ""

# Rename branch and push
Write-Host "🚀 Pushing to GitHub..." -ForegroundColor Yellow
Write-Host "   This may take several minutes (TinyLlama model is ~650MB)`n" -ForegroundColor Cyan

git branch -M main

Write-Host "📤 Starting push to GitHub..." -ForegroundColor Yellow
Write-Host "   If prompted, enter your GitHub credentials:" -ForegroundColor Cyan
Write-Host "   - Username: $GitHubUsername" -ForegroundColor Cyan
Write-Host "   - Password: Use Personal Access Token (NOT your password)" -ForegroundColor Cyan
Write-Host "   - Get token at: https://github.com/settings/tokens`n" -ForegroundColor Cyan

git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ ✅ ✅ SUCCESS! ✅ ✅ ✅" -ForegroundColor Green
    Write-Host "🎉 Your project has been pushed to GitHub!" -ForegroundColor Green
    Write-Host "`nRepository URL:" -ForegroundColor Cyan
    Write-Host "   https://github.com/$GitHubUsername/$RepoName`n" -ForegroundColor White
    Write-Host "✅ What's included:" -ForegroundColor Green
    Write-Host "   - Complete source code (backend + frontend)" -ForegroundColor White
    Write-Host "   - TinyLlama AI model (650MB)" -ForegroundColor White
    Write-Host "   - All documentation and guides" -ForegroundColor White
    Write-Host "   - Setup instructions for users" -ForegroundColor White
    Write-Host "`n✅ What's excluded (as intended):" -ForegroundColor Green
    Write-Host "   - node_modules/" -ForegroundColor White
    Write-Host "   - Unused models (mistral, orca-mini)" -ForegroundColor White
    Write-Host "   - __pycache__, instance/, .env" -ForegroundColor White
    Write-Host "   - Database and cache files" -ForegroundColor White
} else {
    Write-Host "`n❌ Push failed!" -ForegroundColor Red
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "1. Repository doesn't exist on GitHub - create it first at: https://github.com/new" -ForegroundColor White
    Write-Host "2. Wrong credentials - use Personal Access Token as password" -ForegroundColor White
    Write-Host "3. Network issues - check your internet connection" -ForegroundColor White
    Write-Host "`nTry running the commands manually from PUSH_TO_GITHUB.txt" -ForegroundColor Yellow
}

Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
