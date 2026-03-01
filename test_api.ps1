# Testar POST /telhado/analisar na API (local ou Docker em localhost:8000). Correr a API na raiz do projeto (onde está o .env).
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
$body = '{"lat": 38.823245206474496, "lon": -9.163455363593444}'
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8000/telhado/analisar" -Method Post -Body $body -ContentType "application/json"
    Write-Host "OK - id: $($r.id) area_total_m2: $($r.area_total_m2) aguas: $($r.aguas.Count)"
    if ($r.aguas -and $r.aguas.Count -gt 0) {
        foreach ($a in $r.aguas) { Write-Host "  agua: area_real_m2=$($a.area_real_m2) inclinacao=$($a.inclinacao_graus)° orientacao=$($a.orientacao_azimute)°" }
    }
    if ($r.imagem_url) {
        $imgUrl = "http://localhost:8000" + $r.imagem_url
        $outFile = "telhado_$($r.id)_imagem.png"
        Invoke-WebRequest -Uri $imgUrl -OutFile $outFile -UseBasicParsing
        Write-Host "Imagem guardada em $outFile"
    }
    $r | ConvertTo-Json -Depth 5
} catch {
    Write-Host "Erro:" $_.Exception.Message
    if ($_.Exception.Response) { $_.Exception.Response }
}
