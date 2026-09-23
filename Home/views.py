from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from DBstore.models import Product, CartItem, Purchase,Category
from .forms import RegisterForm
from django.core.paginator import Paginator

def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created.")
            return redirect("/accounts/login/")
    else:
        form = RegisterForm()
    return render(request, "Mainpage/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        user = authenticate(request, username=email, password=phone)
        if user is not None:
            login(request, user)
            messages.success(request, "Welcome to our store! Start viewing our products.")
            print("login successful")
            return redirect("/store/")
        messages.error(request, "Email or phone number is incorrect.")
    return render(request, "Mainpage/login.html")


def logout_view(request):
    logout(request)
    return redirect("/store/")



def store_view(request,category_id=None):
    if category_id == "other":
        products_list = Product.objects.filter(category__isnull=True,is_trashed=False)
        paginator=Paginator(products_list,8)
        products=paginator.get_page(request.GET.get("page"))
        return render(request, "Mainpage/store.html", {
            "is_other": True,
            "products": products,
            "categories": Category.objects.filter(is_trashed=False),   # ← add this
        })

    if category_id:
        selected_category = get_object_or_404(Category, id=category_id)
        product_list = selected_category.products.filter(is_trashed=False)
        paginator=Paginator(product_list,8)
        products = paginator.get_page(request.GET.get("page"))
        return render(request, "Mainpage/store.html", {
            "selected_category": selected_category,
            "products": products,
            "categories": Category.objects.filter(is_trashed=False)   # ← add this
        })
    
    categories = Category.objects.filter(is_trashed=False).prefetch_related("products")
    uncategorized = Product.objects.filter(category__isnull=True, is_trashed=False)
    return render(request, "Mainpage/store.html", {
        "categories": categories,
        "uncategorized": uncategorized
    })
    '''products = Product.objects.all().order_by("-id")
    return render(request, "Mainpage/store.html", {"products": products})'''

@login_required(login_url="/accounts/login/")
def add_to_cart_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        requested_qty = int(request.POST.get("quantity", 1))
    else:
        requested_qty = 1

    if requested_qty < 1:
        messages.error(request, "Quantity must be at least 1.")
        return redirect("/store/")
    elif requested_qty > product.quantity:
        messages.error(request, f"Only {product.quantity} of {product.name} available.")
        return redirect("/store/")

    item, created = CartItem.objects.get_or_create(user=request.user, product=product)
    if created:
        item.quantity = requested_qty
    else:
        item.quantity += requested_qty
    item.save()

    # Reserve the stock immediately
    product.quantity -= requested_qty
    product.save(update_fields=["quantity"])

    messages.success(request, f"Added {requested_qty} x {product.name} to your cart.")
    return redirect("/store/")


@login_required(login_url="/accounts/login/")
def view_cart(request):
    items = CartItem.objects.filter(user=request.user,product__is_trashed=False)
    total = sum(item.subtotal() for item in items)
    return render(request, "Mainpage/cart.html", {"items": items, "total": total})


@login_required(login_url="/accounts/login/")
def remove_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)

    # Give the reserved stock back
    product = item.product
    product.quantity += item.quantity
    product.save(update_fields=["quantity"])

    item.delete()
    return redirect("/cart/")

@login_required(login_url="/accounts/login/")
def update_cart_quantity(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    product = item.product

    if request.method == "POST":
        new_qty = int(request.POST.get("quantity", item.quantity))

        if new_qty < 1:
            messages.error(request, "Quantity must be at least 1.")
            return redirect("/cart/")

        diff = new_qty - item.quantity  # positive = wants more, negative = wants less

        if diff > 0 and diff > product.quantity:
            messages.error(request, f"Only {product.quantity} more {product.name} available.")
            return redirect("/cart/")

        product.quantity -= diff   # if diff negative, this correctly gives stock back
        product.save(update_fields=["quantity"])

        item.quantity = new_qty
        item.save()
        messages.success(request, f"Updated {product.name} quantity.")

    return redirect("/cart/")

@login_required(login_url="/accounts/login/")
def checkout(request):
    items = CartItem.objects.filter(user=request.user, product__is_trashed=False)
    if request.method == "POST":
        for item in items:
            product = item.product   # ← this line must exist before using "product" below

            if item.quantity > product.quantity:
                messages.error(request, f"Only {product.quantity} of {product.name} left in stock.")
                return redirect("/cart/")

            Purchase.objects.create(
                user=request.user,
                product=product,
                quantity=item.quantity,
                original_price=product.price,
                unit_price=product.offer_price,
            )
            product.quantity -= item.quantity
            product.save(update_fields=["quantity"])

        items.delete()
        messages.success(request, "Order placed! Thanks for shopping.")
        return redirect("/store/")

    total = sum(item.subtotal() for item in items)
    return render(request, "Home/cart.html", {"items": items, "total": total})

@login_required(login_url="/accounts/login/")
def purchase_history(request):
    purchases = Purchase.objects.filter(user=request.user).order_by("-purchased_at")
    return render(request, "Mainpage/history.html", {"purchases": purchases})