# How to Find and Run the Verification Script

## Step 1: Find Your Repository

In PowerShell, search for your repository:

```powershell
# Search common locations for the real-estate-os folder
Get-ChildItem -Path "C:\Users" -Filter "real-estate-os" -Directory -Recurse -ErrorAction SilentlyContinue -Depth 4 | Select-Object FullName
```

This will search your user directory and show you the full path. Common locations might be:
- `C:\Users\YourUsername\real-estate-os`
- `C:\Users\YourUsername\Documents\real-estate-os`
- `C:\Users\YourUsername\dev\real-estate-os`
- `C:\Users\YourUsername\projects\real-estate-os`
- `C:\Users\YourUsername\source\real-estate-os`

## Step 2: Navigate to the Repository

Once you find the path, navigate there:

```powershell
# Replace YourUsername with your actual Windows username
cd C:\Users\YourUsername\real-estate-os
```

**Tip**: You can also use Tab completion:
```powershell
cd C:\Users\[Tab]  # Press Tab to cycle through usernames
```

## Step 3: Verify You're in the Right Place

```powershell
# Check for key files
ls RUN_ALL_VERIFICATION.ps1
ls docker-compose.yaml
```

You should see both files listed.

## Step 4: Run the Verification Script

```powershell
.\RUN_ALL_VERIFICATION.ps1
```

## Quick Alternative: Use File Explorer

1. Open **File Explorer**
2. Press `Ctrl + F` and search for: `RUN_ALL_VERIFICATION.ps1`
3. Right-click the file → "Open file location"
4. In the address bar of File Explorer, you'll see the full path
5. Click in the address bar, select all (Ctrl+A), and copy (Ctrl+C)
6. In PowerShell:
   ```powershell
   cd "paste-the-path-here"
   .\RUN_ALL_VERIFICATION.ps1
   ```

## Even Faster: Right-Click → Open in Terminal

1. Open **File Explorer**
2. Navigate to your `real-estate-os` folder (wherever you cloned it)
3. **Right-click** inside the folder (on empty space)
4. Select **"Open in Terminal"** or **"Open PowerShell window here"**
5. The terminal will open already in the correct directory
6. Run:
   ```powershell
   .\RUN_ALL_VERIFICATION.ps1
   ```

## Common Locations by Username

If your Windows username is visible in your PowerShell prompt, look for it here:

```powershell
# Example: If your username is "john"
cd C:\Users\john\real-estate-os

# Example: If your username is "admin"
cd C:\Users\admin\real-estate-os

# Example: If in Documents folder
cd C:\Users\YourUsername\Documents\real-estate-os
```

## Still Can't Find It?

If you cloned it recently, check your recent Git commands:

```powershell
# Show recent directories in PowerShell history
Get-History | Select-String "git clone"
```

Or search your entire C: drive (takes longer):

```powershell
Get-ChildItem -Path "C:\" -Filter "real-estate-os" -Directory -Recurse -ErrorAction SilentlyContinue -Depth 5 | Select-Object FullName
```
