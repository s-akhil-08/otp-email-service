from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse, JsonResponse


def home(request):
    # Support JSON response when Accept: application/json is requested
    if "application/json" in request.META.get("HTTP_ACCEPT", ""):
        return JsonResponse({
            "service": "CADverse OTP & Auth Microservice",
            "status": "running",
            "version": "1.0.0",
            "health": "/health/",
            "docs": "https://github.com/s-akhil-08/otp-email-service",
        })

    return HttpResponse("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CADverse OTP & Email Microservice</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box;">
    <div style="background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 40px 32px; max-width: 480px; width: 100%; text-align: center; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);">
        <div style="font-size: 48px; margin-bottom: 12px;">🔐</div>
        <h1 style="margin: 0 0 10px 0; font-size: 24px; font-weight: 700; color: #ffffff;">CADverse OTP & Email Service</h1>
        <p style="margin: 0 0 24px 0; color: #94a3b8; font-size: 14px;">Authentication, verification, and notification backend</p>
        
        <div style="display: inline-flex; align-items: center; gap: 8px; background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); color: #4ade80; padding: 6px 16px; border-radius: 9999px; font-size: 13px; font-weight: 600; margin-bottom: 24px;">
            <span style="display: inline-block; width: 8px; height: 8px; background-color: #22c55e; border-radius: 50%;"></span>
            Operational • v1.0.0
        </div>
        
        <div style="display: flex; justify-content: center; gap: 16px; font-size: 14px;">
            <a href="/health/" style="color: #38bdf8; text-decoration: none; font-weight: 500; border-bottom: 1px dashed #38bdf8; padding-bottom: 2px;">Health Check</a>
            <span style="color: #475569;">•</span>
            <a href="https://github.com/s-akhil-08/otp-email-service" target="_blank" rel="noopener noreferrer" style="color: #38bdf8; text-decoration: none; font-weight: 500; border-bottom: 1px dashed #38bdf8; padding-bottom: 2px;">Source Code</a>
        </div>
    </div>
</body>
</html>""")


def health_check(request):
    return JsonResponse({
        "status": "healthy",
        "service": "CADverse OTP & Auth Microservice",
        "version": "1.0.0"
    })


urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('health', health_check),
    path('health/', health_check),
]
