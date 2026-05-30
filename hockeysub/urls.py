from django.urls import path
from . import views

app_name = 'hockeysub'
urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.create_game, name='create_game'),
    path('games/', views.game_list, name='game_list'),
    path('game/<int:game_id>/', views.game_detail, name='game_detail'),
    path('game/<int:game_id>/edit/', views.edit_game, name='edit_game'),
    path('game/<int:game_id>/generate/', views.generate_schedule, name='generate_schedule'),
    path('game/<int:game_id>/schedule/', views.view_schedule, name='view_schedule'),
    path('game/<int:game_id>/schedule/version/<int:version>/', views.view_schedule_version, name='view_schedule_version'),
    path('game/<int:game_id>/schedule/activate/<int:version>/', views.activate_schedule_version, name='activate_schedule_version'),
]