# Testar POST /telhado/analisar; imagens na raiz: telhado_{id}_imagem.png
# A API deve estar a correr a partir da raiz do projeto (onde está o .env)
# Sem LIDAR: usa coordenadas fixas (Portugal). Com LIDAR: usa coords_covered_by_lidar se existir.
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
$baseUrl = "http://localhost:8000"

# Coordenadas fixas para teste (sem depender de LIDAR)
$coordsFixas = @(
    @{ lat = 38.843172347881364; lon = -9.198009875768737 },
    @{ lat = 38.84380801524735;  lon = -9.19820031567115 },
    @{ lat = 38.843717465063264; lon = -9.197987294607593 },
    @{ lat = 38.84464501070205;  lon = -9.19659456422345 },
    @{ lat = 38.823245; lon = -9.163455 }
)

$coords = $coordsFixas
$total = $coords.Count
Write-Host "A usar $total coordenadas (teste sem LIDAR)"
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
