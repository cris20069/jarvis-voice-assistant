# Jarvis — Launch Session (Windows)
# Mehrere Monitore: Die 4 Fenster (VS Code, Obsidian, Chrome, Spotify) wandern auf den
# linken Monitor, das Dashboard oeffnet auf dem mittleren. Nummerierung von links nach rechts,
# 0 = ganz links. Aenderbar in config.json: "monitor_apps" und "monitor_dashboard".

# Load config
$configPath = Join-Path $PSScriptRoot "..\config.json"
$config = Get-Content $configPath -Raw | ConvertFrom-Json

$WORKSPACE_PATH = $config.workspace_path
$SPOTIFY_URI = $config.spotify_track
$BROWSER_URL = $config.browser_url

# Load assemblies
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class WinPos {
    public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int W, int H, bool repaint);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")]
    static extern bool EnumWindows(EnumProc cb, IntPtr lParam);
    [DllImport("user32.dll")]
    static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    static extern int GetWindowText(IntPtr hWnd, StringBuilder sb, int max);

    // Alle sichtbaren Fenster mit Titel als "Handle|Titel"
    public static List<string> VisibleWindows() {
        List<string> result = new List<string>();
        EnumWindows(delegate (IntPtr h, IntPtr l) {
            if (IsWindowVisible(h)) {
                StringBuilder sb = new StringBuilder(256);
                GetWindowText(h, sb, 256);
                if (sb.Length > 0) result.Add(h.ToInt64().ToString() + "|" + sb.ToString());
            }
            return true;
        }, IntPtr.Zero);
        return result;
    }
}
"@

# Physische Pixel verwenden, damit Fenster bei Skalierung (125 %, 150 %) richtig sitzen
[WinPos]::SetProcessDPIAware() | Out-Null

function Move-Handle($handle, $x, $y, $w, $h) {
    [WinPos]::ShowWindow($handle, 9) | Out-Null
    Start-Sleep -Milliseconds 200
    [WinPos]::MoveWindow($handle, $x, $y, $w, $h, $true) | Out-Null
}

function Snap-Window($proc, $x, $y, $w, $h) {
    if ($proc) { Move-Handle $proc.MainWindowHandle $x $y $w $h }
}

# Fenster per Titel finden (Chrome-Fenster sind ueber Process.MainWindowHandle nicht eindeutig)
function Find-WindowHandle($like) {
    foreach ($entry in [WinPos]::VisibleWindows()) {
        $sep = $entry.IndexOf("|")
        if ($entry.Substring($sep + 1) -like $like) { return [IntPtr][int64]$entry.Substring(0, $sep) }
    }
    return $null
}

# Monitore von links nach rechts sortieren
$screens = @([System.Windows.Forms.Screen]::AllScreens | Sort-Object { $_.Bounds.X })
$count = $screens.Count
$appsIdx = if ($null -ne $config.monitor_apps) { [int]$config.monitor_apps } else { 0 }
$dashIdx = if ($null -ne $config.monitor_dashboard) { [int]$config.monitor_dashboard } else { [math]::Min(1, $count - 1) }
$appsIdx = [math]::Max(0, [math]::Min($appsIdx, $count - 1))
$dashIdx = [math]::Max(0, [math]::Min($dashIdx, $count - 1))
$showDashboard = ($dashIdx -ne $appsIdx)

Write-Host "[jarvis] $count Monitor(e) erkannt. Apps: Monitor $appsIdx, Dashboard: $(if ($showDashboard) { "Monitor $dashIdx" } else { 'aus (nur ein Monitor)' })"

$area = $screens[$appsIdx].WorkingArea
$halfW = [math]::Floor($area.Width / 2)
$halfH = [math]::Floor($area.Height / 2)

# 1. Start server + Spotify + apps
Start-Process "wt.exe" -ArgumentList "new-tab -d `"$WORKSPACE_PATH`" cmd /k `"python $WORKSPACE_PATH\server.py`"" -WindowStyle Minimized
Start-Process $SPOTIFY_URI
code $WORKSPACE_PATH
foreach ($app in $config.apps) { Start-Process $app }

# 2. Chrome with Jarvis + Skool
Start-Process "chrome" -ArgumentList "--autoplay-policy=no-user-gesture-required http://localhost:8340 $BROWSER_URL"

# 3. Dashboard als eigenes App-Fenster (ohne Adressleiste) auf dem Dashboard-Monitor
if ($showDashboard) {
    $dash = $screens[$dashIdx].WorkingArea
    Start-Sleep -Seconds 2   # Server braucht einen Moment
    Start-Process "chrome" -ArgumentList "--app=http://localhost:8340/dashboard --window-position=$($dash.X),$($dash.Y) --window-size=$($dash.Width),$($dash.Height)"
}

# 4. Fenster einsortieren
Start-Sleep -Seconds 4

# Obere Haelfte: VS Code links, Obsidian rechts
$vscode = Get-Process -Name "Code" -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
Snap-Window $vscode $area.X $area.Y $halfW $halfH

$obsidian = Get-Process -Name "Obsidian" -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
Snap-Window $obsidian ($area.X + $halfW) $area.Y $halfW $halfH

# Untere Haelfte: Chrome mit Jarvis links, Spotify rechts
$chromeHandle = Find-WindowHandle "*- Google Chrome"
if ($chromeHandle) { Move-Handle $chromeHandle $area.X ($area.Y + $halfH) $halfW $halfH }

$spotify = Get-Process -Name "Spotify" -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
Snap-Window $spotify ($area.X + $halfW) ($area.Y + $halfH) $halfW $halfH

# Dashboard sicher auf den Zielmonitor legen (falls Chrome die Startposition ignoriert hat)
if ($showDashboard) {
    $dashHandle = Find-WindowHandle "J.A.R.V.I.S. Dashboard*"
    if ($dashHandle) { Move-Handle $dashHandle $dash.X $dash.Y $dash.Width $dash.Height }
    else { Write-Host "[jarvis] Dashboard-Fenster nicht gefunden. Oeffne http://localhost:8340/dashboard von Hand." }
}
