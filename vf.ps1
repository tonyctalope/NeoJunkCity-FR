# Patch français non officiel de Neo Junk City - installation / désinstallation (Windows).
# Lancé par Installer.bat et Desinstaller.bat. Ne contient et ne télécharge aucun programme :
# il lit les fichiers de différences du dossier "patch" et les applique aux fichiers du jeu.
param([string]$Action = "install", [string]$GameDir = "")
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$GameName = "Neo Junk City"
$DataName = "Neo Junk City_Data"
$BackupName = "VF_sauvegarde"
$TmpName = "_vf_tmp"

function Say([string]$Text, [string]$Color) {
    if ($Color) { Write-Host $Text -ForegroundColor $Color } else { Write-Host $Text }
}

function JP([string]$A, [string]$B) { return [System.IO.Path]::Combine($A, $B) }
function Has-File([string]$P) { return [System.IO.File]::Exists($P) }
function Has-Dir([string]$P) { return [System.IO.Directory]::Exists($P) }

function Get-Sha([string]$Path) {
    $s = [System.IO.File]::OpenRead($Path)
    try {
        $h = [System.Security.Cryptography.SHA256]::Create()
        $b = $h.ComputeHash($s)
    } finally { $s.Close() }
    return ([System.BitConverter]::ToString($b)).Replace("-", "").ToLower()
}

# Format VFP1 : "VFP1" puis flux deflate : int32 nombre d'opérations, puis pour chacune
# 0 + int64 position + int32 longueur (copie depuis le fichier d'origine) ou 1 + int32 longueur + octets.
function Invoke-Patch([string]$SrcPath, [string]$PatchPath, [string]$OutPath) {
    $src = [System.IO.File]::OpenRead($SrcPath)
    $pf = [System.IO.File]::OpenRead($PatchPath)
    $out = [System.IO.File]::Create($OutPath)
    try {
        $magic = New-Object byte[] 4
        [void]$pf.Read($magic, 0, 4)
        if ([System.Text.Encoding]::ASCII.GetString($magic) -ne "VFP1") { throw "fichier de patch invalide" }
        $z = New-Object System.IO.Compression.DeflateStream($pf, [System.IO.Compression.CompressionMode]::Decompress)
        $br = New-Object System.IO.BinaryReader($z)
        $buf = New-Object byte[] 1048576
        $count = $br.ReadInt32()
        for ($i = 0; $i -lt $count; $i++) {
            $kind = $br.ReadByte()
            if ($kind -eq 0) {
                $off = $br.ReadInt64()
                $len = $br.ReadInt32()
                $src.Position = $off
                while ($len -gt 0) {
                    $want = $len
                    if ($want -gt $buf.Length) { $want = $buf.Length }
                    $got = $src.Read($buf, 0, $want)
                    if ($got -le 0) { throw "fichier d'origine trop court" }
                    $out.Write($buf, 0, $got)
                    $len -= $got
                }
            } else {
                $len = $br.ReadInt32()
                $d = $br.ReadBytes($len)
                if ($d.Length -ne $len) { throw "fichier de patch tronqué" }
                $out.Write($d, 0, $len)
            }
        }
    } finally {
        $out.Close(); $pf.Close(); $src.Close()
    }
}

