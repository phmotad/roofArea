# Testar POST /telhado/analisar com coordenadas cobertas pelo LIDAR (lidar/); imagens na raiz: telhado_{id}_imagem.png
# A API deve estar a correr a partir da raiz do projeto (onde está o .env) e reiniciada após alterar .env
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
$baseUrl = "http://localhost:8000"

$pythonScript = Join-Path $scriptDir "scripts\coords_covered_by_lidar.py"
$coordsFromLidar = @()
if (Test-Path $pythonScript) {
    $lines = & python -m scripts.coords_covered_by_lidar --max 10 2>$null
    foreach ($line in $lines) {
        $line = $line.Trim()
        if ($line -match "^([\d.-]+),([\d.-]+)$") {
            $coordsFromLidar += @{ lat = [double]$Matches[1]; lon = [double]$Matches[2] }
        }
    }
}
if (-not $coordsFromLidar.Count) {
    Write-Host "Nenhuma coordenada coberta pelo LIDAR. Coloque GeoTIFFs em lidar/ e confirme LIDAR_DGT_PATH no .env"
    exit 1
}
$coords = $coordsFromLidar
$total = $coords.Count
Write-Host "A usar $total coordenadas cobertas pelo LIDAR (lidar/)"
$n = 0
foreach ($c in $coords) {
    $n++
    $body = "{`"lat`": $($c.lat), `"lon`": $($c.lon)}"
    Write-Host "[$n/$total] lat=$($c.lat) lon=$($c.lon)"
    try {
        $r = Invoke-RestMethod -Uri "$baseUrl/telhado/analisar" -Method Post -Body $body -ContentType "application/json"
        Write-Host "  OK id=$($r.id) area_total_m2=$($r.area_total_m2) aguas=$($r.aguas.Count)"
        if ($r.aguas -and $r.aguas.Count -gt 0) {
            foreach ($a in $r.aguas) {
                Write-Host "    agua: area_real_m2=$($a.area_real_m2) inclinacao=$($a.inclinacao_graus) orientacao=$($a.orientacao_azimute)"
            }
        }
        if ($r.imagem_url) {
            $outFile = "telhado_$($r.id)_imagem.png"
            Invoke-WebRequest -Uri "$baseUrl$($r.imagem_url)" -OutFile $outFile -UseBasicParsing
            Write-Host "  Imagem: $outFile"
        }
    } catch {
        Write-Host "  Erro: $($_.Exception.Message)"
    }
}
Write-Host "Concluido. Imagens na raiz do projeto."
