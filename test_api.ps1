# Testar POST /telhado/analisar na API (local ou Docker em localhost:8000)
$body = '{"lat": 38.823245206474496, "lon": -9.163455363593444}'
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8000/telhado/analisar" -Method Post -Body $body -ContentType "application/json"
    Write-Host "OK - id:" $r.id " area_total_m2:" $r.area_total_m2 " aguas:" $r.aguas.Count " imagem_url:" $r.imagem_url
    $imgUrl = "http://localhost:8000" + $r.imagem_url
    Invoke-WebRequest -Uri $imgUrl -OutFile "telhado_imagem.png" -UseBasicParsing
    Write-Host "Imagem guardada em telhado_imagem.png"
    $r | ConvertTo-Json -Depth 5
} catch {
    Write-Host "Erro:" $_.Exception.Message
    if ($_.Exception.Response) { $_.Exception.Response }
}
