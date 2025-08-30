<#
Script que: 1) solicita presigned URL (si no se pasa), 2) sube un archivo local a S3 con PUT, 3) crea el producto vía /products/presign-create
Uso (PowerShell v5.1):
  powershell.exe -ExecutionPolicy Bypass -File .\scripts\upload_and_create_product.ps1 -Token '<TOKEN>'
Parámetros principales:
  -Token       : (required) Bearer token admin
  -LocalFile   : ruta local al archivo (por defecto la que proporcionaste)
  -Key         : clave en S3 (ej: products/892917-1200-auto.webp)
  -UploadUrl   : si ya tienes upload_url puedes pasarlo (evita la llamada a /uploads/presign)

El script imprime status y cuerpos de respuesta.
#>
param(
    [Parameter(Mandatory=$false)] [string]$Key = "products/892917-1200-auto.webp",
    [Parameter(Mandatory=$false)] [string]$LocalFile = "C:\Users\johan\Downloads\nike\892917-1200-auto.webp",
    [Parameter(Mandatory=$true)]  [string]$Token,
    [Parameter(Mandatory=$false)] [string]$UploadUrl = "",
    [Parameter(Mandatory=$false)] [string]$ContentType = "image/webp",
    [Parameter(Mandatory=$false)] [string]$ProductName = "Nike 892917",
    [Parameter(Mandatory=$false)] [string]$Description = "Producto subido con presigned URL",
    [Parameter(Mandatory=$false)] [string]$Price = "780000",
    [Parameter(Mandatory=$false)] [string[]]$Sizes = @("10","10.5","11"),
    [Parameter(Mandatory=$false)] [string[]]$Colors = @("gris"),
    [Parameter(Mandatory=$false)] [string[]]$CategoryIds = @("68b219f06a04cacdd7b3193e"),
    [Parameter(Mandatory=$false)] [string]$ApiBase = "http://127.0.0.1:8000"
)

Write-Host "Starting upload+create script" -ForegroundColor Cyan
Write-Host "LocalFile: $LocalFile" -ForegroundColor Cyan
Write-Host "Key: $Key" -ForegroundColor Cyan

if (-not (Test-Path $LocalFile)) {
    Write-Host "ERROR: Local file not found: $LocalFile" -ForegroundColor Red
    exit 1
}

# If UploadUrl not provided, request presign
if (-not [string]::IsNullOrEmpty($UploadUrl) -and $UploadUrl.Trim() -ne "") {
    Write-Host "Using provided UploadUrl" -ForegroundColor Yellow
} else {
    Write-Host "Requesting presigned URL from $ApiBase/uploads/presign" -ForegroundColor Yellow
    $presignBody = @{ key = $Key; content_type = $ContentType } | ConvertTo-Json
    try {
        $presignResp = Invoke-RestMethod -Uri "$ApiBase/uploads/presign" -Method Post -ContentType 'application/json' -Body $presignBody -Headers @{ Authorization = "Bearer $Token" } -ErrorAction Stop
        Write-Host "Presign response status: OK" -ForegroundColor Green
        $UploadUrl = $presignResp.upload_url
        $Key = $presignResp.key
        Write-Host "UploadUrl: $UploadUrl" -ForegroundColor Green
        Write-Host "Key returned: $Key" -ForegroundColor Green
    } catch {
        Write-Host "Failed to obtain presigned URL:" -ForegroundColor Red
        if ($_.Exception -and $_.Exception.Response) {
            $r = $_.Exception.Response
            $sr = New-Object System.IO.StreamReader($r.GetResponseStream())
            $body = $sr.ReadToEnd()
            Write-Host $body
        } else {
            Write-Host $_.Exception.Message
        }
        exit 1
    }
}

# PUT the file to the presigned URL
Write-Host "Uploading file to presigned URL..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Method Put -Uri $UploadUrl -InFile $LocalFile -ContentType $ContentType -UseBasicParsing -ErrorAction Stop
    Write-Host "File uploaded successfully (PUT)" -ForegroundColor Green
} catch {
    Write-Host "File upload (PUT) failed:" -ForegroundColor Red
    if ($_.Exception -and $_.Exception.Response) {
        $r = $_.Exception.Response
        $sr = New-Object System.IO.StreamReader($r.GetResponseStream())
        $body = $sr.ReadToEnd()
        Write-Host $body
    } else {
        Write-Host $_.Exception.Message
    }
    exit 1
}

# Create product with presigned-create
Write-Host "Creating product via $ApiBase/products/presign-create" -ForegroundColor Yellow
$createBody = @{
    name = $ProductName
    description = $Description
    price = [double]$Price
    sizes = $Sizes
    colors = $Colors
    categoryIds = $CategoryIds
    images = @($Key)
} | ConvertTo-Json -Depth 6

try {
    $createResp = Invoke-RestMethod -Uri "$ApiBase/products/presign-create" -Method Post -ContentType 'application/json' -Body $createBody -Headers @{ Authorization = "Bearer $Token" } -ErrorAction Stop
    Write-Host "Product created:" -ForegroundColor Green
    $createResp | ConvertTo-Json -Depth 6
} catch {
    Write-Host "Product creation failed:" -ForegroundColor Red
    if ($_.Exception -and $_.Exception.Response) {
        $r = $_.Exception.Response
        $sr = New-Object System.IO.StreamReader($r.GetResponseStream())
        $body = $sr.ReadToEnd()
        try { $body | ConvertFrom-Json | ConvertTo-Json -Depth 6 } catch { Write-Host $body }
    } else {
        Write-Host $_.Exception.Message
    }
    exit 1
}

Write-Host "Done." -ForegroundColor Cyan
exit 0
