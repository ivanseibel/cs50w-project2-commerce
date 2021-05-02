from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from decimal import Decimal
from django.core.exceptions import ValidationError
from django import forms
import sys
from .models import User, Auction, Category
from django.shortcuts import get_object_or_404
from django.db import connections


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

class AuctionForm(forms.Form):
    title = forms.CharField(required=True)
    description = forms.CharField(required=True)
    starting_bid = forms.DecimalField(min_value=0)
    photo_url = forms.CharField(required=True)


def index(request):
    with connections['default'].cursor() as cursor:
        sql = ' \
            SELECT \
                a.id, \
                a.photo_url, \
                a.title, \
                a.description, \
                a.starting_bid, \
                COALESCE((SELECT MAX(b.value) FROM auctions_bid b WHERE b.auction_id = a.id),0) as max_bid, \
                created_at \
            FROM auctions_auction a \
        '
        cursor.execute(sql)
        auctions = dictfetchall(cursor)

    return render(request, "auctions/index.html",{
        "auctions": auctions
    })


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
        first_name = request.POST["first_name"]
        last_name = request.POST["last_name"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(
                username=username, 
                email=email, 
                first_name=first_name, 
                last_name=last_name, 
                password=password
            )
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
        form = AuctionForm(request.POST)
        if not form.is_valid():
            return render(request, "auctions/create-auction.html", {
                "message": form.errors.as_text
            })

        title = request.POST["title"]
        description = request.POST["description"]
        starting_bid = Decimal(request.POST["starting_bid"])
        photo_url = request.POST["photo_url"]
        user_id = request.POST["user_id"]
        category_id = request.POST["category_id"]

        try:
            auction = Auction(
                title=title, 
                description=description, 
                starting_bid=starting_bid, 
                photo_url=photo_url, 
                user_id=user_id, 
                category_id=category_id
            )
            auction.save()
        except:
            error = sys.exc_info()[0]
            return render(request, "auctions/create-auction.html", {
                "message": error
            })

        return HttpResponseRedirect(reverse("index"))
    else:
        categories = Category.objects.all()
        # print(categories[0].name)
        return render(request, "auctions/create-auction.html", {
            "categories": categories
        })


@login_required(login_url='login', )
def update_auction(request, auction_id):
    categories = Category.objects.all()
    try:     
        auction = Auction.objects.get(pk=auction_id)
        print(auction.title)
    except (Auction.DoesNotExist, ValidationError) as error:
        auction = None
        print(error)

    if auction == None:
        return HttpResponseRedirect(reverse("index"))
    
    if request.user.id != auction.user.id:
        return HttpResponseRedirect(reverse("index"))

    if request.method == "POST":
        form = AuctionForm(request.POST)
        if not form.is_valid():
            return render(request, "auctions/update-auction.html", {
                "message": form.errors.as_text,
                "categories": categories,
                "auction": auction,
            })

        auction.title = request.POST["title"]
        auction.description = request.POST["description"]
        auction.starting_bid = Decimal(request.POST["starting_bid"])
        auction.photo_url = request.POST["photo_url"]
        auction.category_id = request.POST["category_id"]

        try:
            auction.save()
        except:
            error = sys.exc_info()[0]
            return render(request, "auctions/update-auction.html", {
                "message": error
            })

        return HttpResponseRedirect(reverse("index"))

    if request.method == 'GET':
        return render(request, "auctions/update-auction.html", {
            "categories": categories,
            "auction": auction,
        })


def show_auction(request, auction_id):
    with connections['default'].cursor() as cursor:
        sql = ' \
            SELECT \
                a.id, \
                a.photo_url, \
                a.title, \
                a.description, \
                a.starting_bid, \
                u.username, \
                COALESCE(c.name, "No Category Listed.") as category_name, \
                COALESCE((SELECT MAX(b.value) FROM auctions_bid b WHERE b.auction_id = a.id),0) as max_bid, \
                COALESCE((SELECT COUNT(b.id) FROM auctions_bid b WHERE b.auction_id = a.id),0) as bid_count, \
                a.created_at \
            FROM auctions_auction a \
            INNER JOIN auctions_user u ON u.id = a.user_id \
            LEFT OUTER JOIN auctions_category c ON c.id = a.category_id \
            WHERE \
                a.id = %s \
        '
        cursor.execute(sql, [auction_id])
        auctions = dictfetchall(cursor)
        value_to_show = auctions[0]["starting_bid"] if auctions[0]["starting_bid"] > auctions[0]["max_bid"] else auctions[0]["max_bid"]
        
        print(auctions[0])

    return render(request, "auctions/show-auction.html",{
        "auctions": auctions,
        "value_to_show": value_to_show
    })
