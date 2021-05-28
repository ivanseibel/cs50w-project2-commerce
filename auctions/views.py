from django.contrib.auth import authenticate, get_user, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from decimal import Decimal
from django.core.exceptions import ValidationError
from django import forms
import sys
from .models import Bid, Comment, User, Auction, Category, Watchlist
from django.shortcuts import get_object_or_404
from django.db import connections
from uuid import UUID


def dict_fetch_all(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def get_auction(auction_id):
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
                COALESCE((SELECT MAX(b.value) FROM auctions_bid b WHERE b.auction_id = a.id),0) AS max_bid, \
                COALESCE((SELECT COUNT(b.id) FROM auctions_bid b WHERE b.auction_id = a.id),0) AS bid_count, \
                a.created_at, \
                w.id AS watchlist_id, \
                (SELECT user_id FROM auctions_bid ab WHERE ab.auction_id = a.id ORDER BY ab.value DESC LIMIT 1) AS user_last_bid, \
                a.closed \
            FROM auctions_auction a \
            INNER JOIN auctions_user u ON u.id = a.user_id \
            LEFT OUTER JOIN auctions_category c ON c.id = a.category_id \
            LEFT OUTER JOIN auctions_watchlist w ON w.auction_id = a.id \
            WHERE \
                a.id = %s \
        '
        cursor.execute(sql, [auction_id])
        auctions = dict_fetch_all(cursor)

    if len(auctions) > 0:
        return auctions[0]
    else:
        None


def render_show_auction(request, auction_id, message):
    auction = get_auction(auction_id=auction_id)
    value_to_show = auction["starting_bid"] if auction[
        "starting_bid"] > auction["max_bid"] else auction["max_bid"]
    comments = Comment.objects.filter(
        auction_id=auction_id).order_by("-created_at")

    return render(request, "auctions/show-auction.html", {
        "auction": auction,
        "value_to_show": value_to_show,
        "comments": comments,
        "message": message
    })


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
                a.created_at, \
                a.closed \
            FROM auctions_auction a \
            LEFT OUTER JOIN auctions_watchlist w ON w.auction_id = a.id  \
            LEFT OUTER JOIN auctions_category c ON c.id = a.category_id  \
        '

        if request.path == "/watchlist":
            sql = sql + '\
                WHERE w.user_id = %s \
            '
            user_id = get_user(request).id
            cursor.execute(sql, [user_id])
        elif request.GET["category_id"] != "":
            sql = sql + '\
                WHERE c.id = %s \
                AND a.closed = 0 \
            '
            category_id = UUID(str(request.GET["category_id"])).hex
            cursor.execute(sql, [category_id])
        else:
            sql = sql + '\
                WHERE a.closed=0 \
            '
            cursor.execute(sql)

        auctions = dict_fetch_all(cursor)

    return render(request, "auctions/index.html", {
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
            # Get all user bids
            user_watching_bids = Watchlist.objects.filter(
                user_id=user.id).count()
            request.session['user_watching_bids'] = user_watching_bids
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
        return render(request, "auctions/create-auction.html", {
            "categories": categories
        })


@login_required(login_url='login')
def update_auction(request, auction_id):
    categories = Category.objects.all()
    try:
        auction = Auction.objects.get(pk=auction_id)
    except (Auction.DoesNotExist, ValidationError) as error:
        # TODO: Add better error catch
        auction = None

    if auction == None:
        # TODO: return error Auction doesn't exist
        return HttpResponseRedirect(reverse("index"))

    if request.user.id != auction.user.id:
        # TODO: return Auction update denied
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
            return redirect("show_auction", auction_id=UUID(str(auction_id)).hex)
        except:
            error = sys.exc_info()[0]
            return render(request, "auctions/update-auction.html", {
                "message": error
            })

    if request.method == 'GET':
        return render(request, "auctions/update-auction.html", {
            "categories": categories,
            "auction": auction,
        })


def show_auction(request, auction_id):
    return render_show_auction(request=request, auction_id=auction_id, message="")


@login_required(login_url='login')
def add_watchlist(request, auction_id):
    # get user id
    user_id = get_user(request).id

    # try to add auction to watchlist
    try:
        watchlist = Watchlist(
            auction_id=auction_id,
            user_id=user_id
        )
        watchlist.save()
        request.session['user_watching_bids'] = request.session['user_watching_bids'] + 1

        # redirect to the same item
        return redirect("show_auction", auction_id=auction_id)
    except:
        error = sys.exc_info()[0]
        return render_show_auction(
            request=request,
            auction_id=auction_id,
            message=error
        )


@login_required(login_url='login')
def delete_watchlist(request, watchlist_id):
    # try to delete an auction from the watchlist
    try:
        watchlist = Watchlist.objects.filter(id=watchlist_id)
        auction_id = UUID(str(watchlist[0].auction_id)).hex
        watchlist.delete()
        request.session['user_watching_bids'] = request.session['user_watching_bids'] - 1

        # redirect to the same item
        return redirect("show_auction", auction_id=auction_id)
    except:
        error = sys.exc_info()[0]
        return render_show_auction(
            request=request,
            auction_id=auction_id,
            message=error
        )


@login_required(login_url='login')
def post_bid(request, auction_id):
    if request.method == 'POST':
        value = float(request.POST["bid_value"])
        user_id = get_user(request).id
        auction = Auction.objects.get(id=auction_id)
        bid = auction.bids.all().order_by('-value')[0]
        max_bid = bid.value if bid != None else 0

        if not value > max_bid:
            formatted_value = "%.2f" % max_bid
            return render_show_auction(
                request=request,
                auction_id=auction_id,
                message=f"Your bid must be higher than ${formatted_value}."
            )

        # Attempt to create new bid
        try:
            bid = Bid.objects.create(
                value=value,
                user_id=user_id,
                auction_id=auction_id,
            )
            bid.save()

            return redirect("show_auction", auction_id=auction_id)
        except:
            error = sys.exc_info()[0]
            return render_show_auction(
                request=request,
                auction_id=auction_id,
                message=error
            )
    else:
        return HttpResponseRedirect(reverse("index"))


@login_required(login_url='login')
def close_auction(request, auction_id):
    if request.method == 'POST':
        auction = Auction.objects.get(id=auction_id)
        auction.closed = True
        auction.save()
        return HttpResponseRedirect(reverse("index"))
    else:
        return HttpResponseRedirect(reverse("index"))


@login_required(login_url='login')
def post_comment(request, auction_id):
    if request.method == 'POST':
        comment_text = request.POST["comment_text"]
        user_id = get_user(request).id

        if comment_text == "":
            return render_show_auction(
                request=request,
                auction_id=auction_id,
                message="Comment text is required."
            )

        # Attempt to create new bid
        try:
            comment = Comment.objects.create(
                text=comment_text,
                user_id=user_id,
                auction_id=auction_id,
            )
            comment.save()

            return redirect("show_auction", auction_id=auction_id)
        except:
            error = sys.exc_info()[0]
            return render_show_auction(
                request=request,
                auction_id=auction_id,
                message=error
            )
    else:
        return HttpResponseRedirect(reverse("index"))


def categories(request):
    # Get categories to show
    categories = Category.objects.order_by("name").only("id", "name")
    print(categories)

    # Render page
    return render(request, "auctions/categories.html", {
        "categories": categories
    })
