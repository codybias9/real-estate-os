# Stop the script if any command fails
$ErrorActionPreference = 'Stop'
try {
    Write-Host "
--- Preparing the environment ---" -ForegroundColor Yellow
    wsl --shutdown
    Write-Host "
Please start the Docker Desktop application now and wait for it to be fully running." -ForegroundColor Green
    Read-Host "Press Enter to continue once Docker Desktop is running..."

    $wslDistros = wsl --list
    $distroName = Read-Host "
Found WSL distributions:
$wslDistros
Please enter the name of the distribution you want to use (e.g., Ubuntu)"
    
    Write-Host "
--- Starting deployment inside '$distroName' ---" -ForegroundColor Yellow
    wsl --distribution $distroName --cd "$PSScriptRoot" -- bash wsl-script.sh
    
} catch {
    Write-Host "
An error occurred during the script execution." -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
