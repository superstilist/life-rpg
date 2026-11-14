from django.urls import path
from . import views

app_name = 'game'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('start/', views.start_game_view, name='start_game'),
    path('play/', views.play_view, name='play'),
    path('action/', views.perform_action_view, name='action'),
    path('novel/advance/', views.advance_narrator_phase_view, name='novel_advance'),
    path('novel/skip/', views.skip_narrator_phase_view, name='novel_skip'),
    path('novel/choice/', views.resolve_story_choice_view, name='novel_choice'),
    path('novel/interlude/', views.interlude_action_view, name='novel_interlude'),
    path('chronicle/', views.chronicle_view, name='chronicle'),
    path('graveyard/', views.graveyard_view, name='graveyard'),
    path('retire/', views.retire_view, name='retire'),
]
