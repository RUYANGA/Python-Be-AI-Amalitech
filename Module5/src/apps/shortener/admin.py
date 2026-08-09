from django.contrib import admin

from apps.shortener.models import URL


@admin.register(URL)
class URLAdmin(admin.ModelAdmin):
    list_display = ("short_code", "original_url", "owner", "created_at")
    search_fields = ("short_code", "original_url")
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
    raw_id_fields = ("owner",)
