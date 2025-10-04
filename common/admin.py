from django.contrib import admin

from common.models import AppToken


# Register your models here.
@admin.register(AppToken)
class AppTokenAdmin(admin.ModelAdmin):
    pass
