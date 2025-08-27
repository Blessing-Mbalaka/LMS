from django.contrib import admin
from .models import CustomUser
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Qualification


from django.contrib import admin
from .models import PaperReview
@admin.register(PaperReview)
class PaperReviewAdmin(admin.ModelAdmin):
    list_display = ("paper", "assessment", "decision", "role", "by", "created_at")
    search_fields = ("paper__id", "assessment__id", "by__username", "role", "decision")


#Custom User------
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active']
    ordering = ['-created_at']
    search_fields = ['email', 'first_name', 'last_name']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'qualification', 'activated_at', 'deactivated_at')}),
    )

admin.site.register(Qualification)