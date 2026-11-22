from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

# Register your models here.
from bridge import models


class HistoryAdmin(SimpleHistoryAdmin):
    list_display = ["id"]
    history_list_display = ["name", "user"]
    search_fields = ["name", "user__username"]


admin.site.register(models.OmeroUser, HistoryAdmin)
