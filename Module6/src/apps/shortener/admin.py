"""Admin registrations for the shortener models."""

from django.contrib import admin

from apps.shortener.models import URL, Click, Tag


class ClickInline(admin.TabularInline):
    model = Click
    extra = 0
    readonly_fields = ("ip_address", "user_agent", "country", "city", "referer", "clicked_at")


@admin.register(URL)
class URLAdmin(admin.ModelAdmin):
    list_display = ("short_code", "original_url", "owner", "click_count", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("short_code", "original_url", "title")
    readonly_fields = ("short_code", "click_count", "created_at", "updated_at")
    filter_horizontal = ("tags",)
    inlines = (ClickInline,)


@admin.register(Click)
class ClickAdmin(admin.ModelAdmin):
    list_display = ("url", "ip_address", "country", "city", "clicked_at")
    list_filter = ("country", "clicked_at")
    search_fields = ("ip_address", "referer")
    readonly_fields = ("clicked_at",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
