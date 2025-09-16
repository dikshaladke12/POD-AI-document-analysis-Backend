from django.contrib import admin
from .models import Users, EmailTemplate #Roles, ModuleRolePermissions, Modules

class RolesAdmin(admin.ModelAdmin):
    list_display = ('role_name',)
    search_fields = ('role_name',)

class UsersAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_superuser', 'is_active')
    ordering = ('email',)

admin.site.register(Users, UsersAdmin)

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'modified_date')
    search_fields = ('name', 'subject')