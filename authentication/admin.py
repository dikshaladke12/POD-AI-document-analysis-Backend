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

# admin.site.register(Roles, RolesAdmin)
admin.site.register(Users, UsersAdmin)
# admin.site.register(Modules)
# admin.site.register(ModuleRolePermissions)

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'modified_date')
    search_fields = ('name', 'subject')


# from django.contrib import admin
# from .models import Roles, Users, Modules, ModuleRolePermissions, EmailTemplate
# # Register your models here.

# class RolesAdmin(admin.ModelAdmin):
#     list_display = ('role_name',)
#     search_fields = ('role_name',)

# class UsersAdmin(admin.ModelAdmin):
#     list_display = ('email', 'first_name', 'last_name', 'role_id', 'is_active', 'is_staff')
#     search_fields = ('email', 'first_name', 'last_name')
#     list_filter = ('is_staff', 'is_superuser', 'is_active', 'role_id')
#     ordering = ('email',)
    

# admin.site.register(Roles, RolesAdmin)
# admin.site.register(Users, UsersAdmin)
# admin.site.register(Modules)
# admin.site.register(ModuleRolePermissions)


# @admin.register(EmailTemplate)
# class EmailTemplateAdmin(admin.ModelAdmin):
#     list_display = ('name', 'subject', 'modified_date')
#     search_fields = ('name', 'subject')