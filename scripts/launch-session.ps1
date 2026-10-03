# Jarvis — Launch Session (Windows)
# Ablauf bei mehreren Monitoren:
#   1. Die 4 Fenster (VS Code, Obsidian, Chrome mit Jarvis, Spotify) erscheinen als Viertel auf dem MITTLEREN Monitor.
#   2. Jarvis begruesst dich.
#   3. Nach der Begruessung wandern die 4 Fenster auf den LINKEN Monitor.
#   4. In der Mitte oeffnet sich das Dashboard.
# Monitore werden von links nach rechts gezaehlt (0 = ganz links). Aenderbar in config.json:
#   "monitor_apps"      = wohin die 4 Fenster am Ende wandern (Standard 0)
#   "monitor_dashboard" = wo alles startet und das Dashboard laeuft (Standard 1)

# Load config
$configPath = Join-Path $PSScriptRoot "..\config.json"
$config = Get-Content $configPath -Raw | ConvertFrom-Json

$WORKSPACE_PATH = $config.workspace_path
$SPOTIFY_URI = $config.spotify_track
$BROWSER_URL = $config.browser_url
$BASE = "http://localhost:8340"

# Load assemblies
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;

[StructLayout(LayoutKind.Sequential)]
public struct WinRect {
    public int Left;
    public int Top;
    public int Right;
    public int Bottom;
}

public class WinPos {
    public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int W, int H, bool repaint);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out WinRect rect);
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

# Fenster eines Programms (VS Code, Obsidian, Spotify)
function Get-ProcHandle($name) {
    $p = Get-Process -Name $name -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
    if ($p) { return $p.MainWindowHandle }
    return $null
}

# Fenster per Titel finden (Chrome-Fenster sind ueber Process.MainWindowHandle nicht eindeutig)
function Find-WindowHandle($like) {
    foreach ($entry in [WinPos]::VisibleWindows()) {
        $sep = $entry.IndexOf("|")
        if ($entry.Substring($sep + 1) -like $like) { return [IntPtr][int64]$entry.Substring(0, $sep) }
    }
    return $null
}

# Vier gleich grosse Viertel eines Monitors: oben links, oben rechts, unten links, unten rechts
function Get-Quadrants($a) {
    $w = [math]::Floor($a.Width / 2)
    $h = [math]::Floor($a.Height / 2)
    return @(
        @{ x = $a.X;      y = $a.Y;      w = $w; h = $h },
        @{ x = $a.X + $w; y = $a.Y;      w = $w; h = $h },
        @{ x = $a.X;      y = $a.Y + $h; w = $w; h = $h },
        @{ x = $a.X + $w; y = $a.Y + $h; w = $w; h = $h }
    )
}

# Fenster weich zu den Zielpositionen gleiten lassen
function Slide-To($handles, $targets) {
    $moves = @()
    for ($i = 0; $i -lt $handles.Count; $i++) {
        if (-not $handles[$i]) { continue }
        $r = New-Object WinRect
        [WinPos]::GetWindowRect($handles[$i], [ref]$r) | Out-Null
        $moves += , @{ h = $handles[$i]; sx = $r.Left; sy = $r.Top; sw = ($r.Right - $r.Left); sh = ($r.Bottom - $r.Top); t = $targets[$i] }
    }
    $steps = 24
    for ($s = 1; $s -le $steps; $s++) {
        $p = $s / $steps
        $e = 1 - [math]::Pow(1 - $p, 3)
        foreach ($m in $moves) {
            $x = [int]($m.sx + ($m.t.x - $m.sx) * $e)
            $y = [int]($m.sy + ($m.t.y - $m.sy) * $e)
            $w = [int]($m.sw + ($m.t.w - $m.sw) * $e)
            $h = [int]($m.sh + ($m.t.h - $m.sh) * $e)
            [WinPos]::MoveWindow($m.h, $x, $y, $w, $h, $true) | Out-Null
        }
        Start-Sleep -Milliseconds 20
    }
}

# Wartet bis der Jarvis-Server antwortet und liefert die Zahl der bisherigen Begruessungen
function Get-GreetingCount {
    try { return [int](Invoke-RestMethod "$BASE/api/greeting" -TimeoutSec 2).greetings } catch { return $null }
}

