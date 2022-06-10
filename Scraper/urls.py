from django.urls import path, include

from Scraper import views

urlpatterns = [
    path('', views.home, name='home'),
    path('category', views.category, name='category'),
    path('csvCat', views.uploadCsvCategories, name='csvCat'),
    # path('stop', views.stop, name='stop')
]
