from django.urls import path, include

urlpatterns = [
    # ... 其他URL patterns ...
    path('muggle/', include('muggle.urls')),
] 