# Monitore von links nach rechts sortieren
$screens = @([System.Windows.Forms.Screen]::AllScreens | Sort-Object { $_.Bounds.X })
$count = $screens.Count
$appsIdx = if ($null -ne $config.monitor_apps) { [int]$config.monitor_apps } else { 0 }
$dashIdx = if ($null -ne $config.monitor_dashboard) { [int]$config.monitor_dashboard } else { [math]::Min(1, $count - 1) }
$appsIdx = [math]::Max(0, [math]::Min($appsIdx, $count - 1))
$dashIdx = [math]::Max(0, [math]::Min($dashIdx, $count - 1))
$multi = ($dashIdx -ne $appsIdx)

Write-Host "[jarvis] $count Monitor(e) erkannt. Start auf Monitor $dashIdx$(if ($multi) { ", danach wandern die Apps auf Monitor $appsIdx, Dashboard bleibt auf Monitor $dashIdx" })."

$startQuads = Get-Quadrants $screens[$dashIdx].WorkingArea

# 1. Server + Spotify + Apps starten
Start-Process "wt.exe" -ArgumentList "new-tab -d `"$WORKSPACE_PATH`" cmd /k `"python $WORKSPACE_PATH\server.py`"" -WindowStyle Minimized
Start-Process $SPOTIFY_URI
code $WORKSPACE_PATH
foreach ($app in $config.apps) { Start-Process $app }

# 2. Warten bis der Server laeuft (max. 30 s), damit die Begruessung sicher kommt
$before = $null
for ($i = 0; $i -lt 60 -and $null -eq $before; $i++) {
    $before = Get-GreetingCount
    if ($null -eq $before) { Start-Sleep -Milliseconds 500 }
}

# 3. Chrome mit Jarvis + Website
Start-Process "chrome" -ArgumentList "--autoplay-policy=no-user-gesture-required $BASE $BROWSER_URL"

# 4. Alle 4 Fenster als Viertel auf den Startmonitor (Mitte)
Start-Sleep -Seconds 4
$handles = @(
    (Get-ProcHandle "Code"),
    (Get-ProcHandle "Obsidian"),
    (Find-WindowHandle "*- Google Chrome"),
    (Get-ProcHandle "Spotify")
)
for ($i = 0; $i -lt 4; $i++) {
    if ($handles[$i]) { Move-Handle $handles[$i] $startQuads[$i].x $startQuads[$i].y $startQuads[$i].w $startQuads[$i].h }
}

# Nur ein Monitor: alles bleibt wie es ist
if (-not $multi) { return }

# 5. Auf das Ende der Begruessung warten (max. 60 s), kurz durchatmen, dann nach links gleiten
$deadline = (Get-Date).AddSeconds(60)
if ($null -eq $before) {
    Write-Host "[jarvis] Server nicht erreichbar, warte 20 s statt auf die Begruessung."
    Start-Sleep -Seconds 20
} else {
    while ((Get-Date) -lt $deadline) {
        $now = Get-GreetingCount
        if ($null -ne $now -and $now -gt $before) { break }
        Start-Sleep -Milliseconds 500
    }
}
Start-Sleep -Milliseconds 1200

$appQuads = Get-Quadrants $screens[$appsIdx].WorkingArea
Slide-To $handles $appQuads

# 6. Dashboard als eigenes App-Fenster (ohne Adressleiste) in der Mitte
$dash = $screens[$dashIdx].WorkingArea
Start-Process "chrome" -ArgumentList "--app=$BASE/dashboard --window-position=$($dash.X),$($dash.Y) --window-size=$($dash.Width),$($dash.Height)"
Start-Sleep -Seconds 3
$dashHandle = Find-WindowHandle "J.A.R.V.I.S. Dashboard*"
if ($dashHandle) { Move-Handle $dashHandle $dash.X $dash.Y $dash.Width $dash.Height }
else { Write-Host "[jarvis] Dashboard-Fenster nicht gefunden. Oeffne $BASE/dashboard von Hand." }
