from django.urls import path
from .views import (
    CartDetailView, 
    CartAddView, 
    CartDecrementView, 
    CartRemoveItemView, 
    CartClearView
)

app_name = 'cart'

urlpatterns = [
    path('', CartDetailView.as_view(), name='cart-detail'),
    path('add/', CartAddView.as_view(), name='cart-add'),
    path('decrement/', CartDecrementView.as_view(), name='cart-decrement'),
    path('remove-item/', CartRemoveItemView.as_view(), name='cart-remove-item'),
    path('clear/', CartClearView.as_view(), name='cart-clear'),
]