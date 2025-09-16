from django.urls import path
from .views.authviews import (
    RegisterUser, 
    LoginUser
)
from .views.emailviews import *

urlpatterns = [  
    path('register/', RegisterUser.as_view(), name='register'),
    path('login/', LoginUser.as_view(), name='login'),
]
