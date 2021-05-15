from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("create_auction", views.create_auction, name="create_auction"),
    path("update_auction/<str:auction_id>",
         views.update_auction, name="update_auction"),
    path("show_auction/<str:auction_id>",
         views.show_auction, name="show_auction"),
    path("add_watchlist/<str:auction_id>",
         views.add_watchlist, name="add_watchlist"),
    path("delete_watchlist/<str:watchlist_id>",
         views.delete_watchlist, name="delete_watchlist"),
]
