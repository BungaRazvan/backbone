from django.contrib import admin

from mytools.models import EtfShare, Etf, EtfEvent


class EtfShareInline(admin.StackedInline):
    ordering = ("-efs_purchase_date",)
    readonly_fields = ("efs_created_on",)
    model = EtfShare
    extra = 0


class EtfEventInline(admin.StackedInline):
    ordering = ("-ee_ex_date",)
    readonly_fields = ("ee_created_on",)
    model = EtfEvent
    extra = 0


@admin.register(Etf)
class EtfAdmin(admin.ModelAdmin):
    inlines = [EtfShareInline, EtfEventInline]
