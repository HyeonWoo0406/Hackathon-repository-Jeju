param([switch]$Check)
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectPath
$pythonPath = Join-Path $projectPath '.venv/Scripts/python.exe'
$taskName = 'JejuWeeklyPublicData'
if (!(Test-Path -LiteralPath $pythonPath)) { throw '프로젝트의 Python 환경이 없습니다.' }
if ($Check) { Write-Output '관리 파일 경로 확인 완료'; exit 0 }

function Show-Task {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if (!$task) { Write-Host '자동 수집이 등록되지 않았습니다. 4번으로 등록하세요.'; return }
    $info = Get-ScheduledTaskInfo -TaskName $taskName
    Write-Host "자동 수집 상태: $($task.State) / 다음 실행: $($info.NextRunTime)"
    Write-Host "최근 실행: $($info.LastRunTime) / 종료 코드: $($info.LastTaskResult)"
}

while ($true) {
    Write-Host '
=== 제주 공개 데이터 수집 관리 ===' -ForegroundColor Cyan
    Write-Host '1. 지금 수집 실행 (한 번 실행 후 종료)'
    Write-Host '2. 최근 수집 기록 확인'
    Write-Host '3. 자동 수집 상태 확인'
    Write-Host '4. 자동 수집 켜기 / 등록 (매일 오전 6시)'
    Write-Host '5. 자동 수집 끄기 (다음 예약 실행부터 중지)'
    Write-Host '0. 관리 창 닫기'
    Write-Host '자동 수집에는 PC 전원과 Windows 로그인이 필요합니다.'
    $choice = Read-Host '번호 선택'
    if ($choice -eq '0') { break }
    try {
        switch ($choice) {
            '1' {
                Write-Host '수집 중입니다. 완료될 때까지 기다려 주세요. 중단은 Ctrl+C입니다.'
                $result = & $pythonPath (Join-Path $PSScriptRoot 'collect_public.py') --run
                if ($LASTEXITCODE -ne 0) { throw '수집 실행에 실패했습니다. 위 오류를 확인하세요.' }
                $record = ($result -join "`n") | ConvertFrom-Json
                Write-Host "이번 실행 완료 요청: $($record.completed) / 시도한 요청: $($record.attempted)"
                if ($record.usage) { Write-Host "오늘 수집기 호출: $($record.usage.calls) / 자체 상한: $($record.usage.cap)" }
                if ($record.stopped -eq 'provider_quota') {
                    Write-Host '제공처 일일 한도가 소진되어 중지했습니다. 한도 복구 후 다시 수집해야 합니다.' -ForegroundColor Yellow
                } elseif ($record.stopped) { Write-Host "중지 사유: $($record.stopped)" -ForegroundColor Yellow }
                Write-Host '실행이 끝났습니다. 실행 종료가 모든 자료의 준비 완료를 뜻하지는 않습니다.'
            }
            '2' {
                $logPath = Join-Path $projectPath 'runtime/collection-log.jsonl'
                if (Test-Path -LiteralPath $logPath) {
                    Get-Content -LiteralPath $logPath -Encoding UTF8 -Tail 10 | ForEach-Object {
                        $r = $_ | ConvertFrom-Json
                        Write-Host "[$($r.at)] 수집실행=$($r.run) 완료=$($r.completed) 시도=$($r.attempted) 호출=$($r.usage.calls) 중지=$($r.stopped)"
                    }
                } else { Write-Host '아직 기록이 없습니다.' }
            }
            '3' { Show-Task }
            '4' {
                & (Join-Path $PSScriptRoot 'install_collection_task.ps1')
                Write-Host '매일 오전 6시 자동 수집을 켰습니다. 놓친 예약은 가능한 때 실행될 수 있습니다.'
                Show-Task
            }
            '5' {
                Disable-ScheduledTask -TaskName $taskName | Out-Null
                Write-Host '예약 실행을 껐습니다. 이미 실행 중인 수집은 중단하지 않습니다.'
                Show-Task
            }
            default { Write-Host '0~5 사이 번호를 입력하세요.' }
        }
    } catch { Write-Host "오류: $($_.Exception.Message)" -ForegroundColor Red }
    Read-Host 'Enter를 누르면 메뉴로 돌아갑니다' | Out-Null
}
