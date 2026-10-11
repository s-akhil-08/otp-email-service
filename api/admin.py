from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, TempUser, OTP, PasswordChangeHistory


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'name', 'mobile', 'is_verified', 'is_staff')
    search_fields = ('email', 'name')
    ordering = ('email',)


@admin.register(TempUser)
class TempUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'mobile', 'otp', 'created_at')
    search_fields = ('email', 'name', 'otp')
    readonly_fields = ('created_at',)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp', 'created_at')
    search_fields = ('user__email', 'otp')
    readonly_fields = ('created_at',)


@admin.register(PasswordChangeHistory)
class PasswordChangeHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'changed_at')
    search_fields = ('user__email',)
    readonly_fields = ('user', 'old_password_hashed', 'new_password_hashed', 'changed_at')