function Test-Game([string]$Dir) {
    if (-not $Dir) { return $null }
    $Dir = $Dir.Trim().Trim('"').TrimEnd('\')
    if (-not $Dir) { return $null }
    $cands = @($Dir, (JP $Dir $GameName))
    $parent = $null
    try { $parent = [System.IO.Path]::GetDirectoryName($Dir) } catch { }
    if ($parent) { $cands += $parent }
    foreach ($c in $cands) {
        try {
            if (Has-File (JP (JP $c $DataName) "resources.assets")) { return $c }
        } catch { }
    }
    return $null
}

function Find-Game {
    $roots = @()
    foreach ($k in @("HKCU:\Software\Valve\Steam", "HKLM:\SOFTWARE\WOW6432Node\Valve\Steam", "HKLM:\SOFTWARE\Valve\Steam")) {
        try {
            $p = Get-ItemProperty -Path $k -ErrorAction Stop
            foreach ($n in @("SteamPath", "InstallPath")) {
                $v = $p.$n
                if ($v) { $roots += ([string]$v).Replace("/", "\") }
            }
        } catch { }
    }
    $roots += "C:\Program Files (x86)\Steam"
    $libs = @()
    foreach ($r in $roots) {
        $libs += $r
        try {
            $vdf = JP $r "steamapps\libraryfolders.vdf"
            if (Has-File $vdf) {
                $txt = [System.IO.File]::ReadAllText($vdf, [System.Text.Encoding]::UTF8)
                foreach ($m in [regex]::Matches($txt, '"path"\s+"([^"]+)"')) {
                    $libs += $m.Groups[1].Value.Replace("\\", "\")
                }
            }
        } catch { }
    }
    foreach ($l in $libs) {
        $g = Test-Game (JP $l ("steamapps\common\" + $GameName))
        if ($g) { return $g }
    }
    $g = Test-Game ([System.IO.Path]::GetDirectoryName($Here))
    if ($g) { return $g }
    return (Test-Game $Here)
}

function Main {
    if ($Action -ne "install" -and $Action -ne "uninstall") { Say "Usage : vf.ps1 install|uninstall [dossier du jeu]"; return 2 }
    $patchDir = JP $Here "patch"
    $manifestPath = JP $patchDir "manifest.json"
    if (-not (Has-File $manifestPath)) {
        Say "Dossier 'patch' introuvable à côté de ce script : extrayez tout le zip dans un même dossier." Red
        return 2
    }
    $M = [System.IO.File]::ReadAllText($manifestPath, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
    $game = $null
    if ($GameDir) {
        $game = Test-Game $GameDir
        if (-not $game) { Say ("Jeu introuvable dans : " + $GameDir) Red; return 1 }
    } else {
        $game = Find-Game
    }
    while (-not $game) {
        Say "Jeu introuvable automatiquement." Yellow
        Say "Dans Steam : clic droit sur le jeu > Gérer > Parcourir les fichiers locaux, puis copiez le chemin du dossier et collez-le ici."
        $ans = $null
        try { $ans = Read-Host "Dossier du jeu (vide pour abandonner)" } catch { $ans = "" }
        if (-not $ans -or -not $ans.Trim()) { Say "Abandon, rien n'a été modifié."; return 1 }
        $game = Test-Game $ans
    }
    Say ("Patch français " + $M.patch_version + " pour la version " + $M.build + " du jeu")
    Say ("Jeu : " + $game)
    if (Get-Process -Name $GameName -ErrorAction SilentlyContinue) {
        Say "Le jeu est en cours d'exécution : fermez-le puis relancez." Red
        return 1
    }
    $data = JP $game $DataName
    $bak = JP $game $BackupName
    $files = @($M.files)
    Say ("Vérification de " + $files.Count + " fichiers...")

    if ($Action -eq "uninstall") {
        $todo = @(); $odd = @()
        foreach ($f in $files) {
            $rel = $f.path.Replace("/", "\")
            $cur = JP $data $rel
            $b = JP $bak $rel
            $h = ""
            if (Has-File $cur) { $h = Get-Sha $cur }
            if ($h -eq $f.orig_sha256) { continue }
            if ($h -eq $f.new_sha256 -and (Has-File $b) -and ((Get-Sha $b) -eq $f.orig_sha256)) {
                $todo += , @($cur, $b)
            } else {
                $odd += $f.path
            }
        }
        foreach ($t in $todo) { [System.IO.File]::Copy($t[1], $t[0], $true) }
        Say ([string]$todo.Count + " fichiers remis dans leur état d'origine.")
        if ($odd.Count -gt 0) {
            Say ([string]$odd.Count + " fichiers n'ont pas pu être remis (version différente ou copie absente).") Yellow
            Say "Pour tout remettre d'origine : Steam > clic droit sur le jeu > Propriétés > Fichiers installés > Vérifier l'intégrité des fichiers."
            return 1
        }
        if (Has-Dir $bak) { Remove-Item -LiteralPath $bak -Recurse -Force }
        Say "Désinstallation terminée." Green
        return 0
    }

    $plan = @(); $bad = @()
    foreach ($f in $files) {
        $rel = $f.path.Replace("/", "\")
        $cur = JP $data $rel
        $b = JP $bak $rel
        $h = ""
        if (Has-File $cur) { $h = Get-Sha $cur }
        if ($h -eq $f.new_sha256) { continue }
        if ($h -eq $f.orig_sha256) {
            $plan += , @($f, $cur, $b, $true)
        } elseif ((Has-File $b) -and ((Get-Sha $b) -eq $f.orig_sha256)) {
            $plan += , @($f, $cur, $b, $false)
        } else {
            $bad += $f.path
        }
    }
    if ($bad.Count -gt 0) {
        Say ([string]$bad.Count + " fichiers ne correspondent pas à la version " + $M.build + " du jeu.") Red
        Say "Le jeu a sans doute été mis à jour (ou modifié par autre chose). Rien n'a été modifié."
        Say "Récupérez la dernière version du patch, ou vérifiez l'intégrité des fichiers dans Steam puis relancez."
        return 1
    }
    if ($plan.Count -eq 0) {
        Say "Le patch est déjà installé. Dans le jeu : Options > Language > English." Green
        return 0
    }
    # 1. copie de sécurité des fichiers d'origine
    foreach ($p in $plan) {
        if ($p[3]) {
            $dir = [System.IO.Path]::GetDirectoryName($p[2])
            if (-not (Has-Dir $dir)) { [void][System.IO.Directory]::CreateDirectory($dir) }
            [System.IO.File]::Copy($p[1], $p[2], $true)
        }
    }
    $tmp = JP $data $TmpName
    if (Has-Dir $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
    [void][System.IO.Directory]::CreateDirectory($tmp)
    $placed = 0
    try {
        Say ("Application du patch (" + $plan.Count + " fichiers), cela peut prendre une minute...")
        # 2. tout est préparé et contrôlé à part
        $n = 0
        foreach ($p in $plan) {
            $f = $p[0]
            $o = JP $tmp ([string]$n)
            Invoke-Patch $p[2] (JP $patchDir $f.patch) $o
            if ((Get-Sha $o) -ne $f.new_sha256) { throw ("résultat inattendu pour " + $f.path) }
            $n++
            if ($n % 10 -eq 0) { Write-Host ("  " + $n + " / " + $plan.Count) }
        }
        # 3. puis mis en place
        $n = 0
        foreach ($p in $plan) {
            [System.IO.File]::Copy((JP $tmp ([string]$n)), $p[1], $true)
            $n++; $placed++
        }
    } catch {
        Say ("Erreur : " + $_.Exception.Message) Red
        if ($placed -eq 0) { Say "Rien n'a été modifié dans le jeu." }
        else { Say "L'installation s'est arrêtée en cours de route : relancez-la, elle reprendra où elle en était." }
        return 1
    } finally {
        if (Has-Dir $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue }
    }
    Say "Patch français installé." Green
    Say "Dans le jeu : Options > Language > English (le texte y est en français)."
    return 0
}

$code = 1
try { $code = @(Main)[-1] } catch { Say ("Erreur inattendue : " + $_.Exception.Message) Red; $code = 1 }
exit $code
