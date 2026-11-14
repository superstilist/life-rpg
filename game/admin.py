from django.contrib import admin
from .models import Character, Item, InventoryItem, LogEntry

@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ('name', 'race', 'age', 'turns', 'hp', 'mana', 'gold', 'score', 'is_alive')
    list_filter = ('race', 'is_alive')
    search_fields = ('name', 'origin')

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'item_type', 'price')
    list_filter = ('item_type',)

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('character', 'item', 'quantity')

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('character', 'age', 'turn', 'title', 'log_type', 'created_at')
    list_filter = ('log_type',)
