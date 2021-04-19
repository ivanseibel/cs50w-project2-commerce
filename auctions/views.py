from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from decimal import Decimal
from django import forms
import sys
from .models import User, Auction, Category

class CreateAuctionForm(forms.Form):
    title = forms.CharField(required=True)
    description = forms.CharField(required=True)
    starting_bid = forms.DecimalField(min_value=0)
    photo_url = forms.CharField(required=True)


def index(request):
    return render(request, "auctions/index.html")


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    """Provides a link where users can do logout."""
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")

@login_required(login_url='login')
def create_auction(request):
    if request.method == "POST":
        form = CreateAuctionForm(request.POST)
        if not form.is_valid():
            return render(request, "auctions/create-auction.html", {
                "message": form.errors.as_text
            })

        title = request.POST["title"]
        description = request.POST["description"]
        starting_bid = Decimal(request.POST["starting_bid"])
        photo_url = request.POST["photo_url"]
        user_id = request.POST["user_id"]

        try:
            auction = Auction(title=title, description=description, starting_bid=starting_bid, photo_url=photo_url, user_id=user_id)
            auction.save()
        except:
            print("Unexpected error:", sys.exc_info()[0])
            return render(request, "auctions/create-auction.html", {
                "message": "Testing errors."
            })

        return render(request, "auctions/index.html")
    else:
        categories = Category.objects.all()
        # print(categories[0].name)
        return render(request, "auctions/create-auction.html", {
            "categories": categories
        })
