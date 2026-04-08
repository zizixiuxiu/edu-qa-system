# 实验监控脚本 - 定期检查实验进度
param(
    [int]$IntervalMinutes = 10,  # 检查间隔（分钟）
    [int]$MaxHours = 10           # 最大监控时长（小时）
)

$startTime = Get-Date
$maxDuration = New-TimeSpan -Hours $MaxHours
$logFile = "experiment_monitor_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] $Message"
    Write-Host $logEntry
    Add-Content -Path $logFile -Value $logEntry
}

function Get-ExperimentStatus {
    try {
        $queue = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/experiments/queue" -Method GET -TimeoutSec 10
        $progress = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/benchmark/progress" -Method GET -TimeoutSec 10
        
        $running = $queue.queue | Where-Object { $_.status -eq "running" } | Select-Object -First 1
        $completed = ($queue.queue | Where-Object { $_.status -eq "completed" }).Count
        $pending = ($queue.queue | Where-Object { $_.status -eq "pending" }).Count
        
        return @{
            Success = $true
            RunningExp = $running
            Progress = $progress
            Completed = $completed
            Pending = $pending
            Total = $queue.total
        }
    } catch {
        return @{
            Success = $false
            Error = $_.Exception.Message
        }
    }
}

function Get-LatestReport {
    try {
        $reportsDir = "backend/app/benchmark_reports/reports"
        if (Test-Path $reportsDir) {
            $latest = Get-ChildItem -Path $reportsDir -Filter "*.json" | 
                Sort-Object LastWriteTime -Descending | 
                Select-Object -First 1
            if ($latest) {
                $content = Get-Content $latest.FullName -Raw | ConvertFrom-Json
                $summary = $content.results.summary
                return "最新报告: $($latest.Name) - 准确率: $($summary.accuracy_rate)%, 平均分: $($summary.avg_score)"
            }
        }
        return "暂无报告"
    } catch {
        return "获取报告失败"
    }
}

# 主监控循环
Write-Log "========================================"
Write-Log "🚀 实验监控任务启动"
Write-Log "========================================"
Write-Log "检查间隔: $IntervalMinutes 分钟"
Write-Log "最大监控时长: $MaxHours 小时"
Write-Log "日志文件: $logFile"
Write-Log ""

$checkCount = 0

while ($true) {
    $elapsed = (Get-Date) - $startTime
    
    # 检查是否超过最大监控时间
    if ($elapsed -gt $maxDuration) {
        Write-Log "⏰ 已达到最大监控时长 ($MaxHours 小时)，监控结束"
        break
    }
    
    $checkCount++
    Write-Log "--- 检查 #$checkCount (运行时长: $($elapsed.ToString('hh\:mm\:ss'))) ---"
    
    $status = Get-ExperimentStatus
    
    if (-not $status.Success) {
        Write-Log "❌ 获取状态失败: $($status.Error)"
    } else {
        if ($status.RunningExp) {
            $exp = $status.RunningExp
            $prog = $status.Progress
            Write-Log "🔄 正在运行: $($exp.name)"
            Write-Log "   进度: $($prog.current)/$($prog.total) ($([math]::Round($prog.current/$prog.total*100,1))%)"
            Write-Log "   当前题目: $($prog.current_question)"
            Write-Log "   状态: $($prog.status)"
        } else {
            Write-Log "⏸️  没有正在运行的实验"
        }
        
        Write-Log "📊 队列统计: 完成=$($status.Completed), 等待=$($status.Pending), 总计=$($status.Total)"
        
        # 如果有完成的实验，显示最新报告
        if ($status.Completed -gt 0) {
            $report = Get-LatestReport
            Write-Log "📈 $report"
        }
        
        # 检查是否全部完成
        if ($status.Completed -eq $status.Total -and $status.Total -gt 0) {
            Write-Log ""
            Write-Log "🎉 所有实验已完成！"
            Write-Log "========================================"
            break
        }
    }
    
    Write-Log ""
    
    # 等待下一次检查
    Start-Sleep -Seconds ($IntervalMinutes * 60)
}

Write-Log "监控任务结束"
Write-Log "总运行时长: $((Get-Date) - $startTime)"
