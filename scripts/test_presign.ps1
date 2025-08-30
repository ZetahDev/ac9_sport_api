<#
PowerShell script to test POST /uploads/presign without killing the current server console.
Usage examples:
  # Basic
  pwsh -File .\scripts\test_presign.ps1

  # Provide a custom key and token
  pwsh -File .\scripts\test_presign.ps1 -Key 'products/myfile.jpg' -Token '<TOKEN>'

This script prints HTTP status and response body even on non-2xx responses.
#>
param(
    [string]$Key = "products/test.jpg",
    [string]$ContentType = "image/jpeg",
    [string]$Url = "http://127.0.0.1:8000/uploads/presign",
    [string]$Token = ""
)

Write-Host "POST $Url" -ForegroundColor Cyan
Write-Host "Key: $Key | Content-Type: $ContentType" -ForegroundColor Cyan

$body = @{ key = $Key; content_type = $ContentType } | ConvertTo-Json
$headers = @{}
if ($Token -ne "") { $headers["Authorization"] = "Bearer $Token" }

try {
    $response = Invoke-WebRequest -Uri $Url -Method Post -ContentType 'application/json' -Body $body -Headers $headers -UseBasicParsing -ErrorAction Stop
    $status = $response.StatusCode
    Write-Host "StatusCode: $status" -ForegroundColor Green
    try {
        $json = $response.Content | ConvertFrom-Json
        $json | ConvertTo-Json -Depth 6
    } catch {
        Write-Host $response.Content
    }
} catch [System.Net.WebException] {
    $we = $_.Exception
    $resp = $we.Response
    if ($resp -ne $null) {
        $status = $resp.StatusCode.value__
        Write-Host "HTTP Error: $status" -ForegroundColor Red
        $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
        $respBody = $reader.ReadToEnd()
        try { $respBody | ConvertFrom-Json | ConvertTo-Json -Depth 6 } catch { Write-Host $respBody }
    } else {
        Write-Host "Network error: $($we.Message)" -ForegroundColor Red
    }
} catch {
    Write-Host "Unexpected error: $($_.Exception.Message)" -ForegroundColor Red
}

# Exit with success so calling shells don't get killed; set non-zero if needed
exit 0
