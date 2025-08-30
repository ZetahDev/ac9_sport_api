param(
  [string]$BucketName = "ac9-sport-prod",
  [string]$Region = "us-east-2",
  [string]$PolicyFile = "ac9_s3_bucket_policy.json",
  # Comma-separated list of allowed origins. Use '*' to allow all origins (not recommended for production).
  [string]$AllowedOrigins = "http://localhost:3000,https://www.ac9sport.com"
)

Write-Host "Applying S3 configuration for bucket: $BucketName in region $Region"

try {
  # Create bucket if not exists
  Write-Host "Creating bucket (if not exists)..."
  aws s3api create-bucket --bucket $BucketName --region $Region --create-bucket-configuration LocationConstraint=$Region
}
catch {
  Write-Host "Create bucket may have failed (it might already exist): $_"
}

Write-Host "Applying public access block (block all public access)"
# Build the public access block config as a PowerShell object and write to a temp file
$publicBlock = @{ 
  BlockPublicAcls       = $true
  IgnorePublicAcls      = $true
  BlockPublicPolicy     = $true
  RestrictPublicBuckets = $true
}
$publicBlockFile = [System.IO.Path]::GetTempFileName() + ".json"
$publicBlockJson = $publicBlock | ConvertTo-Json -Depth 3
# Write without BOM to prevent parsing issues in some AWS CLI versions / Windows PowerShell
[System.IO.File]::WriteAllText($publicBlockFile, $publicBlockJson, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "PublicBlock JSON written to: $publicBlockFile"
aws s3api put-public-access-block --bucket $BucketName --public-access-block-configuration file://$publicBlockFile

Write-Host "Enabling versioning"
aws s3api put-bucket-versioning --bucket $BucketName --versioning-configuration Status=Enabled

Write-Host "Applying bucket policy from $PolicyFile"
aws s3api put-bucket-policy --bucket $BucketName --policy file://$PolicyFile

Write-Host "Setting default SSE-S3 encryption (AES256)"
# Server-side encryption configuration written to a temp file to avoid CLI JSON parsing issues
$sse = @{
  Rules = @(
    @{ ApplyServerSideEncryptionByDefault = @{ SSEAlgorithm = "AES256" } }
  )
}
$sseFile = [System.IO.Path]::GetTempFileName() + ".json"
$sseJson = $sse | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText($sseFile, $sseJson, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "SSE JSON written to: $sseFile"
aws s3api put-bucket-encryption --bucket $BucketName --server-side-encryption-configuration file://$sseFile

Write-Host "Applying CORS (adjust AllowedOrigins for production)"
# Build CORSRules payload (aws expects an object with CORSRules key)
$origins = @()
if ($AllowedOrigins -eq '*') {
  $origins = @("*")
}
else {
  $origins = $AllowedOrigins -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
}

$corsRules = @(
  @{ 
    # Allow common headers and wildcard to be permissive for browser PUTs
    AllowedHeaders = @("*")
    # Include OPTIONS for preflight plus write/read verbs
    # Include common write/read verbs (S3 does not accept OPTIONS as an AllowedMethod)
    AllowedMethods = @("PUT", "POST", "GET", "HEAD", "DELETE")
    AllowedOrigins = $origins
    ExposeHeaders  = @()
    MaxAgeSeconds  = 3000
  }
)
$corsPayload = @{ CORSRules = $corsRules }
$corsFile = [System.IO.Path]::GetTempFileName() + ".json"
$corsJson = $corsPayload | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText($corsFile, $corsJson, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "CORS JSON written to: $corsFile"
aws s3api put-bucket-cors --bucket $BucketName --cors-configuration file://$corsFile

# Cleanup temp files (best-effort)
try {
  Remove-Item -Path $publicBlockFile -ErrorAction SilentlyContinue
  Remove-Item -Path $sseFile -ErrorAction SilentlyContinue
  Remove-Item -Path $corsFile -ErrorAction SilentlyContinue
}
catch {
  # ignore cleanup errors
}

Write-Host "S3 configuration applied. You can validate with: aws s3api get-bucket-policy --bucket $BucketName"
