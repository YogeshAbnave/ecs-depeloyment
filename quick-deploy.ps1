# Quick Deploy Script - Single command to deploy changes
# Usage: .\quick-deploy.ps1

Write-Host "🚀 Quick Deploy - Deploying your changes..." -ForegroundColor Green

# Configuration
$AWS_REGION = "us-east-1"
$ECR_REPO = "992167236365.dkr.ecr.us-east-1.amazonaws.com/cloudage-app"
$CLUSTER_NAME = "cloudage-cluster"
$SERVICE_NAME = "cloudage-service"

# Step 0: Normalize proxy env (avoid proxying AWS ECR)
$env:http_proxy=""
$env:https_proxy=""
$env:HTTP_PROXY=""
$env:HTTPS_PROXY=""
$env:NO_PROXY="localhost,127.0.0.1,*.amazonaws.com,amazonaws.com,$ECR_REPO"
$env:no_proxy=$env:NO_PROXY

# Step 1: Login to ECR
Write-Host "🔑 Logging into ECR..." -ForegroundColor Yellow
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to login to ECR" -ForegroundColor Red
    exit 1
}

# Step 2: Build Docker image
Write-Host "🔨 Building Docker image..." -ForegroundColor Yellow
docker build -t cloudage-app .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to build Docker image" -ForegroundColor Red
    exit 1
}

# Step 3: Tag image
Write-Host "🏷️ Tagging image..." -ForegroundColor Yellow
docker tag cloudage-app:latest "$ECR_REPO`:latest"

# Step 4: Push to ECR (with retries/backoff)
Write-Host "📤 Pushing image to ECR..." -ForegroundColor Yellow
$attempt = 1
$maxAttempts = 5
do {
  docker push "$ECR_REPO`:latest"
  $rc = $LASTEXITCODE
  if ($rc -eq 0) { break }
  if ($attempt -ge $maxAttempts) {
    Write-Host "❌ Failed to push image to ECR after $attempt attempts (rc=$rc)" -ForegroundColor Red
    exit $rc
  }
  $sleepSeconds = $attempt * 5
  Write-Host "⚠️ Push failed (rc=$rc). Retrying in ${sleepSeconds}s... (attempt ${attempt}/${maxAttempts})" -ForegroundColor Yellow
  Start-Sleep -Seconds $sleepSeconds
  $attempt += 1
} while ($true)

# Step 5: Force new deployment
Write-Host "🔄 Deploying to ECS..." -ForegroundColor Yellow
aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force-new-deployment --region $AWS_REGION

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to update ECS service" -ForegroundColor Red
    exit 1
}

# Step 6: Wait for deployment
Write-Host "⏳ Waiting for deployment to complete..." -ForegroundColor Yellow
aws ecs wait services-stable --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION

# Step 7: Check deployment status
Write-Host "📊 Checking deployment status..." -ForegroundColor Yellow
$serviceStatus = aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query 'services[0].{Status:status,RunningCount:runningCount,DesiredCount:desiredCount}' --output json | ConvertFrom-Json

Write-Host "✅ Deployment Status:" -ForegroundColor Green
Write-Host "   Status: $($serviceStatus.Status)" -ForegroundColor Cyan
Write-Host "   Running Tasks: $($serviceStatus.RunningCount)/$($serviceStatus.DesiredCount)" -ForegroundColor Cyan

# Step 8: Get app URL
$albDns = aws elbv2 describe-load-balancers --names cloudage-alb --region $AWS_REGION --query 'LoadBalancers[0].DNSName' --output text

Write-Host ""
Write-Host "🎉 Deployment Complete!" -ForegroundColor Green
Write-Host "🌐 Your app is available at: http://$albDns" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 Next time you make changes, just run: .\quick-deploy.ps1" -ForegroundColor Yellow
