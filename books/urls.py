from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    path('', views.LibraryView.as_view(), name='library'),
    path('upload/', views.BookUploadView.as_view(), name='upload'),
    path('book/<int:pk>/', views.BookReaderView.as_view(), name='reader'),
    path('book/<int:pk>/delete/', views.BookDeleteView.as_view(), name='delete'),
    path('book/<int:book_id>/chapter/<int:chapter_id>/', views.chapter_view, name='chapter'),
    path('book/<int:book_id>/progress/', views.update_progress, name='update_progress'),
    path('debug/progress/', views.debug_progress, name='debug_progress'),
    path('book/<int:book_id>/pdf/', views.pdf_options, name='pdf_options'),
    path('book/<int:book_id>/pdf/generate/', views.generate_pdf, name='generate_pdf'),
]
