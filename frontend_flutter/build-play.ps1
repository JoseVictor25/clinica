param(
    [Parameter(Mandatory = $true)]
    [string]$ApiBaseUrl
)

$ErrorActionPreference = 'Stop'
$normalizedApiUrl = $ApiBaseUrl.Trim()
if (-not $normalizedApiUrl.EndsWith('/')) {
    $normalizedApiUrl += '/'
}

$parsedApiUrl = $null
if (-not [Uri]::TryCreate($normalizedApiUrl, [UriKind]::Absolute, [ref]$parsedApiUrl)) {
    throw 'ApiBaseUrl must be an absolute HTTPS URL ending in /api/v1/.'
}
if ($parsedApiUrl.Scheme -ne 'https' -or $parsedApiUrl.AbsolutePath.TrimEnd('/').ToLowerInvariant() -ne '/api/v1') {
    throw 'ApiBaseUrl must use HTTPS and end in /api/v1/.'
}
if ($parsedApiUrl.Host -in @('localhost', '127.0.0.1', '10.0.2.2')) {
    throw 'A production AAB cannot point to localhost or the Android emulator.'
}
$parsedIp = $null
if ([System.Net.IPAddress]::TryParse($parsedApiUrl.Host, [ref]$parsedIp)) {
    throw 'Use a domain with a valid TLS certificate; do not publish with an IP as the API host.'
}

$androidRoot = Join-Path $PSScriptRoot 'android'
$signingFile = Join-Path $androidRoot 'key.properties'
if (-not (Test-Path -LiteralPath $signingFile)) {
    throw 'Missing android/key.properties. Configure your Play upload key as documented in docs/app-movil-play.md.'
}

$storeFileLine = Get-Content -LiteralPath $signingFile | Where-Object { $_ -match '^\s*storeFile\s*=' } | Select-Object -First 1
if (-not $storeFileLine) {
    throw 'android/key.properties does not define storeFile.'
}
$storeFile = ($storeFileLine -split '=', 2)[1].Trim()
$keystorePath = if ([IO.Path]::IsPathRooted($storeFile)) {
    $storeFile
} else {
    Join-Path $androidRoot $storeFile
}
if (-not (Test-Path -LiteralPath $keystorePath)) {
    throw 'The keystore configured in android/key.properties was not found.'
}

Push-Location $PSScriptRoot
try {
    flutter build appbundle --release `
        "--dart-define=API_BASE_URL=$normalizedApiUrl" `
        "--dart-define=API_BASE_URL_ANDROID=$normalizedApiUrl"
    if ($LASTEXITCODE -ne 0) {
        throw 'Flutter failed to generate the Android App Bundle.'
    }
    Write-Output 'Production AAB: build/app/outputs/bundle/release/app-release.aab'
} finally {
    Pop-Location
}
